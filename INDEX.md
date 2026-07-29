---
document_id: PROJECT-INDEX
version: 0.31.0
status: draft
last_updated: 2026-07-29
---

# AI 辅助用户研究工作流

本目录用于建设一套以研究产物为契约、以专家能力为模块、由状态机与人工审核控制的多 Agent 用户研究工作流。

V1 默认运行“研究需求—目标受访者画像—问卷—匿名答卷—分析—报告”的简化主链，访谈作为按需扩展。系统以基金客户研究为首个应用场景，但核心对象和流程不得绑定基金、IMA 或某个问卷平台。

## 权威入口

| 文件 | 作用 | 当前版本 | 状态 |
|---|---|---:|---|
| [仓库说明](README.md) | 面向专业评审的项目总览、工作流、专家体系、案例和目录导航 | 1.0.0 | active |
| [V1 范围说明](00_overview/v1-scope.md) | 固定目标、边界、交付物和成功标准 | 0.6.0 | draft |
| [工作流完整性复查](00_overview/workflow-completeness-review.md) | 复查八阶段覆盖、最新报告追溯、数据状态、资产沉淀和后续优先级 | 0.1.0 | active |
| [术语表](01_standards/glossary.md) | 规定全项目唯一口径 | 0.7.0 | draft |
| [证据等级](01_standards/evidence-levels.yaml) | 规定证据成熟度、主张类型和置信度 | 0.1.0 | draft |
| [审核关口](01_standards/review-gates.md) | 规定四个人工 Gate、审批包及退回逻辑 | 0.10.0 | draft |
| [报告可理解性与上下文规范](01_standards/report-readability-and-context.md) | 规定段落上下文、术语与综合指标解释及首次阅读测试 | 0.1.0 | active |
| [问卷数据有效性与输出状态](01_standards/data-validity-and-output-status.md) | 规定题目值语义、答卷状态、原因码、数据集状态和分群输出 | 0.1.0 | draft |
| [金融事实库与校对规则](01_standards/financial-facts/README.md) | 规定来源优先级、逐题事实审核和动态复核条件 | 0.2.0 | active |
| [研究产物公共规范](01_standards/artifact-conventions.md) | 规定元数据、版本、引用、状态和数据分类 | 0.2.0 | draft |
| [专家运行交接尾注](01_standards/agent-run-response-envelope.md) | 规定状态、核心产物、下一路由和原因的最小运行反馈 | 0.1.0 | active |
| [最小权限矩阵](01_standards/minimum-permission-matrix.md) | 规定专家、总控、服务、适配器和人工角色的数据与工具权限 | 0.1.0 | active |
| [人工升级角色表](01_standards/human-escalation-roles.md) | 规定 Gate 人工角色、升级触发、暂停和恢复条件 | 0.1.0 | active |
| [IMA 轻量接入规范](01_standards/ima-lightweight-integration.md) | 规定人工学习链接、停用接口和未来启用条件 | 0.3.0 | draft |
| [核心 Schema](02_schemas/README.md) | 规定完整核心产物链的机器可读结构、合成示例与历史治理缺口登记 | 0.5.0 | draft |
| [专家能力卡总览](03_experts/expert-capability-overview.md) | 规定六类专家能力、总控边界和完整卡片入口 | 0.16.0 | draft |
| [问卷题型与测量设计参考](03_experts/references/questionnaire-design.md) | 规定轻量测量维度、题型选择和 Gate 1 分群预案 | 0.1.0 | active |
| [专家能力覆盖审计](03_experts/capability-coverage-audit.md) | 复核产物责任、横向风险、角色冲突和真实工程缺口 | 1.5.0 | active |
| [工作流状态机](04_workflows/workflow-state-machine.md) | 规定阶段、运行状态、退回失效、任务与交接规则 | 0.6.0 | draft |
| [研究总控最小运行时](04_workflows/runtime/README.md) | 实现本地 Registry、合法迁移、精确版本 Gate、stale 传播和权限快照 | 0.1.0 | draft |
| [养老目标基金购买者研究](05_cases/养老目标基金购买者研究/README.md) | 首个真实案例；最终报告新增分析已回写正式洞察包，历史控制状态仍停在 Gate 2 | 1.5.0 | draft |
| [腾讯问卷适配器](06_adapters/tencent-survey/README.md) | 将参与者版问卷编译、部署并校验到腾讯问卷 | 0.4.0 | draft |
| [Excel 答卷回传适配器](06_adapters/excel-response/README.md) | 将平台导出文件映射、脱敏并交接到 FieldworkPackage | 0.1.0 | draft |
| [专家能力与运行时测试](07_evaluations/README.md) | 39 个合同场景、7 条冒烟、3 条交接回归、评分器和运行时测试 | 0.5.0 | active |
| [答辩双层范围基线](08_defense/01_scope/full-architecture-demo-baseline.md) | 固定满血版、最小 Demo、演进路线和答辩声明边界 | 0.1.0 | active |
| [完整工作流设计说明书](08_defense/02_workflow/full-workflow-design.md) | 论述四层架构、八阶段流程、Artifact、Gate、工具、迁移和路线图 | 0.2.0 | active |
| [专家 Agent 提示词手册](08_defense/03_experts/expert-agent-prompt-handbook.md) | 固定六位专家与总控的输入、边界、提示词、产物和交接 | 0.2.0 | active |
| [养老目标基金案例复盘](08_defense/04_case/otf-case-retrospective.md) | 复盘选题纠偏、35 项问卷、200 份答卷、洞察和投资者教育建议 | 0.1.0 | active |
| [答辩演示材料](08_defense/05_presentation/README.md) | 登记 27 页交互 HTML、PPTX、配套论述底稿、19 页 Word 答辩稿、专家方法与逐页校验结果 | 0.7.0 | active |
| [变更记录](CHANGELOG.md) | 记录文件新增、修改和废弃 | 0.28.0 | active |

## M4 专家能力卡

| 编号 | 能力卡 | 唯一核心产物 |
|---|---|---|
| Template | [能力卡统一模板](03_experts/capability-card-template.md) | 能力卡契约 |
| CAP-01 | [研究问题理解专家](03_experts/cap-01-frame-research-question.md) | ResearchBrief |
| CAP-02 | [研究方案设计专家](03_experts/cap-02-design-research-plan.md) | ResearchPlan |
| CAP-03 | [研究工具设计专家](03_experts/cap-03-design-research-instrument.md) | InstrumentSpec |
| CAP-04 | [研究质量审核专家](03_experts/cap-04-review-research-quality.md) | ReviewResult |
| CAP-05 | [证据与洞察专家](03_experts/cap-05-synthesize-research-insights.md) | InsightPackage |
| CAP-06 | [研究报告表达专家](03_experts/cap-06-compose-research-report.md) | ResearchReport |
| CTRL-01 | [研究总控](03_experts/ctrl-01-orchestrate-research-workflow.md) | WorkflowState / Task / Handoff |

## 规范目录

| 目录 | 内容 |
|---|---|
| 00_overview | 项目范围、整体架构、路线图 |
| 01_standards | 术语、状态、证据、版本、审核和数据规则 |
| 02_schemas | 核心产物的 JSON Schema |
| 03_experts | 专家能力卡、提示词边界和测试案例 |
| 04_workflows | 工作流模板、状态机和阶段定义 |
| 05_cases | 真实案例、模拟数据和完整产物链 |
| 06_adapters | 问卷平台、IMA、存储和报告工具适配器 |
| 07_evaluations | 质量指标、回归测试和评估结果 |
| 08_defense | 答辩叙事、架构图和演示材料 |
| references | 外部仓库、Skill 和专家建议的来源说明 |
| archive | 已废弃或被替代的历史版本 |

## 核心产物链

业务需求 → ResearchBrief → Gate 1 → ResearchPlan + InstrumentSpec + ReviewResult → Gate 2 → FieldworkPackage → InsightPackage → Gate 3 → ResearchReport → Gate 4

产物之间通过 ID、版本和上游引用连接。Agent 不以完整聊天记录作为正式交接物。

## 当前里程碑

M4 的专家能力卡、工作流状态机和最小运行时已经完成；首个真实案例已收到 200 份 CSV 答卷并完成字段映射、质量审计、标准化、分析和报告生成。真实执行已封装为 DRAFT FieldworkPackage、InsightPackage 和 ResearchReport，并登记最终展示版 DOCX/PDF 哈希。案例已进入本地 Artifact Registry：只应用确实存在的 Gate 1 ApprovalRecord，停在 `GATE_2_REVIEW / WAITING_GATE`，下游历史产物标记为 `STALE`，没有补造 Gate 2、Gate 3 或 Gate 4。数据集本身仍为 `ANALYSIS_READY_WITH_LIMITS`，这与治理运行状态是两个不同口径。

M4 已完成内容：

- WorkflowState、TaskRecord、HandoffRecord 具有 Draft 2020-12 JSON Schema。
- Plan 与 Instrument 分阶段设计，Gate 2 批准二者及相关 ReviewResult 的精确组合。
- “退回”作为迁移事件直接回到最早责任阶段，不使用含义不明的统一 RETURNED 状态。
- 状态、任务和交接记录禁止保存参与者个人信息或完整聊天历史。
- 3 个控制记录示例与原有产物图完成交叉校验；当前共有 12 个 Schema、16 个合成示例。
- Schema 允许历史案例在没有正式批准记录时使用互斥的 `governance_gap` 登记真实缺口，但新项目仍必须引用真实 Gate 批准。
- 六位专家和总控已有 39 条能力合同用例定义及对应盲测包，覆盖正向、边界、对抗、回归、金融事实、IMA、投教、可视化和可访问性；它们尚未被登记为 39 次真实 Agent 通过。
- 最小权限矩阵和人工升级角色表已建立，明确 Agent 无审批权、总控无语义所有权、原始联系方式不进入分析 Agent。
- CTRL-01 最小运行时已经实现：本地持久化 Registry、不可覆盖状态修订、合法迁移、当前精确版本 Gate、最小权限 TaskRecord、上游修订后的 stale 传播和追加式审计。
- 6 个运行时正向/边界/对抗/回归测试已通过；项目级检查还验证真实案例只保留 Gate 1、停在 Gate 2，并把执行、洞察和报告登记为 stale。
- 面向人的 39 条测试清单、无期待答案的盲测包和独立评估协议已生成；评分器已有 10 个抗错测试。其余 32 条真实 Agent 原始回答与全部人工语义抽查仍待执行。
- 首轮 7 条独立 Agent 冒烟测试已完成：核心决策 7/7 一致、禁止行为 0/7；精确机器合同 1/7，暴露路由语义、最低输入和事实来源追溯问题。人工语义复核仍未执行，不能写成完整模型能力通过。
- 三项轻量交接回归已经完成：CAP-03、CAP-05、CAP-06 均能输出当前状态、核心产物、下一路由和原因。答辩前不再扩展剩余 32 条测试。
- 满血版目标架构与最小 Demo 双层范围基线已经固定，后续说明书、专家手册、案例复盘和 PPT 统一使用 `VERIFIED / DEMO / TARGET` 三种状态。

首个真实案例已经完成 v0.2 研究设计和 200 份答卷分析：

- 研究对象收紧为实际购买过养老目标基金的投资者，不研究未开户、未缴存或未购买原因。
- `ResearchBrief 0.2.0` 已通过新的 Gate 1 并冻结，年龄是唯一基础分群。
- `ResearchPlan 0.2.0` 与 `InstrumentSpec 0.2.0` 已生成，后者包含 35 个题目变量和统一数据状态契约。
- Word v0.2 已生成：新增购买经历甄别、五点信息清晰度和年龄段，并附数据有效性与输出状态。
- 腾讯问卷 v0.2 测试版已创建并逐题校验：10 页、35 道可作答题、213 个选择项、3 条逻辑错误数为 0。
- v0.1 Word 和线上问卷保留为历史版本，没有原地覆盖。
- FOF 事实库对 S1、Q2、Q10、Q17—Q20 完成复核，当前未发现知识题标准答案错误。
- IMA 能力验证已完成：订阅知识库可检索标题但不能读取正文，且当前 Skill 没有知识库问答接口。
- `ima_api_status=RESERVED_DISABLED`；工作流只保留人工学习链接和未来 Adapter，不让平台限制进入问卷生成主线。
- 已固定“先测后教”规则：知识题不在回答前显示 AI 解释；解释只以已审核金融事实为依据。
- Gate 2 质量预审为 `PASS_WITH_WARNINGS`；正式 Gate 2 记录尚未形成。问卷已发出这一执行事实不能替代审批，后续需记录该治理偏差。
- 已固定问卷与数据一体化口径：题目阶段定义值语义和质量信号，数据返回后输出单份答卷与整体数据集状态。
- “认知不足”和“很少查看下滑曲线”被保留为可证伪假设，不作为预设结论。
- 系统只定义目标受访者画像，不承担招募、甄别、触达或名单核验；本案例不把人工试答和独立访谈设为前置步骤。
- 腾讯问卷只承担智能发行、回收和文件导出；本次实际回传为 CSV，CSV 与 Excel 均按统一表格适配口径处理。
- CAP-05 已增加 `INVESTOR_EDUCATION` 建议定义，CAP-06 报告必须单独呈现投资者教育建议或明确“证据不足”。
- 35/35 个题目完成字段映射；200 份答卷无硬排除，12 份短时长信号保留并完成敏感性分析，94 份平台互斥冲突按统一规则修复。
- 核心知识四题全部答对者占 20.0%；购买时主动比较下滑曲线者占 3.5%，而提示后自报其会影响判断者占 51.0%，两类指标在报告中严格分离。
- 分析结果以 `analysis-results.v0.1.0.json` 沉淀；内部最终 Word 报告和含 7 张工作表、5 张图表的 Excel 分析工作簿已生成。
- Word 报告 v0.2 已完成可视化优化：执行摘要使用 4 个关键指标卡片，正文使用 5 张结论式图表，并配套 figure manifest、图注、替代文本和 16 页逐页渲染复核。
- CAP-06 已固化“主张—证据—含义—边界”、诚实图表编码、图表来源追踪和可访问性规则；外部 Skill 只作为方法参考，不改变 Artifact、Schema 或 Gate 的权威口径。
- 新增报告可理解性规范：每章和重要数据段落先交代研究对象、问题与指标，专业术语和综合指标首次出现时必须解释，并在 Gate 4 执行首次阅读抽查。
- 平台 IP、地理位置、设备和浏览器元数据未进入分析输出；开放题重复文本只作主题计数，不作为事实证明或代表性原话。
- 原始 CSV 没有复制到正式产物目录；FieldworkPackage 只登记 SHA-256，脱敏答卷和逐条质量信号可以复现。
- 正式 InsightPackage 包含 23 个统计证据单元、5 个 Finding、3 个 Insight 和 3 个 Recommendation；所有数字保留分子、分母和题目 ID。
- 最终展示版报告已登记为 ResearchReport DRAFT；Gate 3 与 Gate 4 缺失保持可见，不把多轮讨论解释为正式批准。

M3 已完成内容：

- FieldworkPackage、InsightPackage、ResearchReport、ApprovalRecord 具有 Draft 2020-12 JSON Schema。
- 原始资料通过 Source Record 和来源定位进入证据链。
- Finding、Insight、Recommendation 分层并保持逐级引用。
- Recommendation 按行动领域分类；投资者教育建议必须说明学习缺口、人群、内容、时点、形式、边界和效果验证。
- 四个 Gate 由独立 ApprovalRecord 记录，AI 预审不能构成正式批准。
- IMA OpenAPI 当前不启用；人工知识库链接仅作为核心答题后的可选学习桥梁，不记录点击或停留，不进入研究证据链。
- 13 个合成实例组成完整产物图，并通过结构、引用和关键语义校验。

## 文件维护规则

1. 每次生成前先复查本索引、变更记录和相关上游文件。
2. 新文件只能写入本项目目录的对应子目录。
3. 已批准版本不得原地改写；修改时创建新版本并保留审批引用。
4. 新增、修改、废弃文件后必须更新本索引和变更记录。
5. 术语冲突以术语表为准；审核流程冲突以审核关口文件为准。
6. 示例数据必须明确标为示例，不得被当作真实研究证据。

## 方法来源与采用记录

- [Skill 采用说明](references/skill-adoption-notes.md)
- [专家能力卡来源与采用记录](references/expert-capability-source-register.md)

## 当前收口状态

当前答辩材料、专家提示词、最终报告及案例追溯产物已经形成：

- 最终报告新增的样本画像、年龄和投资经验分析已经写入 InsightPackage 0.2.0，并登记 ResearchReport 0.2.0。
- 27 页交互 HTML 和 PPTX 已完成，主流程、专家责任图与七个专家提示词页可以相互跳转。
- 仓库级 README 已建立，历史演示版本已归档。
- 案例仍如实保留历史治理边界：只存在真实 Gate 1，未补造 Gate 2、Gate 3 或 Gate 4。
- 39 条能力合同是已定义并通过结构检查的测试场景，不表述为 39 次独立 Agent 实测全部通过。
- 200 份非概率样本只支持本次样本内的方向性洞察，不外推为市场总体结论。
