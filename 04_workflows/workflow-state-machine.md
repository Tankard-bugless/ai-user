---
document_id: WF-STATE-MACHINE
version: 0.6.0
status: draft
last_updated: 2026-07-27
upstream:
  - OVW-V1-SCOPE
  - STD-GLOSSARY
  - STD-ARTIFACT-CONVENTIONS
  - STD-REVIEW-GATES
  - CTRL-01
---

# 用户研究工作流状态机

## 1. 前置一致性复核

进入状态机设计前，已对范围、术语、四个 Gate、八类研究/治理产物、六张专家卡和总控卡进行交叉复核。

结论：当前架构与既定设想一致，没有阻塞下一阶段的问题。

- 主线仍是“需求理解 → 研究方案 → 问卷/访谈 → 执行 → 分析洞察 → 报告 → 资产沉淀”。
- 专家只负责研究判断；总控只负责状态、版本、任务和路由。
- CAP-04 生成 ReviewResult，但不能生成 ApprovalRecord 或代替人工 Gate。
- IMA 人工链接是核心测量后的可选学习入口；OpenAPI 接口为 `RESERVED_DISABLED`，不进入状态迁移、研究主线、事实来源或用户行为证据。
- 研究分群与候选标签不自动成为正式客户标签或适当性标签。
- 问卷工具与数据契约同版：InstrumentSpec 定义变量和有效性规则，FieldworkPackage 只记录规则执行结果。
- 问卷平台只承担智能发行、回收和导出；回传 Excel 由 Adapter 映射、脱敏和规范化后进入 FieldworkPackage。
- 金融研究报告除回答 Research Question 外，还需呈现由上游证据支持的投资者教育建议；证据不足时明确标记不适用。

本轮收口三处轻微口径：

1. 核心研究/治理产物数量统一为八类。
2. Plan 与 Instrument 分为两个阶段，Gate 2 再批准两者的精确版本组合。
3. `RETURNED` 不再作为模糊的稳定状态；“退回”是一种迁移事件，状态直接回到最早责任阶段。

## 2. 三类控制记录

| 控制记录 | 回答的问题 | 不承载的内容 |
|---|---|---|
| WorkflowState | 当前在哪个阶段、哪些版本有效、下一步是否合法 | 研究结论、问卷正文、原始个人信息 |
| TaskRecord | 谁在什么权限下，用哪些精确输入完成什么输出 | 无边界提示词、未授权外部动作 |
| HandoffRecord | 从哪个任务向谁交接哪些最小信息，失败退回哪里 | 完整聊天历史、参与者个人资料副本 |

三类记录采用“同一 `record_id` + 递增 `record_revision`”保存历史。每次状态、任务或交接发生实质变化都生成新修订，不覆盖旧修订。

三类记录的 `contains_personal_data` 固定为 `false`。它们可以引用受控研究产物，但不得复制原始个人信息。

运行时增加三个不改变研究阶段的控制事件：

- `TASK_CREATED`：任务进入运行索引；
- `TASK_STATUS_CHANGED`：任务完成、失败、取消或变为 stale，但该任务本身不触发主路径推进；
- `REGISTRY_UPDATED`：Artifact 的精确版本、哈希或有效性进入 Registry。

三个事件的 `from_stage` 与 `to_stage` 必须相同。它们只解决控制快照的可审计性，不能替代主路径中的 `TASK_SUCCEEDED`、`GATE_SUBMITTED` 或 `GATE_APPROVED`。

## 3. 状态模型

一个 WorkflowState 同时记录两个维度：

- `current_stage`：研究流程走到哪里。
- `run_status`：当前是否活动、等待人工 Gate、风险暂停、技术失败、取消或完成。

规范阶段顺序：

```text
INTAKE
  → BRIEF_DESIGN
  → GATE_1_REVIEW
  → PLAN_DESIGN
  → INSTRUMENT_DESIGN
  → GATE_2_REVIEW
  → FIELDWORK
  → ANALYSIS
  → GATE_3_REVIEW
  → REPORT_COMPOSITION
  → GATE_4_REVIEW
  → ARCHIVE
  → COMPLETED
```

`PAUSED_RISK`、`FAILED_TECHNICAL` 和 `CANCELLED` 是运行状态，不是研究阶段。风险解除或技术恢复后，运行回到暂停前的 `current_stage`，不会伪造一个新的研究阶段。

## 4. 主路径迁移表

| 当前阶段 | 合法触发事件 | 进入下一阶段的最低条件 | 下一阶段 |
|---|---|---|---|
| 无 | `PROJECT_CREATED` | 项目和运行 ID 已创建，未加载个人数据 | INTAKE |
| INTAKE | `TASK_SUCCEEDED` | 原始业务需求、需求方和用途已登记 | BRIEF_DESIGN |
| BRIEF_DESIGN | `GATE_SUBMITTED` | ResearchBrief 结构校验通过；CAP-04 无未解决 BLOCKER/MAJOR | GATE_1_REVIEW |
| GATE_1_REVIEW | `GATE_APPROVED` | 有权限的人提交有效 Gate 1 ApprovalRecord | PLAN_DESIGN |
| PLAN_DESIGN | `TASK_SUCCEEDED` | ResearchPlan 结构校验通过；方法、样本、分析和质量计划可供工具设计 | INSTRUMENT_DESIGN |
| INSTRUMENT_DESIGN | `GATE_SUBMITTED` | 全部拟执行 InstrumentSpec、当前 ReviewResult、Pilot 记录或未试测风险说明齐备 | GATE_2_REVIEW |
| GATE_2_REVIEW | `GATE_APPROVED` | 人工批准 ResearchPlan 与全部执行用 InstrumentSpec 的精确组合 | FIELDWORK |
| FIELDWORK | `TASK_SUCCEEDED` | FieldworkPackage 完整；执行版本、同意、质量、排除和脱敏状态明确；无未解决答卷，数据集为 `ANALYSIS_READY` 或 `ANALYSIS_READY_WITH_LIMITS` | ANALYSIS |
| ANALYSIS | `GATE_SUBMITTED` | InsightPackage 引用链、数字、反例、限制和候选标签状态通过预审 | GATE_3_REVIEW |
| GATE_3_REVIEW | `GATE_APPROVED` | 人工批准 InsightPackage 精确版本及分析边界 | REPORT_COMPOSITION |
| REPORT_COMPOSITION | `GATE_SUBMITTED` | ResearchReport 忠实引用已批准 InsightPackage，投资者教育板块与建议域一致，分享范围明确 | GATE_4_REVIEW |
| GATE_4_REVIEW | `GATE_APPROVED` | 人工批准报告精确版本和分发范围 | ARCHIVE |
| ARCHIVE | `ARCHIVE_COMPLETED` | 全链引用、审批、保留期限、权限和资产索引齐备 | COMPLETED |

任何 `GATE_*_REVIEW` 阶段通常使用 `WAITING_GATE`；如审核中发现必须暂停的风险，可改为 `PAUSED_RISK`，但 `current_gate` 仍保持待决。Gate 阶段必须记录匹配的 `current_gate.gate_id`，其他阶段不得保留 `current_gate`。

## 5. 退回与失效规则

`GATE_CHANGES_REQUIRED`、`VALIDATION_FAILED`、`UPSTREAM_REVISED` 和语义失败不会进入统一的 `RETURNED` 状态，而是直接回到最早产生问题的阶段。

| 问题位置 | 返回阶段 | 必须失效的下游内容 |
|---|---|---|
| 研究目标、问题或范围 | BRIEF_DESIGN | 依赖旧 Brief 的 Plan、Instrument、批准和后续产物 |
| 方法、样本或分析计划 | PLAN_DESIGN | 依赖旧 Plan 的 Instrument、Gate 2 批准和后续产物 |
| 题目、提纲、路由或材料 | INSTRUMENT_DESIGN | 对应 Instrument 的 Gate 2 批准和执行数据 |
| 执行版本、同意、质量或脱敏 | FIELDWORK | 依赖受影响 FieldworkPackage 的分析和报告 |
| 编码、统计、解释或建议 | ANALYSIS | Gate 3 批准、报告和 Gate 4 批准 |
| 报告表达、引用或分享范围 | REPORT_COMPOSITION | Gate 4 批准 |

失效动作必须同时完成：

1. 将受影响 Artifact 在 `artifact_registry` 标记为 `STALE`。
2. 把精确引用加入 `stale_artifact_refs`。
3. 取消或标记尚未完成的下游 TaskRecord 为 `STALE`。
4. 生成新的 WorkflowState 修订并记录原因；不得修改旧 ApprovalRecord。

`GATE_REJECTED` 由授权人决定返回 BRIEF_DESIGN 重新定义，或把运行置为 `CANCELLED`。总控不得自行把拒绝降级为“修改后继续”。

## 6. TaskRecord 规则

每个任务必须冻结：

- 当前 WorkflowState 精确修订。
- 任务类型、目的、目标能力或人工角色。
- 输入 Artifact/控制记录的精确版本。
- 预期输出类型和 Schema。
- 进入条件、完成条件、权限和禁止动作。
- 幂等键、尝试次数和失败分类。

任务幂等键至少由以下内容组成：

```text
project_id + target_id + input_versions + task_purpose
```

技术失败可以在 `max_attempts` 内重试；研究语义失败必须退回责任阶段，不能通过重复调用模型挑选一个更顺眼的答案。

## 7. HandoffRecord 规则

交接以 Artifact 引用为主体，不以聊天摘要为主体。一个合法交接必须说明：

- `from_task_id`、`to_task_id`、发送方和目标能力。
- 传递的 Artifact 与控制记录精确版本。
- 实际开放的字段路径。
- 明确排除的数据类别。
- 预期输出、验收条件和失败返回阶段。
- `chat_history_included=false`。

如果目标能力发现输入不足，应拒绝交接并返回缺失项；不得从历史聊天或其他项目猜测补齐。

问卷数据从采集到分析的内部状态流为：

`UNASSESSED` → `VALID` / `REVIEW_REQUIRED` / `EXCLUDED` → 人工解决全部 `REVIEW_REQUIRED` → `ANALYSIS_READY` / `ANALYSIS_READY_WITH_LIMITS`

若问卷版本、字段或核心逻辑无法对应，整体数据集进入 `BLOCKED`，退回 FieldworkPackage 整理；若问题来自已发布工具定义，则回退到 InstrumentSpec 并生成新版本。

问卷数据通过 Excel 回传时，原始工作簿只读冻结；字段映射、规范化答卷和质量结果分别保存。平台在线统计或答案 API 不是状态迁移条件。

## 8. 并发规则

允许并行：

- 同一 ResearchPlan 下相互独立的问卷与访谈 InstrumentSpec 草稿。
- 同一 Gate 审批包中互不依赖的确定性校验。
- 报告生成前，不改变证据语义的独立格式检查。

禁止提前推进：

- Gate 2 必须等待全部拟执行 InstrumentSpec 和对应 ReviewResult。
- Gate 3 必须等待纳入范围内的全部 FieldworkPackage 和分析完成。
- 任一并行分支产生 BLOCKER/MAJOR 时，相关 Gate 不得因其他分支完成而开启。

## 9. 暂停、失败与恢复

| 情况 | `run_status` | 处理 |
|---|---|---|
| 隐私、合规、金融表达或权限风险 | PAUSED_RISK | 保留当前阶段，记录人工角色和恢复条件 |
| 工具、网络或外部服务失败 | FAILED_TECHNICAL | 保留当前阶段，按有界重试规则恢复 |
| 人工 Gate 尚未决定 | WAITING_GATE | 禁止启动下一阶段任务 |
| 项目被有权限人员取消 | CANCELLED | 取消活动任务，保留全部历史 |
| 归档完成 | COMPLETED | 不再创建研究任务，只允许受控检索 |

恢复必须产生新的 WorkflowState 修订。不得删除失败状态或把失败任务改写成成功。

## 10. 确定性校验

Validator 至少检查：

- 三类控制记录符合对应 JSON Schema。
- `record_revision > 1` 时存在同类型、同 ID 的上一修订引用。
- WorkflowState 中活动、完成和阻塞任务集合互不重叠。
- `transition.to_stage` 等于当前阶段。
- TaskRecord 的 `attempt <= max_attempts`。
- HandoffRecord 的 `to_task_id`、状态引用和目标能力与目标 TaskRecord 一致。
- 交接引用是目标任务输入引用的子集，字段范围不越过权限。
- Gate 阶段、Gate ID、ApprovalRecord 和下一阶段相互匹配。
- 上游版本变化后，不存在继续使用旧批准的活动任务。

Schema 校验只确认控制记录结构可读；研究语义仍由专家能力、CAP-04 和人工 Gate 负责。

## 11. V1 非目标

本状态机不负责：

- 自动发布问卷、联系参与者或发送材料。
- 自动批准 Gate 或生成虚假的人工身份。
- 用运行日志、聊天或 IMA 点击行为补充研究证据。
- 决定研究结论、基金产品、投资建议或正式客户标签。
- 代替问卷平台、存储、权限和归档系统本身。
