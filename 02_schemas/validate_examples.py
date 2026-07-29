"""Validate core schemas, synthetic examples, and the end-to-end artifact graph."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"
EXAMPLE_SCHEMA_MAP = {
    "research-brief.example.json": "research-brief.schema.json",
    "research-plan.example.json": "research-plan.schema.json",
    "instrument-spec.survey.example.json": "instrument-spec.schema.json",
    "instrument-spec.interview.example.json": "instrument-spec.schema.json",
    "review-result.example.json": "review-result.schema.json",
    "review-result.current.example.json": "review-result.schema.json",
    "approval-record.gate1.example.json": "approval-record.schema.json",
    "approval-record.gate2.example.json": "approval-record.schema.json",
    "fieldwork-package.example.json": "fieldwork-package.schema.json",
    "insight-package.example.json": "insight-package.schema.json",
    "approval-record.gate3.example.json": "approval-record.schema.json",
    "research-report.example.json": "research-report.schema.json",
    "approval-record.gate4.example.json": "approval-record.schema.json",
    "workflow-state.instrument-design.example.json": "workflow-state.schema.json",
    "task-record.instrument-design.example.json": "task-record.schema.json",
    "handoff-record.plan-to-instrument.example.json": "handoff-record.schema.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_structure() -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    registry = Registry()

    for path in sorted(ROOT.glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )

    has_error = False
    for example_name, schema_name in EXAMPLE_SCHEMA_MAP.items():
        instance = load_json(EXAMPLES / example_name)
        validator = Draft202012Validator(
            schemas[schema_name],
            registry=registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(instance), key=lambda error: list(error.absolute_path)
        )
        if errors:
            has_error = True
            print(f"FAIL {example_name}: {len(errors)} error(s)")
            for error in errors:
                location = "/" + "/".join(map(str, error.absolute_path))
                print(f"  {location}: {error.message}")
        else:
            print(f"PASS {example_name}")

    if has_error:
        raise ValueError("Schema instance validation failed")
    return schemas


def validate_cross_references() -> None:
    brief = load_json(EXAMPLES / "research-brief.example.json")
    plan = load_json(EXAMPLES / "research-plan.example.json")
    survey = load_json(EXAMPLES / "instrument-spec.survey.example.json")
    interview = load_json(EXAMPLES / "instrument-spec.interview.example.json")
    old_review = load_json(EXAMPLES / "review-result.example.json")
    current_review = load_json(EXAMPLES / "review-result.current.example.json")
    gate_1 = load_json(EXAMPLES / "approval-record.gate1.example.json")
    gate_2 = load_json(EXAMPLES / "approval-record.gate2.example.json")
    fieldwork = load_json(EXAMPLES / "fieldwork-package.example.json")
    insight = load_json(EXAMPLES / "insight-package.example.json")
    gate_3 = load_json(EXAMPLES / "approval-record.gate3.example.json")
    report = load_json(EXAMPLES / "research-report.example.json")
    gate_4 = load_json(EXAMPLES / "approval-record.gate4.example.json")
    workflow_state = load_json(
        EXAMPLES / "workflow-state.instrument-design.example.json"
    )
    instrument_task = load_json(
        EXAMPLES / "task-record.instrument-design.example.json"
    )
    plan_handoff = load_json(
        EXAMPLES / "handoff-record.plan-to-instrument.example.json"
    )

    all_examples = (
        brief,
        plan,
        survey,
        interview,
        old_review,
        current_review,
        gate_1,
        gate_2,
        fieldwork,
        insight,
        gate_3,
        report,
        gate_4,
    )

    research_question_ids = {
        item["research_question_id"] for item in brief["research_questions"]
    }
    hypothesis_ids = {item["hypothesis_id"] for item in brief["hypotheses"]}
    method_ids = {item["method_id"] for item in plan["method_specs"]}
    plan_material_ids = {item["material_id"] for item in plan["materials_plan"]}
    plan_learning_resource_ids = {
        item["resource_id"] for item in plan.get("learning_resources_plan", [])
    }
    errors: list[str] = []

    def artifact_key(reference: dict) -> tuple[str, str, str]:
        return (
            reference["artifact_id"],
            reference["artifact_type"],
            reference["artifact_version"],
        )

    def metadata_key(artifact: dict) -> tuple[str, str, str]:
        metadata = artifact["metadata"]
        return (
            metadata["artifact_id"],
            metadata["artifact_type"],
            metadata["artifact_version"],
        )

    def record_key(record_or_reference: dict) -> tuple[str, str, int]:
        source = record_or_reference.get("metadata", record_or_reference)
        return (
            source["record_id"],
            source["record_type"],
            source["record_revision"],
        )

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    check(
        all(
            item["metadata"]["content_classification"] == "SYNTHETIC"
            for item in all_examples
        ),
        "Every example must be classified as SYNTHETIC.",
    )
    check(
        len({item["metadata"]["project_id"] for item in all_examples}) == 1,
        "Examples do not belong to one demo project.",
    )

    analysis_intent = brief.get("analysis_intent")
    if analysis_intent:
        comparisons = analysis_intent["intended_comparisons"]
        comparison_ids = [item["comparison_id"] for item in comparisons]
        check(
            len(comparison_ids) == len(set(comparison_ids)),
            "ResearchBrief analysis comparison IDs are not unique.",
        )
        for comparison in comparisons:
            check(
                set(comparison["research_question_ids"]) <= research_question_ids,
                f"Unknown research question in analysis comparison {comparison['comparison_id']}.",
            )
        check(
            any(
                item["dimension"] == "PROFILE"
                for item in analysis_intent["measurement_dimensions"]
            ),
            "ResearchBrief analysis_intent must include a PROFILE measurement dimension.",
        )

    check(
        plan["research_brief_ref"]["artifact_id"]
        == brief["metadata"]["artifact_id"],
        "ResearchPlan does not reference the example ResearchBrief.",
    )
    check(
        set(plan["research_design"]["method_ids"]) == method_ids,
        "ResearchPlan design method IDs do not match method_specs.",
    )

    sample_targets = plan["sampling_plan"]["method_sample_targets"]
    check(
        {item["method_id"] for item in sample_targets} == method_ids,
        "Sampling allocations do not cover every method exactly once.",
    )
    check(
        plan["sampling_plan"]["total_target"]
        == sum(item["target"] for item in sample_targets),
        "Sampling total_target does not equal the sum of method targets.",
    )
    for item in sample_targets:
        check(
            item["minimum"] <= item["target"] <= item["maximum"],
            f"Invalid minimum/target/maximum order for {item['method_id']}.",
        )
        check(
            sum(segment["target"] for segment in item["segment_targets"])
            == item["target"],
            f"Segment targets do not add up for {item['method_id']}.",
        )

    for row in plan["question_method_map"]:
        check(
            row["research_question_id"] in research_question_ids,
            f"Unknown research question in question_method_map: {row['research_question_id']}",
        )
        check(
            set(row["method_ids"]) <= method_ids,
            f"Unknown method in question_method_map for {row['research_question_id']}",
        )

    for instrument in (survey, interview):
        artifact_id = instrument["metadata"]["artifact_id"]
        check(
            instrument["research_plan_ref"]["artifact_id"]
            == plan["metadata"]["artifact_id"],
            f"{artifact_id} does not reference the example ResearchPlan.",
        )
        check(
            set(instrument["research_question_ids"]) <= research_question_ids,
            f"{artifact_id} contains an unknown research question.",
        )
        check(
            set(instrument["hypothesis_ids"]) <= hypothesis_ids,
            f"{artifact_id} contains an unknown hypothesis.",
        )
        instrument_material_ids = {
            item["material_id"] for item in instrument["test_materials"]
        }
        check(
            instrument_material_ids <= plan_material_ids,
            f"{artifact_id} contains material not declared in ResearchPlan.",
        )
        instrument_learning_resource_ids = {
            item["resource_id"] for item in instrument.get("learning_resources", [])
        }
        check(
            instrument_learning_resource_ids <= plan_learning_resource_ids,
            f"{artifact_id} contains a learning resource not declared in ResearchPlan.",
        )
        check(
            all(
                item["evidence_use"] == "NOT_RESEARCH_EVIDENCE"
                and item["optional_for_participant"] is True
                for item in instrument.get("learning_resources", [])
            ),
            f"{artifact_id} uses a learning resource as evidence or makes it mandatory.",
        )
        check(
            all(item["source_type"] != "IMA" for item in instrument["test_materials"]),
            f"{artifact_id} places the default IMA bridge in test_materials.",
        )

    survey_sections = survey["survey_spec"]["sections"]
    survey_section_ids = {item["section_id"] for item in survey_sections}
    survey_items = [
        item for section in survey_sections for item in section["items"]
    ]
    survey_item_ids = {item["item_id"] for item in survey_items}
    survey_end_ids = {
        item["termination_id"]
        for item in survey["survey_spec"]["termination_messages"]
    }
    survey_component_ids = (
        survey_section_ids
        | survey_item_ids
        | {item["material_id"] for item in survey["test_materials"]}
    )
    for resource in survey.get("learning_resources", []):
        placement_id = resource.get("placement_after_component_id")
        if placement_id:
            check(
                placement_id in survey_section_ids | survey_item_ids,
                f"Unknown learning resource placement in survey: {placement_id}",
            )
    check(
        len(survey_item_ids) == len(survey_items),
        "Survey item IDs are not unique.",
    )
    for item in survey_items:
        check(
            set(item["research_question_ids"]) <= research_question_ids,
            f"Unknown research question in survey item {item['item_id']}.",
        )
        check(
            set(item["hypothesis_ids"]) <= hypothesis_ids,
            f"Unknown hypothesis in survey item {item['item_id']}.",
        )

    for rule in survey["survey_spec"]["logic_rules"]:
        for condition in rule["conditions"]:
            check(
                condition["source_item_id"] in survey_item_ids,
                f"Unknown survey logic source in {rule['rule_id']}.",
            )
        check(
            rule["target_id"] in survey_component_ids | survey_end_ids,
            f"Unknown survey logic target in {rule['rule_id']}.",
        )

    for variable in survey["survey_spec"]["output_variables"]:
        check(
            variable["source_item_id"] in survey_item_ids,
            f"Unknown output variable source in {variable['variable_id']}.",
        )
    for row in survey["material_measurement_plan"]:
        component_refs = (
            row["baseline_component_ids"]
            + row["exposure_check_component_ids"]
            + row["comprehension_component_ids"]
            + row["attitude_component_ids"]
        )
        check(
            set(component_refs) <= survey_item_ids,
            f"Unknown survey material measurement component for {row['material_id']}.",
        )

    modules = interview["interview_spec"]["modules"]
    module_ids = {item["module_id"] for item in modules}
    interview_questions = [
        item for module in modules for item in module["questions"]
    ]
    interview_question_ids = {
        item["question_id"] for item in interview_questions
    }
    interview_component_ids = (
        module_ids
        | interview_question_ids
        | {item["material_id"] for item in interview["test_materials"]}
    )
    for resource in interview.get("learning_resources", []):
        placement_id = resource.get("placement_after_component_id")
        if placement_id:
            check(
                placement_id in module_ids | interview_question_ids,
                f"Unknown learning resource placement in interview: {placement_id}",
            )
    check(
        len(interview_question_ids) == len(interview_questions),
        "Interview question IDs are not unique.",
    )
    for question in interview_questions:
        check(
            set(question["research_question_ids"]) <= research_question_ids,
            f"Unknown research question in interview question {question['question_id']}.",
        )
        check(
            set(question["hypothesis_ids"]) <= hypothesis_ids,
            f"Unknown hypothesis in interview question {question['question_id']}.",
        )
    for row in interview["material_measurement_plan"]:
        component_refs = (
            row["baseline_component_ids"]
            + row["exposure_check_component_ids"]
            + row["comprehension_component_ids"]
            + row["attitude_component_ids"]
        )
        check(
            set(component_refs) <= interview_question_ids,
            f"Unknown interview material measurement component for {row['material_id']}.",
        )

    for instrument, component_ids in (
        (survey, survey_component_ids),
        (interview, interview_component_ids),
    ):
        for row in instrument["traceability_map"]:
            check(
                row["component_id"] in component_ids,
                f"Unknown traceability component: {row['component_id']}",
            )
            check(
                set(row["research_question_ids"]) <= research_question_ids,
                f"Unknown research question in traceability: {row['component_id']}",
            )
            check(
                set(row["hypothesis_ids"]) <= hypothesis_ids,
                f"Unknown hypothesis in traceability: {row['component_id']}",
            )

    severity_field = {
        "BLOCKER": "blocker_count",
        "MAJOR": "major_count",
        "MINOR": "minor_count",
        "WARNING": "warning_count",
    }
    for review in (old_review, current_review):
        for severity, field in severity_field.items():
            actual = sum(
                1 for issue in review["issues"] if issue["severity"] == severity
            )
            check(
                review["summary"][field] == actual,
                f"{review['metadata']['artifact_id']} {field} does not match issues.",
            )
        check(
            review["is_formal_approval"] is False,
            f"{review['metadata']['artifact_id']} claims formal approval.",
        )
    check(
        survey["metadata"]["supersedes_ref"]["artifact_id"]
        == old_review["target_ref"]["artifact_id"]
        and survey["metadata"]["supersedes_ref"]["artifact_version"]
        == old_review["target_ref"]["artifact_version"],
        "The revised survey does not supersede the reviewed old version.",
    )
    check(
        artifact_key(current_review["target_ref"]) == metadata_key(survey),
        "The current ReviewResult does not target the current survey version.",
    )

    approvals = (gate_1, gate_2, gate_3, gate_4)
    for approval in approvals:
        approval_id = approval["metadata"]["artifact_id"]
        reviewed_keys = {artifact_key(ref) for ref in approval["reviewed_refs"]}
        check(
            approval["status"] == "APPROVED",
            f"Demo approval {approval_id} is not APPROVED.",
        )
        check(
            approval["reviewer"]["actor_type"] == "HUMAN"
            and approval["is_ai_approval"] is False,
            f"Demo approval {approval_id} is not a human approval.",
        )
        check(
            artifact_key(approval["primary_target_ref"]) in reviewed_keys,
            f"Primary target is absent from reviewed_refs in {approval_id}.",
        )

    check(
        artifact_key(gate_1["primary_target_ref"]) == metadata_key(brief),
        "Gate 1 does not approve the example ResearchBrief.",
    )
    check(
        artifact_key(plan["gate_1_approval_ref"]) == metadata_key(gate_1),
        "ResearchPlan does not reference the example Gate 1 approval.",
    )

    gate_2_reviewed = {artifact_key(ref) for ref in gate_2["reviewed_refs"]}
    check(
        artifact_key(gate_2["primary_target_ref"]) == metadata_key(plan),
        "Gate 2 does not use ResearchPlan as its primary target.",
    )
    check(
        {metadata_key(survey), metadata_key(interview), metadata_key(current_review)}
        <= gate_2_reviewed,
        "Gate 2 did not review both instruments and the current ReviewResult.",
    )
    check(
        artifact_key(fieldwork["gate_2_approval_ref"]) == metadata_key(gate_2),
        "FieldworkPackage does not reference Gate 2 approval.",
    )
    check(
        artifact_key(fieldwork["research_plan_ref"]) == metadata_key(plan),
        "FieldworkPackage does not reference the example ResearchPlan.",
    )
    check(
        {artifact_key(ref) for ref in fieldwork["instrument_refs"]}
        == {metadata_key(survey), metadata_key(interview)},
        "FieldworkPackage instrument versions do not match the approved examples.",
    )
    check(
        {item["method_id"] for item in fieldwork["execution_summary"]["method_completion"]}
        == method_ids,
        "FieldworkPackage completion does not cover all planned methods.",
    )
    fieldwork_source_ids = {item["source_id"] for item in fieldwork["source_records"]}
    check(
        len(fieldwork_source_ids) == len(fieldwork["source_records"]),
        "FieldworkPackage source IDs are not unique.",
    )
    check(
        all(
            item["resource_id"] in plan_learning_resource_ids
            and item["evidence_use"] == "NOT_RESEARCH_EVIDENCE"
            for item in fieldwork["learning_resource_delivery"]
        ),
        "FieldworkPackage learning resource delivery violates the IMA boundary.",
    )

    check(
        artifact_key(insight["research_brief_ref"]) == metadata_key(brief)
        and artifact_key(insight["research_plan_ref"]) == metadata_key(plan),
        "InsightPackage upstream brief or plan is incorrect.",
    )
    check(
        {artifact_key(ref) for ref in insight["fieldwork_package_refs"]}
        == {metadata_key(fieldwork)},
        "InsightPackage does not reference the example FieldworkPackage.",
    )
    included_source_ids = set(insight["analysis_scope"]["included_source_ids"])
    excluded_source_ids = set(insight["analysis_scope"]["excluded_source_ids"])
    check(
        included_source_ids | excluded_source_ids <= fieldwork_source_ids,
        "InsightPackage analysis scope contains unknown FieldworkPackage sources.",
    )

    code_ids = {item["code_id"] for item in insight["codebook"]["codes"]}
    evidence_ids = {item["evidence_id"] for item in insight["evidence_units"]}
    finding_ids = {item["finding_id"] for item in insight["findings"]}
    insight_ids = {item["insight_id"] for item in insight["insights"]}
    recommendation_ids = {
        item["recommendation_id"] for item in insight["recommendations"]
    }
    investor_education_recommendation_ids = {
        item["recommendation_id"]
        for item in insight["recommendations"]
        if item["recommendation_domain"] == "INVESTOR_EDUCATION"
    }
    check(
        len(evidence_ids) == len(insight["evidence_units"]),
        "InsightPackage evidence IDs are not unique.",
    )
    for evidence in insight["evidence_units"]:
        check(
            evidence["source_id"] in included_source_ids,
            f"Evidence {evidence['evidence_id']} references a non-included source.",
        )
        check(
            evidence["human_verified"] is True,
            f"Evidence {evidence['evidence_id']} has not been human verified.",
        )
        check(
            set(evidence["research_question_ids"]) <= research_question_ids
            and set(evidence["hypothesis_ids"]) <= hypothesis_ids
            and set(evidence.get("code_ids", [])) <= code_ids,
            f"Evidence {evidence['evidence_id']} contains an unknown research reference.",
        )
    for finding in insight["findings"]:
        check(
            set(finding["supporting_evidence_ids"])
            | set(finding["negative_case_evidence_ids"])
            <= evidence_ids,
            f"Finding {finding['finding_id']} contains an unknown evidence ID.",
        )
        check(
            set(finding["method_ids"]) <= method_ids
            and set(finding["research_question_ids"]) <= research_question_ids,
            f"Finding {finding['finding_id']} contains an unknown method or question.",
        )
    for item in insight["insights"]:
        check(
            set(item["source_finding_ids"]) <= finding_ids,
            f"Insight {item['insight_id']} contains an unknown finding ID.",
        )
    for recommendation in insight["recommendations"]:
        check(
            set(recommendation["source_insight_ids"]) <= insight_ids,
            f"Recommendation {recommendation['recommendation_id']} has an unknown insight.",
        )
        check(
            set(recommendation.get("related_learning_resource_ids", []))
            <= plan_learning_resource_ids,
            f"Recommendation {recommendation['recommendation_id']} has an unknown learning resource.",
        )
    for item in insight["candidate_segments"] + insight["candidate_tags"]:
        check(
            set(item["evidence_ids"]) <= evidence_ids,
            f"Candidate item {item.get('segment_id', item.get('tag_id'))} has unknown evidence.",
        )
    for item in insight["learning_resource_recommendations"]:
        check(
            item["resource_id"] in plan_learning_resource_ids
            and set(item["recommendation_ids"]) <= recommendation_ids
            and item["evidence_use"] == "NOT_RESEARCH_EVIDENCE",
            f"Learning resource recommendation {item['resource_id']} violates traceability.",
        )

    gate_3_reviewed = {artifact_key(ref) for ref in gate_3["reviewed_refs"]}
    check(
        artifact_key(gate_3["primary_target_ref"]) == metadata_key(insight)
        and metadata_key(fieldwork) in gate_3_reviewed,
        "Gate 3 does not approve the InsightPackage with its FieldworkPackage.",
    )
    check(
        artifact_key(report["insight_package_ref"]) == metadata_key(insight)
        and artifact_key(report["gate_3_approval_ref"]) == metadata_key(gate_3),
        "ResearchReport does not reference the approved InsightPackage.",
    )
    for answer in report["executive_summary"]["key_answers"]:
        check(
            answer["research_question_id"] in research_question_ids
            and set(answer["finding_ids"]) <= finding_ids,
            f"Report answer for {answer['research_question_id']} has an unknown finding.",
        )
    check(
        set(report["executive_summary"]["key_recommendation_ids"])
        <= recommendation_ids,
        "Report executive summary contains an unknown recommendation.",
    )
    for item in report["finding_presentations"]:
        check(
            item["finding_id"] in finding_ids
            and {e["evidence_id"] for e in item["evidence_highlights"]}
            <= evidence_ids,
            f"Report finding {item['finding_id']} contains an unknown reference.",
        )
    check(
        {item["insight_id"] for item in report["insight_presentations"]}
        <= insight_ids,
        "Report contains an unknown insight presentation.",
    )
    check(
        {
            item["recommendation_id"]
            for item in report["recommendation_presentations"]
        }
        <= recommendation_ids,
        "Report contains an unknown recommendation presentation.",
    )
    investor_education_section = report["investor_education_section"]
    check(
        set(investor_education_section["recommendation_ids"])
        <= investor_education_recommendation_ids,
        "Report investor education section contains a recommendation outside the INVESTOR_EDUCATION domain.",
    )
    check(
        investor_education_section["applicable"]
        == bool(investor_education_section["recommendation_ids"]),
        "Report investor education applicability does not match its recommendation references.",
    )
    check(
        all(
            item["resource_id"] in plan_learning_resource_ids
            and item["evidence_use"] == "NOT_RESEARCH_EVIDENCE"
            for item in report["learning_resources"]
        ),
        "ResearchReport violates the learning resource evidence boundary.",
    )

    gate_4_reviewed = {artifact_key(ref) for ref in gate_4["reviewed_refs"]}
    check(
        artifact_key(gate_4["primary_target_ref"]) == metadata_key(report)
        and metadata_key(insight) in gate_4_reviewed,
        "Gate 4 does not approve the report with its final InsightPackage.",
    )

    control_records = (workflow_state, instrument_task, plan_handoff)
    check(
        all(
            item["metadata"]["content_classification"] == "SYNTHETIC"
            and item["metadata"]["contains_personal_data"] is False
            for item in control_records
        ),
        "Control examples must be SYNTHETIC and contain no personal data.",
    )
    check(
        len(
            {
                (
                    item["metadata"]["project_id"],
                    item["metadata"]["run_id"],
                )
                for item in control_records
            }
        )
        == 1,
        "Control examples do not belong to one project and run.",
    )
    state_metadata = workflow_state["metadata"]
    previous_state = state_metadata["previous_record_ref"]
    check(
        previous_state["record_id"] == state_metadata["record_id"]
        and previous_state["record_type"] == state_metadata["record_type"]
        and previous_state["record_revision"]
        == state_metadata["record_revision"] - 1,
        "WorkflowState previous revision is not contiguous.",
    )
    active_tasks = set(workflow_state["active_task_ids"])
    completed_tasks = set(workflow_state["completed_task_ids"])
    blocked_tasks = set(workflow_state["blocked_task_ids"])
    check(
        not (
            active_tasks & completed_tasks
            or active_tasks & blocked_tasks
            or completed_tasks & blocked_tasks
        ),
        "WorkflowState task status sets overlap.",
    )
    check(
        workflow_state["transition"]["to_stage"]
        == workflow_state["current_stage"],
        "WorkflowState transition target does not equal current_stage.",
    )
    check(
        instrument_task["metadata"]["record_id"] in active_tasks,
        "Instrument TaskRecord is not active in the WorkflowState.",
    )
    check(
        record_key(instrument_task["state_ref"]) == record_key(workflow_state)
        and record_key(plan_handoff["state_ref"]) == record_key(workflow_state),
        "TaskRecord or HandoffRecord references the wrong WorkflowState revision.",
    )
    check(
        instrument_task["attempt"] <= instrument_task["max_attempts"],
        "TaskRecord attempt exceeds max_attempts.",
    )
    check(
        plan_handoff["to_task_id"] == instrument_task["metadata"]["record_id"],
        "HandoffRecord does not target the example TaskRecord.",
    )
    check(
        plan_handoff["target"] == instrument_task["target"],
        "HandoffRecord target does not match TaskRecord target.",
    )
    check(
        plan_handoff["expected_output"] == instrument_task["expected_output"],
        "HandoffRecord expected output does not match TaskRecord.",
    )
    check(
        {artifact_key(ref) for ref in plan_handoff["payload"]["artifact_refs"]}
        <= {
            artifact_key(ref)
            for ref in instrument_task["input_artifact_refs"]
        },
        "HandoffRecord contains an artifact outside TaskRecord inputs.",
    )
    check(
        {
            record_key(ref)
            for ref in plan_handoff["payload"]["record_refs"]
        }
        <= {
            record_key(ref)
            for ref in instrument_task["input_record_refs"]
        },
        "HandoffRecord contains a control record outside TaskRecord inputs.",
    )
    check(
        plan_handoff["payload"]["chat_history_included"] is False,
        "HandoffRecord includes chat history.",
    )
    check(
        {
            artifact_key(ref)
            for ref in instrument_task["input_artifact_refs"]
        }
        == {metadata_key(plan), metadata_key(gate_1)},
        "Instrument TaskRecord inputs do not match the demo Plan and Gate 1 approval.",
    )

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        raise ValueError("Cross-artifact validation failed")
    print("PASS cross-artifact references and selected semantic rules")


def main() -> int:
    try:
        validate_structure()
        validate_cross_references()
    except Exception as exc:  # The CLI must return a failing status for CI use.
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("ALL VALIDATIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
