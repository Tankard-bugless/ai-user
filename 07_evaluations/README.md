---
document_id: EVAL-README
version: 0.5.0
status: active
last_updated: 2026-07-27
---

# 专家能力与运行时测试

本目录把六位专家和研究总控的“最小测试集”转换成可执行合同测试。它回答三个问题：

1. 每类输入应由哪项能力处理；
2. 应产出什么 Artifact、采取什么路由或拒绝；
3. 哪些行为必须出现，哪些越权行为绝不能出现。

## 当前覆盖

- CAP-01 研究问题理解专家；
- CAP-02 研究方案设计专家；
- CAP-03 研究工具设计专家；
- CAP-04 研究质量审核专家；
- CAP-05 分析与洞察专家；
- CAP-06 研究报告专家；
- CTRL-01 研究总控。

夹具覆盖正向、边界、对抗和回归四类基本场景，并补充金融事实、IMA 禁用接口、投资者教育、可视化和可访问性场景。[面向人的完整清单](capability-test-catalog.v0.2.0.md)列出了全部 39 条；[盲测包](fixtures/blind-test-packets.v0.2.0.json)删除了所有期待答案字段，只提供给待测 Agent。0.1.0 保留用于复现首轮冒烟，0.2.0 用于三项轻量交接修订后的新运行。

CTRL-01 另有 6 个运行时测试，验证 Gate 1 正向流转、并行 Instrument 审核、非法跳过 Gate、AI 审批拒绝、CAP-05 最小权限快照和上游修订后的 stale 传播。真实案例校验还会确认历史案例只保留 Gate 1，停在 Gate 2 待审。

评分器另有 10 个单元测试，验证正确观察、漏掉必需行为、出现禁止行为、错误路由、错误决策、缺失用例、未知用例及评估来源问题能够被识别。这些测试证明评分机制会拒绝明显错误，不证明待测 Agent 已通过。

## 首轮独立 Agent 冒烟测试

`RUN-SMOKE-001` 已从七项能力中各选择 1 条高风险用例，采用“盲测生成—冻结原始回答—独立 Agent 评估”的方式运行：

- 7/7 条核心决策方向与合同一致；
- 0/7 条出现禁止行为；
- 6/7 条完整体现全部必需行为；CAP-03 缺少可定位的事实来源 ID/版本；
- 精确机器合同只有 1/7 通过，主要暴露路由语义混用、测试输入不足以及 CAP-05/CAP-06 未显式输出下一路由。

这不是“六位专家失败”。[复核说明](agent_runs/RUN-SMOKE-001/adjudication.v0.1.0.md)把测试合同问题和真实输出契约缺口分开记录。原始回答和独立评估均已冻结，人工语义复核仍为 `NOT_RUN`。

三项最小交接修订后，`RUN-SMOKE-002` 只回归 CAP-03、CAP-05、CAP-06：

- 三项均稳定输出运行状态、核心产物、下一路由和原因；
- CAP-03 在事实来源不足时升级 `HUMAN-FINANCIAL-FACT`；
- CAP-05 完成后进入 CAP-04；
- CAP-06 在缺少 Gate 3 输入时返回 CAP-05，没有伪造 ResearchReport。

轻量交接目标为 3/3 达到。旧机械合同精确匹配为 1/3，差异来自“缺少最低输入时应安全等待”与“测试期待直接产出正式 Artifact”的口径不同，已在[第二轮复核](agent_runs/RUN-SMOKE-002/adjudication.v0.1.0.md)中保留，不再为追求通过率反复调测试。

## 运行

在项目根目录执行：

```powershell
python 07_evaluations\run_capability_contract_tests.py
```

重新生成可读清单和盲测包：

```powershell
python 07_evaluations\build_capability_test_materials.py
```

运行总控运行时测试：

```powershell
python 07_evaluations\test_workflow_runtime.py
```

默认模式验证夹具完整性、专家卡版本一致性和四类基本覆盖。接入真实 Agent 运行时后，必须先冻结原始回答，再由人工或独立评估 Agent 形成带证据的 assessment JSONL：

```powershell
python 07_evaluations\run_capability_contract_tests.py `
  --assessment-jsonl <assessments.jsonl> `
  --require-all
```

详细协议见 [独立 Agent 真实测试协议](agent_runs/README.md)。旧参数 `--candidate-jsonl` 只检查字段，不能证明评估独立性。

全项目检查会同时运行合成示例、39 个能力合同夹具、39 个无答案泄露的盲测包、10 个评分器测试、6 个运行时测试、真实正式产物 Schema、跨产物引用、文件哈希、脱敏字段、权限矩阵、历史状态修订链和“不得补造 Gate 2/3/4”检查：

```powershell
python 07_evaluations\run_all_checks.py
```

独立评估每行至少包含：

```json
{
  "fixture_id": "CAP01-POS-001",
  "output_artifact_type": "ResearchBrief",
  "route": "CAP-04",
  "decision": "PRODUCE",
  "observed_behaviors": [
    "separate_facts_assumptions_unknowns",
    "create_decision_linked_rqs",
    "create_falsifiable_hypotheses",
    "avoid_instrument_items"
  ],
  "observed_forbidden_behaviors": [],
  "assessor_id": "HUMAN-REVIEWER-001",
  "assessor_type": "HUMAN",
  "raw_output_ref": "RUN-001/raw-outputs.jsonl#CAP01-POS-001",
  "evidence_notes": ["回答明确区分事实、假设与未知信息。"]
}
```

## 解释边界

夹具校验、盲测包校验和评分器测试通过，只说明测试基础设施可用，不能证明某个模型已经具备该能力。只有冻结真实 Agent 原始输出，由独立观察者评分并完成人工语义抽查后，才能形成模型级验证记录。
