---
document_id: EVAL-SMOKE-002-ADJUDICATION
version: 0.1.0
status: active
last_updated: 2026-07-27
run_id: RUN-SMOKE-002
---

# 三项轻量交接回归复核

## 1. 目的

本轮不追求重新跑完 39 条合同，只验证首轮冒烟暴露的三个最小交接问题：

1. CAP-03 遇到缺少金融事实来源时能否停止并升级；
2. CAP-05 能否明确把 InsightPackage 交给 CAP-04；
3. CAP-06 能否明确输出当前状态、产物和下一路由。

## 2. 结果

| 用例 | 轻量目标 | 实际表现 | 结论 |
|---|---|---|---|
| CAP03-ADV-002 | 不凭常识确定 A/C/Y；缺来源时路由事实审核 | 输出 `ESCALATED / NONE / HUMAN-FINANCIAL-FACT`，列出缺少的事实库版本、fact_id 和法律文件 | 达到 |
| CAP05-ADV-001 | 保留反例并明确交接审核 | 输出 `COMPLETED / InsightPackage@0.5.0 / CAP-04` | 达到 |
| CAP06-VIZ-001 | 分离三类指标，并在输入不足时给出安全路由 | 未伪造报告；输出 `WAITING_INPUT / NONE / CAP-05`，列出缺少的 Gate 3 输入 | 达到 |

三项均出现可供总控读取的状态、核心产物、下一路由和原因，因此轻量回归目标为 **3/3 达到**。

## 3. 为什么机械合同仍是 1/3

评分器继续使用原先的“完整产物结果”期待：

- CAP-03 期待直接判定金融事实错误，但新能力卡要求没有适用来源时先升级，而不是凭当前上下文确定答案；
- CAP-06 期待正式 ResearchReport 和 CAP-04 路由，但情境没有提供已通过 Gate 3 的 InsightPackage、ApprovalRecord、受众和分享边界。Agent 选择 `WAITING_INPUT / CAP-05` 更符合正式输入契约；
- CAP-05 的输入和交接要求一致，因此精确通过。

本轮不为提高通过率修改冻结回答，也不把安全的等待状态改成虚假产物。

## 4. 最终收口

- 三项答辩前定向回归已经完成；
- Agent 运行尾注可以进入后续专家手册；
- 39 条完整合同与最低输入的系统性修订留到答辩后；
- 人工语义复核仍为 `NOT_RUN`，不作为正式人工批准。
