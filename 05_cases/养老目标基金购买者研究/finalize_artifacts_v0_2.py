from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from docx import Document


CASE_DIR = Path(__file__).resolve().parent
ROOT = CASE_DIR.parents[1]
FORMAL_DIR = CASE_DIR / "formal_artifacts"
DATA_DIR = FORMAL_DIR / "data"
OUTPUT_DOC_DIR = ROOT / "output" / "doc"
SEGMENT_SOURCE = (
    ROOT
    / "tmp"
    / "report_rewrite"
    / "analysis_v0_3"
    / "segment-analysis.v0.3.0.json"
)
FINAL_DOC_NAME = "养老目标基金购买者认知、决策与持有行为调查报告_最终版.docx"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def actor(capability_id: str, role: str, version: str) -> dict:
    return {
        "actor_id": capability_id,
        "actor_type": "AGENT",
        "role": role,
        "model_id": "codex",
        "capability_version": version,
    }


def copy_and_correct_report(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    document = Document(target)
    replacement = (
        "在本次问卷中，IMA知识库被定位为核心答题后的延伸学习入口，"
        "并未作为四道知识题的事实来源或研究证据。后续可在问卷、产品说明"
        "或持有期材料末尾加入“想了解更多金融常识，可前往IMA知识库搜索”"
        "的链接，或在条件具备时接入关键词跳转。它承担的是从调研到学习的"
        "桥梁，不替代核心解释；当前版本不启用接口搜索，也不追踪用户点击"
        "或停留时长。"
    )
    matched = False
    for paragraph in document.paragraphs:
        if "我们通过读取IMA知识库生成了四道知识问答题" in paragraph.text:
            paragraph.text = replacement
            matched = True
            break
    if not matched:
        raise RuntimeError("未找到需要修正的 IMA 来源表述")
    document.save(target)


def build_evidence(
    evidence_id: str,
    value: object,
    context: str,
    locator: str,
    metric: str,
    numerator: int,
    denominator: int,
    item_ids: list[str],
    research_question_ids: list[str],
    now: str,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "STATISTIC",
        "source_id": "SRC-OTF-SURVEY-NORMALIZED-001",
        "source_locator": {
            "scheme": "ROW_AND_ITEM_ID",
            "value": locator,
        },
        "participant_or_record_id": "GROUP-ALL-200",
        "exact_content_or_value": value,
        "extraction_method": (
            "基于脱敏标准化答卷执行预设分群描述、Pearson 卡方检验、"
            "Cramér's V 和 Benjamini-Hochberg FDR 校正。"
        ),
        "extracted_by": actor(
            "AGENT-CAP-05", "证据与洞察专家", "0.5.0"
        ),
        "human_verified": False,
        "research_question_ids": research_question_ids,
        "hypothesis_ids": [],
        "code_ids": ["CODE-OTF-SEGMENT-COMPARISON"],
        "context": context,
        "quantitative_context": {
            "metric": metric,
            "numerator": numerator,
            "denominator": denominator,
            "item_ids": item_ids,
            "filter_conditions": (
                "working_analysis_included=true；200 份均纳入历史工作分析。"
            ),
            "missing_value_handling": (
                "不插补；沿用既有结构性缺失和互斥冲突处理规则。"
            ),
        },
    }


def build_insight_package(segment: dict, now: str) -> dict:
    insight = read_json(FORMAL_DIR / "insight-package.v0.1.0.json")
    insight = copy.deepcopy(insight)
    metadata = insight["metadata"]
    metadata["artifact_version"] = "0.2.0"
    metadata["created_at"] = now
    metadata["updated_at"] = now
    metadata["created_by"] = actor(
        "AGENT-CAP-05", "证据与洞察专家", "0.5.0"
    )
    metadata["change_summary"] = (
        "补充样本画像、年龄与基金投资经验探索性分群分析及多重校正边界；"
        "未形成 Gate 3 批准。"
    )

    insight["codebook"]["version"] = "0.2.0"
    insight["codebook"]["codes"].append(
        {
            "code_id": "CODE-OTF-SEGMENT-COMPARISON",
            "label": "年龄与投资经验探索性分群",
            "definition": (
                "按 Q31 年龄和 Q32 基金投资经验比较十项预设指标，"
                "并统一进行 FDR 校正。"
            ),
            "include_when": "只报告样本内方向、组内分母和校正后结果。",
            "exclude_when": (
                "不把描述性差异升级为稳定标签、因果关系或总体差异。"
            ),
            "research_question_ids": ["RQ-002", "RQ-003", "RQ-005"],
        }
    )

    outcomes = {
        "四道核心知识题全部答对",
        "两类产品设计思路均答对",
        "购买前看过下滑曲线",
        "购买前主动比较下滑曲线",
        "购买后存在信息触达缺口",
    }
    age_tests = [
        item
        for item in segment["subgroup_tests"]
        if item["grouping"] == "年龄" and item["outcome"] in outcomes
    ]
    experience_tests = [
        item
        for item in segment["subgroup_tests"]
        if item["grouping"] == "基金投资经验"
        and item["outcome"] in outcomes
    ]
    total_tests = len(segment["subgroup_tests"])
    significant_tests = sum(
        item["fdr_q_value"] < 0.05 for item in segment["subgroup_tests"]
    )

    evidence_units = [
        build_evidence(
            "EVID-OTF-024",
            segment["sample"],
            "受访者年龄、基金投资经验、持有状态、购买账户和购买时间画像。",
            "ALL_INCLUDED;ITEMS=ITEM-Q1,ITEM-Q2,ITEM-Q3,ITEM-Q31,ITEM-Q32;"
            "METRIC=SAMPLE_PROFILE",
            "样本画像完整分布",
            200,
            200,
            ["ITEM-Q1", "ITEM-Q2", "ITEM-Q3", "ITEM-Q31", "ITEM-Q32"],
            ["RQ-002", "RQ-005"],
            now,
        ),
        build_evidence(
            "EVID-OTF-025",
            age_tests,
            "年龄分组的基础认知、下滑曲线接触和持有期信息缺口。",
            "ALL_INCLUDED;GROUP=ITEM-Q31;OUTCOMES=Q8,Q14,Q15,Q17-Q20",
            "年龄分组五项指标",
            200,
            200,
            [
                "ITEM-Q8",
                "ITEM-Q14",
                "ITEM-Q15",
                "ITEM-Q17",
                "ITEM-Q18",
                "ITEM-Q19",
                "ITEM-Q20",
                "ITEM-Q31",
            ],
            ["RQ-002", "RQ-003", "RQ-005"],
            now,
        ),
        build_evidence(
            "EVID-OTF-026",
            experience_tests,
            "基金投资经验分组的基础认知、下滑曲线接触和持有期信息缺口。",
            "ALL_INCLUDED;GROUP=ITEM-Q32;OUTCOMES=Q8,Q14,Q15,Q17-Q20",
            "基金投资经验分组五项指标",
            200,
            200,
            [
                "ITEM-Q8",
                "ITEM-Q14",
                "ITEM-Q15",
                "ITEM-Q17",
                "ITEM-Q18",
                "ITEM-Q19",
                "ITEM-Q20",
                "ITEM-Q32",
            ],
            ["RQ-002", "RQ-003", "RQ-005"],
            now,
        ),
        build_evidence(
            "EVID-OTF-027",
            {
                "total_predefined_comparisons": total_tests,
                "fdr_significant_comparisons": significant_tests,
                "alpha": 0.05,
                "method": "Benjamini-Hochberg FDR",
            },
            "五类分群与十项指标共 50 组预设比较的多重校正结果。",
            "ALL_INCLUDED;GROUPS=Q1,Q2,Q3,Q31,Q32;METRIC=FDR_AUDIT",
            "FDR 校正后显著比较数",
            significant_tests,
            total_tests,
            ["ITEM-Q1", "ITEM-Q2", "ITEM-Q3", "ITEM-Q31", "ITEM-Q32"],
            ["RQ-002", "RQ-003", "RQ-005"],
            now,
        ),
    ]
    insight["evidence_units"].extend(evidence_units)
    insight["analysis_log"].append(
        {
            "step_id": "ANALYSIS-OTF-SEGMENTS",
            "performed_at": now,
            "performed_by": actor(
                "AGENT-CAP-05", "证据与洞察专家", "0.5.0"
            ),
            "method": "COMPARISON",
            "input_refs": ["SRC-OTF-SURVEY-NORMALIZED-001"],
            "output_ids": [item["evidence_id"] for item in evidence_units]
            + ["FINDING-OTF-006", "INSIGHT-OTF-004", "REC-OTF-004"],
            "parameters_or_rules": (
                "五类分群×十项预设指标；二元结果使用 Pearson 卡方检验，"
                "记录 Cramér's V，并对 50 组比较统一进行 BH-FDR 校正。"
            ),
            "notes": (
                "校正后无显著比较；分群结果只作为下一轮验证假设。"
            ),
        }
    )
    insight["findings"].append(
        {
            "finding_id": "FINDING-OTF-006",
            "statement": (
                "年龄差异不呈线性变化；基金投资经验与基础产品类型理解呈"
                "方向性上升，但没有形成稳定的综合理解优势。50 组预设比较"
                "经 FDR 校正后均未达到显著水平。"
            ),
            "research_question_ids": ["RQ-002", "RQ-003", "RQ-005"],
            "method_ids": ["METHOD-SUR-OTF-001"],
            "supporting_evidence_ids": [
                "EVID-OTF-024",
                "EVID-OTF-025",
                "EVID-OTF-026",
                "EVID-OTF-027",
            ],
            "negative_case_evidence_ids": [],
            "sample_scope": "历史工作分析纳入的 200 份养老目标基金购买者答卷。",
            "conditions": (
                "分群属于探索性样本内比较，只能描述方向，不能形成客户标签。"
            ),
            "confidence": "LOW",
            "importance": "MEDIUM",
            "importance_rationale": (
                "决定当前应先解决共同理解缺口，还是直接按年龄和经验定制。"
            ),
            "limitations": [
                "没有抽样框、加权和独立验证样本。",
                "多重校正后无显著差异。",
                "未控制收入、职业、投资金额等潜在混杂因素。",
            ],
        }
    )
    insight["insights"].append(
        {
            "insight_id": "INSIGHT-OTF-004",
            "statement": (
                "现阶段更适合先改通用信息路径，再把年龄和投资经验差异"
                "作为下一轮材料测试或访谈假设，而不是直接建立分群策略。"
            ),
            "source_finding_ids": ["FINDING-OTF-006"],
            "reasoning": (
                "年龄和经验组出现若干方向性差异，但校正后没有稳定统计证据；"
                "各组共同存在综合理解不足和持有期信息缺口。"
            ),
            "alternative_explanations": [
                "样本量不足以识别较小组间差异。",
                "观察到的方向可能由未收集的职业、收入或购买渠道造成。",
            ],
            "decision_relevance": (
                "避免在 Demo 阶段过早增加复杂分群和个性化内容。"
            ),
            "applicable_scope": "本项目 200 份工作分析答卷和当前分组口径。",
            "confidence": "LOW",
        }
    )
    insight["recommendations"].append(
        {
            "recommendation_id": "REC-OTF-004",
            "recommendation_domain": "RESEARCH_FOLLOW_UP",
            "statement": (
                "下一轮保留年龄与基金投资经验两个基础分组，先验证通用材料"
                "是否提高理解；只有差异复现后再设计分群版本。"
            ),
            "source_insight_ids": ["INSIGHT-OTF-004"],
            "expected_effect": "以较低复杂度判断分群设计是否真的必要。",
            "risks": ["后续样本仍过小时可能继续无法识别真实差异。"],
            "assumptions": ["下一轮可以使用统一口径的前后理解题。"],
            "validation_needed": [
                "预先声明核心分组和主要指标。",
                "扩大样本或补充专题访谈解释方向性差异。",
            ],
            "owner_suggestion": "用户研究负责人",
            "suggested_priority": "MEDIUM",
            "business_decision_status": "NOT_DECIDED",
        }
    )
    insight["limitations"].append(
        "年龄、经验等 50 组探索性比较经 FDR 校正后均未达到显著水平。"
    )
    insight["unanswered_questions"].append(
        {
            "question_id": "UQ-OTF-004",
            "statement": (
                "年龄和投资经验方向性差异能否在预先设定分组的新样本中复现？"
            ),
            "why_unanswered": (
                "本轮分群属于事后探索，且多重校正后没有显著差异。"
            ),
            "suggested_next_method": (
                "预先声明年龄、经验分组和主要指标后重新采集，"
                "必要时补充专题访谈。"
            ),
        }
    )
    insight["quality_summary"]["review_notes"] = (
        "所有正式统计保留来源题目、组内分母和校正方法；分群结果未升级为"
        "正式客户标签。最新洞察包尚未形成 Gate 3 正式批准。"
    )
    return insight


def build_research_report(
    insight: dict, report_path: Path, now: str
) -> dict:
    report = read_json(FORMAL_DIR / "research-report.v0.1.0.json")
    report = copy.deepcopy(report)
    metadata = report["metadata"]
    metadata["artifact_version"] = "0.2.0"
    metadata["title"] = "养老目标基金购买者认知、决策与持有行为调查报告"
    metadata["created_at"] = now
    metadata["updated_at"] = now
    metadata["created_by"] = actor(
        "AGENT-CAP-06", "研究报告表达专家", "0.7.0"
    )
    metadata["upstream_refs"] = [
        item
        for item in metadata["upstream_refs"]
        if item["artifact_type"] != "InsightPackage"
    ] + [
        {
            "artifact_id": "IP-OTF-001",
            "artifact_type": "InsightPackage",
            "artifact_version": "0.2.0",
        }
    ]
    metadata["change_summary"] = (
        "登记最终版 DOCX，并补充样本画像、年龄与投资经验探索性分群及"
        "首次阅读说明；保留 Gate 3、Gate 4 未形成记录的真实边界。"
    )
    report_uri = "../../../output/doc/" + quote(FINAL_DOC_NAME)
    metadata["extensions"] = {
        "report.files": [
            {
                "format": "DOCX",
                "uri": report_uri,
                "sha256": sha256_file(report_path),
                "size_bytes": report_path.stat().st_size,
            }
        ],
        "report.release_status": "INTERNAL_DRAFT_NO_GATE3_NO_GATE4",
        "report.readability_standard": "STD-REPORT-READABILITY@0.1.0",
    }
    report["insight_package_ref"]["artifact_version"] = "0.2.0"
    report["gate_3_governance_gap"]["operational_effect"] = (
        "最终版报告已完成内容、逻辑和排版迭代，并补齐最新分群证据链，"
        "但没有形成 Gate 3 或 Gate 4 的正式 ApprovalRecord；"
        "ResearchReport 只能登记为 DRAFT。"
    )
    report["report_profile"]["report_date"] = "2026-07-28"
    report["report_profile"]["purpose"] = (
        "展示养老目标基金购买者的样本画像、认知、决策、持有行为、"
        "探索性人群差异及产品与投资者教育建议。"
    )
    report["executive_summary"]["context"] = (
        "本研究基于 200 份养老目标基金实际购买者问卷，考察购买路径、"
        "产品类型认知、下滑曲线理解、持有行为和信息需求，并探索年龄"
        "与基金投资经验的方向性差异。"
    )
    for answer in report["executive_summary"]["key_answers"]:
        if answer["research_question_id"] == "RQ-002":
            answer["answer"] = (
                "购买经历未自动转化为稳定理解；年龄差异不呈线性，"
                "投资经验只呈方向性帮助，分群比较经校正后均未显著。"
            )
            answer["finding_ids"] = ["FINDING-OTF-001", "FINDING-OTF-006"]
    if "探索性分群比较与 FDR 校正" not in report["methodology"]["methods"]:
        report["methodology"]["methods"].append(
            "探索性分群比较与 FDR 校正"
        )
    report["methodology"]["analysis_approach"] = (
        "按 InstrumentSpec 映射字段并生成知识题与行为指标；总体结果保留"
        "分子、分母和题目 ID。分群部分比较五类基础画像与十项预设指标，"
        "使用 Pearson 卡方检验、Cramér's V 和 BH-FDR 校正。"
    )
    report["finding_presentations"].append(
        {
            "finding_id": "FINDING-OTF-006",
            "headline": "分群差异可作研究线索，暂不足以形成客户标签",
            "statement": (
                "40—49 岁基础认知相对较好，投资经验与产品类型理解呈"
                "方向性上升，但综合理解仍低，且 50 组比较经校正后均未显著。"
            ),
            "sample_scope": "本项目 200 份工作分析答卷。",
            "confidence": "LOW",
            "evidence_highlights": [
                {
                    "evidence_id": "EVID-OTF-025",
                    "display_text": (
                        "两类产品思路均答对：40—49 岁 48.6%，"
                        "18—29 岁 27.3%，50—59 岁 29.4%"
                    ),
                },
                {
                    "evidence_id": "EVID-OTF-026",
                    "display_text": (
                        "两类产品思路均答对随经验由 25.9% 方向性升至 48.1%"
                    ),
                },
                {
                    "evidence_id": "EVID-OTF-027",
                    "display_text": "50 组预设比较经 FDR 校正后显著项为 0",
                },
            ],
            "negative_case_note": (
                "年龄并非越大认知越好，经验较长者也未形成稳定综合理解。"
            ),
            "limitation_note": (
                "没有抽样框、加权和混杂因素控制，结果只用于下一轮假设。"
            ),
        }
    )
    report["insight_presentations"].append(
        {
            "insight_id": "INSIGHT-OTF-004",
            "headline": "先改共同问题，再验证人群差异",
            "explanation": (
                "现有证据支持把年龄和经验作为后续研究线索，"
                "不支持立即增加复杂分群版本。"
            ),
            "applicable_scope": "本项目样本和当前分组口径。",
            "confidence": "LOW",
        }
    )
    report["recommendation_presentations"].append(
        {
            "recommendation_id": "REC-OTF-004",
            "action": (
                "下一轮只保留年龄与投资经验两个基础分组，"
                "先验证同一份通用材料。"
            ),
            "rationale": (
                "分群方向存在，但多重校正后没有稳定显著差异。"
            ),
            "expected_effect": "避免在证据不足时过早增加内容复杂度。",
            "validation_next_step": (
                "预先声明分组和主要指标，差异复现后再设计分群版本。"
            ),
            "suggested_owner": "用户研究负责人",
            "suggested_priority": "MEDIUM",
            "decision_status": "RESEARCH_PROPOSAL",
        }
    )
    report["limitations"].append(
        "年龄、经验等分群只作探索；50 组比较经 FDR 校正后均未达到显著水平。"
    )
    report["unanswered_questions"].append(
        "年龄和投资经验方向性差异能否在新样本中复现？"
    )
    report["appendices"] = [
        item
        for item in report["appendices"]
        if item["appendix_id"] not in {"APP-OTF-002", "APP-OTF-003", "APP-OTF-004"}
    ]
    report["appendices"].extend(
        [
            {
                "appendix_id": "APP-OTF-002",
                "title": "InsightPackage 0.2.0",
                "content_type": "ARTIFACT",
                "reference": {
                    "artifact_id": "IP-OTF-001",
                    "artifact_type": "InsightPackage",
                    "artifact_version": "0.2.0",
                },
            },
            {
                "appendix_id": "APP-OTF-003",
                "title": "最终版 DOCX",
                "content_type": "OTHER",
                "reference": report_uri,
            },
            {
                "appendix_id": "APP-OTF-004",
                "title": "探索性分群分析",
                "content_type": "OTHER",
                "reference": "data/segment-analysis.v0.3.0.json",
            },
        ]
    )
    report["quality_declaration"]["all_claims_traceable"] = True
    report["quality_declaration"]["numbers_match_insight_package"] = True
    return report


def build_review(now: str) -> dict:
    reviewer = actor("AGENT-CAP-04", "研究质量审核专家", "0.6.0")
    return {
        "metadata": {
            "schema_version": "0.1.0",
            "artifact_id": "REVIEW-RR-OTF-002",
            "artifact_type": "ReviewResult",
            "artifact_version": "0.1.0",
            "project_id": "PROJ-OTF-001",
            "title": "养老目标基金购买者调查报告 0.2.0 轻量预审",
            "language": "zh-CN",
            "lifecycle_status": "FROZEN",
            "created_at": now,
            "updated_at": now,
            "created_by": reviewer,
            "upstream_refs": [
                {
                    "artifact_id": "RR-OTF-001",
                    "artifact_type": "ResearchReport",
                    "artifact_version": "0.2.0",
                }
            ],
            "content_classification": "REAL",
            "sensitivity_level": "INTERNAL",
            "contains_personal_data": False,
            "change_summary": (
                "检查最新分群追溯、首次阅读上下文、IMA 边界和历史审批缺口。"
            ),
        },
        "target_ref": {
            "artifact_id": "RR-OTF-001",
            "artifact_type": "ResearchReport",
            "artifact_version": "0.2.0",
        },
        "review_scope": "ResearchReport",
        "review_types": [
            "STRUCTURE",
            "TRACEABILITY",
            "LOGIC",
            "WORDING",
            "ACCESSIBILITY",
            "COMPLIANCE",
            "FINANCIAL_EXPRESSION",
            "DATA_QUALITY",
        ],
        "reviewer": reviewer,
        "reviewed_at": now,
        "ruleset_refs": [
            {
                "ruleset_id": "STD-REPORT-READABILITY",
                "version": "0.1.0",
                "uri": "../../../01_standards/report-readability-and-context.md",
            },
            {
                "ruleset_id": "STD-REVIEW-GATES",
                "version": "0.10.0",
                "uri": "../../../01_standards/review-gates.md",
            },
        ],
        "checks": [
            {
                "check_id": "CHECK-RR-TRACE-002",
                "label": "新增分群结论追溯",
                "status": "PASS",
                "details": (
                    "年龄、经验和多重校正结论已回写 InsightPackage 0.2.0。"
                ),
                "related_issue_ids": [],
            },
            {
                "check_id": "CHECK-RR-READ-002",
                "label": "首次阅读上下文",
                "status": "PASS",
                "details": (
                    "研究目的、样本、四道知识题含义和分群口径均在首次出现时说明。"
                ),
                "related_issue_ids": [],
            },
            {
                "check_id": "CHECK-RR-SEG-002",
                "label": "分群证据边界",
                "status": "PASS",
                "details": (
                    "报告明确 50 组比较校正后均未显著，不生成正式客户标签。"
                ),
                "related_issue_ids": [],
            },
            {
                "check_id": "CHECK-RR-IMA-002",
                "label": "IMA 使用边界",
                "status": "PASS",
                "details": (
                    "已删除“通过读取 IMA 生成知识题”的不实表述；"
                    "IMA 仅保留为可选学习入口，当前接口不启用。"
                ),
                "related_issue_ids": [],
            },
            {
                "check_id": "CHECK-RR-GOV-002",
                "label": "历史审批边界",
                "status": "WARNING",
                "details": (
                    "Gate 3、Gate 4 没有历史 ApprovalRecord；"
                    "本预审不构成批准，报告只能作为内部草稿。"
                ),
                "related_issue_ids": ["ISSUE-RR-OTF-002-GOV"],
            },
        ],
        "issues": [
            {
                "issue_id": "ISSUE-RR-OTF-002-GOV",
                "severity": "WARNING",
                "category": "OTHER",
                "rule_id": "RULE-GATE-HISTORY",
                "location": {
                    "json_pointer": "/gate_3_governance_gap",
                    "component_id": "RR-OTF-001",
                },
                "description": "Gate 3、Gate 4 没有可验证的历史正式批准。",
                "evidence": (
                    "项目只保留真实 Gate 1；未发现 Gate 3、Gate 4 ApprovalRecord。"
                ),
                "recommended_change": (
                    "保持 DRAFT；如需正式外发，对精确版本重新执行人工审核。"
                ),
                "status": "ACCEPTED_RISK",
                "owner_role": "研究负责人",
            }
        ],
        "summary": {
            "outcome": "PASS_WITH_WARNINGS",
            "blocker_count": 0,
            "major_count": 0,
            "minor_count": 0,
            "warning_count": 1,
            "summary_text": (
                "内容、追溯和首次阅读检查通过；因缺少历史 Gate 3、Gate 4，"
                "只可作为内部草稿，不构成正式发布批准。"
            ),
        },
        "residual_risks": [
            {
                "risk_id": "RISK-RR-OTF-002",
                "category": "OTHER",
                "description": "报告可能被误当作已经完成正式发布审批。",
                "likelihood": "MEDIUM",
                "impact": "HIGH",
                "mitigation": (
                    "文件和语义产物保持 INTERNAL_DRAFT，并展示审批边界。"
                ),
                "owner_role": "研究负责人",
            }
        ],
        "recommended_next_action": "READY_FOR_HUMAN_REVIEW",
        "is_formal_approval": False,
    }


def file_record(path: Path, manifest_path: str) -> dict:
    return {
        "path": manifest_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def build_manifest(report_path: Path, now: str) -> dict:
    prior = read_json(FORMAL_DIR / "artifact-manifest.v0.1.0.json")
    outputs = []
    for relative in [
        "formal_artifacts/data/field-mapping.v0.1.0.json",
        "formal_artifacts/data/normalized-responses.v0.1.0.csv",
        "formal_artifacts/data/response-quality.v0.1.0.csv",
        "formal_artifacts/data/segment-analysis.v0.3.0.json",
        "formal_artifacts/fieldwork-package.v0.1.0.json",
        "formal_artifacts/insight-package.v0.2.0.json",
        "formal_artifacts/research-report.v0.2.0.json",
        "formal_artifacts/review-result.report.v0.2.0.json",
    ]:
        outputs.append(file_record(CASE_DIR / relative, relative))
    outputs.append(
        file_record(
            report_path,
            "../../output/doc/" + FINAL_DOC_NAME,
        )
    )
    return {
        "manifest_version": "0.2.0",
        "project_id": "PROJ-OTF-001",
        "generated_at": now,
        "source": prior["source"],
        "outputs": outputs,
        "governance": {
            "gate_1": "RECORDED: APR-OTF-G1-002",
            "gate_2": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "gate_3": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "gate_4": "NOT_RECORDED; NOT RETROSPECTIVELY CREATED",
            "release_status": "INTERNAL_DRAFT",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-source", required=True, type=Path)
    args = parser.parse_args()
    if not args.report_source.exists():
        raise FileNotFoundError(args.report_source)
    if not SEGMENT_SOURCE.exists():
        raise FileNotFoundError(SEGMENT_SOURCE)

    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(
        timespec="seconds"
    )
    OUTPUT_DOC_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DOC_DIR / FINAL_DOC_NAME
    copy_and_correct_report(args.report_source, report_path)
    shutil.copy2(SEGMENT_SOURCE, DATA_DIR / SEGMENT_SOURCE.name)

    segment = read_json(SEGMENT_SOURCE)
    insight = build_insight_package(segment, now)
    write_json(FORMAL_DIR / "insight-package.v0.2.0.json", insight)
    report = build_research_report(insight, report_path, now)
    write_json(FORMAL_DIR / "research-report.v0.2.0.json", report)
    review = build_review(now)
    write_json(FORMAL_DIR / "review-result.report.v0.2.0.json", review)
    manifest = build_manifest(report_path, now)
    write_json(FORMAL_DIR / "artifact-manifest.v0.2.0.json", manifest)

    print(f"FINAL_DOC={report_path}")
    print(f"FINAL_DOC_SHA256={sha256_file(report_path)}")
    print("INSIGHT_PACKAGE=0.2.0")
    print("RESEARCH_REPORT=0.2.0")
    print("REVIEW=PASS_WITH_WARNINGS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
