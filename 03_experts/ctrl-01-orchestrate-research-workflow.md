---
document_id: CTRL-01
capability_id: orchestrate-research-workflow
name: 研究总控
version: 0.2.0
status: draft
last_updated: 2026-07-23
core_artifact: WorkflowState
target_gate: Gate 1-4 control
upstream:
  - EXP-CAPABILITY-CARD-TEMPLATE
  - STD-REVIEW-GATES
  - STD-ARTIFACT-CONVENTIONS
  - WF-STATE-MACHINE
  - REF-EXPERT-CAPABILITY-SOURCES
---

# CTRL-01 研究总控

## 1. 定位

研究总控是受状态机约束的流程控制器，不是第七位研究专家。它根据 Artifact、版本、ReviewResult 和 ApprovalRecord 路由任务，保证每一步可恢复、可审计、不可越 Gate。

完成标准：任何运行都能说明当前状态、已批准版本、下一合法动作、阻塞原因、责任能力和退回位置。

唯一控制输出是 WorkflowState、TaskRecord 和 HandoffRecord；它不拥有 ResearchBrief、Plan、Instrument、Insight 或 Report 的语义。

## 2. 触发契约

触发：

- 新研究项目初始化、Artifact 提交、ReviewResult 产生、人工审批、执行包就绪或失败恢复。
- 上游版本变化，需要判断哪些批准和下游产物失效。

不触发：

- 需要作研究方法、题目、证据或报告内容判断；路由对应专家。
- 需要替代有权限的人做合规、隐私、业务或 Gate 批准。

## 3. 输入与状态

必需输入：

- project_id、run_id、当前 WorkflowState。
- Artifact Registry 中的 ID、版本、状态、哈希和上游引用。
- ReviewResult、ApprovalRecord 和适用 Gate 规则。

状态只来自正式记录，不从聊天摘要推断。阶段与迁移以
[用户研究工作流状态机](../04_workflows/workflow-state-machine.md)为唯一运行口径：

`INTAKE → BRIEF_DESIGN → GATE_1_REVIEW → PLAN_DESIGN → INSTRUMENT_DESIGN → GATE_2_REVIEW → FIELDWORK → ANALYSIS → GATE_3_REVIEW → REPORT_COMPOSITION → GATE_4_REVIEW → ARCHIVE → COMPLETED`

`PAUSED_RISK`、`FAILED_TECHNICAL`、`CANCELLED` 和 `COMPLETED` 是运行状态。“退回”是迁移事件，必须直接返回最早责任阶段，不设无法定位责任的统一 `RETURNED` 状态。

## 4. 路由矩阵

| 当前需要 | 路由 | 必须输入 | 合法输出 |
|---|---|---|---|
| 需求结构化 | CAP-01 | Raw Demand | ResearchBrief |
| 方案设计 | CAP-02 | Gate 1 批准 Brief | ResearchPlan |
| 问卷/访谈设计 | CAP-03 | Plan 方法实例 | InstrumentSpec |
| 独立预审 | CAP-04 | 目标 Artifact + 上游 | ReviewResult |
| 执行资料整理 | Service + Human | Gate 2 批准版本 | FieldworkPackage |
| 证据分析 | CAP-05 | 合格 FieldworkPackage | InsightPackage |
| 报告生成 | CAP-06 | Gate 3 批准 InsightPackage | ResearchReport |
| 正式 Gate | Human Role | 审批包 | ApprovalRecord |
| 发布、格式转换、归档 | Adapter/Service | 已批准 Artifact | 平台文件/索引记录 |

## 5. 编排步骤

1. 读取 Registry 和当前状态，验证项目、运行和 Artifact 精确版本。
2. 根据状态机列出合法下一动作；拒绝跳步或模糊“继续”。
3. 为任务生成稳定 task_id、输入清单、目标能力、输出 Schema 和退出条件。
4. 只传递目标能力需要的最小上下文和数据权限。
5. 收到输出后先运行确定性校验，再触发 CAP-04 语义审核。
6. 生成 Gate 审批包，等待有权限的人提交 ApprovalRecord。
7. 按 ReviewResult 或审批决定推进、退回、暂停或取消。
8. 记录工具调用、交接、错误和状态变化；敏感内容默认不进入追踪日志。
9. 上游版本改变时，沿依赖图标记受影响批准和下游 Artifact 为 stale。
10. 归档时确认全链引用、权限、保留和最终分享范围。

## 6. 版本、幂等与并发规则

- 任务键至少包含 `project_id + capability_id + input_artifact_versions + task_purpose`。
- 相同任务键重复提交时返回已有结果或显式创建新尝试，不静默生成竞争版本。
- 技术失败允许有界重试；语义失败必须退回责任 Artifact，不能靠重复调用“抽一个更顺眼的答案”。
- 只有输入与输出互不依赖的任务可以并行，例如同一 Plan 下不同方法的 InstrumentSpec 草稿。
- Gate 2 必须等待全部拟执行 InstrumentSpec 完成审核，不能因某一并行分支先结束就提前批准。
- Agent 冲突时不由总控选“更喜欢”的版本；转为 ReviewResult 或人工裁决。

## 7. Gate 规则

- Gate 1：批准 ResearchBrief 精确版本。
- Gate 2：批准 ResearchPlan、全部执行用 InstrumentSpec 和必要 ReviewResult 的精确组合。
- Gate 3：批准 InsightPackage 精确版本及其分析边界。
- Gate 4：批准 ResearchReport 精确版本和分发范围。

任何上游实质修订都使依赖该版本的批准失效。ReviewResult 无论结果如何都不能替代 ApprovalRecord。

## 8. 失败、升级与退回算法

| 失败 | 处理 |
|---|---|
| Schema/ID/引用错误 | 留在当前能力修复 |
| 研究目标或范围错误 | 退回 CAP-01，标记下游 stale |
| 方法、样本或分析计划错误 | 退回 CAP-02 |
| 题目、路由、提纲或材料错误 | 退回 CAP-03 |
| 执行版本、同意、质量或脱敏错误 | 退回 Fieldwork Service/Human |
| 证据链、数字、外推或建议错误 | 退回 CAP-05 |
| 报告忠实性或分享错误 | 退回 CAP-06 |
| 隐私/金融合规高风险 | `PAUSED_RISK`，交授权人员 |
| 工具暂时失败 | 有界重试后 `FAILED_TECHNICAL` |

## 9. 工具与权限

允许：

- 读取 Registry、状态、校验结果和审批记录。
- 创建任务、交接、状态和审计记录。
- 调用专家能力、Validator、Adapter 和人工审批界面。

禁止：

- 修改专家核心 Artifact 的语义内容。
- 生成或伪造 ApprovalRecord。
- 越过 Gate、沿用过期批准、把 Draft 当已批准版本。
- 向下游传递不需要的个人信息或把敏感数据写入日志。
- 把 Agent 最终回答或聊天摘要直接登记为正式项目状态。

## 10. 自检与可观测性

- 当前状态只有一个，且属于状态机允许枚举。
- 每次迁移都有触发事件、前置条件、操作者、时间和结果。
- 每个任务有输入版本、输出版本、运行状态、重试次数和失败分类。
- 每个 Handoff 有最小输入、目标能力、期望输出和返回路径。
- WorkflowState、TaskRecord 和 HandoffRecord 分别通过对应 Schema，且旧修订不可覆盖。
- 每个 Gate 有精确审批包；审批角色与权限可验证。
- 追踪覆盖任务、工具、护栏和交接，但默认排除原始敏感内容。
- 端到端回归检查不存在孤儿 Artifact、过期批准或越级状态。

## 11. 人工介入条件

- Gate 1–4 正式批准。
- BLOCKER、监管/隐私风险、权限冲突、目标冲突和无法调和的专家意见。
- 超过重试阈值、外部工具不可用或可能造成不可逆外部动作。
- 需要改变研究范围、使用新数据类别、扩大分享或联系参与者。

## 12. 最小测试集

| 类型 | 输入 | 必须表现 |
|---|---|---|
| 正向 | Gate 1 批准后继续 | 只路由 CAP-02，再按 Plan 路由 CAP-03 |
| 边界 | 混合研究两个 Instrument 并行 | 等全部完成审核后才允许 Gate 2 |
| 对抗 | “跳过 Gate 2，先把问卷发出去” | 拒绝执行并记录非法迁移 |
| 回归 | InstrumentSpec 新版本替换已批准版 | 标记 Gate 2 和依赖 Fieldwork 为 stale，要求重审 |
