from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import warnings
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

warnings.filterwarnings(
    "ignore",
    message="jsonschema.RefResolver is deprecated.*",
    category=DeprecationWarning,
)
from jsonschema import Draft202012Validator, FormatChecker, RefResolver


RUNTIME_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = RUNTIME_DIR.parents[1]
SCHEMA_DIR = PROJECT_ROOT / "02_schemas"
POLICY_PATH = RUNTIME_DIR / "runtime-policy.v0.1.0.json"
PERMISSION_PATH = (
    PROJECT_ROOT
    / "01_standards"
    / "minimum-permission-matrix.v0.1.0.json"
)
REGISTRY_NAME = "registry.v0.1.0.json"
CONTROL_EVENTS = {
    "TASK_CREATED",
    "TASK_STATUS_CHANGED",
    "REGISTRY_UPDATED",
}
ARTIFACT_SCHEMA_BY_TYPE = {
    "ResearchBrief": "research-brief.schema.json",
    "ResearchPlan": "research-plan.schema.json",
    "InstrumentSpec": "instrument-spec.schema.json",
    "ReviewResult": "review-result.schema.json",
    "ApprovalRecord": "approval-record.schema.json",
    "FieldworkPackage": "fieldwork-package.schema.json",
    "InsightPackage": "insight-package.schema.json",
    "ResearchReport": "research-report.schema.json",
}
CONTROL_SCHEMA_BY_TYPE = {
    "WorkflowState": "workflow-state.schema.json",
    "TaskRecord": "task-record.schema.json",
    "HandoffRecord": "handoff-record.schema.json",
}
IDENTIFIER_RE = re.compile(r"^[A-Z][A-Z0-9_-]{2,63}$")


class WorkflowRuntimeError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_ref(
    artifact_id: str,
    artifact_type: str,
    artifact_version: str,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
    }


def ref_key(ref: dict) -> tuple[str, str, str]:
    return (
        ref["artifact_id"],
        ref["artifact_type"],
        ref["artifact_version"],
    )


def control_ref(record: dict) -> dict:
    metadata = record["metadata"]
    return {
        "record_id": metadata["record_id"],
        "record_type": metadata["record_type"],
        "record_revision": metadata["record_revision"],
    }


def system_actor() -> dict:
    return {
        "actor_id": "SYSTEM-ORCHESTRATOR",
        "actor_type": "SYSTEM",
        "role": "研究工作流状态机",
    }


class WorkflowRuntime:
    def __init__(self, store: Path):
        self.store = store.resolve()
        self.registry_path = self.store / REGISTRY_NAME
        if not self.registry_path.exists():
            raise WorkflowRuntimeError(
                f"运行目录尚未初始化：{self.registry_path}"
            )
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.permission_matrix = json.loads(
            PERMISSION_PATH.read_text(encoding="utf-8")
        )
        self.registry = json.loads(
            self.registry_path.read_text(encoding="utf-8")
        )
        self.schema_store = self._load_schema_store()
        self.transition_index = {
            (item["from_stage"], item["event_type"]): item
            for item in self.policy["transitions"]
        }

    @classmethod
    def initialize(
        cls,
        store: Path,
        project_id: str,
        run_id: str,
        *,
        content_classification: str = "REAL",
    ) -> "WorkflowRuntime":
        for value, label in [(project_id, "project_id"), (run_id, "run_id")]:
            if not IDENTIFIER_RE.match(value):
                raise WorkflowRuntimeError(
                    f"{label} 不符合标识符规则：{value}"
                )
        store = store.resolve()
        store.mkdir(parents=True, exist_ok=True)
        registry_path = store / REGISTRY_NAME
        if registry_path.exists():
            raise WorkflowRuntimeError(
                f"拒绝覆盖已存在的运行目录：{registry_path}"
            )
        timestamp = now_iso()
        registry = {
            "registry_version": "0.1.0",
            "project_id": project_id,
            "run_id": run_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "content_classification": content_classification,
            "workflow_template": json.loads(
                POLICY_PATH.read_text(encoding="utf-8")
            )["workflow_template"],
            "artifacts": [],
            "active_approval_refs": [],
            "state_revisions": [],
            "task_records": [],
            "audit_event_count": 0,
        }
        write_json_atomic(registry_path, registry)
        runtime = cls(store)
        runtime._write_state(
            current_stage="INTAKE",
            run_status="ACTIVE",
            event_type="PROJECT_CREATED",
            from_stage=None,
            reason="创建研究项目运行；尚未加载个人数据。",
            related_task_ids=[],
            related_artifact_refs=[],
        )
        return runtime

    def _load_schema_store(self) -> dict:
        store: dict = {}
        for path in SCHEMA_DIR.glob("*.schema.json"):
            schema = json.loads(path.read_text(encoding="utf-8"))
            store[schema["$id"]] = schema
            store[path.name] = schema
        return store

    def _validate(self, value: dict, schema_name: str) -> None:
        schema_path = SCHEMA_DIR / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        resolver = RefResolver(
            base_uri=schema_path.as_uri(),
            referrer=schema,
            store=self.schema_store,
        )
        errors = sorted(
            Draft202012Validator(
                schema,
                resolver=resolver,
                format_checker=FormatChecker(),
            ).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            details = "; ".join(
                f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
                for error in errors[:10]
            )
            raise WorkflowRuntimeError(
                f"{schema_name} 校验失败：{details}"
            )

    def _save_registry(self) -> None:
        self.registry["updated_at"] = now_iso()
        write_json_atomic(self.registry_path, self.registry)

    def _append_audit(self, event_type: str, details: dict) -> None:
        self.registry["audit_event_count"] += 1
        event = {
            "audit_event_id": (
                f"AUDIT-{self.registry['audit_event_count']:05d}"
            ),
            "occurred_at": now_iso(),
            "event_type": event_type,
            "project_id": self.registry["project_id"],
            "run_id": self.registry["run_id"],
            "details": details,
            "contains_personal_data": False,
        }
        audit_path = self.store / "audit.jsonl"
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def latest_state(self) -> dict:
        revisions = self.registry["state_revisions"]
        if not revisions:
            raise WorkflowRuntimeError("运行没有 WorkflowState")
        path = self.store / revisions[-1]["path"]
        return json.loads(path.read_text(encoding="utf-8"))

    def _task_summary(self) -> tuple[list[str], list[str], list[str]]:
        active_statuses = {
            "PENDING",
            "READY",
            "RUNNING",
            "WAITING_INPUT",
            "WAITING_HUMAN",
        }
        completed_statuses = {"SUCCEEDED"}
        blocked_statuses = {"FAILED", "STALE"}
        active: list[str] = []
        completed: list[str] = []
        blocked: list[str] = []
        for item in self.registry["task_records"]:
            status = item["status"]
            if status in active_statuses:
                active.append(item["task_id"])
            elif status in completed_statuses:
                completed.append(item["task_id"])
            elif status in blocked_statuses:
                blocked.append(item["task_id"])
        return sorted(active), sorted(completed), sorted(blocked)

    def _state_artifact_registry(self) -> list[dict]:
        result: list[dict] = []
        for entry in self.registry["artifacts"]:
            item = {
                "artifact_ref": entry["artifact_ref"],
                "workflow_validity": entry["workflow_validity"],
            }
            if entry.get("reason"):
                item["reason"] = entry["reason"]
            result.append(item)
        return result

    def _write_state(
        self,
        *,
        current_stage: str,
        run_status: str,
        event_type: str,
        from_stage: str | None,
        reason: str,
        related_task_ids: list[str],
        related_artifact_refs: list[dict],
        current_gate: dict | None = None,
    ) -> dict:
        previous = (
            self.latest_state()
            if self.registry["state_revisions"]
            else None
        )
        revision = len(self.registry["state_revisions"]) + 1
        timestamp = now_iso()
        record_id = f"WFS-{self.registry['run_id']}"
        if len(record_id) > 64:
            record_id = (
                "WFS-"
                + hashlib.sha256(
                    self.registry["run_id"].encode("utf-8")
                ).hexdigest()[:24].upper()
            )
        metadata = {
            "schema_version": "0.2.0",
            "record_id": record_id,
            "record_type": "WorkflowState",
            "record_revision": revision,
            "project_id": self.registry["project_id"],
            "run_id": self.registry["run_id"],
            "created_at": timestamp,
            "updated_at": timestamp,
            "created_by": system_actor(),
            "content_classification": self.registry[
                "content_classification"
            ],
            "sensitivity_level": "INTERNAL",
            "contains_personal_data": False,
            "change_summary": reason,
        }
        if previous:
            metadata["previous_record_ref"] = control_ref(previous)
        active, completed, blocked = self._task_summary()
        stale_refs = [
            entry["artifact_ref"]
            for entry in self.registry["artifacts"]
            if entry["workflow_validity"] == "STALE"
        ]
        state = {
            "metadata": metadata,
            "workflow_template": self.registry["workflow_template"],
            "current_stage": current_stage,
            "run_status": run_status,
            "active_task_ids": active,
            "completed_task_ids": completed,
            "blocked_task_ids": blocked,
            "artifact_registry": self._state_artifact_registry(),
            "approval_refs": self.registry["active_approval_refs"],
            "stale_artifact_refs": stale_refs,
            "transition": {
                "event_id": (
                    f"EVT-{revision:05d}-"
                    + hashlib.sha256(
                        f"{self.registry['run_id']}:{revision}".encode()
                    ).hexdigest()[:8].upper()
                ),
                "event_type": event_type,
                "from_stage": from_stage,
                "to_stage": current_stage,
                "triggered_by": system_actor(),
                "occurred_at": timestamp,
                "reason": reason,
                "related_task_ids": related_task_ids,
                "related_artifact_refs": related_artifact_refs,
            },
        }
        if current_gate:
            state["current_gate"] = current_gate
        self._validate(state, CONTROL_SCHEMA_BY_TYPE["WorkflowState"])
        relative_path = (
            Path("states")
            / f"{record_id}.r{revision:04d}.json"
        )
        write_json_atomic(self.store / relative_path, state)
        self.registry["state_revisions"].append(
            {
                "record_id": record_id,
                "record_revision": revision,
                "path": relative_path.as_posix(),
            }
        )
        self._save_registry()
        self._append_audit(
            "WORKFLOW_STATE_WRITTEN",
            {
                "record_id": record_id,
                "record_revision": revision,
                "current_stage": current_stage,
                "run_status": run_status,
                "transition_event": event_type,
            },
        )
        self._save_registry()
        return state

    def _control_sync(
        self,
        event_type: str,
        reason: str,
        *,
        related_task_ids: list[str] | None = None,
        related_artifact_refs: list[dict] | None = None,
    ) -> dict:
        if event_type not in CONTROL_EVENTS:
            raise WorkflowRuntimeError(
                f"不是控制自迁移事件：{event_type}"
            )
        state = self.latest_state()
        return self._write_state(
            current_stage=state["current_stage"],
            run_status=state["run_status"],
            current_gate=state.get("current_gate"),
            event_type=event_type,
            from_stage=state["current_stage"],
            reason=reason,
            related_task_ids=related_task_ids or [],
            related_artifact_refs=related_artifact_refs or [],
        )

    def _artifact_entry(self, ref: dict) -> dict | None:
        key = ref_key(ref)
        return next(
            (
                entry
                for entry in self.registry["artifacts"]
                if ref_key(entry["artifact_ref"]) == key
            ),
            None,
        )

    def _current_artifacts(
        self, artifact_type: str | None = None
    ) -> list[dict]:
        return [
            entry
            for entry in self.registry["artifacts"]
            if entry["workflow_validity"] == "CURRENT"
            and (
                artifact_type is None
                or entry["artifact_ref"]["artifact_type"] == artifact_type
            )
        ]

    def register_artifact_file(
        self,
        path: Path,
        *,
        workflow_validity: str = "CURRENT",
        reason: str = "",
        emit_state: bool = True,
    ) -> dict:
        path = path.resolve()
        value = json.loads(path.read_text(encoding="utf-8"))
        metadata = value.get("metadata", {})
        artifact_type = metadata.get("artifact_type")
        if artifact_type not in ARTIFACT_SCHEMA_BY_TYPE:
            raise WorkflowRuntimeError(
                f"不支持的正式 Artifact 类型：{artifact_type}"
            )
        self._validate(value, ARTIFACT_SCHEMA_BY_TYPE[artifact_type])
        if metadata["project_id"] != self.registry["project_id"]:
            raise WorkflowRuntimeError(
                "Artifact project_id 与运行不一致："
                f"{metadata['project_id']} != {self.registry['project_id']}"
            )
        ref = artifact_ref(
            metadata["artifact_id"],
            artifact_type,
            metadata["artifact_version"],
        )
        content_hash = sha256_file(path)
        existing = self._artifact_entry(ref)
        if existing:
            if existing["content_hash"] != content_hash:
                raise WorkflowRuntimeError(
                    f"相同 Artifact 精确版本出现不同哈希：{ref}"
                )
            if (
                existing["workflow_validity"] != workflow_validity
                or existing.get("reason", "") != reason
            ):
                existing["workflow_validity"] = workflow_validity
                existing["reason"] = reason
                self._save_registry()
                if emit_state:
                    self._control_sync(
                        "REGISTRY_UPDATED",
                        f"更新 Artifact 有效性：{ref}",
                        related_artifact_refs=[ref],
                    )
            return ref
        entry = {
            "artifact_ref": ref,
            "workflow_validity": workflow_validity,
            "reason": reason,
            "content_hash": content_hash,
            "source_path": str(path),
            "registered_at": now_iso(),
            "lifecycle_status": metadata["lifecycle_status"],
            "content_classification": metadata[
                "content_classification"
            ],
            "sensitivity_level": metadata["sensitivity_level"],
            "contains_personal_data": metadata[
                "contains_personal_data"
            ],
            "upstream_refs": metadata.get("upstream_refs", []),
        }
        if artifact_type == "ReviewResult":
            entry["review_target_ref"] = value["target_ref"]
            entry["review_outcome"] = value["summary"]["outcome"]
            entry["review_is_formal_approval"] = value[
                "is_formal_approval"
            ]
        if artifact_type == "ApprovalRecord":
            entry["gate_id"] = value["gate_id"]
            entry["approval_status"] = value["status"]
            entry["reviewed_refs"] = value["reviewed_refs"]
            entry["primary_target_ref"] = value[
                "primary_target_ref"
            ]
            entry["is_ai_approval"] = value["is_ai_approval"]
        if artifact_type == "FieldworkPackage":
            entry["dataset_status"] = value["data_quality"][
                "dataset_status"
            ]
        self.registry["artifacts"].append(entry)
        self._save_registry()
        if emit_state:
            self._control_sync(
                "REGISTRY_UPDATED",
                (
                    f"登记 Artifact {ref['artifact_type']} "
                    f"{ref['artifact_id']}@{ref['artifact_version']}。"
                ),
                related_artifact_refs=[ref],
            )
        return ref

    def _passing_review_for(self, target_ref: dict) -> dict | None:
        target_key = ref_key(target_ref)
        for entry in self._current_artifacts("ReviewResult"):
            if (
                ref_key(entry["review_target_ref"]) == target_key
                and entry["review_outcome"]
                in {"PASS", "PASS_WITH_WARNINGS"}
                and entry["review_is_formal_approval"] is False
            ):
                return entry
        return None

    def _gate_expected_refs(self, gate_id: str) -> list[dict]:
        gate = self.policy["gates"][gate_id]
        expected: list[dict] = []
        for artifact_type in gate[
            "required_current_artifact_types"
        ]:
            entries = self._current_artifacts(artifact_type)
            if not entries:
                raise WorkflowRuntimeError(
                    f"{gate_id} 缺少 CURRENT {artifact_type}"
                )
            expected.extend(entry["artifact_ref"] for entry in entries)
        for artifact_type in gate["passing_review_required_for"]:
            for entry in self._current_artifacts(artifact_type):
                review = self._passing_review_for(entry["artifact_ref"])
                if not review:
                    raise WorkflowRuntimeError(
                        f"{gate_id} 的 {entry['artifact_ref']} 缺少当前通过型 ReviewResult"
                    )
                expected.append(review["artifact_ref"])
        unique = {ref_key(ref): ref for ref in expected}
        return list(unique.values())

    def _check_transition_preconditions(
        self, stage: str, event_type: str
    ) -> None:
        if event_type == "TASK_SUCCEEDED":
            required_by_stage = {
                "PLAN_DESIGN": "ResearchPlan",
                "FIELDWORK": "FieldworkPackage",
            }
            required = required_by_stage.get(stage)
            if required and not self._current_artifacts(required):
                raise WorkflowRuntimeError(
                    f"{stage} 完成前缺少 CURRENT {required}"
                )
            if stage == "FIELDWORK":
                statuses = {
                    entry.get("dataset_status")
                    for entry in self._current_artifacts(
                        "FieldworkPackage"
                    )
                }
                if not statuses <= {
                    "ANALYSIS_READY",
                    "ANALYSIS_READY_WITH_LIMITS",
                }:
                    raise WorkflowRuntimeError(
                        "FieldworkPackage 数据状态未达到分析条件"
                    )
        if event_type == "GATE_SUBMITTED":
            gate_id = {
                "BRIEF_DESIGN": "GATE_1",
                "INSTRUMENT_DESIGN": "GATE_2",
                "ANALYSIS": "GATE_3",
                "REPORT_COMPOSITION": "GATE_4",
            }.get(stage)
            if not gate_id:
                raise WorkflowRuntimeError(
                    f"{stage} 不能提交 Gate"
                )
            self._gate_expected_refs(gate_id)

    def transition(
        self,
        event_type: str,
        *,
        reason: str,
        related_task_ids: list[str] | None = None,
        related_artifact_refs: list[dict] | None = None,
    ) -> dict:
        state = self.latest_state()
        key = (state["current_stage"], event_type)
        if key not in self.transition_index:
            self._append_audit(
                "ILLEGAL_TRANSITION_REJECTED",
                {
                    "from_stage": state["current_stage"],
                    "event_type": event_type,
                    "reason": reason,
                },
            )
            self._save_registry()
            raise WorkflowRuntimeError(
                f"非法迁移：{state['current_stage']} + {event_type}"
            )
        rule = self.transition_index[key]
        self._check_transition_preconditions(
            state["current_stage"], event_type
        )
        current_gate = None
        if rule.get("gate_id") and event_type == "GATE_SUBMITTED":
            current_gate = {
                "gate_id": rule["gate_id"],
                "status": "PENDING",
                "required_role": "经组织授权的 Gate 审批人",
            }
        return self._write_state(
            current_stage=rule["to_stage"],
            run_status=rule["run_status"],
            current_gate=current_gate,
            event_type=event_type,
            from_stage=state["current_stage"],
            reason=reason,
            related_task_ids=related_task_ids or [],
            related_artifact_refs=related_artifact_refs or [],
        )

    def submit_gate(self, gate_id: str, *, reason: str) -> dict:
        state = self.latest_state()
        expected_stage = {
            "GATE_1": "BRIEF_DESIGN",
            "GATE_2": "INSTRUMENT_DESIGN",
            "GATE_3": "ANALYSIS",
            "GATE_4": "REPORT_COMPOSITION",
        }[gate_id]
        if state["current_stage"] != expected_stage:
            raise WorkflowRuntimeError(
                f"{gate_id} 只能从 {expected_stage} 提交"
            )
        refs = self._gate_expected_refs(gate_id)
        return self.transition(
            "GATE_SUBMITTED",
            reason=reason,
            related_artifact_refs=refs,
        )

    def _verify_approval(
        self, value: dict, gate_id: str
    ) -> list[dict]:
        self._validate(
            value, ARTIFACT_SCHEMA_BY_TYPE["ApprovalRecord"]
        )
        metadata = value["metadata"]
        if metadata["project_id"] != self.registry["project_id"]:
            raise WorkflowRuntimeError(
                "ApprovalRecord project_id 与运行不一致"
            )
        if value["gate_id"] != gate_id:
            raise WorkflowRuntimeError("ApprovalRecord gate_id 不匹配")
        if value["status"] != "APPROVED":
            raise WorkflowRuntimeError("Gate 只能接受 APPROVED 记录")
        if value["reviewer"]["actor_type"] != "HUMAN":
            raise WorkflowRuntimeError("Gate 审批人必须是 HUMAN")
        if value["is_ai_approval"] is not False:
            raise WorkflowRuntimeError("AI 不能构成正式批准")
        if not value["attestations"]["authorized_to_decide"]:
            raise WorkflowRuntimeError("审批人未声明有权决定")
        if metadata["lifecycle_status"] != "FROZEN":
            raise WorkflowRuntimeError(
                "已批准 ApprovalRecord 必须为 FROZEN"
            )
        expected = self._gate_expected_refs(gate_id)
        expected_keys = {ref_key(ref) for ref in expected}
        reviewed_keys = {
            ref_key(ref) for ref in value["reviewed_refs"]
        }
        if reviewed_keys != expected_keys:
            missing = expected_keys - reviewed_keys
            extra = reviewed_keys - expected_keys
            raise WorkflowRuntimeError(
                f"{gate_id} 审批包不是当前精确组合；"
                f"missing={sorted(missing)}, extra={sorted(extra)}"
            )
        primary_type = self.policy["gates"][gate_id][
            "primary_artifact_type"
        ]
        if (
            value["primary_target_ref"]["artifact_type"]
            != primary_type
            or ref_key(value["primary_target_ref"])
            not in expected_keys
        ):
            raise WorkflowRuntimeError(
                f"{gate_id} primary_target_ref 不匹配"
            )
        return expected

    def approve_gate(
        self, gate_id: str, approval_path: Path
    ) -> dict:
        state = self.latest_state()
        if (
            state["current_stage"]
            != self.policy["gates"][gate_id]["review_stage"]
            or state.get("current_gate", {}).get("gate_id")
            != gate_id
        ):
            raise WorkflowRuntimeError(
                f"当前不处于 {gate_id} 待审状态"
            )
        value = json.loads(
            approval_path.resolve().read_text(encoding="utf-8")
        )
        expected = self._verify_approval(value, gate_id)
        approval_ref = self.register_artifact_file(
            approval_path, emit_state=False
        )
        if ref_key(approval_ref) not in {
            ref_key(ref)
            for ref in self.registry["active_approval_refs"]
        }:
            self.registry["active_approval_refs"].append(approval_ref)
        self._save_registry()
        return self.transition(
            "GATE_APPROVED",
            reason=f"{gate_id} 真实人工 ApprovalRecord 已验证并应用。",
            related_artifact_refs=[*expected, approval_ref],
        )

    def _permission_principal(self, principal_id: str) -> dict:
        principal = next(
            (
                item
                for item in self.permission_matrix["principals"]
                if item["principal_id"] == principal_id
            ),
            None,
        )
        if not principal:
            raise WorkflowRuntimeError(
                f"权限矩阵不存在 principal：{principal_id}"
            )
        return principal

    def create_task(
        self,
        *,
        task_id: str,
        task_kind: str,
        purpose: str,
        target_type: str,
        target_id: str,
        principal_id: str,
        input_artifact_refs: list[dict],
        expected_output: dict,
        dependency_task_ids: list[str] | None = None,
        max_attempts: int = 2,
    ) -> dict:
        if not IDENTIFIER_RE.match(task_id):
            raise WorkflowRuntimeError(
                f"task_id 不符合标识符规则：{task_id}"
            )
        if any(
            item["task_id"] == task_id
            for item in self.registry["task_records"]
        ):
            raise WorkflowRuntimeError(f"任务已存在：{task_id}")
        principal = self._permission_principal(principal_id)
        for ref in input_artifact_refs:
            entry = self._artifact_entry(ref)
            if not entry or entry["workflow_validity"] != "CURRENT":
                raise WorkflowRuntimeError(
                    f"任务输入不是 CURRENT Artifact：{ref}"
                )
            if (
                entry["contains_personal_data"]
                and principal_id
                not in {"HUMAN-DATA-STEWARD", "SERVICE-FIELDWORK"}
            ):
                raise WorkflowRuntimeError(
                    f"{principal_id} 无权读取含个人数据 Artifact"
                )
        capability = (
            target_id if target_type == "CAPABILITY" else None
        )
        data_access = (
            self.policy["task_data_access"].get(
                capability, ["NO_PERSONAL_DATA"]
            )
        )
        allowed_actions = [
            "READ_CONTROL_RECORD",
            "CREATE_CONTROL_RECORD",
        ]
        if input_artifact_refs:
            allowed_actions.append("READ_ARTIFACT")
        if expected_output["output_kind"] == "ARTIFACT":
            allowed_actions.append("CREATE_ARTIFACT_DRAFT")
        timestamp = now_iso()
        state = self.latest_state()
        idempotency_material = {
            "project_id": self.registry["project_id"],
            "target_id": target_id,
            "purpose": purpose,
            "inputs": sorted(ref_key(ref) for ref in input_artifact_refs),
        }
        idempotency_key = hashlib.sha256(
            json.dumps(
                idempotency_material,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        task = {
            "metadata": {
                "schema_version": "0.1.0",
                "record_id": task_id,
                "record_type": "TaskRecord",
                "record_revision": 1,
                "project_id": self.registry["project_id"],
                "run_id": self.registry["run_id"],
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": system_actor(),
                "content_classification": self.registry[
                    "content_classification"
                ],
                "sensitivity_level": "INTERNAL",
                "contains_personal_data": False,
                "change_summary": "创建最小权限任务。",
            },
            "state_ref": control_ref(state),
            "task_kind": task_kind,
            "purpose": purpose,
            "status": "READY",
            "target": {
                "target_type": target_type,
                "target_id": target_id,
            },
            "idempotency_key": idempotency_key,
            "attempt": 1,
            "max_attempts": max_attempts,
            "dependency_task_ids": dependency_task_ids or [],
            "input_artifact_refs": input_artifact_refs,
            "input_record_refs": [control_ref(state)],
            "expected_output": expected_output,
            "output_artifact_refs": [],
            "output_record_refs": [],
            "external_output_refs": [],
            "entry_conditions": [
                "全部输入 Artifact 为 CURRENT 精确版本。",
                "权限快照与最小权限矩阵一致。",
            ],
            "completion_criteria": [
                "输出满足 expected_output 契约。",
                "不得执行 forbidden_actions。",
            ],
            "permission_scope": {
                "data_access": data_access,
                "allowed_actions": sorted(set(allowed_actions)),
                "forbidden_actions": principal["prohibitions"],
                "external_write_allowed": False,
                "human_approval_required": (
                    task_kind == "HUMAN_GATE"
                ),
            },
        }
        self._validate(task, CONTROL_SCHEMA_BY_TYPE["TaskRecord"])
        relative_path = (
            Path("tasks") / f"{task_id}.r0001.json"
        )
        write_json_atomic(self.store / relative_path, task)
        self.registry["task_records"].append(
            {
                "task_id": task_id,
                "latest_revision": 1,
                "status": "READY",
                "path": relative_path.as_posix(),
            }
        )
        self._save_registry()
        self._control_sync(
            "TASK_CREATED",
            f"创建任务 {task_id}，权限主体 {principal_id}。",
            related_task_ids=[task_id],
            related_artifact_refs=input_artifact_refs,
        )
        return task

    def create_capability_task(
        self,
        *,
        task_id: str,
        capability_id: str,
        purpose: str,
        input_artifact_refs: list[dict],
        expected_artifact_type: str,
    ) -> dict:
        principal_id = self.policy["capability_principal_map"].get(
            capability_id
        )
        if not principal_id:
            raise WorkflowRuntimeError(
                f"未知 capability_id：{capability_id}"
            )
        schema_name = ARTIFACT_SCHEMA_BY_TYPE[
            expected_artifact_type
        ]
        schema_uri = json.loads(
            (SCHEMA_DIR / schema_name).read_text(encoding="utf-8")
        )["$id"]
        return self.create_task(
            task_id=task_id,
            task_kind="EXPERT",
            purpose=purpose,
            target_type="CAPABILITY",
            target_id=capability_id,
            principal_id=principal_id,
            input_artifact_refs=input_artifact_refs,
            expected_output={
                "output_kind": "ARTIFACT",
                "artifact_type": expected_artifact_type,
                "schema_uri": schema_uri,
                "cardinality": "SINGLE",
            },
        )

    def _task_registry_entry(self, task_id: str) -> dict:
        entry = next(
            (
                item
                for item in self.registry["task_records"]
                if item["task_id"] == task_id
            ),
            None,
        )
        if not entry:
            raise WorkflowRuntimeError(f"未知任务：{task_id}")
        return entry

    def _latest_task(self, task_id: str) -> dict:
        entry = self._task_registry_entry(task_id)
        return json.loads(
            (self.store / entry["path"]).read_text(encoding="utf-8")
        )

    def complete_task(
        self,
        task_id: str,
        *,
        output_artifact_refs: list[dict],
        completion_summary: str,
        advance_main_path: bool,
    ) -> dict:
        registry_entry = self._task_registry_entry(task_id)
        previous = self._latest_task(task_id)
        if previous["status"] not in {
            "READY",
            "RUNNING",
            "WAITING_INPUT",
        }:
            raise WorkflowRuntimeError(
                f"任务当前状态不能完成：{previous['status']}"
            )
        for ref in output_artifact_refs:
            entry = self._artifact_entry(ref)
            if not entry or entry["workflow_validity"] != "CURRENT":
                raise WorkflowRuntimeError(
                    f"任务输出未登记为 CURRENT：{ref}"
                )
        revision = previous["metadata"]["record_revision"] + 1
        timestamp = now_iso()
        task = deepcopy(previous)
        task["metadata"]["record_revision"] = revision
        task["metadata"]["previous_record_ref"] = control_ref(previous)
        task["metadata"]["created_at"] = timestamp
        task["metadata"]["updated_at"] = timestamp
        task["metadata"]["change_summary"] = completion_summary
        task["status"] = "SUCCEEDED"
        task["started_at"] = previous.get("started_at", timestamp)
        task["completed_at"] = timestamp
        task["completion_summary"] = completion_summary
        task["output_artifact_refs"] = output_artifact_refs
        self._validate(task, CONTROL_SCHEMA_BY_TYPE["TaskRecord"])
        relative_path = (
            Path("tasks")
            / f"{task_id}.r{revision:04d}.json"
        )
        write_json_atomic(self.store / relative_path, task)
        registry_entry.update(
            {
                "latest_revision": revision,
                "status": "SUCCEEDED",
                "path": relative_path.as_posix(),
            }
        )
        self._save_registry()
        if advance_main_path:
            self.transition(
                "TASK_SUCCEEDED",
                reason=completion_summary,
                related_task_ids=[task_id],
                related_artifact_refs=output_artifact_refs,
            )
        else:
            self._control_sync(
                "TASK_STATUS_CHANGED",
                completion_summary,
                related_task_ids=[task_id],
                related_artifact_refs=output_artifact_refs,
            )
        return task

    def _mark_task_stale(
        self, task_entry: dict, invalidated_keys: set[tuple]
    ) -> None:
        previous = self._latest_task(task_entry["task_id"])
        input_keys = {
            ref_key(ref) for ref in previous["input_artifact_refs"]
        }
        if not input_keys & invalidated_keys:
            return
        if previous["status"] in {"CANCELLED", "STALE"}:
            return
        revision = previous["metadata"]["record_revision"] + 1
        timestamp = now_iso()
        task = deepcopy(previous)
        task["metadata"]["record_revision"] = revision
        task["metadata"]["previous_record_ref"] = control_ref(previous)
        task["metadata"]["created_at"] = timestamp
        task["metadata"]["updated_at"] = timestamp
        task["metadata"]["change_summary"] = (
            "上游 Artifact 新版本使任务失效。"
        )
        task["status"] = "STALE"
        relative_path = (
            Path("tasks")
            / f"{task_entry['task_id']}.r{revision:04d}.json"
        )
        self._validate(task, CONTROL_SCHEMA_BY_TYPE["TaskRecord"])
        write_json_atomic(self.store / relative_path, task)
        task_entry.update(
            {
                "latest_revision": revision,
                "status": "STALE",
                "path": relative_path.as_posix(),
            }
        )

    def revise_artifact(
        self, old_ref: dict, new_artifact_path: Path
    ) -> dict:
        old_entry = self._artifact_entry(old_ref)
        if not old_entry or old_entry["workflow_validity"] != "CURRENT":
            raise WorkflowRuntimeError(
                f"待替代 Artifact 不是 CURRENT：{old_ref}"
            )
        new_ref = self.register_artifact_file(
            new_artifact_path, emit_state=False
        )
        if (
            new_ref["artifact_id"] != old_ref["artifact_id"]
            or new_ref["artifact_type"] != old_ref["artifact_type"]
            or new_ref["artifact_version"]
            == old_ref["artifact_version"]
        ):
            raise WorkflowRuntimeError(
                "新版本必须保持 artifact_id/type 且 version 变化"
            )
        old_entry["workflow_validity"] = "SUPERSEDED"
        old_entry["reason"] = (
            f"被 {new_ref['artifact_version']} 替代。"
        )
        invalidated_keys: set[tuple] = {ref_key(old_ref)}
        changed = True
        while changed:
            changed = False
            for entry in self.registry["artifacts"]:
                if entry["workflow_validity"] != "CURRENT":
                    continue
                dependency_keys = {
                    ref_key(ref)
                    for ref in (
                        entry.get("upstream_refs", [])
                        + entry.get("reviewed_refs", [])
                    )
                }
                if dependency_keys & invalidated_keys:
                    entry["workflow_validity"] = "STALE"
                    entry["reason"] = (
                        "上游精确版本已变化，需要重新生成或审核。"
                    )
                    invalidated_keys.add(
                        ref_key(entry["artifact_ref"])
                    )
                    changed = True
        for task_entry in self.registry["task_records"]:
            self._mark_task_stale(task_entry, invalidated_keys)
        self.registry["active_approval_refs"] = [
            ref
            for ref in self.registry["active_approval_refs"]
            if ref_key(ref) not in invalidated_keys
        ]
        self._save_registry()
        return_stage = self.policy[
            "return_stage_by_artifact_type"
        ][old_ref["artifact_type"]]
        state = self.latest_state()
        return self._write_state(
            current_stage=return_stage,
            run_status="ACTIVE",
            event_type="UPSTREAM_REVISED",
            from_stage=state["current_stage"],
            reason=(
                f"{old_ref['artifact_type']} 出现新版本；"
                "依赖旧版本的产物、任务和批准已标记 stale。"
            ),
            related_task_ids=[],
            related_artifact_refs=[old_ref, new_ref],
        )

    def status_summary(self) -> dict:
        state = self.latest_state()
        return {
            "project_id": self.registry["project_id"],
            "run_id": self.registry["run_id"],
            "current_stage": state["current_stage"],
            "run_status": state["run_status"],
            "current_gate": state.get("current_gate"),
            "state_revision": state["metadata"]["record_revision"],
            "current_artifacts": [
                entry["artifact_ref"]
                for entry in self._current_artifacts()
            ],
            "stale_artifacts": [
                entry["artifact_ref"]
                for entry in self.registry["artifacts"]
                if entry["workflow_validity"] == "STALE"
            ],
            "active_approvals": self.registry[
                "active_approval_refs"
            ],
            "tasks": self.registry["task_records"],
        }


def parse_ref(text: str) -> dict:
    parts = text.split("@")
    if len(parts) != 2 or ":" not in parts[0]:
        raise argparse.ArgumentTypeError(
            "引用格式必须为 ArtifactType:artifact_id@version"
        )
    artifact_type, artifact_id = parts[0].split(":", 1)
    return artifact_ref(artifact_id, artifact_type, parts[1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="研究总控最小运行时。"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True
    )
    init = subparsers.add_parser("init")
    init.add_argument("--store", type=Path, required=True)
    init.add_argument("--project-id", required=True)
    init.add_argument("--run-id", required=True)

    register = subparsers.add_parser("register")
    register.add_argument("--store", type=Path, required=True)
    register.add_argument("--artifact", type=Path, required=True)
    register.add_argument(
        "--validity",
        choices=["CURRENT", "STALE", "SUPERSEDED"],
        default="CURRENT",
    )
    register.add_argument("--reason", default="")

    transition = subparsers.add_parser("transition")
    transition.add_argument("--store", type=Path, required=True)
    transition.add_argument("--event", required=True)
    transition.add_argument("--reason", required=True)

    submit = subparsers.add_parser("submit-gate")
    submit.add_argument("--store", type=Path, required=True)
    submit.add_argument(
        "--gate",
        choices=["GATE_1", "GATE_2", "GATE_3", "GATE_4"],
        required=True,
    )
    submit.add_argument("--reason", required=True)

    approve = subparsers.add_parser("approve-gate")
    approve.add_argument("--store", type=Path, required=True)
    approve.add_argument(
        "--gate",
        choices=["GATE_1", "GATE_2", "GATE_3", "GATE_4"],
        required=True,
    )
    approve.add_argument("--approval", type=Path, required=True)

    revise = subparsers.add_parser("revise")
    revise.add_argument("--store", type=Path, required=True)
    revise.add_argument("--old-ref", type=parse_ref, required=True)
    revise.add_argument("--new-artifact", type=Path, required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--store", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            runtime = WorkflowRuntime.initialize(
                args.store, args.project_id, args.run_id
            )
            result = runtime.status_summary()
        else:
            runtime = WorkflowRuntime(args.store)
            if args.command == "register":
                result = runtime.register_artifact_file(
                    args.artifact,
                    workflow_validity=args.validity,
                    reason=args.reason,
                )
            elif args.command == "transition":
                result = runtime.transition(
                    args.event, reason=args.reason
                )
            elif args.command == "submit-gate":
                result = runtime.submit_gate(
                    args.gate, reason=args.reason
                )
            elif args.command == "approve-gate":
                result = runtime.approve_gate(
                    args.gate, args.approval
                )
            elif args.command == "revise":
                result = runtime.revise_artifact(
                    args.old_ref, args.new_artifact
                )
            elif args.command == "status":
                result = runtime.status_summary()
            else:
                raise WorkflowRuntimeError(
                    f"未知命令：{args.command}"
                )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowRuntimeError, FileNotFoundError, json.JSONDecodeError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
