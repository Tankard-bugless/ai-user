---
document_id: STD-IMA-LIGHTWEIGHT-INTEGRATION
version: 0.3.0
status: draft
last_updated: 2026-07-24
upstream:
  - OVW-V1-SCOPE
  - STD-GLOSSARY
  - STD-ARTIFACT-CONVENTIONS
---

# IMA 轻量接入规范

## 1. 当前能力状态

IMA 在体系中被拆成两个互不混淆的组件：

| 组件 | 当前状态 | V1 用法 |
|---|---|---|
| IMA 链接桥梁 | `OPTIONAL_ENABLED` | 研究人员可人工提供并审核知识库入口，放在核心测量之后供参与者自愿学习 |
| IMA OpenAPI / Skill 接口 | `RESERVED_DISABLED` | 只保留适配器位置，默认运行不得调用 |

当前能力验证显示：

- Skill 可以检索订阅知识库中的标题。
- 订阅知识库正文读取会返回权限限制。
- Skill 未提供可在本工作流中使用的知识库自然语言问答接口。
- 完整正文阅读和知识库问答目前依赖 IMA 等腾讯侧产品环境，不具备在当前 Codex 工作流中的可迁移性。

“Skill 已安装”不等于“接口已启用”。V1 不把一个只能在特定产品环境中工作的能力写进问卷生成必经链路。

## 2. 主流程边界

当前默认路径为：

```text
ResearchBrief
  → ResearchPlan
  → CAP-03 生成问卷初稿
  → 使用金融事实库、监管文件和产品法律文件完成知识复核
  → 设计必要的 AI 解释及展示时点
  → 可选：人工加入已审核的 IMA 知识库入口
  → CAP-04 审核
  → Gate 2
```

CAP-01、CAP-02 和 CAP-03 默认都不调用 IMA OpenAPI。接口不可用不会阻断研究问题理解、方案设计、问卷生成、事实审核或报告生成。

## 3. 链接桥梁规则

IMA 链接只能作为 `learning_resources`：

- 默认放在知识题完成后、问卷完成页或访谈结束后。
- 参与者是否点击、阅读或停留不被采集。
- 链接及其访问行为不进入研究证据链。
- 不把“提供了链接”写成“用户已经理解”。
- 不把知识库入口写成产品推荐、收益承诺或适当性判断。

只有项目明确研究某项材料本身时，材料才进入 `test_materials`，并按新的材料理解度研究重新设计。

学习资源最小记录：

- `resource_id`
- `title`
- `source_type`
- `uri`
- `purpose`
- `placement`
- `placement_after_component_id`
- `link_review_status`
- `optional_for_participant = true`
- `evidence_use = NOT_RESEARCH_EVIDENCE`

## 4. AI 解释规则

AI 解释当前只能基于已审核金融事实和高优先级来源生成，不标注为“来源于 IMA”。

| 题目目的 | 回答前解释 | 回答后/模块后解释 |
|---|---|---|
| 经历、行为或态度题 | 仅可给不暗示答案的中性定义 | 可选 |
| 主观熟悉度题 | 原则上不解释 | 可选 |
| 客观知识、辨识或理解题 | 禁止出现会泄露答案的解释 | 推荐在提交该模块后或完成页展示 |

解释不得写进选项，不得包含收益承诺、产品推荐或确定性判断。

## 5. 预留接口

未来保留 `IMAAdapter`，但当前不实例化、不加入 Agent 必需工具、不写入 Gate 2 必需输入。预留能力包括：

- `search(query, filters)`：检索候选内容。
- `ask(question, scope)`：基于指定知识库回答问题并返回来源。
- `resolve(resource_id)`：取得可访问正文、标题和稳定链接。
- `health_check(uri)`：检查链接可用性。

当前 Schema 仅通过 `extensions` 保留扩展空间，不新增 IMA 专属必填字段。

## 6. 启用条件

只有以下条件全部满足，才能把接口状态从 `RESERVED_DISABLED` 改为 `ACTIVATED`：

1. 当前运行环境可直接调用，不依赖人工切换到其他产品。
2. 对目标知识库能够读取正文或完成知识库问答，而不只是返回标题。
3. 输出带有可核验的内容来源、稳定链接和适用范围。
4. 通过凭证、最小权限、隐私和失败降级测试。
5. 完成一个真实案例的正向、权限不足、无结果和来源冲突测试。
6. 研究负责人批准新的规范版本和能力状态。

启用必须产生新版本，不得因某次调用偶然成功而静默开启。

## 7. 当前 Gate 2 检查

- `ima_api_status` 必须为 `RESERVED_DISABLED`。
- InstrumentSpec 不把 IMA 接口输出列为必需输入或事实来源。
- 若人工加入 IMA 链接，位置、标题、用途和可访问性已审核。
- AI 解释能回到金融事实库或更高优先级来源，不冒充 IMA 正文。
- 接口不可用不会改变问卷或分析流程。
