from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd


CASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CASE_DIR.parents[1]
DEFAULT_SOURCE = Path(
    r"C:\Users\10247\Documents\xwechat_files\wxid_d5ht5v6ig82c22_fe60"
    r"\msg\file\2026-07\FOF问卷回答_200人.csv"
)
DATA_DIR = CASE_DIR / "formal_artifacts" / "data"
ARTIFACT_DIR = CASE_DIR / "formal_artifacts"
REPORT_DOCX = (
    PROJECT_ROOT
    / "output"
    / "doc"
    / "养老目标基金购买者认知与持有行为洞察报告_展示版.docx"
)
REPORT_PDF = (
    PROJECT_ROOT
    / "output"
    / "doc"
    / "养老目标基金购买者认知与持有行为洞察报告_展示版.pdf"
)

QUESTION_RE = re.compile(r"^\d+\.(C0|S1|Q\d+A?)\.\s*(.*)$")
ANSWER_PREFIX_RE = re.compile(r"^[A-Z]\.(.*)$")
MAX_SELECT_RE = re.compile(r"最多选\s*(\d+)\s*项")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actor(
    actor_id: str,
    actor_type: str,
    role: str,
    *,
    model_id: str | None = None,
    capability_version: str | None = None,
) -> dict:
    value = {"actor_id": actor_id, "actor_type": actor_type, "role": role}
    if model_id:
        value["model_id"] = model_id
    if capability_version:
        value["capability_version"] = capability_version
    return value


def artifact_ref(
    artifact_id: str,
    artifact_type: str,
    artifact_version: str,
    approval_id: str | None = None,
) -> dict:
    value = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
    }
    if approval_id:
        value["approval_id"] = approval_id
    return value


def governance_gap(gate_id: str, operational_effect: str, next_action: str) -> dict:
    return {
        "gate_id": gate_id,
        "status": "NOT_RECORDED",
        "reason": "该真实案例先于完整治理链落地运行，当时没有形成可验证的正式批准记录。",
        "operational_effect": operational_effect,
        "required_next_action": next_action,
        "retrospective_approval_prohibited": True,
    }


def parse_columns(columns: list[str]) -> tuple[dict[str, list[dict]], list[str]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    metadata_columns: list[str] = []
    for raw_column in columns:
        column = raw_column.lstrip("\ufeff")
        match = QUESTION_RE.match(column)
        if not match:
            metadata_columns.append(column)
            continue
        code, remainder = match.groups()
        option = None
        prompt = remainder
        if ":" in remainder:
            prompt, option = remainder.rsplit(":", 1)
        groups[code].append(
            {
                "raw_column": raw_column,
                "column": column,
                "prompt": prompt,
                "option": option,
            }
        )
    return dict(groups), metadata_columns


def normalize_single_answer(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    match = ANSWER_PREFIX_RE.match(text)
    return match.group(1).strip() if match else text


def selected_labels(row: pd.Series, group: list[dict]) -> list[str]:
    selected: list[str] = []
    for entry in group:
        value = row[entry["raw_column"]]
        if pd.isna(value) or not str(value).strip():
            continue
        selected.append(entry["option"] or str(value).strip())
    return selected


def question_answered(row: pd.Series, group: list[dict]) -> bool:
    return any(
        not pd.isna(row[entry["raw_column"]])
        and bool(str(row[entry["raw_column"]]).strip())
        for entry in group
    )


def load_items(instrument: dict) -> dict[str, dict]:
    items: dict[str, dict] = {}
    for section in instrument["survey_spec"]["sections"]:
        for item in section["items"]:
            items[item["item_id"].removeprefix("ITEM-")] = item
    return items


def prepare_normalized_data(
    source_path: Path, instrument: dict, expected_analysis: dict
) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    items = load_items(instrument)
    raw = pd.read_csv(
        source_path,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    raw.columns = [column.lstrip("\ufeff") for column in raw.columns]
    groups, metadata_columns = parse_columns(list(raw.columns))

    mapping_issues: list[str] = []
    for code, item in items.items():
        if code not in groups:
            mapping_issues.append(f"{code}: CSV 中缺少题目字段")
            continue
        group = groups[code]
        if item["item_type"] == "MULTI_SELECT":
            expected = {option["label"] for option in item["answer_options"]}
            actual = {entry["option"] for entry in group}
            if expected != actual:
                mapping_issues.append(
                    f"{code}: 多选字段不一致，缺少={sorted(expected-actual)}，"
                    f"多出={sorted(actual-expected)}"
                )
        elif len(group) != 1:
            mapping_issues.append(f"{code}: 预期 1 列，实际 {len(group)} 列")
    for code in groups:
        if code not in items:
            mapping_issues.append(f"{code}: CSV 中存在 InstrumentSpec 未定义题目")

    duration_column = "答题时长"
    durations = pd.to_numeric(raw[duration_column], errors="coerce")
    speed_threshold = float(durations.median()) / 3
    speed_flags = durations < speed_threshold
    required_codes = [
        code
        for code, item in items.items()
        if item.get("required") and code not in {"C0", "S1"}
    ]

    high_missing_flags: list[bool] = []
    logic_conflicts: dict[int, list[str]] = defaultdict(list)
    cap_violations: dict[int, list[str]] = defaultdict(list)
    for row_index, row in raw.iterrows():
        q22_answer = normalize_single_answer(row[groups["Q22"][0]["raw_column"]])
        expected_count = 0
        missing_count = 0
        for code in required_codes:
            if code == "Q23" and q22_answer == "没有经历过或记不清":
                continue
            expected_count += 1
            if not question_answered(row, groups[code]):
                missing_count += 1
        high_missing_flags.append(
            expected_count > 0 and missing_count / expected_count > 0.20
        )

        for code, item in items.items():
            if item.get("item_type") != "MULTI_SELECT":
                continue
            labels = selected_labels(row, groups[code])
            exclusive_labels = {
                option["label"]
                for option in item.get("answer_options", [])
                if option.get("exclusive")
            }
            if len(labels) > 1 and exclusive_labels.intersection(labels):
                logic_conflicts[row_index].append(
                    f"{code}:EXCLUSIVE_WITH_SUBSTANTIVE"
                )
            max_match = MAX_SELECT_RE.search(item.get("help_text", ""))
            if max_match and len(labels) > int(max_match.group(1)):
                cap_violations[row_index].append(f"{code}:ABOVE_SELECTION_CAP")

        if (
            q22_answer == "没有经历过或记不清"
            and question_answered(row, groups["Q23"])
        ):
            logic_conflicts[row_index].append("Q23:STRUCTURAL_MISSING_REQUIRED")

    answer_columns = [
        entry["raw_column"] for group in groups.values() for entry in group
    ]
    signatures = raw[answer_columns].astype(str).agg("\u241f".join, axis=1)
    duplicate_record_flags = signatures.duplicated(keep=False)

    normalized = pd.DataFrame(
        {
            "response_id": [
                f"RESP-OTF-{index + 1:04d}" for index in range(len(raw))
            ],
            "duration_seconds": durations,
            "speed_flag": speed_flags,
        }
    )
    exclusivity_corrections: Counter = Counter()
    for code, item in items.items():
        group = groups[code]
        if item.get("item_type") == "MULTI_SELECT":
            exclusive_labels = {
                option["label"]
                for option in item.get("answer_options", [])
                if option.get("exclusive")
            }
            values: list[list[str]] = []
            for _, row in raw.iterrows():
                labels = selected_labels(row, group)
                if len(labels) > 1 and exclusive_labels.intersection(labels):
                    labels = [
                        label for label in labels if label not in exclusive_labels
                    ]
                    exclusivity_corrections[code] += 1
                values.append(labels)
            normalized[code] = values
        else:
            normalized[code] = raw[group[0]["raw_column"]].map(
                normalize_single_answer
            )

    q22_not_applicable = normalized["Q22"] == "没有经历过或记不清"
    normalized.loc[q22_not_applicable, "Q23"] = normalized.loc[
        q22_not_applicable, "Q23"
    ].map(lambda _: [])

    correct_labels = {
        "Q17": "主要根据预计退休年份选择，接近目标日期时通常会调整资产配置",
        "Q18": "主要按照预设风险水平选择，并在策略范围内维持相应风险特征",
        "Q19": "随着目标日期接近，基金资产配置可能如何逐步调整",
        "Q20": "仍可能出现净值波动或亏损，不代表本金和收益有保证",
    }
    for code, correct_label in correct_labels.items():
        normalized[f"{code}_correct"] = normalized[code] == correct_label
    normalized["product_knowledge_score"] = (
        normalized["Q17_correct"].astype(int)
        + normalized["Q18_correct"].astype(int)
    )
    normalized["glide_knowledge_score"] = (
        normalized["Q19_correct"].astype(int)
        + normalized["Q20_correct"].astype(int)
    )
    normalized["all_knowledge_score"] = (
        normalized["product_knowledge_score"]
        + normalized["glide_knowledge_score"]
    )

    review_indexes = (
        set(logic_conflicts)
        | set(cap_violations)
        | set(normalized.index[normalized["speed_flag"]])
        | set(normalized.index[duplicate_record_flags])
        | set(index for index, value in enumerate(high_missing_flags) if value)
    )
    normalized["formal_review_signal"] = normalized.index.map(
        lambda index: index in review_indexes
    )
    normalized["formal_response_status"] = normalized[
        "formal_review_signal"
    ].map({True: "REVIEW_REQUIRED", False: "VALID"})
    normalized["working_analysis_included"] = True

    quality_rows: list[dict] = []
    for index, response_id in enumerate(normalized["response_id"]):
        signals: list[str] = []
        if bool(speed_flags.iloc[index]):
            signals.append("SPEEDING_SUSPECTED")
        signals.extend(logic_conflicts.get(index, []))
        signals.extend(cap_violations.get(index, []))
        if high_missing_flags[index]:
            signals.append("HIGH_CORE_MISSING")
        if bool(duplicate_record_flags.iloc[index]):
            signals.append("EXACT_DUPLICATE_SUSPECTED")
        quality_rows.append(
            {
                "response_id": response_id,
                "formal_response_status": (
                    "REVIEW_REQUIRED" if signals else "VALID"
                ),
                "working_analysis_included": True,
                "review_signals": ";".join(signals),
                "resolution_basis": (
                    "历史工作分析按确定性互斥修正及速度敏感性比较后纳入；"
                    "未保存逐条人工复核记录。"
                    if signals
                    else "未触发预设复核信号。"
                ),
            }
        )
    quality = pd.DataFrame(quality_rows)

    observed = {
        "raw_records": len(raw),
        "mapping_issue_count": len(mapping_issues),
        "speed_flag_records": int(speed_flags.sum()),
        "exclusive_conflict_records": len(logic_conflicts),
        "exclusive_corrections_by_question": dict(exclusivity_corrections),
        "multi_select_cap_violation_records": len(cap_violations),
        "high_missing_records": int(sum(high_missing_flags)),
        "exact_duplicate_records": int(duplicate_record_flags.sum()),
        "formal_review_signal_records": int(
            normalized["formal_review_signal"].sum()
        ),
        "duration_minimum": float(durations.min()),
        "duration_median": float(durations.median()),
        "duration_maximum": float(durations.max()),
        "speed_threshold": speed_threshold,
    }
    expected_quality = expected_analysis["data_quality"]
    checks = {
        "raw_records": expected_quality["raw_records"],
        "mapping_issue_count": expected_quality["mapping_issue_count"],
        "speed_flag_records": expected_quality["speed_flag_records"],
        "exclusive_conflict_records": expected_quality[
            "exclusive_conflict_records"
        ],
        "exclusive_corrections_by_question": expected_quality[
            "exclusive_corrections_by_question"
        ],
        "multi_select_cap_violation_records": expected_quality[
            "multi_select_cap_violation_records"
        ],
        "high_missing_records": expected_quality["high_missing_records"],
        "exact_duplicate_records": expected_quality["exact_duplicate_records"],
        "formal_review_signal_records": expected_quality[
            "formal_review_signal_records"
        ],
    }
    mismatches = {
        key: {"observed": observed[key], "expected": expected}
        for key, expected in checks.items()
        if observed[key] != expected
    }
    if mapping_issues or mismatches:
        raise RuntimeError(
            "CSV 复现结果与已登记分析口径不一致："
            + json.dumps(
                {"mapping_issues": mapping_issues, "mismatches": mismatches},
                ensure_ascii=False,
            )
        )

    for column in normalized.columns:
        if normalized[column].map(lambda value: isinstance(value, list)).any():
            normalized[column] = normalized[column].map(
                lambda value: (
                    json.dumps(value, ensure_ascii=False)
                    if isinstance(value, list)
                    else value
                )
            )

    field_mapping = {
        "mapping_version": "0.1.0",
        "project_id": "PROJ-OTF-001",
        "source_file": source_path.name,
        "source_sha256": sha256_file(source_path),
        "instrument_ref": artifact_ref(
            "INS-OTF-SURVEY-001", "InstrumentSpec", "0.2.0"
        ),
        "shape": {
            "rows": int(raw.shape[0]),
            "raw_columns": int(raw.shape[1]),
            "question_groups": len(groups),
            "excluded_platform_metadata_columns": len(metadata_columns),
        },
        "fields": [
            {
                "item_id": item["item_id"],
                "variable_name": item.get("variable_name", code),
                "item_type": item["item_type"],
                "source_columns": [
                    entry["column"] for entry in groups.get(code, [])
                ],
            }
            for code, item in items.items()
        ],
        "excluded_platform_metadata": [
            {
                "column": column,
                "reason": (
                    "平台元数据不属于问卷研究变量；IP、UA、地理位置等"
                    "不得进入脱敏分析数据。"
                ),
            }
            for column in metadata_columns
        ],
        "transformations": [
            "单选值移除平台生成的 A./B. 等前缀。",
            "多选值按 InstrumentSpec 选项文本转换为 JSON 数组。",
            "互斥选项与实质选项并存时，只移除互斥的无/不确定项。",
            "Q22 为无相关经历时，Q23 重编码为空数组并视为结构性缺失。",
            "Q17-Q20 按冻结版正确答案生成知识题正确标记与分数。",
            "速度、互斥冲突、缺失、超选和重复只生成复核信号，不自动排除。",
        ],
        "mapping_issues": mapping_issues,
    }
    return normalized, quality, field_mapping, observed


def evidence_unit(
    evidence_id: str,
    metric: str,
    numerator: int,
    denominator: int,
    item_ids: list[str],
    research_question_ids: list[str],
    hypothesis_ids: list[str],
    context: str,
) -> dict:
    formal_item_ids = [
        item_id if item_id.startswith("ITEM-") else f"ITEM-{item_id}"
        for item_id in item_ids
    ]
    return {
        "evidence_id": evidence_id,
        "evidence_type": "STATISTIC",
        "source_id": "SRC-OTF-SURVEY-NORMALIZED-001",
        "source_locator": {
            "scheme": "ROW_AND_ITEM_ID",
            "value": f"ALL_INCLUDED;ITEMS={','.join(formal_item_ids)};METRIC={evidence_id}",
        },
        "participant_or_record_id": "GROUP-ALL-200",
        "exact_content_or_value": {
            "count": numerator,
            "denominator": denominator,
            "percent": round(numerator / denominator * 100, 1),
        },
        "extraction_method": (
            "按冻结版字段映射对 200 份工作分析记录进行样本内描述统计；"
            "保留分子、分母、题目 ID 和复核限制。"
        ),
        "extracted_by": actor(
            "AGENT-CAP-05",
            "AGENT",
            "分析与洞察专家",
            model_id="codex",
            capability_version="0.4.0",
        ),
        "human_verified": False,
        "research_question_ids": research_question_ids,
        "hypothesis_ids": hypothesis_ids,
        "code_ids": [],
        "context": context,
        "quantitative_context": {
            "metric": metric,
            "numerator": numerator,
            "denominator": denominator,
            "item_ids": formal_item_ids,
            "filter_conditions": (
                "working_analysis_included=true；200 份均纳入历史工作分析。"
            ),
            "missing_value_handling": (
                "不插补；Q23 按跳转规则处理结构性缺失；多选互斥冲突"
                "按已记录的确定性规则修正。"
            ),
        },
    }


def build_insight_content() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    evidence_specs = [
        ("EVID-OTF-001", "目标日期与目标风险两题均答对", 79, ["Q17", "Q18"], ["RQ-002"], ["HYP-001"], "产品类型与选择逻辑理解。"),
        ("EVID-OTF-002", "四道知识题全部答对", 40, ["Q17", "Q18", "Q19", "Q20"], ["RQ-002", "RQ-003"], ["HYP-001", "HYP-002"], "产品类型、下滑曲线与风险边界综合理解。"),
        ("EVID-OTF-003", "购买前信息清晰度给出 4—5 分", 58, ["Q9A"], ["RQ-004"], ["HYP-003"], "购买前信息主观清晰度。"),
        ("EVID-OTF-004", "购买前主动比较下滑曲线", 7, ["Q8"], ["RQ-003"], ["HYP-002"], "无直接提示时的主动比较行为。"),
        ("EVID-OTF-005", "自报下滑曲线曾影响购买、类型或持有决策", 102, ["Q16"], ["RQ-003"], ["HYP-002"], "直接提示下的回忆性自报。"),
        ("EVID-OTF-006", "持有期从未查看或想看但找不到入口", 119, ["Q15"], ["RQ-003", "RQ-005"], ["HYP-002", "HYP-004"], "持有期配置路径查看行为。"),
        ("EVID-OTF-007", "购买触发：认可基金公司或管理团队", 63, ["Q6"], ["RQ-001", "RQ-004"], ["HYP-003"], "最近一次购买的触发因素。"),
        ("EVID-OTF-008", "购买触发：费率或 Y 份额安排", 52, ["Q6"], ["RQ-001", "RQ-004"], ["HYP-003"], "最近一次购买的触发因素。"),
        ("EVID-OTF-009", "购买触发：历史表现或排名", 51, ["Q6"], ["RQ-001", "RQ-004"], ["HYP-003"], "最近一次购买的触发因素。"),
        ("EVID-OTF-010", "主动比较：退休年份是否匹配", 87, ["Q8"], ["RQ-004"], ["HYP-003"], "购买前认真比较的信息。"),
        ("EVID-OTF-011", "主动比较：风险类型是否符合选择", 80, ["Q8"], ["RQ-004"], ["HYP-003"], "购买前认真比较的信息。"),
        ("EVID-OTF-012", "主动比较：历史业绩或排名", 75, ["Q8"], ["RQ-004"], ["HYP-003"], "购买前认真比较的信息。"),
        ("EVID-OTF-013", "最终最重要因素：风险类型", 41, ["Q9"], ["RQ-004"], ["HYP-003"], "购买决策最终最重要因素。"),
        ("EVID-OTF-014", "持有期不确定：未来资产配置变化", 55, ["Q25"], ["RQ-005", "RQ-006"], ["HYP-004"], "当前最希望澄清的持有期信息。"),
        ("EVID-OTF-015", "持有期不确定：现在承担的风险", 52, ["Q25"], ["RQ-005", "RQ-006"], ["HYP-004"], "当前最希望澄清的持有期信息。"),
        ("EVID-OTF-016", "持有期不确定：为什么调整资产配置", 45, ["Q25"], ["RQ-005", "RQ-006"], ["HYP-004"], "当前最希望澄清的持有期信息。"),
        ("EVID-OTF-017", "偏好形式：结合年龄或退休年份举例", 60, ["Q27"], ["RQ-006"], ["HYP-004"], "通俗呈现形式偏好。"),
        ("EVID-OTF-018", "偏好形式：资产配置表", 49, ["Q27"], ["RQ-006"], ["HYP-004"], "通俗呈现形式偏好。"),
        ("EVID-OTF-019", "偏好形式：一句话说明", 48, ["Q27"], ["RQ-006"], ["HYP-004"], "通俗呈现形式偏好。"),
        ("EVID-OTF-020", "偏好时点：第一次了解产品时", 63, ["Q28"], ["RQ-006"], ["HYP-004"], "投教与说明信息的触达时点偏好。"),
        ("EVID-OTF-021", "偏好时点：基金调整资产配置时", 53, ["Q28"], ["RQ-005", "RQ-006"], ["HYP-004"], "投教与说明信息的触达时点偏好。"),
        ("EVID-OTF-022", "偏好时点：市场波动较大时", 49, ["Q28"], ["RQ-005", "RQ-006"], ["HYP-004"], "投教与说明信息的触达时点偏好。"),
        ("EVID-OTF-023", "偏好形式：可自行搜索的知识库", 17, ["Q27"], ["RQ-006"], ["HYP-004"], "知识库作为次级自助入口的偏好。"),
    ]
    evidence_units = [
        evidence_unit(
            evidence_id,
            metric,
            numerator,
            200,
            item_ids,
            rq_ids,
            hyp_ids,
            context,
        )
        for (
            evidence_id,
            metric,
            numerator,
            item_ids,
            rq_ids,
            hyp_ids,
            context,
        ) in evidence_specs
    ]
    findings = [
        {
            "finding_id": "FINDING-OTF-001",
            "statement": "购买经历没有自动转化为稳定的产品类型、下滑曲线与风险边界理解。",
            "research_question_ids": ["RQ-002", "RQ-003", "RQ-004"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": ["EVID-OTF-001", "EVID-OTF-002", "EVID-OTF-003"],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份养老目标基金购买者答卷。",
            "conditions": "知识题和清晰度题只描述本次样本；主观清晰不等同于正确理解。",
            "confidence": "MEDIUM",
            "importance": "HIGH",
            "importance_rationale": "产品选择和风险理解是购买说明与投教设计的基础。",
            "limitations": ["没有独立认知访谈验证答错原因。", "100 份答卷保留未正式逐条解决的复核信号。"],
        },
        {
            "finding_id": "FINDING-OTF-002",
            "statement": "下滑曲线在主动比较中存在感较弱，但直接提示后自报使用并不低，说明知晓、主动查看与事后回忆不能合并为单一使用率。",
            "research_question_ids": ["RQ-003", "RQ-005"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": ["EVID-OTF-004", "EVID-OTF-005", "EVID-OTF-006"],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份答卷。",
            "conditions": "不同题目提示强度不同，只能并列解释。",
            "confidence": "MEDIUM",
            "importance": "HIGH",
            "importance_rationale": "决定了下滑曲线应如何展示以及如何测量真实使用。",
            "limitations": ["回忆性自报可能受题目提示影响。"],
        },
        {
            "finding_id": "FINDING-OTF-003",
            "statement": "购买触发信息与最终判断依据分成两层：品牌、费率和历史表现更像入口触发器，退休年份和风险类型更接近主动判断标准。",
            "research_question_ids": ["RQ-001", "RQ-004"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": ["EVID-OTF-007", "EVID-OTF-008", "EVID-OTF-009", "EVID-OTF-010", "EVID-OTF-011", "EVID-OTF-012", "EVID-OTF-013"],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份答卷。",
            "conditions": "触发为多选、最终最重要因素为单选，不直接比较绝对比例。",
            "confidence": "MEDIUM",
            "importance": "HIGH",
            "importance_rationale": "支持把吸引注意与支持判断设计为不同信息层。",
            "limitations": ["回答者可能用当前理解重构过去决策。"],
        },
        {
            "finding_id": "FINDING-OTF-004",
            "statement": "持有期信息缺口集中在当前风险、未来配置和配置调整原因。",
            "research_question_ids": ["RQ-005", "RQ-006"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": ["EVID-OTF-014", "EVID-OTF-015", "EVID-OTF-016"],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份答卷。",
            "conditions": "多选比例反映被选择频次，不等于业务优先级已批准。",
            "confidence": "MEDIUM",
            "importance": "HIGH",
            "importance_rationale": "说明长期养老产品的解释需求并未在购买完成时结束。",
            "limitations": ["没有测试现有持有页面的可发现性。"],
        },
        {
            "finding_id": "FINDING-OTF-005",
            "statement": "投教更适合采用具体情境、配置表和简短解释，并覆盖首次了解、配置调整和市场波动等时点；知识库更适合作为次级自助入口。",
            "research_question_ids": ["RQ-005", "RQ-006"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": ["EVID-OTF-017", "EVID-OTF-018", "EVID-OTF-019", "EVID-OTF-020", "EVID-OTF-021", "EVID-OTF-022", "EVID-OTF-023"],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份答卷。",
            "conditions": "表达偏好不能替代理解效果测试。",
            "confidence": "MEDIUM",
            "importance": "HIGH",
            "importance_rationale": "直接连接产品说明和投资者教育的内容、形式与时点设计。",
            "limitations": ["本轮没有比较具体材料版本的理解效果。"],
        },
    ]
    insights = [
        {
            "insight_id": "INSIGHT-OTF-001",
            "statement": "购买者处在“知道一些、但关键边界不稳定”的中间状态，增加术语曝光不能替代理解验证。",
            "source_finding_ids": ["FINDING-OTF-001", "FINDING-OTF-002"],
            "reasoning": "购买经历、术语接触和自报使用均存在，但综合知识正确率仍低；不同提示方式又产生显著不同的自报结果。",
            "alternative_explanations": ["知识题难度可能影响正确率。", "样本来源未知，不能代表市场总体。"],
            "decision_relevance": "产品说明应把核心机制与风险边界做成可验证的理解任务。",
            "applicable_scope": "本项目 200 份工作分析答卷及当前问卷口径。",
            "confidence": "MEDIUM",
        },
        {
            "insight_id": "INSIGHT-OTF-002",
            "statement": "入口触发与最终判断属于不同信息任务，应分别设计吸引注意的信息和支持选择的信息。",
            "source_finding_ids": ["FINDING-OTF-003"],
            "reasoning": "品牌、费率和历史表现更多出现在购买触发，而退休年份与风险类型更多进入主动比较和最终判断。",
            "alternative_explanations": ["多选与单选题型不同。", "回忆偏差可能改变对购买过程的复述。"],
            "decision_relevance": "支持采用分层信息架构，而不是把所有卖点放在同一层。",
            "applicable_scope": "本项目样本中的最近一次购买回忆。",
            "confidence": "MEDIUM",
        },
        {
            "insight_id": "INSIGHT-OTF-003",
            "statement": "投教不应只发生在购买前，配置变化和市场波动是持有人重新理解产品机制的关键时点。",
            "source_finding_ids": ["FINDING-OTF-004", "FINDING-OTF-005"],
            "reasoning": "持有期的主要不确定性与配置、风险和调整原因有关，偏好时点也覆盖配置变化和市场波动。",
            "alternative_explanations": ["偏好不等于真实使用。", "未测试具体材料，不能判断效果。"],
            "decision_relevance": "支持把持有陪伴和投资者教育纳入产品全生命周期。",
            "applicable_scope": "本项目样本表达的持有期信息需求。",
            "confidence": "MEDIUM",
        },
    ]
    recommendations = [
        {
            "recommendation_id": "REC-OTF-001",
            "recommendation_domain": "PRODUCT_OR_SERVICE",
            "statement": "购买说明采用“类型与匹配逻辑—当前配置与未来变化—风险边界”的三层信息顺序。",
            "source_insight_ids": ["INSIGHT-OTF-001", "INSIGHT-OTF-002"],
            "expected_effect": "让触发信息之后出现一条支持真实选择判断的清晰路径。",
            "risks": ["信息层级过多可能增加阅读负担。", "具体金融表述仍需事实与合规审核。"],
            "assumptions": ["产品页面可以调整信息顺序。"],
            "validation_needed": ["使用改版前后同口径知识题比较理解结果。", "记录完成时长和主观负担。"],
            "owner_suggestion": "产品内容负责人",
            "suggested_priority": "HIGH",
            "business_decision_status": "NOT_DECIDED",
        },
        {
            "recommendation_id": "REC-OTF-002",
            "recommendation_domain": "PRODUCT_OR_SERVICE",
            "statement": "持有页面提供可找到的当前配置、未来配置变化和调整原因，并在波动或配置调整时提示查看。",
            "source_insight_ids": ["INSIGHT-OTF-003"],
            "expected_effect": "减少持有人在关键时点无法解释产品变化的情况。",
            "risks": ["过度推送可能造成信息疲劳。", "信息更新频率需要与真实组合变化一致。"],
            "assumptions": ["可以获得经审核的配置与调整原因内容。"],
            "validation_needed": ["先做小范围可用性测试。", "验证用户能找到并正确解释信息。"],
            "owner_suggestion": "产品与持有陪伴负责人",
            "suggested_priority": "HIGH",
            "business_decision_status": "NOT_DECIDED",
        },
        {
            "recommendation_id": "REC-OTF-003",
            "recommendation_domain": "INVESTOR_EDUCATION",
            "statement": "投教优先解释目标日期/目标风险选择逻辑、下滑曲线、当前风险和市场波动边界，采用年龄示例、配置表和简短问答；IMA 仅作为答题后的可选自助入口。",
            "source_insight_ids": ["INSIGHT-OTF-001", "INSIGHT-OTF-003"],
            "expected_effect": "在不干扰核心测量的前提下，把已识别的理解缺口转化为分阶段学习内容。",
            "risks": ["链接内容和可用性可能变化。", "用户可能把通用知识误解为个性化投资建议。"],
            "assumptions": ["学习资源位于核心测量之后。"],
            "validation_needed": ["使用教育前后同口径理解题或材料版本对比。", "不以点击率替代理解效果。"],
            "owner_suggestion": "投资者教育与产品内容负责人",
            "suggested_priority": "HIGH",
            "related_learning_resource_ids": ["LR-IMA-OTF-001"],
            "investor_education_design": {
                "target_learning_need": "区分产品类型，理解下滑曲线、当前风险、配置变化和非保本边界。",
                "audience_scope": "本项目中知识题未全部答对、未查看配置路径或表达相关信息需求的购买者类型；不形成正式客户标签。",
                "content_focus": ["目标日期型与目标风险型的选择逻辑", "下滑曲线表示配置路径而非收益路径", "降低高波动资产比例不等于本金或收益保证", "当前配置、未来变化及调整原因"],
                "recommended_moments": ["首次了解产品时", "基金调整资产配置时", "市场波动较大时"],
                "recommended_formats": ["结合年龄或退休年份的例子", "资产配置表和简单下滑曲线图", "一句话说明与常见问题回答", "IMA 知识库作为次级自助入口"],
                "guardrails": ["不承诺收益或本金安全", "不推荐具体产品或赎回时点", "不把内容偏好或链接点击当作理解效果"],
                "effectiveness_validation": "使用教育前后同口径理解题或材料版本对比，验证是否减少误解。",
                "evidence_boundary": "建议仅依据本项目的需求和偏好；未测试具体材料效果，不外推为全部投资者的普遍结论。",
            },
            "business_decision_status": "NOT_DECIDED",
        },
    ]
    return evidence_units, findings, insights, recommendations


def build_fieldwork_package(
    now: str,
    source_path: Path,
    normalized_path: Path,
    quality_path: Path,
    mapping_path: Path,
    observed: dict,
    content_hashes: dict[str, str],
) -> dict:
    plan_ref = artifact_ref("RP-OTF-001", "ResearchPlan", "0.2.0")
    instrument_ref = artifact_ref(
        "INS-OTF-SURVEY-001", "InstrumentSpec", "0.2.0"
    )
    return {
        "metadata": {
            "schema_version": "0.2.0",
            "artifact_id": "FWP-OTF-001",
            "artifact_type": "FieldworkPackage",
            "artifact_version": "0.1.0",
            "project_id": "PROJ-OTF-001",
            "title": "养老目标基金购买者问卷执行与数据质量包",
            "language": "zh-CN",
            "lifecycle_status": "DRAFT",
            "created_at": now,
            "updated_at": now,
            "created_by": actor(
                "SYSTEM-FIELDWORK-PACKAGER",
                "SYSTEM",
                "CSV 字段映射、脱敏与质量处理服务",
            ),
            "upstream_refs": [plan_ref, instrument_ref],
            "content_classification": "REAL",
            "sensitivity_level": "INTERNAL",
            "contains_personal_data": False,
            "change_summary": (
                "把已完成问卷的原始文件清单、脱敏字段映射、逐条质量信号、"
                "历史分析纳入口径和治理缺口封装为正式执行包；未补造 Gate 2。"
            ),
            "extensions": {
                "fieldwork.source_sha256": content_hashes["raw"],
                "fieldwork.mapping_sha256": content_hashes["mapping"],
                "fieldwork.normalized_sha256": content_hashes["normalized"],
                "fieldwork.quality_sha256": content_hashes["quality"],
            },
        },
        "research_plan_ref": plan_ref,
        "gate_2_governance_gap": governance_gap(
            "GATE_2",
            (
                "问卷已实际发布并回收，ResearchPlan 与 InstrumentSpec 仍为 DRAFT；"
                "本执行包只能登记为 DRAFT，不能宣称按正式 Gate 2 批准版本执行。"
            ),
            (
                "本案例继续作为内部复盘与答辩演示材料；任何对外发布需基于当前"
                "产物重新完成相应审核。未来新项目必须在发布前取得真实 Gate 2。"
            ),
        ),
        "instrument_refs": [instrument_ref],
        "execution_summary": {
            "fieldwork_scope": "MAIN",
            "status": "COMPLETED",
            "started_at": "2026-07-24T10:01:15+08:00",
            "ended_at": "2026-07-24T14:29:30+08:00",
            "timezone": "Asia/Shanghai",
            "method_completion": [
                {
                    "method_id": "METHOD-SUR-OTF-001",
                    "instrument_ref": instrument_ref,
                    "planned": 200,
                    "invited": 200,
                    "started": 200,
                    "completed": 200,
                    "included": 200,
                    "excluded": 0,
                }
            ],
        },
        "participant_index": {
            "storage_uri": "formal_artifacts/data/normalized-responses.v0.1.0.csv",
            "content_hash": content_hashes["normalized"],
            "total_records": 200,
            "id_scheme": "RESP-OTF-NNNN；平台 IP、UA、地理位置和其他元数据不进入脱敏分析文件。",
            "contains_direct_identifiers": False,
            "contact_linkage_separated": True,
        },
        "consent_summary": {
            "consent_process": "问卷首页 C0 选择“同意并继续”后进入研究题目。",
            "consented": 200,
            "declined": 0,
            "withdrawn": 0,
            "recording_consented": 0,
            "recording_declined": 0,
            "withdrawal_handling": "本项目无录音；若发生撤回，应在原始数据与后续派生数据中按稳定响应编号删除。",
        },
        "source_records": [
            {
                "source_id": "SRC-OTF-SURVEY-RAW-001",
                "source_type": "SURVEY_DATASET",
                "method_id": "METHOD-SUR-OTF-001",
                "instrument_ref": instrument_ref,
                "storage_uri": (
                    "urn:source:PROJ-OTF-001:FOF-questionnaire-200:"
                    f"sha256:{content_hashes['raw']}"
                ),
                "captured_at": "2026-07-24T14:29:30+08:00",
                "version": "raw-1",
                "content_hash": content_hashes["raw"],
                "sensitivity_level": "RESTRICTED",
                "contains_direct_identifiers": True,
                "deidentification_status": "PENDING",
                "quality_status": "RAW",
                "included_in_analysis": False,
                "locator_scheme": "ROW_AND_ITEM_ID",
            },
            {
                "source_id": "SRC-OTF-SURVEY-NORMALIZED-001",
                "source_type": "SURVEY_DATASET",
                "method_id": "METHOD-SUR-OTF-001",
                "instrument_ref": instrument_ref,
                "storage_uri": "formal_artifacts/data/normalized-responses.v0.1.0.csv",
                "captured_at": now,
                "version": "0.1.0",
                "content_hash": content_hashes["normalized"],
                "sensitivity_level": "INTERNAL",
                "contains_direct_identifiers": False,
                "deidentification_status": "COMPLETED",
                "quality_status": "CHECKED",
                "included_in_analysis": True,
                "locator_scheme": "ROW_AND_ITEM_ID",
            },
            {
                "source_id": "SRC-OTF-QUALITY-LOG-001",
                "source_type": "EXECUTION_LOG",
                "method_id": "METHOD-SUR-OTF-001",
                "instrument_ref": instrument_ref,
                "storage_uri": "formal_artifacts/data/response-quality.v0.1.0.csv",
                "captured_at": now,
                "version": "0.1.0",
                "content_hash": content_hashes["quality"],
                "sensitivity_level": "INTERNAL",
                "contains_direct_identifiers": False,
                "deidentification_status": "COMPLETED",
                "quality_status": "CHECKED",
                "included_in_analysis": False,
                "locator_scheme": "ROW_AND_ITEM_ID",
            },
            {
                "source_id": "SRC-OTF-FIELD-MAPPING-001",
                "source_type": "EXECUTION_LOG",
                "method_id": "METHOD-SUR-OTF-001",
                "instrument_ref": instrument_ref,
                "storage_uri": "formal_artifacts/data/field-mapping.v0.1.0.json",
                "captured_at": now,
                "version": "0.1.0",
                "content_hash": content_hashes["mapping"],
                "sensitivity_level": "INTERNAL",
                "contains_direct_identifiers": False,
                "deidentification_status": "NOT_REQUIRED",
                "quality_status": "CHECKED",
                "included_in_analysis": False,
                "locator_scheme": "OTHER",
            },
        ],
        "fieldwork_events": [
            {
                "event_id": "EVENT-OTF-FIELD-START",
                "event_type": "FIELDWORK_STARTED",
                "occurred_at": "2026-07-24T10:01:15+08:00",
                "description": "按平台返回的最早开始答题时间登记主问卷开始。",
                "resolution_status": "NOT_APPLICABLE",
            },
            {
                "event_id": "EVENT-OTF-NO-GATE2",
                "event_type": "PROCESS_DEVIATION",
                "occurred_at": "2026-07-24T10:01:15+08:00",
                "description": "问卷发布前没有形成正式 Gate 2 ApprovalRecord。",
                "resolution_status": "ACCEPTED_RISK",
                "resolution": "禁止追溯补造批准；所有后续正式产物保持 DRAFT 并标明治理缺口。",
            },
            {
                "event_id": "EVENT-OTF-FOMO-LOGIC",
                "event_type": "PROCESS_DEVIATION",
                "occurred_at": "2026-07-24T14:29:30+08:00",
                "description": "FOMO 团队部署未启用自定义互斥与部分跳转逻辑，导致互斥项和实质选项并存。",
                "resolution_status": "RESOLVED",
                "resolution": "保留实质选项、删除互斥的无/不确定项；Q23 按 Q22 重编码为结构性缺失，并保存逐条质量信号。",
            },
            {
                "event_id": "EVENT-OTF-FIELD-END",
                "event_type": "FIELDWORK_COMPLETED",
                "occurred_at": "2026-07-24T14:29:30+08:00",
                "description": "按平台返回的最晚结束答题时间登记本批 200 份问卷回收完成。",
                "resolution_status": "NOT_APPLICABLE",
            },
        ],
        "learning_resource_delivery": [
            {
                "resource_id": "LR-IMA-OTF-001",
                "instrument_ref": instrument_ref,
                "placement": "COMPLETION_PAGE",
                "delivery_status": "CONFIGURED",
                "checked_at": "2026-07-23T19:18:00+08:00",
                "evidence_use": "NOT_RESEARCH_EVIDENCE",
                "notes": "冻结工具中已配置链接；未保存发布后可用性复核记录，不记录点击或停留，也不作为研究证据。",
            }
        ],
        "data_quality": {
            "overall_status": "PASS_WITH_ISSUES",
            "quality_checks": [
                {
                    "check_id": "DQ-OTF-MAPPING",
                    "label": "CSV 字段与 InstrumentSpec 映射",
                    "status": "PASS",
                    "details": "35 个题目组完成映射，未发现缺失题目或未定义题目。",
                },
                {
                    "check_id": "DQ-OTF-PRIVACY",
                    "label": "平台元数据剔除",
                    "status": "PASS",
                    "details": "IP、UA、地理位置、平台清洗字段等 15 列未进入脱敏分析数据。",
                },
                {
                    "check_id": "DQ-OTF-REVIEW",
                    "label": "单份答卷复核状态",
                    "status": "WARNING",
                    "details": f"{observed['formal_review_signal_records']} 份触发正式复核信号，但历史逐条人工解析记录未保存。",
                },
                {
                    "check_id": "DQ-OTF-SENSITIVITY",
                    "label": "低时长敏感性比较",
                    "status": "PASS",
                    "details": "排除 12 份低时长答卷后，已登记关键指标绝对变化为 0.2—2.2 个百分点。",
                },
                {
                    "check_id": "DQ-OTF-GOVERNANCE",
                    "label": "执行前 Gate 2",
                    "status": "WARNING",
                    "details": "未形成正式 Gate 2；不得把本执行包解释为合规放行记录。",
                },
            ],
            "response_status_summary": {
                "unassessed_count": 0,
                "valid_count": 100,
                "review_required_count": 100,
                "excluded_count": 0,
            },
            "reason_code_summary": [
                {"reason_code": "SPEEDING_SUSPECTED", "count": 12},
                {
                    "reason_code": "MULTISELECT_EXCLUSIVITY_CONFLICT",
                    "count": 94,
                },
            ],
            "dataset_status": "ANALYSIS_READY_WITH_LIMITS",
            "dataset_status_reason": (
                "历史工作分析实际纳入 200 份并完成互斥修正与速度敏感性比较；"
                "但 100 份正式复核信号没有逐条人工解决记录，因此该状态仅描述"
                "既有内部分析用途，不是对原质量计划的完全合规结论。"
            ),
            "excluded_records": [],
            "missing_data_summary": "核心必答题无高缺失记录；Q23 在 Q22 无相关经历时按设计重编码为结构性缺失。",
            "transcription_quality": {
                "applicable": False,
                "unclear_segments": 0,
                "review_rule": "本项目为结构化问卷，无逐字稿。",
            },
            "duplicate_handling": "按全部研究答案生成精确签名；未发现精确重复答卷。",
        },
        "deviations": [
            {
                "deviation_id": "DEV-OTF-GATE2",
                "planned_rule": "主调研发布前必须取得 Gate 2 正式批准。",
                "actual_execution": "问卷实际发布并回收，但未形成 Gate 2 ApprovalRecord。",
                "reason": "完整治理链尚未落地。",
                "affected_records": [],
                "impact_assessment": "不能宣称按正式批准版本执行；所有正式化产物保持 DRAFT。",
                "decision": "INCLUDE_WITH_LIMITATION",
            },
            {
                "deviation_id": "DEV-OTF-REVIEW-LOG",
                "planned_rule": "所有 REVIEW_REQUIRED 必须由研究人员逐条转为 VALID 或 EXCLUDED。",
                "actual_execution": "100 份触发信号的答卷在确定性互斥修正和速度敏感性比较后进入工作分析，未保存逐条人工决定记录。",
                "reason": "历史分析先于逐条质量日志机制。",
                "affected_records": [],
                "impact_assessment": "统计仅用于内部洞察草稿；外发前需要重新审核证据和质量边界。",
                "decision": "INCLUDE_WITH_LIMITATION",
            },
            {
                "deviation_id": "DEV-OTF-TIMESTAMP",
                "planned_rule": "平台执行时间与文件接收时间应形成一致时间链。",
                "actual_execution": "CSV 内的最晚答题时间晚于本地文件系统记录的接收时间。",
                "reason": "平台时区、导出时间或本地文件时间口径未保存，无法追溯确认。",
                "affected_records": [],
                "impact_assessment": "只使用日期描述调研期，不据此计算投放节奏或因果顺序。",
                "decision": "INCLUDE_WITH_LIMITATION",
            },
        ],
        "deidentification": {
            "status": "COMPLETED",
            "direct_identifier_rule": "平台 IP、UA、地理位置、自定义字段及其他非研究元数据不进入分析数据。",
            "replacement_rule": "每份答卷仅保留稳定编号 RESP-OTF-NNNN。",
            "linkage_storage_rule": "原始 CSV 保留在项目发起人提供的外部位置，不复制到 formal_artifacts；正式分析只引用内容哈希。",
            "completed_by": actor(
                "SYSTEM-FIELDWORK-PACKAGER",
                "SYSTEM",
                "CSV 字段映射、脱敏与质量处理服务",
            ),
            "completed_at": now,
        },
        "unresolved_issues": [
            {
                "risk_id": "RISK-OTF-SAMPLE",
                "category": "SAMPLE",
                "description": "未提供抽样框、投放渠道明细和代表性说明。",
                "likelihood": "HIGH",
                "impact": "HIGH",
                "mitigation": "所有比例只描述本次 200 份答卷，不外推市场总体。",
                "owner_role": "研究负责人",
            },
            {
                "risk_id": "RISK-OTF-REVIEW",
                "category": "DATA",
                "description": "100 份答卷的正式复核信号缺少逐条人工解析记录。",
                "likelihood": "HIGH",
                "impact": "MEDIUM",
                "mitigation": "保留逐条信号、确定性修正规则和敏感性比较；报告外发前重新人工审核。",
                "owner_role": "数据质量负责人",
            },
            {
                "risk_id": "RISK-OTF-GOVERNANCE",
                "category": "COMPLIANCE",
                "description": "Gate 2 未记录，后续 Gate 3 与 Gate 4 也未形成正式批准。",
                "likelihood": "HIGH",
                "impact": "HIGH",
                "mitigation": "禁止追溯补造；产物保持 DRAFT，限制为内部复盘与答辩演示。",
                "owner_role": "研究负责人",
            },
        ],
    }


def build_insight_package(now: str) -> dict:
    evidence_units, findings, insights, recommendations = build_insight_content()
    return {
        "metadata": {
            "schema_version": "0.2.0",
            "artifact_id": "IP-OTF-001",
            "artifact_type": "InsightPackage",
            "artifact_version": "0.1.0",
            "project_id": "PROJ-OTF-001",
            "title": "养老目标基金购买者认知与持有行为洞察包",
            "language": "zh-CN",
            "lifecycle_status": "DRAFT",
            "created_at": now,
            "updated_at": now,
            "created_by": actor(
                "AGENT-CAP-05",
                "AGENT",
                "分析与洞察专家",
                model_id="codex",
                capability_version="0.4.0",
            ),
            "upstream_refs": [
                artifact_ref(
                    "RB-OTF-001",
                    "ResearchBrief",
                    "0.2.0",
                    approval_id="APR-OTF-G1-002",
                ),
                artifact_ref("RP-OTF-001", "ResearchPlan", "0.2.0"),
                artifact_ref("FWP-OTF-001", "FieldworkPackage", "0.1.0"),
            ],
            "content_classification": "REAL",
            "sensitivity_level": "INTERNAL",
            "contains_personal_data": False,
            "change_summary": "把既有 analysis-results 转换为证据—发现—洞察—建议的正式可追溯结构；未形成 Gate 3 批准。",
        },
        "research_brief_ref": artifact_ref(
            "RB-OTF-001",
            "ResearchBrief",
            "0.2.0",
            approval_id="APR-OTF-G1-002",
        ),
        "research_plan_ref": artifact_ref(
            "RP-OTF-001", "ResearchPlan", "0.2.0"
        ),
        "fieldwork_package_refs": [
            artifact_ref("FWP-OTF-001", "FieldworkPackage", "0.1.0")
        ],
        "analysis_scope": {
            "included_source_ids": ["SRC-OTF-SURVEY-NORMALIZED-001"],
            "excluded_source_ids": [
                "SRC-OTF-SURVEY-RAW-001",
                "SRC-OTF-QUALITY-LOG-001",
                "SRC-OTF-FIELD-MAPPING-001",
            ],
            "included_method_ids": ["METHOD-SUR-OTF-001"],
            "sample_scope": "历史工作分析纳入 200 份完成答卷；只支持本项目样本内的描述与方向性判断。",
            "analysis_started_at": "2026-07-24T11:25:27+08:00",
            "analysis_completed_at": "2026-07-24T11:49:57+08:00",
        },
        "codebook": {
            "version": "0.1.0",
            "approach": "按研究问题和冻结版分析计划建立演绎指标；不从开放题生成正式人物标签。",
            "codes": [
                {
                    "code_id": "CODE-OTF-KNOWLEDGE",
                    "label": "产品机制与风险边界理解",
                    "definition": "Q17—Q20 的预设正确作答及组合正确率。",
                    "include_when": "按冻结版正确答案计算单题和组合得分。",
                    "exclude_when": "自报听说过、主观清晰度或购买经历不能替代理解正确。",
                    "research_question_ids": ["RQ-002", "RQ-003"],
                },
                {
                    "code_id": "CODE-OTF-GLIDE-USAGE",
                    "label": "下滑曲线知晓—查看—使用层级",
                    "definition": "区分听说过、购买前查看、持有期查看、主动比较和提示后自报影响。",
                    "include_when": "使用 Q13—Q16 与 Q8 的对应指标。",
                    "exclude_when": "不把不同提示强度的问题合并为单一使用率。",
                    "research_question_ids": ["RQ-003"],
                },
                {
                    "code_id": "CODE-OTF-DECISION-LAYERS",
                    "label": "购买触发与最终判断分层",
                    "definition": "分别呈现 Q6 触发因素、Q8 主动比较和 Q9 最重要因素。",
                    "include_when": "比较信息在决策链中的位置而非直接比较题型比例。",
                    "exclude_when": "不把多选触发率解释为最终决定权重。",
                    "research_question_ids": ["RQ-001", "RQ-004"],
                },
                {
                    "code_id": "CODE-OTF-HOLDING-GAP",
                    "label": "持有期信息缺口",
                    "definition": "当前风险、未来配置和调整原因等持有期不确定性。",
                    "include_when": "使用 Q25 与相关持有行为题。",
                    "exclude_when": "不把信息需求直接解释为产品缺陷。",
                    "research_question_ids": ["RQ-005", "RQ-006"],
                },
                {
                    "code_id": "CODE-OTF-EDUCATION",
                    "label": "投教内容、形式与时点",
                    "definition": "Q26—Q28 的学习内容、呈现形式和触达时点偏好。",
                    "include_when": "只作为投教设计输入和后续验证假设。",
                    "exclude_when": "不把偏好、点击或阅读意愿作为理解效果。",
                    "research_question_ids": ["RQ-006"],
                },
            ],
            "revision_notes": [
                "沿用 2026-07-24 已完成分析的字段、分母和确定性修正规则。",
                "正式化时补充证据 ID、适用范围、替代解释和决策边界。",
            ],
        },
        "analysis_log": [
            {
                "step_id": "ANALYSIS-OTF-IMPORT",
                "performed_at": "2026-07-24T11:25:27+08:00",
                "performed_by": actor(
                    "SYSTEM-CSV-IMPORT",
                    "SYSTEM",
                    "CSV 字段映射与脱敏服务",
                ),
                "method": "EXTRACTION",
                "input_refs": ["SRC-OTF-SURVEY-RAW-001"],
                "output_ids": [
                    "SRC-OTF-SURVEY-NORMALIZED-001",
                    "SRC-OTF-QUALITY-LOG-001",
                ],
                "parameters_or_rules": "按 InstrumentSpec 0.2.0 映射 35 个题组，剔除平台元数据，执行互斥修正与结构性缺失规则。",
                "notes": "原始 CSV 不复制到正式产物目录，只登记哈希。",
            },
            {
                "step_id": "ANALYSIS-OTF-STATS",
                "performed_at": "2026-07-24T11:49:57+08:00",
                "performed_by": actor(
                    "AGENT-CAP-05",
                    "AGENT",
                    "分析与洞察专家",
                    model_id="codex",
                    capability_version="0.4.0",
                ),
                "method": "STATISTICAL_SUMMARY",
                "input_refs": ["SRC-OTF-SURVEY-NORMALIZED-001"],
                "output_ids": [unit["evidence_id"] for unit in evidence_units],
                "parameters_or_rules": "样本内描述统计，所有比例保留分子、分母、题目 ID；不进行总体推断。",
                "notes": "所有 200 份进入历史工作分析，100 份正式复核信号未逐条人工解决。",
            },
            {
                "step_id": "ANALYSIS-OTF-SENSITIVITY",
                "performed_at": "2026-07-24T11:49:57+08:00",
                "performed_by": actor(
                    "AGENT-CAP-05",
                    "AGENT",
                    "分析与洞察专家",
                    model_id="codex",
                    capability_version="0.4.0",
                ),
                "method": "COMPARISON",
                "input_refs": ["SRC-OTF-SURVEY-NORMALIZED-001"],
                "output_ids": ["ANALYSIS-OTF-SENSITIVITY-001"],
                "parameters_or_rules": "比较全部 200 份与排除 12 份速度信号后的关键指标；记录绝对百分点差。",
                "notes": "关键指标变化 0.2—2.2 个百分点；该比较不替代逐条人工复核。",
            },
            {
                "step_id": "ANALYSIS-OTF-SYNTHESIS",
                "performed_at": now,
                "performed_by": actor(
                    "AGENT-CAP-05",
                    "AGENT",
                    "分析与洞察专家",
                    model_id="codex",
                    capability_version="0.4.0",
                ),
                "method": "SYNTHESIS",
                "input_refs": [unit["evidence_id"] for unit in evidence_units],
                "output_ids": [
                    *[item["finding_id"] for item in findings],
                    *[item["insight_id"] for item in insights],
                    *[item["recommendation_id"] for item in recommendations],
                ],
                "parameters_or_rules": "发现只描述证据，洞察补充机制和替代解释，建议保持 NOT_DECIDED。",
                "notes": "没有把项目内模式升级为正式客户标签。",
            },
        ],
        "evidence_units": evidence_units,
        "findings": findings,
        "insights": insights,
        "recommendations": recommendations,
        "candidate_segments": [],
        "candidate_tags": [],
        "learning_resource_recommendations": [
            {
                "resource_id": "LR-IMA-OTF-001",
                "recommendation_ids": ["REC-OTF-003"],
                "target_learning_need": "完成核心测量后，为希望继续了解养老目标基金常识的用户提供官方知识搜索入口。",
                "recommended_context": "问卷完成页或其他核心测量之后；不记录使用行为，不作为理解或购买意向证据。",
                "evidence_use": "NOT_RESEARCH_EVIDENCE",
            }
        ],
        "unanswered_questions": [
            {
                "question_id": "UQ-OTF-001",
                "statement": "三层购买说明是否能提高理解且不过度增加阅读负担？",
                "why_unanswered": "本轮没有测试改版材料。",
                "suggested_next_method": "认知访谈后进行前后版本同口径理解题比较。",
            },
            {
                "question_id": "UQ-OTF-002",
                "statement": "持有页面增加配置和调整原因后，用户是否能更快找到并正确解释信息？",
                "why_unanswered": "本轮没有可用性任务或行为数据。",
                "suggested_next_method": "用可点击原型开展任务型可用性测试。",
            },
            {
                "question_id": "UQ-OTF-003",
                "statement": "本次样本模式能否在明确抽样框和不同渠道中复现？",
                "why_unanswered": "未提供样本来源与抽样框。",
                "suggested_next_method": "按渠道和核心人群配额重新采集并预注册比较口径。",
            },
        ],
        "limitations": [
            "未提供抽样框、投放渠道和代表性说明，不能外推市场总体。",
            "100 份答卷触发正式复核信号但缺少逐条人工解析记录。",
            "FOMO 部署未启用部分互斥与跳转逻辑，虽按确定性规则修正，仍需保留执行限制。",
            "不同提示强度和不同题型的比例不能直接合并或进行因果解释。",
            "开放题存在完全相同文本，仅作轻量主题计数，不作为逐字引语或真实性证明。",
            "没有认知访谈、可用性任务或材料版本实验验证误解形成机制与建议效果。",
            "Gate 2 与 Gate 3 未形成正式批准，洞察包保持 DRAFT。",
        ],
        "ai_usage": [
            {
                "task": "CSV 字段映射、描述统计、证据封装、发现与建议草拟",
                "model_id": "codex",
                "capability_version": "0.4.0",
                "input_scope": "脱敏问卷回答、InstrumentSpec、ResearchBrief、ResearchPlan 和既有 analysis-results。",
                "output_scope": "正式 InsightPackage 草稿；不包含审批与业务决策。",
                "human_review_status": "PARTIALLY_REVIEWED",
            }
        ],
        "quality_summary": {
            "traceability_complete": True,
            "negative_cases_reviewed": False,
            "sample_scope_declared": True,
            "quantitative_denominators_complete": True,
            "quotes_source_located": True,
            "candidate_tags_not_promoted": True,
            "review_notes": "无逐字引语证据；所有正式统计保留分子、分母和题目 ID。报告内容曾由项目发起人迭代审阅，但未形成 Gate 3 正式批准。",
        },
    }


def build_research_report(
    now: str,
    docx_hash: str,
    pdf_hash: str,
    docx_size: int,
    pdf_size: int,
) -> dict:
    report_docx_uri = (
        "../../../output/doc/"
        + quote(REPORT_DOCX.name)
    )
    report_pdf_uri = (
        "../../../output/doc/"
        + quote(REPORT_PDF.name)
    )
    learning_resource = read_json(
        CASE_DIR / "instrument-spec.v0.2.0.json"
    )["learning_resources"][0]
    return {
        "metadata": {
            "schema_version": "0.2.0",
            "artifact_id": "RR-OTF-001",
            "artifact_type": "ResearchReport",
            "artifact_version": "0.1.0",
            "project_id": "PROJ-OTF-001",
            "title": "养老目标基金购买者认知与持有行为洞察报告",
            "language": "zh-CN",
            "lifecycle_status": "DRAFT",
            "created_at": now,
            "updated_at": now,
            "created_by": actor(
                "AGENT-CAP-06",
                "AGENT",
                "研究报告专家",
                model_id="codex",
                capability_version="0.4.0",
            ),
            "upstream_refs": [
                artifact_ref(
                    "RB-OTF-001",
                    "ResearchBrief",
                    "0.2.0",
                    approval_id="APR-OTF-G1-002",
                ),
                artifact_ref("RP-OTF-001", "ResearchPlan", "0.2.0"),
                artifact_ref("IP-OTF-001", "InsightPackage", "0.1.0"),
            ],
            "content_classification": "REAL",
            "sensitivity_level": "INTERNAL",
            "contains_personal_data": False,
            "change_summary": "把最终展示版 DOCX/PDF 登记为正式 ResearchReport 草稿；保留 Gate 3、Gate 4 未形成记录的真实边界。",
            "extensions": {
                "report.files": [
                    {
                        "format": "DOCX",
                        "uri": report_docx_uri,
                        "sha256": docx_hash,
                        "size_bytes": docx_size,
                    },
                    {
                        "format": "PDF",
                        "uri": report_pdf_uri,
                        "sha256": pdf_hash,
                        "size_bytes": pdf_size,
                    },
                ],
                "report.release_status": "INTERNAL_DRAFT_NO_GATE3_NO_GATE4",
            },
        },
        "research_brief_ref": artifact_ref(
            "RB-OTF-001",
            "ResearchBrief",
            "0.2.0",
            approval_id="APR-OTF-G1-002",
        ),
        "research_plan_ref": artifact_ref(
            "RP-OTF-001", "ResearchPlan", "0.2.0"
        ),
        "insight_package_ref": artifact_ref(
            "IP-OTF-001", "InsightPackage", "0.1.0"
        ),
        "gate_3_governance_gap": governance_gap(
            "GATE_3",
            (
                "最终展示版报告已制作并经多轮内容、逻辑和排版迭代，但没有形成"
                "证据审核 Gate 3 的正式 ApprovalRecord；ResearchReport 只能登记为 DRAFT。"
            ),
            (
                "内部答辩可明确展示其历史状态；任何新的正式发布应由研究负责人、"
                "数据质量负责人和必要的金融事实/合规角色完成当前版本审核。"
            ),
        ),
        "report_profile": {
            "audiences": [
                "内部管理者",
                "产品与服务团队",
                "投资者教育团队",
                "用户研究团队",
            ],
            "purpose": "展示本次养老目标基金购买者调研的研究目的、关键判断、证据链、产品与投教建议，并作为 AI 辅助用户研究工作流的真实案例。",
            "confidentiality": "INTERNAL",
            "distribution_scope": "仅限内部答辩、复盘与决策讨论；未取得 Gate 4，不得作为外部正式研究结论发布。",
            "report_date": "2026-07-27",
        },
        "executive_summary": {
            "context": "本研究围绕已经购买过养老目标基金的人群，考察其购买路径、产品类型认知、下滑曲线理解、持有行为和信息需求，并补充投资者教育建议。",
            "key_answers": [
                {
                    "research_question_id": "RQ-001",
                    "answer": "购买触发更多出现品牌/团队、费率/Y 份额和历史表现；这些入口信息不等于最终判断依据。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-003"],
                },
                {
                    "research_question_id": "RQ-002",
                    "answer": "购买经历未自动转化为稳定的产品类型理解；目标日期与目标风险两题均答对 79/200。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-001"],
                },
                {
                    "research_question_id": "RQ-003",
                    "answer": "下滑曲线主动比较比例很低，但直接提示后的自报影响率较高，知晓、查看、使用和理解必须分开测量。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-002"],
                },
                {
                    "research_question_id": "RQ-004",
                    "answer": "退休年份和风险类型更接近主动比较与最终判断标准，品牌、费率和历史表现更像购买入口触发。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-003"],
                },
                {
                    "research_question_id": "RQ-005",
                    "answer": "持有期的主要信息缺口集中在当前风险、未来配置和配置调整原因，说明解释需求贯穿持有周期。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-004"],
                },
                {
                    "research_question_id": "RQ-006",
                    "answer": "年龄/退休年份示例、资产配置表和简短说明更适合作为优先验证的表达形式；知识库是次级自助入口。",
                    "confidence": "MEDIUM",
                    "finding_ids": ["FINDING-OTF-005"],
                },
            ],
            "key_recommendation_ids": [
                "REC-OTF-001",
                "REC-OTF-002",
                "REC-OTF-003",
            ],
            "limitation_summary": "样本来源与抽样框未知，100 份答卷保留未逐条人工解决的复核信号，且未形成 Gate 2、Gate 3、Gate 4 正式记录，因此结论只用于内部样本内判断。",
        },
        "methodology": {
            "methods": ["远程非主持结构化问卷", "样本内描述统计", "低时长记录敏感性比较", "证据—发现—洞察—建议链式综合"],
            "fieldwork_period": {
                "started_on": "2026-07-24",
                "completed_on": "2026-07-24",
            },
            "sample_completion": "回传 200 份完成答卷；历史工作分析纳入 200 份，其中 100 份存在正式复核信号。",
            "exclusions": [
                "无硬排除。",
                "原始 CSV 的 IP、UA、地理位置和平台元数据不进入分析。",
            ],
            "analysis_approach": "按 InstrumentSpec 映射字段，修正已知互斥冲突与结构性缺失，生成知识题和分群指标；所有正式比例保留分子、分母和题目 ID，并对 12 份低时长记录进行敏感性比较。",
            "ai_role": "AI 用于字段映射、质量信号生成、描述统计、可视化与报告草拟；没有替代人工审批、金融事实审核或业务决策。",
        },
        "finding_presentations": [
            {
                "finding_id": "FINDING-OTF-001",
                "headline": "购买过，不等于已经理解",
                "statement": "产品类型、下滑曲线与风险边界的综合理解仍不稳定。",
                "sample_scope": "历史工作分析纳入的 200 份答卷。",
                "confidence": "MEDIUM",
                "evidence_highlights": [
                    {"evidence_id": "EVID-OTF-001", "display_text": "目标日期与目标风险两题均答对 79/200（39.5%）"},
                    {"evidence_id": "EVID-OTF-002", "display_text": "四道知识题全部答对 40/200（20.0%）"},
                    {"evidence_id": "EVID-OTF-003", "display_text": "购买前信息清晰度给 4—5 分 58/200（29.0%）"},
                ],
                "negative_case_note": "本轮没有形成可定位的定性反例证据。",
                "limitation_note": "知识题正确率受题目难度影响，不能外推市场总体。",
            },
            {
                "finding_id": "FINDING-OTF-002",
                "headline": "下滑曲线：主动比较弱，提示后自报不低",
                "statement": "不同提示强度产生不同回答，不能合并为单一使用率。",
                "sample_scope": "历史工作分析纳入的 200 份答卷。",
                "confidence": "MEDIUM",
                "evidence_highlights": [
                    {"evidence_id": "EVID-OTF-004", "display_text": "购买前主动比较 7/200（3.5%）"},
                    {"evidence_id": "EVID-OTF-005", "display_text": "提示后自报影响过决策 102/200（51.0%）"},
                    {"evidence_id": "EVID-OTF-006", "display_text": "持有期从未查看或想看但找不到 119/200（59.5%）"},
                ],
                "negative_case_note": "提示后自报影响较高，是对“普遍不用”的重要矛盾证据。",
                "limitation_note": "回忆性自报可能受直接提示影响。",
            },
            {
                "finding_id": "FINDING-OTF-003",
                "headline": "购买触发与最终判断分成两层",
                "statement": "品牌、费率和历史表现更像入口，退休年份和风险类型更接近判断。",
                "sample_scope": "历史工作分析纳入的 200 份答卷。",
                "confidence": "MEDIUM",
                "evidence_highlights": [
                    {"evidence_id": "EVID-OTF-007", "display_text": "购买触发：品牌/团队 63/200（31.5%）"},
                    {"evidence_id": "EVID-OTF-010", "display_text": "主动比较退休年份 87/200（43.5%）"},
                    {"evidence_id": "EVID-OTF-013", "display_text": "最终最重要因素首位为风险类型 41/200（20.5%）"},
                ],
                "negative_case_note": "历史表现同时出现在触发和主动比较中，信息角色并非完全分离。",
                "limitation_note": "多选触发和单选最重要因素不可直接比较绝对比例。",
            },
            {
                "finding_id": "FINDING-OTF-004",
                "headline": "持有期需要解释当前风险和未来变化",
                "statement": "信息缺口集中在未来配置、当前风险与调整原因。",
                "sample_scope": "历史工作分析纳入的 200 份答卷。",
                "confidence": "MEDIUM",
                "evidence_highlights": [
                    {"evidence_id": "EVID-OTF-014", "display_text": "未来资产配置变化 55/200（27.5%）"},
                    {"evidence_id": "EVID-OTF-015", "display_text": "现在承担的风险 52/200（26.0%）"},
                    {"evidence_id": "EVID-OTF-016", "display_text": "为什么调整配置 45/200（22.5%）"},
                ],
                "negative_case_note": "“没有明显不确定”仅 3/200，但多选题设计可能强化需求表达。",
                "limitation_note": "信息需求频次不等于改版优先级已经获批。",
            },
            {
                "finding_id": "FINDING-OTF-005",
                "headline": "投教应具体、可视，并覆盖关键持有时点",
                "statement": "具体示例、配置表和简短解释优先于单纯知识库入口。",
                "sample_scope": "历史工作分析纳入的 200 份答卷。",
                "confidence": "MEDIUM",
                "evidence_highlights": [
                    {"evidence_id": "EVID-OTF-017", "display_text": "年龄/退休年份示例 60/200（30.0%）"},
                    {"evidence_id": "EVID-OTF-018", "display_text": "资产配置表 49/200（24.5%）"},
                    {"evidence_id": "EVID-OTF-023", "display_text": "可自行搜索的知识库 17/200（8.5%）"},
                ],
                "negative_case_note": "知识库偏好较低，支持把 IMA 保留为次级自助入口而非主线。",
                "limitation_note": "偏好不能替代理解效果测试。",
            },
        ],
        "insight_presentations": [
            {
                "insight_id": "INSIGHT-OTF-001",
                "headline": "认知处于中间态",
                "explanation": "购买者知道部分概念，但关键机制和风险边界不稳定；应以可验证理解替代术语曝光。",
                "applicable_scope": "本项目 200 份工作分析答卷。",
                "confidence": "MEDIUM",
            },
            {
                "insight_id": "INSIGHT-OTF-002",
                "headline": "入口信息与判断信息不是一回事",
                "explanation": "吸引注意的信息和支持选择的信息承担不同任务，需要分层设计。",
                "applicable_scope": "本项目最近一次购买回忆。",
                "confidence": "MEDIUM",
            },
            {
                "insight_id": "INSIGHT-OTF-003",
                "headline": "投教应进入持有期",
                "explanation": "配置调整和市场波动会重新激活理解需求，持有陪伴应解释变化而非只展示收益。",
                "applicable_scope": "本项目样本表达的持有期需求。",
                "confidence": "MEDIUM",
            },
        ],
        "recommendation_presentations": [
            {
                "recommendation_id": "REC-OTF-001",
                "action": "重构购买说明为三层信息路径。",
                "rationale": "入口触发和最终判断分层，综合知识正确率仍低。",
                "expected_effect": "提高类型、配置变化和风险边界的可理解性。",
                "validation_next_step": "改版前后使用同口径理解题比较，并记录阅读负担。",
                "suggested_owner": "产品内容负责人",
                "suggested_priority": "HIGH",
                "decision_status": "RESEARCH_PROPOSAL",
            },
            {
                "recommendation_id": "REC-OTF-002",
                "action": "在持有页面提供当前配置、未来变化和调整原因。",
                "rationale": "这些内容是样本中最集中的持有期信息缺口。",
                "expected_effect": "支持持有人在波动和配置调整时重新理解产品。",
                "validation_next_step": "开展任务型可用性测试，验证可发现性与正确解释。",
                "suggested_owner": "产品与持有陪伴负责人",
                "suggested_priority": "HIGH",
                "decision_status": "RESEARCH_PROPOSAL",
            },
            {
                "recommendation_id": "REC-OTF-003",
                "action": "建设覆盖购买前、配置调整和市场波动时点的投教内容组合。",
                "rationale": "用户偏好具体情境、配置表与简短解释，且需求延伸至持有期。",
                "expected_effect": "把理解缺口转化为分阶段、可验证的学习路径。",
                "validation_next_step": "使用前后同口径理解题或材料版本实验，不以点击率代替效果。",
                "suggested_owner": "投资者教育与产品内容负责人",
                "suggested_priority": "HIGH",
                "decision_status": "RESEARCH_PROPOSAL",
            },
        ],
        "investor_education_section": {
            "applicable": True,
            "summary": "投教重点应从泛化科普转向产品类型选择逻辑、下滑曲线、当前风险与配置变化，并覆盖关键持有情境。",
            "recommendation_ids": ["REC-OTF-003"],
            "priority_learning_needs": [
                "目标日期型与目标风险型的选择逻辑",
                "下滑曲线是配置路径而非收益保证",
                "当前风险、未来配置与调整原因",
                "市场波动不等于产品机制失效",
            ],
            "audience_scope": "本项目中知识题未全部答对、未查看配置路径或表达相关信息需求的购买者类型；不形成正式客户标签。",
            "recommended_moments": [
                "第一次了解产品时",
                "基金调整资产配置时",
                "市场波动较大时",
            ],
            "recommended_formats": [
                "结合年龄或退休年份的例子",
                "资产配置表与简单下滑曲线图",
                "一句话说明与常见问题回答",
                "IMA 知识库作为次级自助入口",
            ],
            "guardrails": [
                "不承诺收益或本金安全",
                "不推荐具体产品或赎回时点",
                "不把偏好、链接点击或阅读意愿当作理解效果",
            ],
            "effectiveness_boundary": "本轮只识别学习需求与形式偏好；投教效果必须通过前后同口径理解题或材料版本比较另行验证。",
        },
        "learning_resources": [learning_resource],
        "limitations": [
            "未提供抽样框、投放渠道和代表性说明。",
            "100 份答卷触发正式复核信号但缺少逐条人工解析记录。",
            "FOMO 部署未启用部分互斥与跳转逻辑。",
            "不同提示强度和题型的比例不可直接合并或因果解释。",
            "没有认知访谈、可用性任务或材料版本实验。",
            "Gate 2、Gate 3、Gate 4 均未形成完整历史记录。",
        ],
        "unanswered_questions": [
            "三层购买说明能否提高理解且不过度增加阅读负担？",
            "持有页面改版后，用户能否找到并正确解释配置变化？",
            "本次样本模式能否在明确抽样框和不同渠道中复现？",
        ],
        "appendices": [
            {
                "appendix_id": "APP-OTF-001",
                "title": "FieldworkPackage",
                "content_type": "ARTIFACT",
                "reference": artifact_ref(
                    "FWP-OTF-001", "FieldworkPackage", "0.1.0"
                ),
            },
            {
                "appendix_id": "APP-OTF-002",
                "title": "InsightPackage",
                "content_type": "ARTIFACT",
                "reference": artifact_ref(
                    "IP-OTF-001", "InsightPackage", "0.1.0"
                ),
            },
            {
                "appendix_id": "APP-OTF-003",
                "title": "最终展示版 DOCX",
                "content_type": "OTHER",
                "reference": report_docx_uri,
            },
            {
                "appendix_id": "APP-OTF-004",
                "title": "最终展示版 PDF",
                "content_type": "OTHER",
                "reference": report_pdf_uri,
            },
        ],
        "decision_boundary": {
            "contains_business_decisions": False,
            "statement": "报告中的建议属于研究提案，不构成已批准业务方案、个性化投资建议或对外发布许可。",
        },
        "quality_declaration": {
            "all_claims_traceable": True,
            "numbers_match_insight_package": True,
            "limitations_visible": True,
            "personal_data_removed": True,
            "human_review_required_before_release": True,
        },
    }


def build_manifest(
    now: str,
    source_path: Path,
    output_files: list[Path],
) -> dict:
    return {
        "manifest_version": "0.1.0",
        "project_id": "PROJ-OTF-001",
        "generated_at": now,
        "source": {
            "logical_name": source_path.name,
            "sha256": sha256_file(source_path),
            "size_bytes": source_path.stat().st_size,
            "copied_into_project": False,
            "reason": "原始 CSV 含平台 IP、UA、地理位置等元数据，正式目录只保留哈希和脱敏派生文件。",
        },
        "outputs": [
            {
                "path": str(path.relative_to(CASE_DIR)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in output_files
        ],
        "governance": {
            "gate_1": "RECORDED: APR-OTF-G1-002",
            "gate_2": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "gate_3": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "gate_4": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "release_status": "INTERNAL_DRAFT",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="复现真实 CSV 处理并登记正式 Fieldwork/Insight/Report 产物。"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="原始腾讯问卷 CSV 路径；不会复制到项目目录。",
    )
    args = parser.parse_args()
    source_path = args.source.resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    for report_path in (REPORT_DOCX, REPORT_PDF):
        if not report_path.exists():
            raise FileNotFoundError(report_path)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

    instrument = read_json(CASE_DIR / "instrument-spec.v0.2.0.json")
    analysis = read_json(CASE_DIR / "analysis-results.v0.1.0.json")
    normalized, quality, mapping, observed = prepare_normalized_data(
        source_path, instrument, analysis
    )

    normalized_path = DATA_DIR / "normalized-responses.v0.1.0.csv"
    quality_path = DATA_DIR / "response-quality.v0.1.0.csv"
    mapping_path = DATA_DIR / "field-mapping.v0.1.0.json"
    normalized.to_csv(normalized_path, index=False, encoding="utf-8-sig")
    quality.to_csv(quality_path, index=False, encoding="utf-8-sig")
    write_json(mapping_path, mapping)

    content_hashes = {
        "raw": sha256_file(source_path),
        "normalized": sha256_file(normalized_path),
        "quality": sha256_file(quality_path),
        "mapping": sha256_file(mapping_path),
    }
    fieldwork = build_fieldwork_package(
        now,
        source_path,
        normalized_path,
        quality_path,
        mapping_path,
        observed,
        content_hashes,
    )
    insight = build_insight_package(now)
    report = build_research_report(
        now,
        sha256_file(REPORT_DOCX),
        sha256_file(REPORT_PDF),
        REPORT_DOCX.stat().st_size,
        REPORT_PDF.stat().st_size,
    )

    fieldwork_path = ARTIFACT_DIR / "fieldwork-package.v0.1.0.json"
    insight_path = ARTIFACT_DIR / "insight-package.v0.1.0.json"
    report_path = ARTIFACT_DIR / "research-report.v0.1.0.json"
    write_json(fieldwork_path, fieldwork)
    write_json(insight_path, insight)
    write_json(report_path, report)

    manifest_path = ARTIFACT_DIR / "artifact-manifest.v0.1.0.json"
    write_json(
        manifest_path,
        build_manifest(
            now,
            source_path,
            [
                mapping_path,
                normalized_path,
                quality_path,
                fieldwork_path,
                insight_path,
                report_path,
            ],
        ),
    )
    print(
        json.dumps(
            {
                "status": "BUILT",
                "source_sha256": content_hashes["raw"],
                "observed_quality": observed,
                "artifacts": [
                    str(fieldwork_path),
                    str(insight_path),
                    str(report_path),
                    str(manifest_path),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
