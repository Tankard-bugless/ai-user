from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

from run_capability_contract_tests import (  # noqa: E402
    evaluate_candidates,
    load_candidates,
    validate_assessment_provenance,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def assemble_raw_outputs(run_dir: Path, manifest: dict) -> list[dict]:
    expected = {
        item["fixture_id"]: item
        for item in manifest["selected_packets"]
    }
    observed: dict[str, dict] = {}
    for path in sorted((run_dir / "raw").glob("raw-batch-*.json")):
        batch = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(batch, list):
            raise ValueError(f"{path.name} must contain a JSON array")
        for record in batch:
            fixture_id = record.get("fixture_id")
            if fixture_id not in expected:
                raise ValueError(
                    f"{path.name}: unexpected fixture {fixture_id}"
                )
            if fixture_id in observed:
                raise ValueError(f"duplicate raw output {fixture_id}")
            packet = expected[fixture_id]
            exact_fields = {
                "run_id": manifest["run_id"],
                "subject_id": packet["subject_id"],
                "capability_id": packet["capability_id"],
                "capability_version": packet["capability_version"],
            }
            for field, expected_value in exact_fields.items():
                if record.get(field) != expected_value:
                    raise ValueError(
                        f"{fixture_id}: {field} mismatch"
                    )
            if not str(record.get("raw_response", "")).strip():
                raise ValueError(
                    f"{fixture_id}: raw_response is empty"
                )
            leaked_fields = {
                "expected_output_artifact",
                "expected_route",
                "expected_decision",
                "required_behaviors",
                "forbidden_behaviors",
            } & set(record)
            if leaked_fields:
                raise ValueError(
                    f"{fixture_id}: answer fields leaked "
                    f"{sorted(leaked_fields)}"
                )
            observed[fixture_id] = record
    missing = set(expected) - set(observed)
    if missing:
        raise ValueError(f"raw outputs missing {sorted(missing)}")
    ordered = [
        observed[item["fixture_id"]]
        for item in manifest["selected_packets"]
    ]
    raw_path = run_dir / "raw-outputs.jsonl"
    raw_path.write_text(
        "".join(
            json.dumps(item, ensure_ascii=False) + "\n"
            for item in ordered
        ),
        encoding="utf-8",
    )
    return ordered


def assemble_assessments(
    run_dir: Path, manifest: dict
) -> Path | None:
    assessment_dir = run_dir / "assess"
    batch_paths = sorted(
        assessment_dir.glob("assessment-batch-*.json")
    )
    if not batch_paths:
        return None
    expected_ids = [
        item["fixture_id"]
        for item in manifest["selected_packets"]
    ]
    observed: dict[str, dict] = {}
    for path in batch_paths:
        batch = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(batch, list):
            raise ValueError(f"{path.name} must contain a JSON array")
        for assessment in batch:
            fixture_id = assessment.get("fixture_id")
            if fixture_id not in expected_ids:
                raise ValueError(
                    f"{path.name}: unexpected assessment {fixture_id}"
                )
            if fixture_id in observed:
                raise ValueError(
                    f"duplicate assessment {fixture_id}"
                )
            observed[fixture_id] = assessment
    if set(observed) != set(expected_ids):
        missing = set(expected_ids) - set(observed)
        raise ValueError(
            f"assessment batches missing {sorted(missing)}"
        )
    assessment_path = run_dir / "assessments.jsonl"
    assessment_path.write_text(
        "".join(
            json.dumps(observed[fixture_id], ensure_ascii=False)
            + "\n"
            for fixture_id in expected_ids
        ),
        encoding="utf-8",
    )
    return assessment_path


def score(
    run_dir: Path,
    manifest: dict,
    raw_outputs: list[dict],
) -> dict:
    assessment_path = run_dir / "assessments.jsonl"
    if not assessment_path.exists():
        return {
            "run_id": manifest["run_id"],
            "status": "RAW_OUTPUTS_FROZEN",
            "raw_output_count": len(raw_outputs),
            "assessment_count": 0,
            "human_semantic_review_status": "NOT_RUN",
        }
    suite_version = manifest["fixture_suite"].split("@", 1)[1]
    fixture_path = (
        EVAL_DIR
        / "fixtures"
        / f"capability-contract-fixtures.v{suite_version}.json"
    )
    all_fixtures = json.loads(
        fixture_path.read_text(encoding="utf-8")
    )["fixtures"]
    selected_ids = {
        item["fixture_id"]
        for item in manifest["selected_packets"]
    }
    selected_fixtures = [
        item
        for item in all_fixtures
        if item["fixture_id"] in selected_ids
    ]
    assessments = load_candidates(assessment_path)
    raw_by_id = {
        item["fixture_id"]: item for item in raw_outputs
    }
    global_errors = []
    if set(assessments) != selected_ids:
        global_errors.append(
            "assessment fixture set must exactly match smoke selection"
        )
    global_errors.extend(
        validate_assessment_provenance(assessments)
    )
    for fixture_id, assessment in assessments.items():
        if fixture_id not in raw_by_id:
            continue
        if assessment.get("assessor_id") == raw_by_id[fixture_id][
            "subject_id"
        ]:
            global_errors.append(
                f"{fixture_id}: subject cannot assess own output"
            )
        expected_ref = f"raw-outputs.jsonl#{fixture_id}"
        if assessment.get("raw_output_ref") != expected_ref:
            global_errors.append(
                f"{fixture_id}: raw_output_ref must equal {expected_ref}"
            )

    fixture_results = []
    for fixture in selected_fixtures:
        fixture_id = fixture["fixture_id"]
        assessment = assessments.get(fixture_id)
        if not assessment:
            fixture_results.append(
                {
                    "fixture_id": fixture_id,
                    "passed": False,
                    "errors": ["missing assessment"],
                }
            )
            continue
        errors = evaluate_candidates(
            [fixture],
            {fixture_id: assessment},
            require_all=True,
        )
        errors.extend(
            validate_assessment_provenance(
                {fixture_id: assessment}
            )
        )
        fixture_results.append(
            {
                "fixture_id": fixture_id,
                "capability_id": fixture["capability_id"],
                "passed": not errors,
                "errors": errors,
            }
        )
    passed_count = sum(
        item["passed"] for item in fixture_results
    )
    raw_path = run_dir / "raw-outputs.jsonl"
    return {
        "run_id": manifest["run_id"],
        "status": (
            "INDEPENDENT_ASSESSMENT_COMPLETE"
            if not global_errors
            else "ASSESSMENT_INVALID"
        ),
        "raw_output_count": len(raw_outputs),
        "assessment_count": len(assessments),
        "passed_count": passed_count,
        "failed_count": len(fixture_results) - passed_count,
        "all_contracts_passed": (
            not global_errors
            and passed_count == len(fixture_results)
        ),
        "global_errors": global_errors,
        "fixture_results": fixture_results,
        "raw_outputs_sha256": sha256_file(raw_path),
        "assessments_sha256": sha256_file(assessment_path),
        "human_semantic_review_status": "NOT_RUN",
        "interpretation": (
            "这是独立 Agent 冒烟评估，不是人工 Gate，"
            "也不能外推为全部 39 条测试通过。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    manifest = json.loads(
        (
            run_dir / "run-manifest.v0.1.0.json"
        ).read_text(encoding="utf-8")
    )
    raw_outputs = assemble_raw_outputs(run_dir, manifest)
    assemble_assessments(run_dir, manifest)
    result = score(run_dir, manifest, raw_outputs)
    result_path = run_dir / "score-summary.v0.1.0.json"
    write_json(result_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "ASSESSMENT_INVALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
