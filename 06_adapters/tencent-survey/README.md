---
document_id: ADAPTER-TENCENT-SURVEY
version: 0.4.0
status: draft
last_updated: 2026-07-24
---

# 腾讯问卷适配器

本目录负责把已经完成研究设计和 Gate 2 审核的参与者版问卷转换为腾讯问卷 DSL，并记录平台问卷 ID、平台题目 ID 和内部变量 ID 的映射。

## 责任边界

- 研究问题、题目、选项、计分和分析口径仍以 `InstrumentSpec` 为权威来源。
- 当前案例已有完整 `InstrumentSpec 0.2.0`。Word 与 InstrumentSpec 由同一构建脚本生成；`compile_questionnaire.py` 只读取 Word 的参与者端内容，检测到“内部配置附录”后立即停止。
- 腾讯问卷只承担智能发行、答卷回收和 Excel 导出，不成为客户信息库，也不决定数据分析口径。
- 本项目不把 `list_answers` 作为必要依赖；业务方回传的 Excel 按 [Excel 答卷回传适配器](../excel-response/README.md) 进入 FieldworkPackage。
- 导入时只保留回答内容和必要时间字段；昵称、头像、OpenID、IP、精确地区、User-Agent 等平台元数据必须在分析前删除或隔离。

## 创建流程

1. 编译参与者版 DSL，并生成源文件哈希和人工检查清单。
2. 调用 `create_survey` 一次，记录 `survey_id` 和 `hash`，防止重复创建。
3. 调用 `get_survey` 复核题目、题型、必答状态和选项。
4. 使用平台返回的真实题目/选项 ID 配置 C0 退出、S1 未购买退出与 Q22 跳转逻辑。
5. 运行 `validate_deployment.py`，逐题比对标题、题型、必答、选项、逻辑和隐私设置。
6. 发布前人工确认多选上限和互斥选项。

## 当前限制

- `create_survey` 非幂等，失败重试前必须先检查部署记录。
- `update_logic` 整体覆盖原逻辑，更新前必须读取并合并已有 DSL。
- 当前接口不能可靠设置多选上限、互斥选项以及全部隐私设置，因此这些仍是 Gate 2 后的平台检查项。

## 当前部署

| 案例 | 部署记录 | 在线问卷 | 状态 |
|---|---|---|---|
| 养老目标基金购买者研究 v0.2（FOMO 团队） | [FOMO Deployment Record](case-otf-questionnaire.v0.2.0.fomo.deployment.json) | [腾讯问卷](https://wj.qq.com/s2/27394126/fb35) | COLLECTING（据项目发起人确认）；三条自定义跳转未启用 |
| 养老目标基金购买者研究 v0.2 | [Deployment Record](case-otf-questionnaire.v0.2.0.deployment.json) | [腾讯问卷](https://wj.qq.com/s2/27390837/c5d8) | TEST_VALIDATED；待人工确认多选设置和 Gate 2 |
| 养老目标基金购买者研究 v0.1 | [历史 Deployment Record](case-otf-questionnaire.v0.1.0.deployment.json) | [历史腾讯问卷](https://wj.qq.com/s2/27388585/6e69) | 历史测试版，不原地更新 |

v0.2 线上结构已经与 Word 逐题比对：10 页、35 道可作答题、213 个选择项，三条跳转逻辑均无语法错误。登录验证和定位采集关闭。Q9A 使用有序单选实现五点评分，以保留“记不清”独立值。

FOMO 团队部署沿用相同 V0.2 正文，结构检查结果同为 10 页、35 道可作答题和 213 个选择项。该团队调用 `update_logic` 时返回 `paid_function_trial_no_permission`，因此 C0 退出、S1 退出和 Q22 跳至 Q24 尚未启用。项目发起人已确认问卷发出；回传 Excel 时必须依据 C0、S1 和 Q22 的答案重建纳入条件与结构性缺失，并在 FieldworkPackage 中记录这项执行偏差。该处理不改变原问卷题目和预定义分析口径。
