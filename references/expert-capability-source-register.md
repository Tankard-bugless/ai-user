---
document_id: REF-EXPERT-CAPABILITY-SOURCES
version: 0.1.0
status: active
last_updated: 2026-07-23
scope:
  - CAP-01
  - CAP-02
  - CAP-03
  - CAP-04
  - CAP-05
  - CAP-06
  - CTRL-01
---

# 专家能力卡来源与采用记录

## 1. 使用说明

本文件记录 M4 专家能力卡所依据的公开资料、内部方法 Skill，以及“采用、条件采用或拒绝”的决定。它不是文献综述，也不把任何单一框架视为绝对标准。

采用规则：

1. 法律法规、监管机构和官方标准优先用于定义硬边界。
2. 同行评审方法论文用于定义分析方法，但不机械转成全场景硬门槛。
3. 专业研究组织和政府服务手册用于形成操作检查项。
4. 内部 Skill 用于补充步骤与模板；与本项目术语、Schema 或 Gate 冲突时，以项目规范为准。
5. 公开资料中的经验数字、固定题量和固定洞察数量，不自动成为机器规则。

## 2. 外部权威来源

| source_id | 来源 | 主要适用能力 | 采用内容 | 使用边界 |
|---|---|---|---|---|
| SRC-UR-01 | [GOV.UK：Plan user research for your service](https://www.gov.uk/service-manual/user-research/plan-user-research-for-your-service) | CAP-01、CAP-02 | 从假设形成研究问题；目标人群、方法和决策相连 | 政府服务语境下的操作指南，不替代行业合规 |
| SRC-UR-02 | [GOV.UK：Capturing research questions](https://www.gov.uk/service-manual/user-research/capturing-research-questions) | CAP-01 | 研究问题应宽泛、开放、可排序；研究问题不是直接问用户的话 | 不把示例措辞当固定模板 |
| SRC-UR-03 | [GOV.UK：Plan a round of user research](https://www.gov.uk/service-manual/user-research/plan-round-of-user-research) | CAP-02 | 每轮研究说明决策、假设、招募、同意、记录、练习和分析时间 | 轮次规模由方法和风险决定 |
| SRC-UR-04 | [GOV.UK：Finding participants](https://www.gov.uk/service-manual/user-research/find-user-research-participants) | CAP-02、CAP-04 | 招募真实或潜在用户；研究问题驱动纳排标准；兼顾可访问性并降低招募偏差 | “4–8 人”仅是部分访谈轮次经验值，不固化为通用样本规则 |
| SRC-UR-05 | [GOV.UK：Using in-depth interviews](https://www.gov.uk/service-manual/user-research/using-in-depth-interviews) | CAP-03 | 开放、中性问题；追问真实经历；试访；知情同意和记录计划 | 不要求访谈严格逐字照读提纲 |
| SRC-UR-06 | [GOV.UK：Getting informed consent](https://www.gov.uk/service-manual/user-research/getting-users-consent-for-research) | CAP-02、CAP-03、CAP-04 | 说明研究方、目的、数据、用途、共享、保存、退出、观察和录音 | 具体表单仍需组织法务或隐私责任人确认 |
| SRC-UR-07 | [GOV.UK：Managing research data and participant privacy](https://www.gov.uk/service-manual/user-research/managing-user-research-data-participant-privacy) | CAP-04、CAP-05、CAP-06 | 直接标识符移除；分享范围最小化；可识别材料限制访问 | 与中国法及组织制度冲突时，采用更严格要求 |
| SRC-SUR-01 | [AAPOR：Best Practices for Survey Research](https://aapor.org/standards-and-ethics/best-practices/) | CAP-02、CAP-03、CAP-04 | 先判断是否应做问卷；单一概念、简短中性、题序、敏感题、低负担和偏差控制 | 不把自愿应答样本描述为概率样本 |
| SRC-SUR-02 | [AAPOR：Disclosure Standards](https://aapor.org/standards-and-ethics/disclosure-standards/) | CAP-04、CAP-06 | 披露研究方、目的、总体、样本、模式、日期、题目、处理和质量程序 | 内部报告可按受众裁剪，但核心方法不可隐去 |
| SRC-SUR-03 | [Pew Research Center：Writing Survey Questions](https://www.pewresearch.org/writing-survey-questions/) | CAP-03 | 开放/封闭题选择、选项穷尽互斥、题序和措辞效应、预测试 | Pew 的具体调查惯例不直接成为金融场景硬规则 |
| SRC-SUR-04 | [U.S. Census Bureau：Statistical Quality Standard A2](https://www.census.gov/about/policies/quality/standards/standarda2.html) | CAP-03、CAP-04 | 可读性与理解度审查；认知访谈；系统集成测试；保存预测试记录 | 用作高质量参照，不宣称本项目获得 Census 认证 |
| SRC-SUR-05 | [CDC CCQDER：Question Evaluation](https://www.cdc.gov/nchs/ccqder/index.html) | CAP-03、CAP-04 | 用认知访谈识别理解、回忆、判断和作答错误 | 高风险或新构念优先使用，非每道题都强制认知访谈 |
| SRC-MM-01 | [NIH OBSSR：Best Practices for Mixed Methods Research](https://obssr.od.nih.gov/research-resources/mixed-methods-research) | CAP-02、CAP-05 | 组合研究必须说明整合目的、设计、程序和整合点 | “同时收集两类数据”本身不构成 mixed methods |
| SRC-MM-02 | [Fetters、Curry、Creswell：混合方法整合原则](https://pubmed.ncbi.nlm.nih.gov/24279835/) | CAP-02、CAP-05 | 在设计、方法、解释和报告层整合；处理一致、互补和矛盾结果 | 不用一种方法自动覆盖另一种方法的反例 |
| SRC-QUAL-01 | [Braun 与 Clarke：Using thematic analysis in psychology](https://doi.org/10.1191/1478088706qp063oa) | CAP-05 | 熟悉资料、编码、主题形成、复核、命名和报告的分析链 | 反思式主题分析不等同于要求编码者一致性系数 |
| SRC-QUAL-02 | [Gale 等：Framework Method](https://doi.org/10.1186/1471-2288-13-117) | CAP-05 | 逐字稿、熟悉、编码、分析框架、索引、矩阵和解释；保留跨案例比较 | 需说明选择该方法的理由和研究者反思 |
| SRC-QUAL-03 | [EQUATOR：COREQ](https://www.equator-network.org/reporting-guidelines/coreq/) | CAP-04、CAP-06 | 作为访谈/焦点小组报告完整性提示 | 它是报告指南，不是质量合格证；不机械设置 32 个强制 Gate |
| SRC-STAT-01 | [American Statistical Association：p 值声明](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) | CAP-04、CAP-05、CAP-06 | p 值不等于效应大小或结论重要性；结论不能只依赖阈值 | V1 以描述分析为主，复杂推断应升级统计专家 |
| SRC-RPT-01 | [GOV.UK：Sharing user research findings](https://www.gov.uk/service-manual/user-research/sharing-user-research-findings) | CAP-06 | 面向决策分享；发现说明事实、重要性和证据 | 推荐页数不是固定输出约束 |
| SRC-RPT-02 | [GOV.UK：Analyse a research session](https://www.gov.uk/service-manual/user-research/analyse-a-research-session) | CAP-05、CAP-06 | 原始记录→观察→分组→发现→行动；尽早协作分析 | “发现”和本项目“洞察”仍按项目术语表分层 |
| SRC-PRIV-01 | [《中华人民共和国个人信息保护法》](https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html) | 全部能力 | 目的明确、直接相关、最小范围、公开透明和数据质量 | Agent 只能检查并提示，不作正式法律结论 |
| SRC-FIN-01 | [证监会：证券期货投资者适当性管理办法（2022 年修正）](https://neris.csrc.gov.cn/falvfagui/rdqsHeader/mainbody?navbarId=3&secFutrsLawId=b139ee3b6fea460a818840e0a982cb98) | CAP-01、CAP-03、CAP-04、CAP-06 | 研究标签不替代正式适当性；不得提供可能被理解为确定性的判断 | 研究工作流不执行风险匹配或产品销售 |
| SRC-FIN-02 | [证监会：公开募集证券投资基金销售机构监督管理办法](https://www.csrc.gov.cn/csrc/c106256/c1653806/content.shtml) | CAP-03、CAP-04、CAP-06 | 区分研究与基金宣传、销售；触及宣传或推荐时升级合规审核 | Agent 不批准宣传材料或产品推荐 |
| SRC-FIN-03 | [FCA：Consumer understanding](https://handbook.fca.org.uk/handbook/prin2a/prin2as5?timeline=true) | CAP-02、CAP-03、CAP-04 | 测试沟通是否让目标客户理解并作出知情决定；关注脆弱和低金融能力用户 | 作为理解度研究参考，不把英国监管要求冒充中国法 |
| SRC-AI-01 | [OpenAI：A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | CTRL-01、CAP-04 | 清晰工具与指令、结构化输出、分层护栏、高风险人工介入、渐进式多 Agent | 产品实现可替换模型或框架，能力契约保持中立 |
| SRC-AI-02 | [OpenAI Agents SDK：Handoffs](https://openai.github.io/openai-agents-python/handoffs/) | CTRL-01 | 专家交接应有明确目的、输入过滤和目标能力 | 不把聊天摘要作为正式 Artifact |
| SRC-AI-03 | [OpenAI Agents SDK：Tracing](https://openai.github.io/openai-agents-python/tracing/) | CTRL-01 | 记录运行、工具、交接、护栏和自定义事件 | 追踪中默认不写入非必要敏感数据 |
| SRC-AI-04 | [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | CTRL-01、CAP-04 | 范围、科学完整性、数据适用性、人类监督、测试和文档化 | 作为风险治理参考，不宣称正式符合性认证 |

## 3. 本地 Skill 采用记录

| source_id | Skill | 采用内容 | 明确不采用 |
|---|---|---|---|
| SKILL-01 | `skill-creator` | 能力卡主体简洁；详细方法按需加载；稳定校验交给脚本；正向、边界、对抗、回归测试 | 当前阶段不直接封装成可执行 Skill |
| SKILL-02 | `interview-research` | 开放中性提问、行为与态度分离、追问具体事件、反例和替代做法、原话可定位、听不清不猜测 | 固定访谈数量、固定发现数量、自动生成传播级结论 |
| SKILL-03 | `user-needs-research` | 需求层级、痛点、分层、决策链路、动机和行为作为可选分析镜头 | 六维框架不强制套用；不输出未经证据支持的市场规模、正式画像或客户标签 |

## 4. 关键拒绝项

以下做法已明确不写入能力卡：

- “每次访谈必须 5–8 人”或“每份报告必须 5–10 条洞察”。
- “定性和定量结果不一致时，以样本更多的一方为准”。
- “AI 质量审核通过即可替代合规、法务、隐私或业务审批”。
- “问卷点击 IMA 链接即可证明用户阅读、理解或有购买意愿”。
- “研究中形成的候选分群可直接写回 CRM 成为正式标签”。
- “统计显著即可证明业务重要、因果关系或总体代表性”。
- “报告为了简洁可以删除反例、局限、样本口径或未回答问题”。

## 5. 复核要求

- 每季度或相关法规、平台能力发生重大变化时复核一次来源状态。
- 法规页面仅用于能力边界设计；具体项目执行前由组织授权人员确认适用版本。
- 新增来源必须记录对应能力、采用规则、限制条件和复核日期。
