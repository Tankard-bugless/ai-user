"""Validate a Tencent Survey deployment against the source Word questionnaire."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path

from compile_questionnaire import (
    OPTIONAL_IDS,
    TEXT_TYPES,
    parse_questionnaire,
    question_type,
)


MCORTER = Path.home() / "AppData" / "Roaming" / "npm" / "mcporter.cmd"
CHOICE_TYPES = {"radio", "checkbox", "select", "star", "sort"}


def clean_text(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def get_survey(survey_id: int) -> dict:
    result = subprocess.run(
        [
            str(MCORTER),
            "call",
            "tencent-survey.get_survey",
            f"survey_id={survey_id}",
            "--output",
            "json",
            "--timeout",
            "120000",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def expected_online_type(qid: str, type_label: str) -> str:
    if qid in TEXT_TYPES:
        return "text" if TEXT_TYPES[qid] == "单行文本题" else "textarea"
    if type_label == "多选题":
        return "checkbox"
    # Q9A intentionally uses an ordered single-select implementation so that
    # "记不清" remains distinguishable from a missing response.
    return "radio"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survey-id", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--logic", type=Path, required=True)
    args = parser.parse_args()

    _, expected_questions, adapter_version = parse_questionnaire(args.source)
    survey = get_survey(args.survey_id)
    online_questions = [
        question
        for page in survey["pages"]
        for question in page["questions"]
        if question["type"] != "description"
    ]

    errors: list[str] = []
    if len(online_questions) != len(expected_questions):
        errors.append(
            f"question count {len(online_questions)} != {len(expected_questions)}"
        )

    for expected, actual in zip(expected_questions, online_questions, strict=False):
        expected_title = f"{expected.qid}. {expected.title}"
        actual_title = clean_text(actual.get("title", ""))
        if actual_title != expected_title:
            errors.append(f"{expected.qid} title mismatch: {actual_title!r}")
        expected_type = expected_online_type(expected.qid, question_type(expected))
        if actual.get("type") != expected_type:
            errors.append(
                f"{expected.qid} type {actual.get('type')} != {expected_type}"
            )
        expected_required = expected.qid not in OPTIONAL_IDS
        if bool(actual.get("required")) != expected_required:
            errors.append(
                f"{expected.qid} required {actual.get('required')} != {expected_required}"
            )
        if expected.options:
            actual_options = [
                clean_text(option.get("text", "")) for option in actual.get("options", [])
            ]
            if actual_options != expected.options:
                errors.append(f"{expected.qid} option mismatch")

    online_choice_options = sum(
        len(question.get("options", []))
        for question in online_questions
        if question["type"] in CHOICE_TYPES
    )
    expected_choice_options = sum(
        len(question.options) for question in expected_questions
    )
    if online_choice_options != expected_choice_options:
        errors.append(
            f"choice options {online_choice_options} != {expected_choice_options}"
        )

    expected_logic = args.logic.read_text(encoding="utf-8").strip()
    actual_logic = (survey.get("survey_dsl") or {}).get("code", "").strip()
    if actual_logic != expected_logic:
        errors.append("logic DSL mismatch")
    logic_errors = [
        error
        for error in ((survey.get("survey_dsl") or {}).get("errors") or [])
        if error
    ]
    if logic_errors:
        errors.append(f"logic errors: {logic_errors}")
    if survey.get("login_check") is not False:
        errors.append("login_check must be false")
    if survey.get("is_enabled_location") is not False:
        errors.append("is_enabled_location must be false")

    summary = {
        "survey_id": survey["id"],
        "hash": survey["hash"],
        "adapter_version": adapter_version,
        "state": survey["state"],
        "page_count": survey["page_count"],
        "answerable_question_count": len(online_questions),
        "choice_option_count": online_choice_options,
        "logic_rule_count": len([line for line in actual_logic.splitlines() if line]),
        "logic_error_count": len(logic_errors),
        "login_check": survey.get("login_check"),
        "location_collection": survey.get("is_enabled_location"),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
