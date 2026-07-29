from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CASE_DIR.parents[1]
RUNTIME_MODULE_DIR = PROJECT_ROOT / "04_workflows" / "runtime"
RUNTIME_STORE = CASE_DIR / "formal_artifacts" / "runtime"
SUMMARY_PATH = RUNTIME_STORE / "historical-registration-summary.v0.1.0.json"

sys.path.insert(0, str(RUNTIME_MODULE_DIR))

from workflow_runtime import WorkflowRuntime  # noqa: E402


def build_runtime() -> dict:
    if (RUNTIME_STORE / "registry.v0.1.0.json").exists():
        runtime = WorkflowRuntime(RUNTIME_STORE)
        summary = runtime.status_summary()
        if SUMMARY_PATH.exists():
            return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        return summary

    runtime = WorkflowRuntime.initialize(
        RUNTIME_STORE,
        project_id="PROJ-OTF-001",
        run_id="RUN-OTF-HIST-001",
        content_classification="REAL",
    )

    intake_task = runtime.create_task(
        task_id="TASK-OTF-HIST-IMPORT-001",
        task_kind="VALIDATOR",
        purpose=(
            "登记当前历史迁移动作：确认既有研究需求可进入 Brief "
            "登记；不声称补做历史研究任务。"
        ),
        target_type="VALIDATOR",
        target_id="SYSTEM-HISTORICAL-REGISTRAR",
        principal_id="SYSTEM-VALIDATOR",
        input_artifact_refs=[],
        expected_output={
            "output_kind": "NONE",
            "cardinality": "SINGLE",
        },
    )
    runtime.complete_task(
        intake_task["metadata"]["record_id"],
        output_artifact_refs=[],
        completion_summary=(
            "历史迁移入口登记完成；推进到 Brief 登记阶段，"
            "不补造历史执行记录。"
        ),
        advance_main_path=True,
    )

    brief_ref = runtime.register_artifact_file(
        CASE_DIR / "research-brief.v0.2.0.json"
    )
    runtime.submit_gate(
        "GATE_1",
        reason="提交案例中真实存在的 ResearchBrief v0.2.0 及既有 Gate 1 审批。",
    )
    runtime.approve_gate(
        "GATE_1",
        CASE_DIR / "approval-record.gate1.v0.2.0.json",
    )

    plan_ref = runtime.register_artifact_file(
        CASE_DIR / "research-plan.v0.2.0.json"
    )
    plan_registration_task = runtime.create_task(
        task_id="TASK-OTF-HIST-PLAN-001",
        task_kind="VALIDATOR",
        purpose=(
            "确认既有 ResearchPlan 已按精确版本登记；"
            "只推进当前迁移状态，不重写历史。"
        ),
        target_type="VALIDATOR",
        target_id="SYSTEM-HISTORICAL-REGISTRAR",
        principal_id="SYSTEM-VALIDATOR",
        input_artifact_refs=[brief_ref, plan_ref],
        expected_output={
            "output_kind": "NONE",
            "cardinality": "SINGLE",
        },
    )
    runtime.complete_task(
        plan_registration_task["metadata"]["record_id"],
        output_artifact_refs=[],
        completion_summary=(
            "ResearchPlan v0.2.0 登记完成；"
            "推进到 Instrument 设计复核阶段。"
        ),
        advance_main_path=True,
    )

    runtime.register_artifact_file(
        CASE_DIR / "instrument-spec.v0.2.0.json"
    )
    runtime.register_artifact_file(
        CASE_DIR / "review-result.gate2-precheck.v0.2.0.json"
    )
    runtime.register_artifact_file(
        CASE_DIR
        / "formal_artifacts"
        / "fieldwork-package.v0.1.0.json",
        workflow_validity="STALE",
        reason=(
            "真实执行已经发生，但历史上没有形成 Gate 2 "
            "ApprovalRecord；仅保留为追溯证据，不视为当前流程有效输入。"
        ),
    )
    runtime.register_artifact_file(
        CASE_DIR
        / "formal_artifacts"
        / "insight-package.v0.1.0.json",
        workflow_validity="STALE",
        reason=(
            "依赖未获 Gate 2 正式批准的历史执行，且没有 Gate 3 "
            "ApprovalRecord；仅供复盘与答辩展示。"
        ),
    )
    runtime.register_artifact_file(
        CASE_DIR
        / "formal_artifacts"
        / "research-report.v0.1.0.json",
        workflow_validity="STALE",
        reason=(
            "历史上没有 Gate 3、Gate 4 ApprovalRecord；"
            "报告文件真实存在，但不登记为当前流程已批准输出。"
        ),
    )

    runtime.submit_gate(
        "GATE_2",
        reason=(
            "历史案例停在最早缺失的 Gate 2："
            "等待真实人工审批，不补造 Gate 2、Gate 3、Gate 4 记录。"
        ),
    )
    status = runtime.status_summary()
    summary = {
        "summary_version": "0.1.0",
        "project_id": status["project_id"],
        "run_id": status["run_id"],
        "registration_mode": "HISTORICAL_GOVERNANCE_IMPORT",
        "historical_execution_recreated": False,
        "retrospective_approvals_created": False,
        "current_stage": status["current_stage"],
        "run_status": status["run_status"],
        "current_gate": status["current_gate"],
        "active_approvals": status["active_approvals"],
        "stale_artifacts": status["stale_artifacts"],
        "interpretation": (
            "案例已登记到最早治理缺口 Gate 2。"
            "Gate 1 真实审批保持有效；执行、洞察与报告保留为可追溯但 stale 的历史产物。"
        ),
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(build_runtime(), ensure_ascii=False, indent=2))
