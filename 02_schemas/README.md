---
document_id: SCHEMA-README
version: 0.5.0
status: draft
last_updated: 2026-07-27
---

# 核心产物 Schema

本目录保存平台无关的 JSON Schema。字段口径以 `../01_standards/glossary.md` 和 `../01_standards/artifact-conventions.md` 为准。

## 文件

| 文件 | 产物 | 主要交接位置 |
|---|---|---|
| `common.schema.json` | 公共元数据与复用结构 | 所有核心产物 |
| `research-brief.schema.json` | ResearchBrief | 原始需求 → Gate 1 |
| `research-plan.schema.json` | ResearchPlan | Gate 1 → Gate 2 |
| `instrument-spec.schema.json` | InstrumentSpec | 研究方案 → Gate 2 |
| `review-result.schema.json` | ReviewResult | AI/人工质量预审 → Gate 2 或其他质量检查 |
| `fieldwork-package.schema.json` | FieldworkPackage | Gate 2 → 执行与原始资料整理 |
| `insight-package.schema.json` | InsightPackage | 原始资料 → Gate 3 |
| `research-report.schema.json` | ResearchReport | Gate 3 → Gate 4 |
| `approval-record.schema.json` | ApprovalRecord | 四个人工 Gate 的独立批准记录 |
| `workflow-state.schema.json` | WorkflowState | 当前阶段、运行状态、有效版本和最近迁移 |
| `task-record.schema.json` | TaskRecord | 任务输入、目标能力、权限、输出契约和失败处理 |
| `handoff-record.schema.json` | HandoffRecord | 任务间最小上下文交接和返回路径 |

`examples` 中的实例全部是合成数据，只用于说明和自动校验，不构成客户证据。

| 示例 | 说明 |
|---|---|
| `examples/research-brief.example.json` | 材料理解研究任务书 |
| `examples/research-plan.example.json` | 访谈后问卷的组合研究方案 |
| `examples/instrument-spec.interview.example.json` | 材料理解探索访谈提纲 |
| `examples/instrument-spec.survey.example.json` | 带产品材料理解测量和答题后 IMA 学习入口的问卷 |
| `examples/review-result.example.json` | 对旧问卷版本提出修改要求的质量预审 |
| `examples/review-result.current.example.json` | 对当前问卷版本的通过型质量预审 |
| `examples/fieldwork-package.example.json` | 执行、资料清单、质量和脱敏记录 |
| `examples/insight-package.example.json` | 证据—发现—洞察—建议的完整分析链 |
| `examples/research-report.example.json` | 面向业务沟通的研究报告 |
| `examples/approval-record.gate*.example.json` | 四个 Gate 的人工批准记录 |
| `examples/workflow-state.instrument-design.example.json` | 进入研究工具设计阶段的控制快照 |
| `examples/task-record.instrument-design.example.json` | CAP-03 研究工具设计任务 |
| `examples/handoff-record.plan-to-instrument.example.json` | CAP-02 向 CAP-03 的最小上下文交接 |

## 设计约束

- 当前结构契约基线为 `0.3.0`，使用 JSON Schema Draft 2020-12；各产物实例仍按自身版本独立演进。
- `InstrumentSpec` 通过 `instrument_type` 区分问卷与访谈，但复用同一套元数据、研究问题映射、测试材料和合规字段。
- 问卷型 `InstrumentSpec` 必须同时定义题目、输出变量、特殊值语义和 `response_validity_plan`；问卷内容与回收数据口径属于同一个设计产物。
- `FieldworkPackage` 必须记录规则执行后的答卷状态汇总、原因码汇总和数据集状态，不得在数据返回后临时发明新的排除口径。
- 新项目的 `FieldworkPackage` 仍必须引用真实 `gate_2_approval_ref`。对于已经实际运行、但历史上没有形成 Gate 2 记录的案例，只能使用互斥字段 `gate_2_governance_gap` 登记 `NOT_RECORDED`；它不能替代批准，且固定禁止追溯补造。
- 外部问卷平台导出的 Excel 通过 Adapter 完成字段映射、脱敏和规范化，再登记为 FieldworkPackage 的 Source Record；平台在线统计不是核心产物。
- `Recommendation` 必须标明行动领域；`INVESTOR_EDUCATION` 建议必须同时说明学习缺口、人群范围、内容、时点、形式、边界和效果验证。
- `ResearchReport` 必须保留独立的投资者教育建议板块；证据不足时显式标为不适用，不得用通用科普内容填充。
- 新项目的 `ResearchReport` 仍必须引用真实 `gate_3_approval_ref`。历史案例缺少 Gate 3 时只能使用 `gate_3_governance_gap` 并保持 `DRAFT`，不能为了通过 Schema 伪造 ApprovalRecord。
- `ResearchPlan` 的 sampling、recruitment 和 fieldwork 为可选运行模块；简化问卷模式只继承目标受访者画像，不负责招募、联系和名单核验。
- 简化模式可使用 `participant_profile` 明确目标人群、分析维度和“外部提供答卷、系统只定义画像”的责任边界，不要求虚构样本数量。
- 人工试答不是默认前置条件。未启用时 `pilot_required` 或 `pilot_config.required` 为 `false`；题目追溯、选项、跳转、变量和结构检查仍然必需。
- 新建或实质修订的问卷项目可在 ResearchBrief 中使用 `analysis_intent`，在 Gate 1 只约定一个主要分群、拟比较结果、测量维度和外推边界；具体题目、量表措辞与编码仍由 ResearchPlan 和 InstrumentSpec 承担。
- 交付日期只有在业务方提供明确排期时填写；未知时不得为了通过 Schema 虚构日期。
- 材料理解度测试是 `instrument_mode`，不是独立研究主线。
- IMA 默认进入 `learning_resources`，作为答题后的可选知识入口；不记录点击或停留，也不进入研究证据链。
- `ReviewResult` 只能给出质量检查建议，`is_formal_approval` 固定为 `false`。
- 平台字段只能进入 `metadata.extensions`，核心 Schema 不绑定 SurveyKing、IMA 或特定模型。
- 三类控制记录不是研究证据，使用 `record_id + record_revision`，并禁止直接保存个人信息和完整聊天历史。
- `TASK_CREATED`、`TASK_STATUS_CHANGED` 和 `REGISTRY_UPDATED` 是控制层原阶段自迁移事件，用于保证创建任务、任务变更和 Registry 更新都有不可覆盖快照；它们不能推动研究主线越过 Gate。

## 校验范围

JSON Schema 可以检查字段完整性、数据类型、枚举、问卷题型所需结构以及问卷/访谈分支。诱导性、方法适配性和金融表达风险等问题仍需专家能力与人工 Gate 判断。

安装校验依赖后，在本目录运行：

```powershell
python -m pip install -r .\requirements.txt
python .\validate_examples.py
```

脚本同时检查全部 Schema 和合成实例，以及核心引用、混合研究样本分配、问卷逻辑、学习资源边界、执行资料、证据链、投资者教育建议域、报告引用、四个 Gate 的精确版本关系，以及 WorkflowState、TaskRecord、HandoffRecord 的控制关系。

真实案例、专家合同测试、权限矩阵和产物哈希使用项目级检查：

```powershell
python ..\07_evaluations\run_all_checks.py
```
