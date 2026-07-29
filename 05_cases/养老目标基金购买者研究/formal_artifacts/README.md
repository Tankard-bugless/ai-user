---
document_id: CASE-OTF-FORMAL-ARTIFACTS
version: 0.3.0
status: active
last_updated: 2026-07-28
---

# 正式追溯产物

本目录把已经完成的真实问卷执行、分析和最终展示报告登记为工作流标准产物：

- `fieldwork-package.v0.1.0.json`：执行、来源、脱敏、质量与偏差；
- `insight-package.v0.2.0.json`：在原证据链上补充样本画像与探索性分群；
- `research-report.v0.2.0.json`：最终版报告的语义登记与文件哈希；
- `review-result.report.v0.2.0.json`：CAP-04 轻量预审，不构成正式批准；
- `artifact-manifest.v0.2.0.json`：当前文件级完整性和治理状态；
- `data/`：脱敏标准化答卷、逐条质量状态和字段映射。
- `runtime/`：当前 Artifact Registry、不可覆盖状态快照、最小权限迁移任务、审计日志和历史登记摘要。

原始 CSV 含 IP、UA、地理位置等平台元数据，因此没有复制到本目录。执行包只登记其 SHA-256，并由 `build_formal_artifacts.py` 在指定原文件可用时复现派生数据。

0.1.0 版本继续保留为历史登记；0.2.0 是当前内容最完整的内部草稿。二者都不改变历史运行停在 Gate 2 的事实。

## 真实审批边界

本案例只有 Gate 1 正式记录。Gate 2、Gate 3、Gate 4 当时没有形成 ApprovalRecord，因此：

- 不补造历史批准；
- 三个核心产物均保持 `DRAFT`；
- Schema 使用 `gate_2_governance_gap` 或 `gate_3_governance_gap` 明确缺口；
- 当前用途限于内部复盘和答辩演示；
- 未来正式外发时，应针对当时的精确版本重新走当前审核流程。

控制层已按这条边界登记：唯一有效批准是 Gate 1，当前状态为 `GATE_2_REVIEW / WAITING_GATE`；FieldworkPackage、InsightPackage 和 ResearchReport 在 Registry 中为 `STALE`。这里的 stale 表示“不能推动当前治理流程”，不否认文件和当时分析实际存在。

## 复现

```powershell
python ..\build_formal_artifacts.py --source <原始CSV路径>
```

脚本会先核对原文件哈希和既有质量统计。若 200 份记录、字段映射、互斥修正、速度信号或正式复核信号与历史分析不一致，将停止生成。
