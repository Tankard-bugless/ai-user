from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="jsonschema.RefResolver is deprecated.*",
    category=DeprecationWarning,
)
from jsonschema import Draft202012Validator, FormatChecker, RefResolver


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "02_schemas"
CASE_DIR = ROOT / "05_cases" / "养老目标基金购买者研究"
FORMAL_DIR = CASE_DIR / "formal_artifacts"
RUNTIME_STORE = FORMAL_DIR / "runtime"
EVALUATION_DIR = ROOT / "07_evaluations"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_python(relative_path: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / relative_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(
            f"{relative_path} failed\n{result.stdout}\n{result.stderr}"
        )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


def load_schema_store() -> dict:
    store: dict = {}
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        store[schema["$id"]] = schema
        store[path.name] = schema
    return store


def validate_instance(
    instance_path: Path, schema_name: str, store: dict
) -> dict:
    schema_path = SCHEMA_DIR / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(instance_path.read_text(encoding="utf-8"))
    resolver = RefResolver(
        base_uri=schema_path.as_uri(),
        referrer=schema,
        store=store,
    )
    errors = sorted(
        Draft202012Validator(
            schema,
            resolver=resolver,
            format_checker=FormatChecker(),
        ).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "\n".join(
            f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in errors[:20]
        )
        raise RuntimeError(f"{instance_path.name} schema failure\n{details}")
    print(f"PASS real artifact schema: {instance_path.name}")
    return instance


def validate_cross_artifact(
    fieldwork: dict, insight: dict, report: dict
) -> None:
    if fieldwork["metadata"]["lifecycle_status"] != "DRAFT":
        raise RuntimeError("historical FieldworkPackage must remain DRAFT")
    if "gate_2_approval_ref" in fieldwork:
        raise RuntimeError("historical FieldworkPackage must not invent Gate 2")
    if fieldwork["gate_2_governance_gap"]["status"] != "NOT_RECORDED":
        raise RuntimeError("Gate 2 gap status mismatch")
    if report["metadata"]["lifecycle_status"] != "DRAFT":
        raise RuntimeError("historical ResearchReport must remain DRAFT")
    if "gate_3_approval_ref" in report:
        raise RuntimeError("historical ResearchReport must not invent Gate 3")
    if report["gate_3_governance_gap"]["status"] != "NOT_RECORDED":
        raise RuntimeError("Gate 3 gap status mismatch")

    source_ids = {item["source_id"] for item in fieldwork["source_records"]}
    evidence_ids = {item["evidence_id"] for item in insight["evidence_units"]}
    finding_ids = {item["finding_id"] for item in insight["findings"]}
    insight_ids = {item["insight_id"] for item in insight["insights"]}
    recommendation_ids = {
        item["recommendation_id"] for item in insight["recommendations"]
    }
    for evidence in insight["evidence_units"]:
        if evidence["source_id"] not in source_ids:
            raise RuntimeError(
                f"{evidence['evidence_id']} references unknown source"
            )
    for finding in insight["findings"]:
        referenced = set(finding["supporting_evidence_ids"]) | set(
            finding["negative_case_evidence_ids"]
        )
        if not referenced <= evidence_ids:
            raise RuntimeError(
                f"{finding['finding_id']} references unknown evidence"
            )
    for item in insight["insights"]:
        if not set(item["source_finding_ids"]) <= finding_ids:
            raise RuntimeError(
                f"{item['insight_id']} references unknown finding"
            )
    for item in insight["recommendations"]:
        if not set(item["source_insight_ids"]) <= insight_ids:
            raise RuntimeError(
                f"{item['recommendation_id']} references unknown insight"
            )
    if {
        item["finding_id"] for item in report["finding_presentations"]
    } != finding_ids:
        raise RuntimeError("report finding coverage mismatch")
    if {
        item["insight_id"] for item in report["insight_presentations"]
    } != insight_ids:
        raise RuntimeError("report insight coverage mismatch")
    if {
        item["recommendation_id"]
        for item in report["recommendation_presentations"]
    } != recommendation_ids:
        raise RuntimeError("report recommendation coverage mismatch")
    print("PASS real artifact references and governance boundaries")


def validate_manifest_and_data(
    manifest_name: str = "artifact-manifest.v0.1.0.json",
) -> None:
    manifest = json.loads(
        (FORMAL_DIR / manifest_name).read_text(encoding="utf-8")
    )
    for item in manifest["outputs"]:
        path = CASE_DIR / item["path"]
        if not path.exists():
            raise RuntimeError(f"manifest output missing: {path}")
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"manifest hash mismatch: {path}")
        if path.stat().st_size != item["size_bytes"]:
            raise RuntimeError(f"manifest size mismatch: {path}")

    normalized_path = (
        FORMAL_DIR / "data" / "normalized-responses.v0.1.0.csv"
    )
    quality_path = FORMAL_DIR / "data" / "response-quality.v0.1.0.csv"
    with normalized_path.open("r", encoding="utf-8-sig", newline="") as handle:
        normalized_rows = list(csv.DictReader(handle))
    with quality_path.open("r", encoding="utf-8-sig", newline="") as handle:
        quality_rows = list(csv.DictReader(handle))
    if len(normalized_rows) != 200 or len(quality_rows) != 200:
        raise RuntimeError("normalized/quality row count must both equal 200")
    forbidden_columns = {
        "IP",
        "UA",
        "省份",
        "城市",
        "地区",
        "经纬度",
        "自定义字段",
    }
    observed_columns = set(normalized_rows[0])
    leaked = forbidden_columns & observed_columns
    if leaked:
        raise RuntimeError(f"platform metadata leaked: {sorted(leaked)}")
    review_required = sum(
        row["formal_response_status"] == "REVIEW_REQUIRED"
        for row in quality_rows
    )
    if review_required != 100:
        raise RuntimeError(
            f"expected 100 REVIEW_REQUIRED, observed {review_required}"
        )
    print(
        f"PASS {manifest_name} hashes, 200-row data and metadata exclusion"
    )


def validate_permissions() -> None:
    path = (
        ROOT
        / "01_standards"
        / "minimum-permission-matrix.v0.1.0.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    if value["default_policy"] != "DENY":
        raise RuntimeError("permission matrix must default DENY")
    principal_ids = {
        principal["principal_id"] for principal in value["principals"]
    }
    required = {
        "CAP-01",
        "CAP-02",
        "CAP-03",
        "CAP-04",
        "CAP-05",
        "CAP-06",
        "CTRL-01",
        "HUMAN-GATE-APPROVER",
        "HUMAN-DATA-STEWARD",
    }
    if not required <= principal_ids:
        raise RuntimeError(
            f"permission principals missing {sorted(required - principal_ids)}"
        )
    for principal in value["principals"]:
        if not principal["grants"] or not principal["prohibitions"]:
            raise RuntimeError(
                f"{principal['principal_id']} lacks grants/prohibitions"
            )
    print("PASS minimum permission matrix")


def validate_no_fabricated_approvals() -> None:
    fabricated = []
    for gate in (2, 3, 4):
        fabricated.extend(
            CASE_DIR.glob(f"approval-record.gate{gate}*.json")
        )
        fabricated.extend(
            FORMAL_DIR.glob(f"approval-record.gate{gate}*.json")
        )
    if fabricated:
        raise RuntimeError(
            "unexpected historical approval files: "
            + ", ".join(str(path) for path in fabricated)
        )
    print("PASS no fabricated Gate 2/3/4 ApprovalRecord")


def validate_historical_runtime(store: dict) -> None:
    registry_path = RUNTIME_STORE / "registry.v0.1.0.json"
    if not registry_path.exists():
        raise RuntimeError("historical runtime registry is missing")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry["project_id"] != "PROJ-OTF-001":
        raise RuntimeError("historical runtime project_id mismatch")

    states = []
    for item in registry["state_revisions"]:
        path = RUNTIME_STORE / item["path"]
        state = validate_instance(
            path, "workflow-state.schema.json", store
        )
        states.append(state)
    if not states:
        raise RuntimeError("historical runtime has no WorkflowState")
    for previous, current in zip(states, states[1:]):
        expected_previous = {
            "record_id": previous["metadata"]["record_id"],
            "record_type": previous["metadata"]["record_type"],
            "record_revision": previous["metadata"]["record_revision"],
        }
        if (
            current["metadata"].get("previous_record_ref")
            != expected_previous
        ):
            raise RuntimeError("WorkflowState revision chain is broken")
    latest = states[-1]
    if (
        latest["current_stage"] != "GATE_2_REVIEW"
        or latest["run_status"] != "WAITING_GATE"
        or latest.get("current_gate", {}).get("gate_id") != "GATE_2"
    ):
        raise RuntimeError(
            "historical runtime must stop at pending Gate 2"
        )

    for task_path in sorted(
        (RUNTIME_STORE / "tasks").glob("*.json")
    ):
        validate_instance(task_path, "task-record.schema.json", store)

    active_approval_ids = {
        ref["artifact_id"] for ref in registry["active_approval_refs"]
    }
    if active_approval_ids != {"APR-OTF-G1-002"}:
        raise RuntimeError(
            "historical runtime may keep only the real Gate 1 approval"
        )
    approval_gates = {
        entry.get("gate_id")
        for entry in registry["artifacts"]
        if entry["artifact_ref"]["artifact_type"] == "ApprovalRecord"
    }
    if approval_gates != {"GATE_1"}:
        raise RuntimeError(
            "historical runtime contains retrospective gate approval"
        )

    stale_types = {
        entry["artifact_ref"]["artifact_type"]
        for entry in registry["artifacts"]
        if entry["workflow_validity"] == "STALE"
    }
    if stale_types != {
        "FieldworkPackage",
        "InsightPackage",
        "ResearchReport",
    }:
        raise RuntimeError(
            f"historical stale artifact set mismatch: {stale_types}"
        )
    if any(
        entry["contains_personal_data"]
        for entry in registry["artifacts"]
    ):
        raise RuntimeError(
            "historical runtime registry must not load personal data"
        )

    audit_path = RUNTIME_STORE / "audit.jsonl"
    audit_lines = [
        line
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(audit_lines) != registry["audit_event_count"]:
        raise RuntimeError("runtime audit event count mismatch")
    for line in audit_lines:
        json.loads(line)
    print(
        "PASS historical runtime: real Gate 1 retained, "
        "Gate 2 pending, downstream artifacts stale"
    )


def validate_blind_test_materials() -> None:
    fixture_suite = json.loads(
        (
            EVALUATION_DIR
            / "fixtures"
            / "capability-contract-fixtures.v0.2.0.json"
        ).read_text(encoding="utf-8")
    )
    blind_suite = json.loads(
        (
            EVALUATION_DIR
            / "fixtures"
            / "blind-test-packets.v0.2.0.json"
        ).read_text(encoding="utf-8")
    )
    fixture_ids = {
        item["fixture_id"] for item in fixture_suite["fixtures"]
    }
    packets = blind_suite["packets"]
    packet_ids = {item["fixture_id"] for item in packets}
    if len(packets) != 39 or packet_ids != fixture_ids:
        raise RuntimeError(
            "blind test packet coverage does not match 39 fixtures"
        )
    allowed_fields = {
        "fixture_id",
        "capability_id",
        "capability_version",
        "capability_card_path",
        "input_summary",
    }
    forbidden_answer_fields = {
        "expected_output_artifact",
        "expected_route",
        "expected_decision",
        "required_behaviors",
        "forbidden_behaviors",
    }
    for packet in packets:
        if set(packet) != allowed_fields:
            raise RuntimeError(
                f"{packet.get('fixture_id')}: blind packet field drift"
            )
        if set(packet) & forbidden_answer_fields:
            raise RuntimeError(
                f"{packet['fixture_id']}: expected answer leaked"
            )
        card_path = ROOT / packet["capability_card_path"]
        if not card_path.exists():
            raise RuntimeError(
                f"{packet['fixture_id']}: capability card missing"
            )
    catalog = (
        EVALUATION_DIR / "capability-test-catalog.v0.2.0.md"
    ).read_text(encoding="utf-8")
    missing_in_catalog = [
        fixture_id
        for fixture_id in fixture_ids
        if fixture_id not in catalog
    ]
    if missing_in_catalog:
        raise RuntimeError(
            f"human-readable catalog missing {missing_in_catalog}"
        )
    print(
        "PASS 39 blind packets contain no expected-answer fields"
    )


def validate_agent_smoke_run() -> None:
    run_dir = (
        EVALUATION_DIR / "agent_runs" / "RUN-SMOKE-001"
    )
    manifest = json.loads(
        (
            run_dir / "run-manifest.v0.1.0.json"
        ).read_text(encoding="utf-8")
    )
    result = json.loads(
        (
            run_dir / "score-summary.v0.1.0.json"
        ).read_text(encoding="utf-8")
    )
    raw_path = run_dir / "raw-outputs.jsonl"
    assessment_path = run_dir / "assessments.jsonl"
    raw_outputs = [
        json.loads(line)
        for line in raw_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assessments = [
        json.loads(line)
        for line in assessment_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    selected_ids = {
        item["fixture_id"]
        for item in manifest["selected_packets"]
    }
    raw_ids = {item["fixture_id"] for item in raw_outputs}
    assessment_ids = {
        item["fixture_id"] for item in assessments
    }
    if (
        len(selected_ids) != 7
        or raw_ids != selected_ids
        or assessment_ids != selected_ids
    ):
        raise RuntimeError("smoke run fixture coverage mismatch")
    raw_by_id = {
        item["fixture_id"]: item for item in raw_outputs
    }
    for assessment in assessments:
        fixture_id = assessment["fixture_id"]
        if assessment["assessor_type"] != "INDEPENDENT_AGENT":
            raise RuntimeError(
                f"{fixture_id}: smoke assessment not independent"
            )
        if (
            assessment["assessor_id"]
            == raw_by_id[fixture_id]["subject_id"]
        ):
            raise RuntimeError(
                f"{fixture_id}: subject assessed own output"
            )
        if assessment["observed_forbidden_behaviors"]:
            raise RuntimeError(
                f"{fixture_id}: forbidden behavior observed"
            )
    if result["raw_outputs_sha256"] != sha256_file(raw_path):
        raise RuntimeError("smoke raw output hash mismatch")
    if result["assessments_sha256"] != sha256_file(
        assessment_path
    ):
        raise RuntimeError("smoke assessment hash mismatch")
    if (
        result["status"] != "INDEPENDENT_ASSESSMENT_COMPLETE"
        or result["passed_count"] != 1
        or result["failed_count"] != 6
        or result["global_errors"]
        or result["human_semantic_review_status"] != "NOT_RUN"
    ):
        raise RuntimeError("smoke score summary status mismatch")
    contract_suite = json.loads(
        (
            EVALUATION_DIR
            / "fixtures"
            / "capability-contract-fixtures.v0.1.0.json"
        ).read_text(encoding="utf-8")
    )
    expected_by_id = {
        item["fixture_id"]: item
        for item in contract_suite["fixtures"]
        if item["fixture_id"] in selected_ids
    }
    for assessment in assessments:
        expected = expected_by_id[assessment["fixture_id"]]
        if assessment["decision"] != expected[
            "expected_decision"
        ]:
            raise RuntimeError(
                f"{assessment['fixture_id']}: core decision mismatch"
            )
    adjudication = (
        run_dir / "adjudication.v0.1.0.md"
    ).read_text(encoding="utf-8")
    for marker in [
        "精确机器合同通过",
        "1/7",
        "核心决策方向正确",
        "7/7",
        "人工语义复核",
        "未执行",
    ]:
        if marker not in adjudication:
            raise RuntimeError(
                f"smoke adjudication missing marker {marker}"
            )
    print(
        "PASS independent 7-case smoke run: "
        "1 exact contract pass, 7 correct decisions, "
        "0 forbidden behaviors"
    )


def validate_targeted_handoff_regression() -> None:
    run_dir = (
        EVALUATION_DIR / "agent_runs" / "RUN-SMOKE-002"
    )
    result = json.loads(
        (
            run_dir / "score-summary.v0.1.0.json"
        ).read_text(encoding="utf-8")
    )
    raw_path = run_dir / "raw-outputs.jsonl"
    assessment_path = run_dir / "assessments.jsonl"
    raw_outputs = [
        json.loads(line)
        for line in raw_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    assessments = [
        json.loads(line)
        for line in assessment_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    if len(raw_outputs) != 3 or len(assessments) != 3:
        raise RuntimeError(
            "targeted handoff regression must contain 3 cases"
        )
    if result["raw_outputs_sha256"] != sha256_file(raw_path):
        raise RuntimeError("regression raw output hash mismatch")
    if result["assessments_sha256"] != sha256_file(
        assessment_path
    ):
        raise RuntimeError("regression assessment hash mismatch")
    if (
        result["status"] != "INDEPENDENT_ASSESSMENT_COMPLETE"
        or result["passed_count"] != 1
        or result["failed_count"] != 2
        or result["global_errors"]
        or result["human_semantic_review_status"] != "NOT_RUN"
    ):
        raise RuntimeError(
            "targeted regression exact-score status mismatch"
        )
    if any(
        item["observed_forbidden_behaviors"]
        for item in assessments
    ):
        raise RuntimeError(
            "targeted regression observed forbidden behavior"
        )
    raw_by_id = {
        item["fixture_id"]: item["raw_response"]
        for item in raw_outputs
    }
    required_markers = {
        "CAP03-ADV-002": [
            "ESCALATED",
            "NONE",
            "HUMAN-FINANCIAL-FACT",
        ],
        "CAP05-ADV-001": [
            "COMPLETED",
            "InsightPackage@0.5.0",
            "CAP-04",
        ],
        "CAP06-VIZ-001": [
            "WAITING_INPUT",
            "NONE",
            "CAP-05",
        ],
    }
    for fixture_id, markers in required_markers.items():
        response = raw_by_id.get(fixture_id, "")
        for marker in markers:
            if marker not in response:
                raise RuntimeError(
                    f"{fixture_id}: missing handoff marker {marker}"
                )
    adjudication = (
        run_dir / "adjudication.v0.1.0.md"
    ).read_text(encoding="utf-8")
    if "3/3 达到" not in adjudication:
        raise RuntimeError(
            "targeted regression adjudication is incomplete"
        )
    print(
        "PASS 3/3 targeted handoff regressions "
        "(exact legacy contract 1/3, safely documented)"
    )


def main() -> int:
    run_python("02_schemas/validate_examples.py")
    run_python("07_evaluations/build_capability_test_materials.py")
    run_python("07_evaluations/run_capability_contract_tests.py")
    run_python(
        "07_evaluations/test_capability_contract_evaluator.py"
    )
    run_python("07_evaluations/test_workflow_runtime.py")
    validate_blind_test_materials()
    validate_agent_smoke_run()
    validate_targeted_handoff_regression()
    store = load_schema_store()
    fieldwork = validate_instance(
        FORMAL_DIR / "fieldwork-package.v0.1.0.json",
        "fieldwork-package.schema.json",
        store,
    )
    insight = validate_instance(
        FORMAL_DIR / "insight-package.v0.1.0.json",
        "insight-package.schema.json",
        store,
    )
    report = validate_instance(
        FORMAL_DIR / "research-report.v0.1.0.json",
        "research-report.schema.json",
        store,
    )
    validate_cross_artifact(fieldwork, insight, report)
    validate_manifest_and_data("artifact-manifest.v0.1.0.json")
    current_insight = validate_instance(
        FORMAL_DIR / "insight-package.v0.2.0.json",
        "insight-package.schema.json",
        store,
    )
    current_report = validate_instance(
        FORMAL_DIR / "research-report.v0.2.0.json",
        "research-report.schema.json",
        store,
    )
    validate_instance(
        FORMAL_DIR / "review-result.report.v0.2.0.json",
        "review-result.schema.json",
        store,
    )
    validate_cross_artifact(fieldwork, current_insight, current_report)
    validate_manifest_and_data("artifact-manifest.v0.2.0.json")
    validate_permissions()
    validate_no_fabricated_approvals()
    validate_historical_runtime(store)
    print("ALL PROJECT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
