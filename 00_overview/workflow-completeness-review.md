---
document_id: OVW-WORKFLOW-COMPLETENESS-REVIEW
version: 0.1.0
status: active
last_updated: 2026-07-28
upstream:
  - OVW-V1-SCOPE@0.6.0
  - WF-STATE-MACHINE@0.6.0
  - EXP-CAPABILITY-COVERAGE-AUDIT@1.5.0
  - STD-REPORT-READABILITY@0.1.0
---

# 工作流完整性复查

## 1. 复查结论

当前工作流的主架构正确，已经形成可用于答辩的完整闭环说明，也用真实问卷完成了从需求理解、工具设计、发行回传、数据处理、洞察到报告的 Demo。现阶段不需要新增专家 Agent。

真正未收口的部分集中在“最后一公里”：

1. 最新报告与正式证据链尚未同步。
2. 数据质量状态在历史案例中存在双口径。
3. 报告可理解性过去主要依赖人工迭代，刚刚完成规范化，但尚未进入 Schema 和自动测试。
4. 资产归档目前是文件目录，不是可检索、可迁移的正式资产服务。
5. 完整 Gate 1—4 尚未在一个全新项目中真实运行。

因此，下一步不应继续扩展角色和功能数量，而应完成产物链、状态口径和最终资产登记。

## 2. 本次复查范围

复查了：

- 范围、术语、产物规范和四个 Gate。
- 六位专家能力卡、总控和提示词手册。
- WorkflowState、TaskRecord、HandoffRecord 和最小运行时。
- 问卷与 Excel/CSV 回传口径。
- 养老目标基金的 FieldworkPackage、InsightPackage、ResearchReport 和最终展示文件。
- 39 条能力合同、7 条冒烟、3 条交接回归和 6 条运行时测试。
- 报告的研究目的、样本画像、分群分析、图表、术语和首次阅读体验。

`run_all_checks.py` 当前全部通过，包括 16 个 Schema 示例、39 条合同夹具、10 条评分器测试、6 条运行时测试、历史治理边界、真实产物引用和文件哈希。这里的“通过”证明现有约束自洽，不代表下面列出的业务闭环缺口已经完成。

## 3. 八阶段覆盖情况

| 阶段 | 当前状态 | 已完成 | 主要缺口 |
|---|---|---|---|
| 1 接收需求 | `DEMO` | 有 Raw Demand、总控和 Intake 路由 | 原始需求仍主要来自聊天或人工整理，没有独立 Intake Artifact；V1 可接受 |
| 2 理解研究问题 | `VERIFIED` | ResearchBrief、Gate 1、分群与测量意图已建立 | 下一项目需验证新主题迁移 |
| 3 设计研究方案 | `VERIFIED` | ResearchPlan、方法与分析计划已建立 | 访谈和组合研究未用真实项目验证 |
| 4 设计问卷/访谈 | `VERIFIED/DEMO` | 35 项问卷、变量、事实审核和平台转换已跑通 | PilotRunRecord 未定义；访谈工具未实跑 |
| 5 执行调研 | `DEMO` | 腾讯问卷发行、CSV 回传、字段映射、脱敏和质量处理已完成 | Excel Adapter 目前以规范和案例脚本为主，尚不是可迁移的通用组件 |
| 6 分析与洞察 | `DEMO` | Evidence→Finding→Insight→Recommendation 链已建立 | 最新年龄/经验分组分析未进入新的 InsightPackage |
| 7 报告生成 | `VERIFIED/DEMO` | 最终 Word 报告的结构、分析和展示已成熟；新增首次阅读规范 | 最新 DOCX 未登记为新的 ResearchReport；现有 Schema 未显式承载画像和术语定义 |
| 8 资产沉淀 | `TARGET/DEMO` | 有目录、索引、哈希和案例文件 | 缺少 AssetIndex、当前版本指针、检索接口、复用条件和正式 release manifest |

## 4. 已经收口的设计

以下部分不需要继续扩展：

- 六位专家加一个总控的角色数量足够。
- 问卷和访谈仍作为 CAP-03 的两个模块。
- 定性和定量仍作为 CAP-05 的两个模块。
- 腾讯问卷只负责发行、回收和导出。
- IMA 保持人工学习链接和停用接口，不进入研究证据链。
- 问卷设计与变量、缺失和有效性规则保持同版。
- CAP-05 负责分析，CAP-06 负责表达，CAP-04 独立审核。
- Gate 必须由有权限的人批准，历史缺口不追溯补造。
- 投资者教育建议必须来自证据链，偏好不等于效果。

## 5. 本次新增的报告表达规范

新增 [研究报告可理解性与上下文规范](../01_standards/report-readability-and-context.md)，并接入 CAP-04、CAP-06 和 Gate 4。

它把过去依靠人工反馈形成的经验固定为：

- 默认读者没有看过问卷，也不熟悉专业术语。
- 每章先说明研究问题、分析对象、题目或指标范围。
- 重要数据段落先交代统计对象或筛选，再给数据、解释和业务意义。
- 专业术语第一次出现时解释“是什么、为什么相关、不代表什么”。
- 综合指标第一次出现时说明组成题目、计算方式和适用边界。
- 总览、章节首段、术语、综合指标和分群图表必须通过首次阅读抽查。

这项规则只改善表达，不能让 CAP-06 新增上游没有的分析。

## 6. 当前最重要的四个缺口

### 6.1 最新报告没有回到正式证据链

当前 `formal_artifacts/research-report.v0.1.0.json` 登记的是较早的展示报告。之后报告新增了：

- 年龄与投资经验分组分析。
- 组间差异和多重比较说明。
- 更完整的受访者画像。
- 十项结论总览。
- 多轮领导审阅后的最终 DOCX。

这些新增分析没有先形成新的 Evidence Unit、Finding 或 Insight，因此不能只把最新 Word 文件的哈希替换进旧 ResearchReport。

正确路径：

> 最新分析结果 → InsightPackage 0.2.0 → CAP-04 预审 → ResearchReport 0.2.0 → 最新 DOCX 登记

由于历史 Gate 3、Gate 4 不存在，新版本仍应保持 `DRAFT` 并保留治理缺口。

### 6.2 历史数据质量存在双口径

标准规定：存在未解决的 `REVIEW_REQUIRED` 时，数据集应为 `BLOCKED`。

历史案例同时记录：

- 100 份答卷仍为 `REVIEW_REQUIRED`。
- `dataset_status=ANALYSIS_READY_WITH_LIMITS`。
- 200 份均进入当时的工作分析。

这是为了诚实保留历史执行事实，但不应复制到新项目。后续建议拆成两个字段：

- `contract_dataset_status`：按当前规范应为 `BLOCKED`。
- `historical_working_analysis_status`：记录历史上确实进行过内部分析，并说明限制。

新项目不得使用“历史工作分析”绕过答卷状态解析。

### 6.3 ResearchReport 的机器结构弱于写作规范

当前 Schema 能验证证据引用、数字、限制和投教板块，但不能强制验证：

- 受访者画像是否完整。
- 哪些字段未采集。
- 专业术语第一次出现时如何解释。
- “四道题全部答对”等综合指标如何组成。
- 首次阅读测试是否完成。

Demo 阶段先由文本规范和 Gate 4 审核控制。下一版 Schema 可兼容新增：

- `participant_profile`
- `term_definitions`
- `composite_metric_definitions`
- `first_reader_review`

### 6.4 资产沉淀仍是目录，不是正式服务

当前已有文件、哈希、Registry 和索引，但缺少：

- 一个明确的“当前内容最终版”指针。
- 报告、图表数据、分析代码和上游 Artifact 的 release manifest。
- 资产适用范围、复用条件和失效原因。
- 跨项目检索和权限控制。

Demo 可以继续以文件目录交付；满血版应新增确定性的 AssetIndex/ReleaseManifest，而不是新增“归档 Agent”。

## 7. 分阶段完善清单

### 最小收尾：当前案例

1. 冻结最新最终版 DOCX 到项目目录并登记哈希。
2. 把新增年龄/经验分析整理为 InsightPackage 0.2.0。
3. 生成 ResearchReport 0.2.0，登记最终 DOCX，保持 `DRAFT / NO GATE 3 / NO GATE 4`。
4. 为最终报告执行一次 CAP-04 首次阅读复核并保存 ReviewResult；不能补造 ApprovalRecord。

### 下一真实项目

5. 在发行前真实完成 Gate 2，分析后完成 Gate 3，发布前完成 Gate 4。
6. 使用通用 Excel/CSV Adapter，而不是复制养老目标基金案例脚本。
7. 记录每份 `REVIEW_REQUIRED` 的人工决定，避免数据状态双口径。
8. 用一轮访谈或组合研究验证 CAP-03/CAP-05 的非问卷路径。
9. 把报告可理解性加入 CAP-04/CAP-06 新版本盲测和人工抽查。

### 生产化以后

10. 接入组织身份、持久化、备份和并发控制。
11. 建设 AssetIndex、检索和模板复用。
12. 扩展金融事实领域；满足条件后再评估 IMA 接口。

## 8. 最终判断

工作流没有“主线错误”或“专家角色缺失”。当前最需要补的是：

> 让最新分析回到 InsightPackage，让最终报告回到 ResearchReport，让历史数据状态和正式状态不再混用，再用一个全新项目走完真实 Gate 1—4。

完成这三类收口后，Demo 不只是“做出了一份好问卷和好报告”，而能更有说服力地证明这是一套可迁移、可复核、可持续运行的研究工作流。
