---
document_id: STD-AGENT-RUN-RESPONSE
version: 0.1.0
status: active
last_updated: 2026-07-27
---

# 专家 Agent 运行交接尾注

## 1. 目的

专家的核心工作仍写入 ResearchBrief、ResearchPlan、InstrumentSpec、ReviewResult、InsightPackage 或 ResearchReport。为了让总控知道“这次调用结束后该做什么”，每次运行只需额外附加一个简短交接尾注。

它不是新的研究 Artifact，也不替代 TaskRecord、HandoffRecord 或人工 ApprovalRecord。

## 2. 最小字段

```text
运行状态：COMPLETED / WAITING_INPUT / ESCALATED / REFUSED
核心产物：<ArtifactType@version 或 NONE>
下一路由：<能力、人工角色或 STOP>
原因：<一句话说明>
```

## 3. 使用规则

- 正常完成时，`核心产物`填写已生成的精确版本，`下一路由`填写审核方或下一能力。
- 缺少最低输入时使用 `WAITING_INPUT`，路由到能够补充信息的角色，不伪造正式产物。
- 需要事实、合规、隐私或方法人工判断时使用 `ESCALATED`。
- 拒绝越权、诱导、删证据或跳 Gate 时使用 `REFUSED`，并说明恢复条件。
- 尾注只表达当前立即发生的下一步，不把“补齐输入后的最终下游”混写成当前路由。
- 如果业务流程需要记录最终下游，由总控在新的 TaskRecord 中创建，不要求专家一次写完所有未来步骤。

## 4. Demo 边界

V1 Demo 先在 CAP-03、CAP-05、CAP-06 中使用该尾注，解决金融事实升级、洞察审核和报告审核的稳定交接。后续若运行稳定，再推广到其他专家，不作为本次答辩前置条件。
