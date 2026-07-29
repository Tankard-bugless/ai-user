"""Compile the participant-facing Word questionnaire to Tencent Survey DSL.

The Word document contains internal appendices after the participant
questionnaire. This compiler deliberately stops at "内部配置附录" and never
exports answer keys, scoring rules, report mappings, or review notes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document


OPTIONAL_IDS = {"Q11", "Q29"}
TEXT_TYPES = {"Q11": "单行文本题", "Q29": "多行文本题"}
IMA_URL = (
    "https://ima.qq.com/wiki/?shareId="
    "3f82c28e1844208f0d4489f0ef3057c012f070cdce772a8ee050212c899234fc"
)


def expected_configuration(source: Path) -> tuple[list[str], int, str]:
    if source.name.endswith("_v0.1.docx"):
        return ["C0"] + [f"Q{i}" for i in range(1, 32)], 198, "0.1.0"
    if source.name.endswith("_v0.2.docx"):
        return (
            ["C0", "S1"]
            + [f"Q{i}" for i in range(1, 10)]
            + ["Q9A"]
            + [f"Q{i}" for i in range(10, 33)],
            213,
            "0.2.0",
        )
    raise ValueError(f"Unsupported questionnaire version: {source.name}")


@dataclass
class Question:
    qid: str
    title: str
    instruction: str = ""
    options: list[str] = field(default_factory=list)
    skip_note: str = ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_questionnaire(source: Path) -> tuple[list[tuple[str, object]], list[Question], str]:
    document = Document(source)
    sequence: list[tuple[str, object]] = []
    questions: list[Question] = []
    current: Question | None = None
    participant_started = False

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = paragraph.style.name if paragraph.style else ""

        if text == "内部配置附录":
            break
        if style == "Heading 1" and text == "填写说明":
            participant_started = True
        if not participant_started:
            continue

        if style == "Heading 1":
            if text == "问卷结束":
                sequence.append(("completion", text))
            elif text != "填写说明":
                sequence.append(("section", text))
            continue

        if style == "Question":
            match = re.match(r"^(C0|S1|Q\d+(?:A)?)\.\s*(.+)$", text)
            if not match:
                raise ValueError(f"Cannot parse question paragraph: {text}")
            current = Question(qid=match.group(1), title=match.group(2))
            questions.append(current)
            sequence.append(("question", current))
            continue

        if current is None:
            continue
        if style == "Instruction":
            current.instruction = text
        elif style == "Option":
            current.options.append(re.sub(r"^☐\s*", "", text))
        elif style == "SkipNote":
            current.skip_note = re.sub(r"^跳转提示：\s*", "", text)

    expected_ids, expected_options, adapter_version = expected_configuration(source)
    actual_ids = [question.qid for question in questions]
    if actual_ids != expected_ids:
        raise ValueError(f"Unexpected question order: {actual_ids}")
    if sum(len(question.options) for question in questions) != expected_options:
        raise ValueError("Unexpected option count; refusing to export.")
    return sequence, questions, adapter_version


def question_type(question: Question) -> str:
    if question.qid in TEXT_TYPES:
        return TEXT_TYPES[question.qid]
    if "多选" in question.instruction:
        return "多选题"
    return "单选题"


def question_to_dsl(question: Question) -> str:
    setting = "选答" if question.qid in OPTIONAL_IDS else "必答"
    description_parts = [question.instruction]
    if question.skip_note:
        description_parts.append(question.skip_note)
    description = "；".join(part for part in description_parts if part)
    header = f"{question.qid}. {question.title}[{question_type(question)}][{setting}]"
    if description:
        header += f"({description})"
    lines = [header]
    lines.extend(question.options)
    return "\n".join(lines)


def compile_dsl(sequence: list[tuple[str, object]]) -> str:
    blocks = [
        "您是怎么选择和持有养老基金的？",
        (
            "本问卷面向当前持有或过去购买过养老目标基金的投资者，预计约 10 分钟。"
            "请根据最近一次实际购买经历作答；不确定时请直接选择“不确定”，无需猜测。"
            "问卷不主动收集姓名、联系方式、账户号码、购买金额或持仓截图，"
            "答案仅用于用户研究，不构成投资建议、风险测评或产品推荐。"
        ),
        (
            "填写即表示您自愿参与；您可以随时停止。若在 C0 选择“不同意”，"
            "系统将直接结束问卷。[段落说明]"
        ),
    ]

    for kind, payload in sequence:
        if kind == "section":
            blocks.extend(["=== 分页 ===", f"{payload}[段落说明]"])
        elif kind == "question":
            blocks.append(question_to_dsl(payload))
        elif kind == "completion":
            blocks.extend(
                [
                    "=== 分页 ===",
                    "感谢您的参与。[段落说明]",
                    (
                        "如想继续了解相关金融常识，可自愿访问"
                        f"[易方达基金 IMA 知识库]({IMA_URL})，"
                        "并搜索“养老目标基金”“目标日期基金”“目标风险基金”或“下滑曲线”。"
                        "是否访问不影响答卷，本研究也不会把访问行为作为研究变量或研究证据。"
                        "[段落说明]"
                    ),
                ]
            )
    return "\n\n".join(blocks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--dsl-out", required=True, type=Path)
    parser.add_argument("--manifest-out", required=True, type=Path)
    args = parser.parse_args()

    sequence, questions, adapter_version = parse_questionnaire(args.source)
    dsl = compile_dsl(sequence)

    if "内部配置附录" in dsl or "知识题答案与计分" in dsl:
        raise ValueError("Internal appendix content leaked into participant DSL.")
    if dsl.count("=== 分页 ===") != 9:
        raise ValueError("Unexpected page-break count.")

    args.dsl_out.parent.mkdir(parents=True, exist_ok=True)
    args.dsl_out.write_text(dsl, encoding="utf-8")
    manifest = {
        "adapter": "tencent-survey",
        "adapter_version": adapter_version,
        "source_document": args.source.name,
        "source_sha256": sha256(args.source),
        "scene": 1,
        "answerable_question_count": len(questions),
        "option_count": sum(len(question.options) for question in questions),
        "question_ids": [question.qid for question in questions],
        "optional_question_ids": sorted(OPTIONAL_IDS),
        "post_create_logic": [
            "C0=不同意 -> END",
            *(
                ["S1=没有 -> END"]
                if adapter_version == "0.2.0"
                else []
            ),
            "Q22=没有经历过或记不清 -> Q24",
        ],
        "manual_release_checks": [
            "Configure multi-select maximum selections.",
            "Configure mutually exclusive options.",
            "Confirm Q9A is represented as a five-point ordered response with a separate recall option.",
            "Confirm login and location collection are disabled.",
            "Confirm internal answer keys are absent.",
        ],
    }
    args.manifest_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "dsl": str(args.dsl_out),
                "manifest": str(args.manifest_out),
                "questions": len(questions),
                "options": manifest["option_count"],
                "page_breaks": dsl.count("=== 分页 ==="),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
