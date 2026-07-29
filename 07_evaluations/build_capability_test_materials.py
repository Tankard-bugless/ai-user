from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
FIXTURE_PATH = (
    EVAL_DIR
    / "fixtures"
    / "capability-contract-fixtures.v0.2.0.json"
)
CATALOG_PATH = EVAL_DIR / "capability-test-catalog.v0.2.0.md"
BLIND_PACKET_PATH = (
    EVAL_DIR / "fixtures" / "blind-test-packets.v0.2.0.json"
)

CAPABILITY_LABELS = {
    "frame-research-question": "CAP-01 研究问题理解",
    "design-research-plan": "CAP-02 研究方案设计",
    "design-research-instrument": "CAP-03 研究工具设计",
    "review-research-quality": "CAP-04 研究质量审核",
    "synthesize-research-insights": "CAP-05 证据与洞察",
    "compose-research-report": "CAP-06 研究报告表达",
    "orchestrate-research-workflow": "CTRL-01 研究总控",
}
CARD_PATHS = {
    "frame-research-question": (
        "03_experts/cap-01-frame-research-question.md"
    ),
    "design-research-plan": (
        "03_experts/cap-02-design-research-plan.md"
    ),
    "design-research-instrument": (
        "03_experts/cap-03-design-research-instrument.md"
    ),
    "review-research-quality": (
        "03_experts/cap-04-review-research-quality.md"
    ),
    "synthesize-research-insights": (
        "03_experts/cap-05-synthesize-research-insights.md"
    ),
    "compose-research-report": (
        "03_experts/cap-06-compose-research-report.md"
    ),
    "orchestrate-research-workflow": (
        "03_experts/ctrl-01-orchestrate-research-workflow.md"
    ),
}
TEST_TYPE_LABELS = {
    "POSITIVE": "正向",
    "BOUNDARY": "边界",
    "ADVERSARIAL": "对抗",
    "REGRESSION": "回归",
    "INVESTOR_EDUCATION": "投资者教育",
    "VISUALIZATION": "可视化",
    "ACCESSIBILITY": "可访问性",
}


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def build() -> tuple[str, dict]:
    suite = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixtures = suite["fixtures"]
    counts = Counter(
        fixture["capability_id"] for fixture in fixtures
    )
    lines = [
        "---",
        "document_id: EVAL-CAPABILITY-TEST-CATALOG",
        "version: 0.2.0",
        "status: active",
        "last_updated: 2026-07-27",
        "---",
        "",
        "# 专家能力测试清单",
        "",
        "## 1. 这 39 条是什么",
        "",
        (
            "这些条目是七项能力的合成合同用例，不是 39 次真实调研，"
            "也不是已经完成的 39 次独立 Agent 调用。"
        ),
        "",
        (
            "每条用例定义一个输入情境及其应有的产物、路由、决策、"
            "必需行为和禁止行为。真实能力验证必须让待测 Agent "
            "只看到盲测包，再由独立观察者依据原始输出评分。"
        ),
        "",
        "## 2. 数量分布",
        "",
        "| 能力 | 数量 |",
        "|---|---:|",
    ]
    for capability, label in CAPABILITY_LABELS.items():
        lines.append(f"| {label} | {counts[capability]} |")
    lines.extend(
        [
            f"| 合计 | {len(fixtures)} |",
            "",
            "## 3. 完整清单",
            "",
        ]
    )
    for capability, label in CAPABILITY_LABELS.items():
        lines.extend(
            [
                f"### {label}",
                "",
                "| ID | 类型 | 给待测 Agent 的情境 | 期待产物 | 期待决策 | 下一路由 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for fixture in fixtures:
            if fixture["capability_id"] != capability:
                continue
            values = [
                fixture["fixture_id"],
                TEST_TYPE_LABELS[fixture["test_type"]],
                fixture["input_summary"],
                fixture["expected_output_artifact"],
                fixture["expected_decision"],
                fixture["expected_route"],
            ]
            lines.append(
                "| " + " | ".join(escape_cell(value) for value in values) + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## 4. 执行口径",
            "",
            "1. 待测 Agent 只能读取相应能力卡和盲测包，不能读取本清单或原始 fixture 中的期待答案。",
            "2. 原始回答必须先冻结，再由人工或独立评估 Agent 标注产物类型、路由、决策和行为证据。",
            "3. 评分脚本检查结构化观察结果是否符合合同；评分脚本本身不判断长文本语义。",
            "4. 合同通过不等于研究结论正确，关键金融事实、方法判断和 Gate 仍需人工复核。",
            "",
        ]
    )
    catalog = "\n".join(lines)
    blind_suite = {
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "packet_version": "0.2.0",
        "purpose": (
            "提供给待测 Agent 的无标准答案输入包。"
            "不得与 capability-test-catalog 或原始 fixture 同时提供。"
        ),
        "contains_expected_answers": False,
        "packets": [
            {
                "fixture_id": fixture["fixture_id"],
                "capability_id": fixture["capability_id"],
                "capability_version": fixture["capability_version"],
                "capability_card_path": CARD_PATHS[
                    fixture["capability_id"]
                ],
                "input_summary": fixture["input_summary"],
            }
            for fixture in fixtures
        ],
    }
    return catalog, blind_suite


def main() -> int:
    catalog, blind_suite = build()
    CATALOG_PATH.write_text(catalog + "\n", encoding="utf-8")
    BLIND_PACKET_PATH.write_text(
        json.dumps(blind_suite, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS generated capability test catalog and "
        f"{len(blind_suite['packets'])} blind packets"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
