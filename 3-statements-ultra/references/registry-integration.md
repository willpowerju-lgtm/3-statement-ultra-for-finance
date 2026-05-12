# R11 Data Registry — Integration with data-validator

> 原 SKILL.md R11 段已迁移至此。SESSION E QC Suite 通过后强制执行。

## R11 — Data Registry (_Registry sheet, SESSION E 完成后执行)

**三表模型完成、QC Suite全部通过后，必须在同一 Excel 文件内建 `_Registry` sheet。**
这是强制步骤，不可跳过。

### 哪些行进 _Registry

| 数据类型 | 分类 | derived | 处理方式 |
|---|---|---|---|
| Raw_Info 从原始报告提取的历史值（Revenue、COGS、NI 等） | 原始数据 | FALSE | 登记 tier/source/timestamp |
| Assumptions tab 的输入参数（YoY%、Margin%、AR Days 等） | 原始数据 | FALSE | tier 按来源判断（analyst=T4，consensus=T3，自研=T4） |
| IS/BS/CF 中由公式算出的行（GP、EBIT、FCF、Net Debt 等） | 派生数据 | TRUE | 登记 formula + inputs |

### IS/BS/CF 派生行规则（与 Rule Zero 配套）

三表所有非输入行已经是 Excel 公式（Rule Zero 保证）。在 `_Registry` 对应登记：
- `formula` = 该行第一个 forecast 期的 Excel 公式字符串（代表整行逻辑）
- `inputs` = 驱动该行的 Assumptions 或 Raw_Info `data_point_id`，逗号分隔
- `tier` = 自动继承 inputs 最低 tier（script 自动算，不手动填）

重点派生行必须登记（不可省略）：

```
gross_profit, ebit, ebitda, net_income, adj_eps
cfo_total, cfi_total, cff_total, fcf
net_debt, ev, roic, roe
```

### 登记方式

SESSION E QC Suite 通过后，新增一个代码块：

```python
# 批量登记 _Registry（SESSION E 最后一步）
import subprocess, json

raw_inputs = [
    # (id, value_cell, tier, source, timestamp, data_category)
    ("revenue_fy2023a", "=Raw_Info!C15", "T1", "Annual Report 2023 p.48", "2023-12-31", "revenue"),
    ("rev_yoy_fy2025e", "=Assumptions!B3", "T4", "analyst internal estimate", "2026-04-01", "consensus_estimate"),
    # ... 所有 Raw_Info 和 Assumptions 行
]

derived_rows = [
    # (id, formula, inputs_list)
    ("gross_profit_fy2025e", "=IS!E8-IS!E9", ["revenue_fy2025e", "cogs_fy2025e"]),
    ("ebit_fy2025e",         "=IS!E15",      ["gross_profit_fy2025e", "opex_fy2025e"]),
    ("fcf_fy2025e",          "=CF!E42-CF!E28", ["cfo_fy2025e", "capex_fy2025e"]),
    # ... 所有派生行
]

json_path = f"{ticker}_3statements_data_registry.json"
xlsx_path = filepath  # same Excel file

for row in raw_inputs:
    subprocess.run(["python3", "data-validator/scripts/registry_update.py",
        "--json", json_path, "--xlsx", xlsx_path,
        "--id", row[0], "--value", row[1],
        "--tier", row[2], "--source", row[3], "--timestamp", row[4],
        "--data-category", row[5]])

for row in derived_rows:
    subprocess.run(["python3", "data-validator/scripts/registry_update.py",
        "--json", json_path, "--xlsx", xlsx_path,
        "--id", row[0], "--derived", "TRUE",
        "--formula", row[1], "--inputs", ",".join(row[2])])
```

### Validation Gate（_Registry 写完后强制执行）

```bash
python3 data-validator/scripts/validate.py \
  --json {ticker}_3statements_data_registry.json --mode full
```

- `❌ FAIL` → **硬性阻断**，MODEL_COMPLETE 不得写入 _State
- `⚠️ RECALC` → 视同 ❌ 处理，重算后重跑 validate
- `🟡 WARN` → 记录在 _model_log.md，不阻断
- 全部清零后，写入 `_State: REGISTRY_VALIDATED: TRUE`，再写 `PHASE_DONE: MODEL_COMPLETE`

**写入顺序（SESSION E 末尾）：**
```
QC Suite (9 checks pass) → _Registry 登记 → validate.py gate → REGISTRY_VALIDATED: TRUE → MODEL_COMPLETE
```

