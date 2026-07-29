---
document_id: WF-RUNTIME-README
version: 0.1.0
status: draft
last_updated: 2026-07-27
---

# 研究总控最小运行时

本目录把 CTRL-01 的状态、版本、Gate 和权限规则实现为一个本地、平台无关的最小原型。它不是新的研究专家，也不生成研究语义内容。

## V0.1 能力

- 创建不可覆盖的 WorkflowState 修订；
- 将 Artifact 的精确 ID、版本、哈希和上游引用登记到本地 Registry；
- 根据状态机拦截非法迁移；
- Gate 只接受人类创建、`is_ai_approval=false`、精确覆盖当前版本组合的 ApprovalRecord；
- 上游新版本出现时，沿引用图把依赖产物和批准标为 `STALE`；
- 根据最小权限矩阵为 TaskRecord 生成权限快照；
- 保存追加式审计事件，不把聊天历史或原始个人信息写入控制记录。

## 存储结构

每个运行目录包含：

```text
registry.v0.1.0.json
states/
tasks/
audit.jsonl
```

Registry 是运行服务的索引；正式研究语义仍只存在于 ResearchBrief、ResearchPlan、InstrumentSpec、FieldworkPackage、InsightPackage 和 ResearchReport 中。

## 历史案例规则

历史案例缺少 Gate 时，不允许“直接导入为已完成”。应从项目最早仍有效的真实批准重新登记：

1. 登记真实 Artifact 和哈希；
2. 只应用确实存在的 ApprovalRecord；
3. 停在最早缺失 Gate；
4. 把在缺失 Gate 之后产生的下游 Artifact 标记为 `STALE`；
5. 明确这些文件仍可用于内部复盘，但不能推动工作流进入下一 Gate。

养老目标基金案例因此会停在 `GATE_2_REVIEW / WAITING_GATE`，而不是伪装为已通过 Gate 4。

该案例的运行登记位于：

```text
05_cases/养老目标基金购买者研究/formal_artifacts/runtime/
```

可用 `register_historical_runtime.py` 在目录尚不存在时重建登记。脚本是幂等读取的：Registry 已存在时不会覆盖其状态历史。

## 运行

```powershell
python 04_workflows\runtime\workflow_runtime.py --help
```

创建运行：

```powershell
python 04_workflows\runtime\workflow_runtime.py init `
  --store <运行目录> `
  --project-id PROJ-DEMO-001 `
  --run-id RUN-DEMO-001
```

总控运行时的自动测试：

```powershell
python 07_evaluations\test_workflow_runtime.py
```

当前 6 个测试覆盖正常流转、并行审核、非法跳 Gate、AI 审批、最小权限和版本失效回退。完整项目检查还会验证真实案例的历史治理边界：

```powershell
python 07_evaluations\run_all_checks.py
```

## 非目标

- 不自主生成问卷、洞察或报告；
- 不联系参与者或自动发布问卷；
- 不保存密钥、联系方式或原始答卷；
- 不替代 CAP-04 或人类 Gate；
- 不提供网络服务、并发队列或组织级身份系统。
