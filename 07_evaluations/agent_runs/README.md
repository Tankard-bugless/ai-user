---
document_id: EVAL-AGENT-RUN-PROTOCOL
version: 0.3.0
status: active
last_updated: 2026-07-27
---

# 独立 Agent 真实测试协议

## 1. 目的

本目录用于保存 39 条能力测试真正运行后的原始回答和独立评估。测试定义完整不等于 Agent 能力通过；只有原始回答、独立评估和人工抽查同时存在，才能登记为真实测试结果。

## 2. 两段式执行

### A. 待测 Agent

待测 Agent 只能读取：

- 自己对应的专家能力卡；
- 当前运行清单指定的 `blind-test-packets` 精确版本中分配给自己的条目。

不得读取：

- `../capability-test-catalog.v0.1.0.md`；
- 与当前运行对应的 `capability-contract-fixtures` 期待答案文件；
- 其他评估结果。

每次回答先原样冻结到 `<run_id>/raw-outputs.jsonl`，不能在看到评分后改写。

建议的原始记录：

```json
{
  "fixture_id": "CAP01-POS-001",
  "run_id": "RUN-AGENT-EVAL-001",
  "subject_id": "SUBJECT-CAP01-001",
  "capability_id": "frame-research-question",
  "capability_version": "0.2.0",
  "generated_at": "2026-07-27T12:00:00+08:00",
  "raw_response": "待测 Agent 的完整原始回答"
}
```

### B. 独立观察者

人工或独立评估 Agent 读取冻结后的原始回答，再依据测试合同标注结果。观察者不能修改原始回答，也不能和待测 Agent 使用同一个响应。

每行评估至少包括：

```json
{
  "fixture_id": "CAP01-POS-001",
  "output_artifact_type": "ResearchBrief",
  "route": "CAP-04",
  "decision": "PRODUCE",
  "observed_behaviors": [
    "separate_facts_assumptions_unknowns"
  ],
  "observed_forbidden_behaviors": [],
  "assessor_id": "HUMAN-RESEARCH-REVIEWER-001",
  "assessor_type": "HUMAN",
  "raw_output_ref": "RUN-AGENT-EVAL-001/raw-outputs.jsonl#CAP01-POS-001",
  "evidence_notes": [
    "回答明确拆分已知事实、业务假设和待验证信息。"
  ]
}
```

`observed_behaviors` 需要有原始文本证据，不能由待测 Agent 自报。

## 3. 评分

```powershell
python 07_evaluations\run_capability_contract_tests.py `
  --assessment-jsonl <run_id>\assessments.jsonl `
  --require-all
```

`--candidate-jsonl` 只为旧文件兼容保留。它不检查评估来源，不能作为正式能力通过证据。

## 4. 当前状态

- 39 条合同用例：已定义；
- 39 条盲测输入：已生成；
- 评分器抗错测试：已建立；
- 独立 Agent 冒烟回答：`RUN-SMOKE-001` 已运行 7 条；
- 独立评估：7 条已完成；精确机器合同 1/7，通过核心决策 7/7，禁止行为 0/7；
- 定向交接回归：`RUN-SMOKE-002` 已运行 CAP-03、CAP-05、CAP-06 三条，轻量交接目标 3/3 达到；
- 全部 39 条独立 Agent 原始回答：尚未运行；
- 人工语义抽查：尚未运行。

未产生的记录不得补造或登记为通过。
