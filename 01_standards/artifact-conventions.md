---
document_id: STD-ARTIFACT-CONVENTIONS
version: 0.2.0
status: draft
last_updated: 2026-07-23
upstream:
  - OVW-V1-SCOPE
  - STD-GLOSSARY
  - STD-REVIEW-GATES
---

# 研究产物公共规范

本文件规定所有核心研究产物共同遵守的机器字段、版本、引用和状态规则。具体业务字段由 `02_schemas` 中的 JSON Schema 定义。

## 1. 字段与格式

- 机器字段统一使用英文 `snake_case`，中文仅用于标题、内容和 Schema 描述。
- JSON 是标准交换格式；表格、文档或外部平台格式必须通过 Adapter 转换。
- 时间使用带时区的 ISO 8601 格式；日期使用 `YYYY-MM-DD`。
- Schema 使用 JSON Schema Draft 2020-12。
- 未采集、未知和不适用不得混写为空字符串：未知值应省略；业务上允许明确空值时才使用 `null`；不适用应在对应说明字段中解释。

## 2. 公共元数据

每个核心产物必须包含 `metadata`，至少记录：

| 字段 | 含义 |
|---|---|
| schema_version | 当前产物所遵循的 Schema 版本 |
| artifact_id | 跨版本稳定的产物 ID |
| artifact_type | 术语表规定的唯一产物类型 |
| artifact_version | 本产物内容版本 |
| project_id | 所属研究项目 ID |
| title | 人可读标题 |
| lifecycle_status | 产物自身的生命周期状态 |
| created_at、updated_at | 创建和最后更新时间 |
| created_by | 创建主体；Agent 创建时记录模型和能力版本 |
| upstream_refs | 直接上游产物的 ID、类型和版本 |
| content_classification | 内容是真实、脱敏、合成还是模板 |
| sensitivity_level | 内容敏感级别 |
| contains_personal_data | 是否包含个人信息 |
| change_summary | 相对上一版本的变更摘要 |

## 3. ID 与版本

- ID 在同一项目内唯一，推荐格式为 `类型缩写-项目缩写-序号`，例如 `RB-DEMO-001`。
- `artifact_id` 跨版本保持不变；修改内容只提升 `artifact_version`。
- Schema 版本与产物版本独立。Schema 升级不自动改变既有产物版本。
- 版本格式为 `主版本.次版本.修订版本`。不兼容字段变化提升主版本；兼容新增提升次版本；说明或错误修正提升修订版本。
- 新版本替代旧版本时必须填写 `supersedes_ref`，旧版本保留，不得覆盖。

## 4. 生命周期与审批

产物生命周期使用：

- `DRAFT`：正在编辑。
- `IN_REVIEW`：已提交质量或人工审核。
- `FROZEN`：已有有效 ApprovalRecord，内容冻结。
- `SUPERSEDED`：已被新版本替代。
- `ARCHIVED`：不再参与活动流程，但保留追溯。

`lifecycle_status` 不等于审核关口状态。正式 `APPROVED` 只能存在于独立的 ApprovalRecord 中；ReviewResult 也不能替代 ApprovalRecord。

## 5. 引用与可追溯

- 产物引用必须同时包含 `artifact_id`、`artifact_type` 和 `artifact_version`。
- 引用已经批准的产物时，可附带 `approval_id`，但不得只写“最新版”。
- 下游产物不得静默改写上游内容。需要修正上游时，必须生成上游新版本并按回溯规则重新推进。
- 人可读链接是辅助信息，不替代结构化引用。

## 6. 内容来源与数据边界

`content_classification` 采用四类：

| 值 | 含义 | 是否可进入正式证据链 |
|---|---|---|
| REAL | 经授权的真实业务或研究内容 | 可以，仍需满足证据规范 |
| SANITIZED | 对真实内容进行脱敏或改写后的内容 | 可以，但必须保留受控来源映射 |
| SYNTHETIC | 为演示、测试或开发生成的合成内容 | 不可以 |
| TEMPLATE | 无项目事实的空白模板 | 不可以 |

示例目录中的文件必须使用 `SYNTHETIC`，不得与真实研究数据混放。

## 7. 扩展机制

- 平台专属字段不得进入核心字段。
- 确需保留的非核心信息放入 `extensions`，键名必须带命名空间，例如 `surveyking.questionnaire_id`。
- Adapter 不得改变核心字段语义；无法无损转换时必须输出警告，不得静默丢弃。

## 8. 三层校验

1. 结构校验：JSON Schema 检查类型、必填字段、枚举和条件结构。
2. 语义校验：专家能力检查目标映射、方法合理性、题目质量、风险和证据边界。
3. Gate 审批：授权人员判断指定版本是否可以进入下一阶段。

结构校验通过只表示“格式可读取”，不表示研究设计有效或已经获批。

## 9. 控制记录

WorkflowState、TaskRecord 和 HandoffRecord 是流程控制记录，不是研究证据，也不使用核心研究产物的 `artifact_metadata`。

- 控制记录使用 `record_id + record_revision` 保存不可覆盖的修订历史。
- 控制记录必须包含 `project_id`、`run_id`、创建主体、时间、分类和变更说明。
- 控制记录本身不得保存参与者个人信息，`contains_personal_data` 固定为 `false`。
- 控制记录可以引用受控 Artifact，但不得复制原始答卷、逐字稿、客户信息或完整聊天记录。
- 状态变化、任务状态变化和交接状态变化均生成新修订；旧修订保留以供审计。
- 三类控制记录的具体结构由 `workflow-state.schema.json`、`task-record.schema.json` 和 `handoff-record.schema.json` 定义。
