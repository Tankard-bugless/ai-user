from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "capability-contract-fixtures.v0.2.0.json"
)
CARD_BY_CAPABILITY = {
    "frame-research-question": ROOT / "03_experts" / "cap-01-frame-research-question.md",
    "design-research-plan": ROOT / "03_experts" / "cap-02-design-research-plan.md",
    "design-research-instrument": ROOT / "03_experts" / "cap-03-design-research-instrument.md",
    "review-research-quality": ROOT / "03_experts" / "cap-04-review-research-quality.md",
    "synthesize-research-insights": ROOT / "03_experts" / "cap-05-synthesize-research-insights.md",
    "compose-research-report": ROOT / "03_experts" / "cap-06-compose-research-report.md",
    "orchestrate-research-workflow": ROOT / "03_experts" / "ctrl-01-orchestrate-research-workflow.md",
}
REQUIRED_TYPES = {"POSITIVE", "BOUNDARY", "ADVERSARIAL", "REGRESSION"}
REQUIRED_FIELDS = {
    "fixture_id",
    "capability_id",
    "capability_version",
    "test_type",
    "input_summary",
    "expected_output_artifact",
    "expected_route",
    "expected_decision",
    "required_behaviors",
    "forbidden_behaviors",
}
ASSESSMENT_PROVENANCE_FIELDS = {
    "assessor_id",
    "assessor_type",
    "raw_output_ref",
    "evidence_notes",
}


def read_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError(f"{path}: missing YAML-like front matter")
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def validate_fixture_corpus(suite: dict) -> list[str]:
    errors: list[str] = []
    fixtures = suite.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        return ["fixture suite must contain a non-empty fixtures array"]

    ids: set[str] = set()
    types_by_capability: dict[str, set[str]] = defaultdict(set)
    counts: Counter = Counter()
    card_meta = {
        capability: read_front_matter(path)
        for capability, path in CARD_BY_CAPABILITY.items()
    }
    for index, fixture in enumerate(fixtures):
        label = fixture.get("fixture_id", f"index:{index}")
        missing = REQUIRED_FIELDS - set(fixture)
        if missing:
            errors.append(f"{label}: missing fields {sorted(missing)}")
            continue
        if label in ids:
            errors.append(f"{label}: duplicate fixture_id")
        ids.add(label)

        capability = fixture["capability_id"]
        if capability not in CARD_BY_CAPABILITY:
            errors.append(f"{label}: unknown capability_id {capability}")
            continue
        meta = card_meta[capability]
        if meta.get("capability_id") != capability:
            errors.append(
                f"{label}: card capability_id {meta.get('capability_id')} mismatch"
            )
        if meta.get("version") != fixture["capability_version"]:
            errors.append(
                f"{label}: fixture version {fixture['capability_version']} "
                f"!= card version {meta.get('version')}"
            )
        if not fixture["input_summary"].strip():
            errors.append(f"{label}: empty input_summary")
        if not fixture["expected_route"].strip():
            errors.append(f"{label}: empty expected_route")
        if not fixture["expected_decision"].strip():
            errors.append(f"{label}: empty expected_decision")
        required = fixture["required_behaviors"]
        forbidden = fixture["forbidden_behaviors"]
        if not isinstance(required, list) or not required:
            errors.append(f"{label}: required_behaviors must be non-empty")
        if not isinstance(forbidden, list) or not forbidden:
            errors.append(f"{label}: forbidden_behaviors must be non-empty")
        overlap = set(required) & set(forbidden)
        if overlap:
            errors.append(f"{label}: required/forbidden overlap {sorted(overlap)}")
        if len(required) != len(set(required)):
            errors.append(f"{label}: duplicate required behavior")
        if len(forbidden) != len(set(forbidden)):
            errors.append(f"{label}: duplicate forbidden behavior")
        types_by_capability[capability].add(fixture["test_type"])
        counts[capability] += 1

    if set(types_by_capability) != set(CARD_BY_CAPABILITY):
        errors.append(
            "capability coverage mismatch: "
            f"observed={sorted(types_by_capability)}, "
            f"expected={sorted(CARD_BY_CAPABILITY)}"
        )
    for capability, types in types_by_capability.items():
        missing_types = REQUIRED_TYPES - types
        if missing_types:
            errors.append(
                f"{capability}: missing canonical test types {sorted(missing_types)}"
            )
    return errors


def load_candidates(path: Path) -> dict[str, dict]:
    candidates: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            fixture_id = value.get("fixture_id")
            if not fixture_id:
                raise ValueError(f"candidate line {line_number}: missing fixture_id")
            if fixture_id in candidates:
                raise ValueError(
                    f"candidate line {line_number}: duplicate {fixture_id}"
                )
            candidates[fixture_id] = value
    return candidates


def evaluate_candidates(
    fixtures: list[dict], candidates: dict[str, dict], require_all: bool
) -> list[str]:
    errors: list[str] = []
    fixture_by_id = {item["fixture_id"]: item for item in fixtures}
    unknown = set(candidates) - set(fixture_by_id)
    if unknown:
        errors.append(f"candidate file contains unknown fixtures {sorted(unknown)}")
    if require_all:
        missing = set(fixture_by_id) - set(candidates)
        if missing:
            errors.append(f"candidate file missing fixtures {sorted(missing)}")

    for fixture_id, candidate in candidates.items():
        if fixture_id not in fixture_by_id:
            continue
        expected = fixture_by_id[fixture_id]
        for field, expected_field in [
            ("output_artifact_type", "expected_output_artifact"),
            ("route", "expected_route"),
            ("decision", "expected_decision"),
        ]:
            if candidate.get(field) != expected[expected_field]:
                errors.append(
                    f"{fixture_id}: {field}={candidate.get(field)!r}, "
                    f"expected {expected[expected_field]!r}"
                )
        observed = set(candidate.get("observed_behaviors", []))
        violations = set(candidate.get("observed_forbidden_behaviors", []))
        missing_behaviors = set(expected["required_behaviors"]) - observed
        if missing_behaviors:
            errors.append(
                f"{fixture_id}: missing behaviors {sorted(missing_behaviors)}"
            )
        forbidden_seen = set(expected["forbidden_behaviors"]) & (
            observed | violations
        )
        if forbidden_seen:
            errors.append(
                f"{fixture_id}: forbidden behaviors observed "
                f"{sorted(forbidden_seen)}"
            )
    return errors


def validate_assessment_provenance(
    assessments: dict[str, dict],
) -> list[str]:
    errors: list[str] = []
    for fixture_id, assessment in assessments.items():
        missing = ASSESSMENT_PROVENANCE_FIELDS - set(assessment)
        if missing:
            errors.append(
                f"{fixture_id}: assessment missing provenance "
                f"{sorted(missing)}"
            )
            continue
        if assessment["assessor_type"] not in {
            "HUMAN",
            "INDEPENDENT_AGENT",
        }:
            errors.append(
                f"{fixture_id}: unsupported assessor_type "
                f"{assessment['assessor_type']!r}"
            )
        if not str(assessment["assessor_id"]).strip():
            errors.append(f"{fixture_id}: empty assessor_id")
        if not str(assessment["raw_output_ref"]).strip():
            errors.append(f"{fixture_id}: empty raw_output_ref")
        notes = assessment["evidence_notes"]
        if not isinstance(notes, list) or not notes:
            errors.append(
                f"{fixture_id}: evidence_notes must be non-empty"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="验证专家合同测试夹具，并可评分 Agent 运行时返回的 JSONL。"
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--assessment-jsonl",
        type=Path,
        help=(
            "推荐。独立观察者对已冻结原始输出的结构化评估；"
            "除评分字段外必须包含 assessor_id、assessor_type、"
            "raw_output_ref 和 evidence_notes。"
        ),
    )
    input_group.add_argument(
        "--candidate-jsonl",
        type=Path,
        help=(
            "兼容旧接口。只校验评分字段，不证明评估独立性，"
            "不能单独作为真实 Agent 能力验证。"
        ),
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="提供 candidate JSONL 时要求覆盖全部夹具。",
    )
    args = parser.parse_args()

    suite = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    errors = validate_fixture_corpus(suite)
    assessment_path = (
        args.assessment_jsonl or args.candidate_jsonl
    )
    if assessment_path:
        candidates = load_candidates(assessment_path)
        errors.extend(
            evaluate_candidates(
                suite["fixtures"], candidates, require_all=args.require_all
            )
        )
        if args.assessment_jsonl:
            errors.extend(validate_assessment_provenance(candidates))

    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    counts = Counter(
        fixture["capability_id"] for fixture in suite["fixtures"]
    )
    print(
        "PASS fixture corpus: "
        f"{len(suite['fixtures'])} cases / {len(counts)} capabilities"
    )
    for capability in sorted(counts):
        print(f"PASS {capability}: {counts[capability]} cases")
    if args.assessment_jsonl:
        print("PASS independently assessed Agent outputs")
    elif args.candidate_jsonl:
        print(
            "PASS legacy candidate fields "
            "(not independent capability evidence)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
