---
document_id: FFR-OTF-001
version: 0.2.0
status: draft
last_updated: 2026-07-23
project_id: PROJ-OTF-001
target_instrument: INS-OTF-SURVEY-001@0.2.0
knowledge_base: FIN-FACT-FOF@0.1.0
review_type: FINANCIAL_FACT_PRE_REVIEW
is_formal_compliance_approval: false
---

# 养老目标基金问卷 v0.2 金融事实审核记录

## 1. 审核范围

审核对象：

- `instrument-spec.v0.2.0.json`
- `output/doc/养老目标基金购买与持有情况调查问卷_v0.2.docx`
- 腾讯问卷测试部署 `survey_id=27390837`
- 金融事实库 `FIN-FACT-FOF@0.1.0`

本记录只审核 FOF、养老目标基金、目标日期、目标风险、下滑曲线、个人养老金账户和份额事实，不替代 Gate 2 人工审核或正式合规批准。

## 2. v0.2 变更审核

| 位置 | 事实引用 | 结果 | 审核说明 |
|---|---|---|---|
| S1 购买经历甄别 | FF-FOF-003、FF-FOF-009 | PASS | 明确区分“实际购买养老目标基金”和“仅开户、缴存或购买储蓄/保险/理财”；保留“不确定”，避免研究人员强行判断产品类型。 |
| Q9A 信息清晰度 | - | NOT_APPLICABLE | 只测量主观清晰程度，不提供金融事实，也不替代 Q17—Q20 的客观知识测量。 |
| Q32 年龄段 | - | NOT_APPLICABLE | 只用于匿名分群，不构成适当性、风险等级或投资建议。 |

## 3. 沿用题目复核

| 位置 | 事实引用 | 结果 | 审核说明 |
|---|---|---|---|
| Q2 账户与份额 | FF-FOF-010 | PASS | 个人养老金账户中的 Y 份额与普通基金账户中的 A/C 等份额继续分开。 |
| Q10 产品类型 | FF-FOF-003、FF-FOF-004、FF-FOF-005 | PASS | 目标日期型与目标风险型分开呈现，并允许无法判断。 |
| Q17 | FF-FOF-004、FF-FOF-007 | PASS | 正确答案是接近目标日期时通常调整资产配置；保本只作为错误选项。 |
| Q18 | FF-FOF-005、FF-FOF-007 | PASS | 正确答案是围绕预设风险水平配置；稳健型不等于不会亏损。 |
| Q19 | FF-FOF-006 | PASS | 下滑曲线表示资产配置路径，不是净值、收益或费率预测。 |
| Q20 | FF-FOF-007 | PASS | 降低波动较高资产比例后仍可能波动或亏损，不构成保本承诺。 |
| Q25、Q26 Y 份额信息需求 | FF-FOF-011 | PASS_WITH_NOTE | 只询问信息需求；后续如解释具体费率，必须重新核对产品文件。 |
| 持有、追加、赎回相关题 | FF-FOF-008 | PASS_WITH_NOTE | 只询问经历，没有声称所有产品可在任意时间操作。 |

## 4. 结论

- v0.2 新增题目没有引入金融事实错误。
- S1、Q2、Q10、Q17—Q20 已在 InstrumentSpec 中记录对应 `fact_id`。
- 未发现会改变知识题标准答案的 BLOCKER 或 MAJOR 问题。
- 费率、产品名录、具体持有期和具体下滑曲线仍是动态或产品特定事实，出现时必须重新查证。

本记录可作为 Gate 2 的金融事实预审输入，但不是法律、合规、产品适当性或正式发布批准。
