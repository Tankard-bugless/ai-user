from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = (
    ROOT
    / "04_workflows"
    / "runtime"
    / "workflow_runtime.py"
)
SPEC = importlib.util.spec_from_file_location(
    "workflow_runtime", RUNTIME_PATH
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
WorkflowRuntime = MODULE.WorkflowRuntime
WorkflowRuntimeError = MODULE.WorkflowRuntimeError
EXAMPLES = ROOT / "02_schemas" / "examples"


class WorkflowRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Path(self.temp_dir.name) / "runtime"
        self.runtime = WorkflowRuntime.initialize(
            self.store,
            "PROJ-DEMO-001",
            "RUN-RUNTIME-TEST-001",
            content_classification="SYNTHETIC",
        )
        self.generated = Path(self.temp_dir.name) / "generated"
        self.generated.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_generated(self, name: str, value: dict) -> Path:
        path = self.generated / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def reach_instrument_design(self) -> None:
        self.runtime.transition(
            "TASK_SUCCEEDED",
            reason="测试登记原始需求，进入 Brief 设计。",
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "research-brief.example.json"
        )
        self.runtime.submit_gate(
            "GATE_1", reason="提交合成 ResearchBrief。"
        )
        self.runtime.approve_gate(
            "GATE_1",
            EXAMPLES / "approval-record.gate1.example.json",
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "research-plan.example.json"
        )
        self.runtime.transition(
            "TASK_SUCCEEDED",
            reason="合成 ResearchPlan 已登记，进入工具设计。",
        )
        self.assertEqual(
            self.runtime.status_summary()["current_stage"],
            "INSTRUMENT_DESIGN",
        )

    def build_second_review(self) -> Path:
        review = json.loads(
            (
                EXAMPLES / "review-result.current.example.json"
            ).read_text(encoding="utf-8")
        )
        interview_ref = {
            "artifact_id": "INS-INTERVIEW-DEMO-001",
            "artifact_type": "InstrumentSpec",
            "artifact_version": "0.1.0",
        }
        review["metadata"]["artifact_id"] = "REVIEW-DEMO-INT-001"
        review["metadata"]["title"] = "示例：访谈工具质量预审"
        review["metadata"]["upstream_refs"] = [interview_ref]
        review["metadata"]["change_summary"] = (
            "为并行分支测试生成的合成通过型访谈审核。"
        )
        review["target_ref"] = interview_ref
        review["summary"]["summary_text"] = (
            "访谈工具通过合成质量预审，可以提交人工审核。"
        )
        return self.write_generated(
            "review-result.interview.example.json", review
        )

    def register_gate2_bundle(
        self, *, include_second_review: bool
    ) -> Path | None:
        self.runtime.register_artifact_file(
            EXAMPLES / "instrument-spec.survey.example.json"
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "instrument-spec.interview.example.json"
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "review-result.current.example.json"
        )
        if include_second_review:
            second = self.build_second_review()
            self.runtime.register_artifact_file(second)
            return second
        return None

    def build_gate2_approval(self) -> Path:
        approval = json.loads(
            (
                EXAMPLES / "approval-record.gate2.example.json"
            ).read_text(encoding="utf-8")
        )
        second_review_ref = {
            "artifact_id": "REVIEW-DEMO-INT-001",
            "artifact_type": "ReviewResult",
            "artifact_version": "0.1.0",
        }
        approval["metadata"]["upstream_refs"].append(
            second_review_ref
        )
        approval["reviewed_refs"].append(second_review_ref)
        approval["metadata"]["change_summary"] = (
            "合成 Gate 2 批准，精确覆盖 Plan、两份 Instrument 和两份 Review。"
        )
        return self.write_generated(
            "approval-record.gate2.runtime.json", approval
        )

    def reach_fieldwork(self) -> None:
        self.reach_instrument_design()
        self.register_gate2_bundle(include_second_review=True)
        self.runtime.submit_gate(
            "GATE_2", reason="全部并行工具已有通过型预审。"
        )
        self.runtime.approve_gate(
            "GATE_2", self.build_gate2_approval()
        )
        self.assertEqual(
            self.runtime.status_summary()["current_stage"],
            "FIELDWORK",
        )

    def test_positive_gate1_routes_to_plan_design(self) -> None:
        self.runtime.transition(
            "TASK_SUCCEEDED",
            reason="原始需求已登记。",
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "research-brief.example.json"
        )
        self.runtime.submit_gate(
            "GATE_1", reason="提交 Gate 1。"
        )
        self.runtime.approve_gate(
            "GATE_1",
            EXAMPLES / "approval-record.gate1.example.json",
        )
        summary = self.runtime.status_summary()
        self.assertEqual(summary["current_stage"], "PLAN_DESIGN")
        self.assertEqual(summary["run_status"], "ACTIVE")
        self.assertEqual(len(summary["active_approvals"]), 1)

    def test_parallel_instruments_wait_for_all_reviews(self) -> None:
        self.reach_instrument_design()
        self.register_gate2_bundle(include_second_review=False)
        with self.assertRaisesRegex(
            WorkflowRuntimeError, "缺少当前通过型 ReviewResult"
        ):
            self.runtime.submit_gate(
                "GATE_2", reason="错误地提前提交。"
            )
        self.runtime.register_artifact_file(
            self.build_second_review()
        )
        self.runtime.submit_gate(
            "GATE_2", reason="两个分支都完成审核。"
        )
        summary = self.runtime.status_summary()
        self.assertEqual(summary["current_stage"], "GATE_2_REVIEW")
        self.assertEqual(summary["run_status"], "WAITING_GATE")

    def test_adversarial_skip_gate2_is_rejected_and_audited(self) -> None:
        self.reach_instrument_design()
        self.register_gate2_bundle(include_second_review=True)
        self.runtime.submit_gate(
            "GATE_2", reason="进入 Gate 2 等待人工决定。"
        )
        with self.assertRaisesRegex(
            WorkflowRuntimeError, "非法迁移"
        ):
            self.runtime.transition(
                "TASK_SUCCEEDED",
                reason="要求跳过 Gate 2 直接发行。",
            )
        summary = self.runtime.status_summary()
        self.assertEqual(summary["current_stage"], "GATE_2_REVIEW")
        audit = (self.store / "audit.jsonl").read_text(
            encoding="utf-8"
        )
        self.assertIn("ILLEGAL_TRANSITION_REJECTED", audit)

    def test_regression_new_instrument_invalidates_downstream(self) -> None:
        self.reach_fieldwork()
        fieldwork_ref = self.runtime.register_artifact_file(
            EXAMPLES / "fieldwork-package.example.json"
        )
        old_ref = {
            "artifact_id": "INS-SURVEY-DEMO-001",
            "artifact_type": "InstrumentSpec",
            "artifact_version": "0.1.0",
        }
        instrument = json.loads(
            (
                EXAMPLES / "instrument-spec.survey.example.json"
            ).read_text(encoding="utf-8")
        )
        instrument["metadata"]["artifact_version"] = "0.2.0"
        instrument["metadata"]["updated_at"] = (
            "2026-07-27T12:00:00+08:00"
        )
        instrument["metadata"]["supersedes_ref"] = old_ref
        instrument["metadata"]["change_summary"] = (
            "合成回归测试：InstrumentSpec 产生新版本。"
        )
        new_path = self.write_generated(
            "instrument-spec.survey.v0.2.0.json", instrument
        )
        self.runtime.revise_artifact(old_ref, new_path)
        summary = self.runtime.status_summary()
        self.assertEqual(
            summary["current_stage"], "INSTRUMENT_DESIGN"
        )
        stale_keys = {
            (
                ref["artifact_id"],
                ref["artifact_type"],
                ref["artifact_version"],
            )
            for ref in summary["stale_artifacts"]
        }
        self.assertIn(
            (
                fieldwork_ref["artifact_id"],
                fieldwork_ref["artifact_type"],
                fieldwork_ref["artifact_version"],
            ),
            stale_keys,
        )
        active_approval_ids = {
            ref["artifact_id"] for ref in summary["active_approvals"]
        }
        self.assertEqual(active_approval_ids, {"APR-DEMO-G1-001"})
        self.assertNotIn("APR-DEMO-G2-001", active_approval_ids)

    def test_permission_snapshot_for_insight_agent(self) -> None:
        self.runtime.transition(
            "TASK_SUCCEEDED",
            reason="原始需求已登记。",
        )
        brief_ref = self.runtime.register_artifact_file(
            EXAMPLES / "research-brief.example.json"
        )
        task = self.runtime.create_capability_task(
            task_id="TASK-PERMISSION-001",
            capability_id="synthesize-research-insights",
            purpose="验证 CAP-05 最小权限快照。",
            input_artifact_refs=[brief_ref],
            expected_artifact_type="InsightPackage",
        )
        scope = task["permission_scope"]
        self.assertEqual(
            scope["data_access"], ["DEIDENTIFIED_RESEARCH_DATA"]
        )
        self.assertFalse(scope["external_write_allowed"])
        self.assertIn(
            "READ_CONTACT_LINKAGE",
            scope["forbidden_actions"],
        )

    def test_ai_cannot_approve_gate(self) -> None:
        self.runtime.transition(
            "TASK_SUCCEEDED",
            reason="原始需求已登记。",
        )
        self.runtime.register_artifact_file(
            EXAMPLES / "research-brief.example.json"
        )
        self.runtime.submit_gate(
            "GATE_1", reason="提交 Gate 1。"
        )
        approval = json.loads(
            (
                EXAMPLES / "approval-record.gate1.example.json"
            ).read_text(encoding="utf-8")
        )
        approval["metadata"]["artifact_id"] = "APR-DEMO-AI-001"
        approval["metadata"]["created_by"] = {
            "actor_id": "AGENT-FAKE-APPROVER",
            "actor_type": "AGENT",
            "role": "无权限审批者",
            "model_id": "demo-model",
            "capability_version": "0.1.0",
        }
        approval["reviewer"] = approval["metadata"]["created_by"]
        approval["is_ai_approval"] = True
        path = self.write_generated(
            "approval-record.ai-invalid.json", approval
        )
        with self.assertRaises(WorkflowRuntimeError):
            self.runtime.approve_gate("GATE_1", path)
        self.assertEqual(
            self.runtime.status_summary()["current_stage"],
            "GATE_1_REVIEW",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
