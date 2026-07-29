---
document_id: STD-MINIMUM-PERMISSIONS
version: 0.1.0
status: active
last_updated: 2026-07-27
machine_readable: minimum-permission-matrix.v0.1.0.json
---

# 最小权限矩阵

## 1. 原则

工作流默认拒绝访问。每次授权至少绑定 `project_id + task_id + purpose + resource_class + allowed_actions + expires_at`，不能用“研究团队成员”作为无限期、全项目授权理由。

权限遵循五条底线：

1. 专家只读取完成当前任务所需的最小上游信息；
2. 原始个人信息、联系方式映射与分析资料分离；
3. ReviewResult 不是 ApprovalRecord，Agent 永远没有正式审批权；
4. 外部发布、联系用户和扩大分发范围必须有单独授权；
5. 审计日志记录任务与版本，不默认复制原始答卷、逐字稿或联系方式。

## 2. 核心矩阵

| 角色 | 主要可读 | 主要可写/执行 | 明确禁止 |
|---|---|---|---|
| CAP-01 研究问题理解 | 原始需求、项目范围 | ResearchBrief | 原始调研数据、联系方式、审批、发行 |
| CAP-02 研究方案设计 | Gate 1 批准的 Brief | ResearchPlan | 原始调研数据、启动执行、审批 |
| CAP-03 研究工具设计 | 当前 Plan、已审核金融事实、IMA 链接元数据 | InstrumentSpec | 联系用户、发布问卷、虚构事实、把 IMA 当已启用事实接口 |
| CAP-04 研究质量审核 | 目标 Artifact、必要上游、已审核事实 | ReviewResult | ApprovalRecord、静默改写原 Artifact |
| CAP-05 分析与洞察 | FieldworkPackage、脱敏数据、Brief/Plan | InsightPackage | 联系方式、无关平台元数据、正式客户标签、业务决策 |
| CAP-06 研究报告 | 经审核 InsightPackage 及必要上下文 | ResearchReport | 原始数据、未追溯新结论、外部发布、审批 |
| CTRL-01 研究总控 | Registry、状态、Review、Approval | WorkflowState、TaskRecord、HandoffRecord | 改写专家语义、补造批准、越 Gate、记录原始敏感内容 |
| Fieldwork Service | Gate 2 批准的 Plan/Instrument、执行所需原始资料 | 脱敏数据、FieldworkPackage | 洞察解释、改变题意、审批 |
| 腾讯问卷 Adapter | Gate 2 批准的 InstrumentSpec | 建卷、经授权发布、导出 | 自行改题、未批准发布、洞察分析 |
| Excel/CSV Adapter | 指定文件、字段映射 | 脱敏标准化数据、质量日志 | 扩散原始文件、单一弱信号自动排除、生成结论 |
| Validator | Artifact 与 Schema | ValidationResult | 改 Artifact、语义审批、读取联系方式 |
| Human Gate Approver | 指定 Gate 审批包 | 精确版本 ApprovalRecord | 审批未授权 Gate、批准过期版本、把审批委托给 Agent |
| Human Data Steward | 原始数据、联系方式映射、脱敏结果 | 数据治理、隔离、删除与验证记录 | 为未批准目的使用联系方式、向分析 Agent 暴露映射 |

## 3. 数据分层

| 层级 | 内容 | 默认访问 |
|---|---|---|
| L0 公开 | 公开方法、公开金融常识、已批准公开报告 | 按任务开放 |
| L1 内部 | Brief、Plan、Instrument、Insight、Report、控制记录 | 项目内按能力开放 |
| L2 机密 | 脱敏答卷、脱敏逐字稿、项目内证据 | CAP-04/05 与授权研究人员 |
| L3 受限 | 原始答卷、IP/UA、录音、招募名单、联系方式映射 | Fieldwork Service 与 Data Steward；默认不进 Agent |

IMA 在当前体系中属于 L0/L1 的“可选学习资源元数据”。其链接可以被 CAP-03 和 CAP-06 引用，但接口能力处于 `RESERVED_DISABLED` 时，不得声称已经检索、读取或用其完成金融事实复核。

## 4. 运行要求

- 总控下发任务时必须生成权限快照；
- 上游版本改变或任务结束时撤销临时权限；
- 原始资料进入分析前必须先完成去标识化；
- CAP-05 和 CAP-06 默认只见稳定研究编号；
- 需要新数据类别、扩大分享或联系参与者时，暂停并按人工升级表处理；
- 权限拒绝不能通过把敏感信息复制到提示词、聊天摘要或日志中绕过。

## 5. 当前 Demo 的应用

养老目标基金案例的原始 CSV 含 IP、UA 和地理位置等平台字段，因此原始文件没有复制到 `formal_artifacts`。正式执行包只登记原文件哈希，并保存脱敏标准化数据和逐条质量信号。分析与报告专家只读取脱敏数据，不获得原始平台元数据。
