---
document_id: CASE-OTF-IMA-INTEGRATION-DECISION
version: 0.1.0
status: active
last_updated: 2026-07-24
project_id: PROJ-OTF-001
evidence_ref: CASE-OTF-IMA-KNOWLEDGE-REVIEW@0.1.0
---

# IMA 接口暂不启用决定

## 决定

当前案例和 V1 通用工作流不启用 IMA OpenAPI / Skill 接口：

- `ima_api_status = RESERVED_DISABLED`
- `manual_learning_link_status = OPTIONAL_ENABLED`

已安装的 Skill 作为未来能力储备保留，但 CAP-03 不在问卷生成、金融事实复核或 AI 解释生成过程中调用它。

## 原因

2026-07-24 的能力验证显示：

1. 当前 Skill 可以在「易方达基金」订阅知识库中搜索到相关标题。
2. 通过 Skill 请求正文时返回订阅知识库权限限制。
3. 当前 Skill 没有可供本工作流调用的知识库自然语言问答接口。
4. 完整阅读和知识库问答依赖 IMA 等腾讯侧产品环境，不能作为可迁移工作流的必需能力。

因此，把接口写进正式主链会使问卷生成依赖特定产品环境，并造成“搜到标题等于读过正文”的来源风险。

## 当前替代路径

- 金融知识复核：使用 `FIN-FACT-FOF@0.1.0`、监管文件和产品法律文件。
- AI 解释：只基于已审核事实生成，并遵守“知识题先测后教”。
- IMA 衔接：研究人员可人工提供知识库首页链接，放在问卷完成页供参与者自愿学习。
- 数据处理：不采集点击、停留、身份关联，不把链接访问作为研究证据。

## 重新启用条件

只有以下条件全部满足，才提交新的启用决定：

1. 当前 Agent 环境可直接完成知识库正文读取或问答。
2. 返回结果具有可核验来源和稳定内容链接。
3. 订阅知识库权限在目标运行环境中有效。
4. 正向、无结果、权限不足、来源冲突和凭证安全测试通过。
5. 研究负责人批准新版本的 IMA 接入规范和 Gate 2 规则。

接口恢复后必须生成新版本，不修改本记录来追认启用。

## 对当前产物的影响

- ResearchBrief 0.2.0：不变。
- ResearchPlan 0.2.0：不变。
- InstrumentSpec、Word 和腾讯问卷 0.2.0：不变。
- 现有 IMA 试用记录继续作为能力验证证据，不作为问卷知识来源。
- 工作流主线和 Gate 数量不变。
