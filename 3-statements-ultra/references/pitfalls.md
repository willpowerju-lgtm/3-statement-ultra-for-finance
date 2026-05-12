# 3-Statements Pitfall Index

48 项 pitfall 的完整索引。每项标注 (a) 严重程度 (b) 防御层 (c) 触发 session (d) 修复入口。

参考：`gate-spec.md` 定义 severity 与防御层语义；`format-spec.md` 定义 QC-14..19 基准。

---

## BLOCKER (33 项，硬阻断，hook 或 gate 自动拦截)

### Rule Zero — 硬编码（最严重）

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P1 | IS/BS/CF forecast cell 写 float/int (`ws_is["E5"].value = 0.30`) | H1 + QC-2 | B/C/D | `f"=Assumptions!B{asm_map['X']}"` |
| P2 | 混用 bare ref 和 `=` 标准式 (`f"=D5*(1+=Assumptions!B2)"`) | H1 (Form 4) + QC-2 | B/C/D | 嵌入式去掉 inner `=` |
| P3 | IS/BS/CF historical cell 写 float/int | H1 + QC-2 | B | `f"=Raw_Info!C{raw_map['IS: Revenue']}"` |
| P4 | `float(rev * 0.3)` / `int(...)` / `abs(...)` wrapper hardcode | H1 (Pattern wrap) + QC-2 | B/C/D | 直接公式字符串 |

### 单位 / 颗粒度

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P5 | 单位错 (万元 vs 百万元，100× 静默错) | H3 + PF-1 + QC-14 | A | PRE-FLIGHT 锁定 UNIT 字段 |
| P6 | A 股 ticker 设 Annual/Semi-annual | H5 | A | `IS_GRANULARITY: Quarterly` |
| P7 | 美股 ticker 设 Annual/Semi-annual | H5 | A | `IS_GRANULARITY: Quarterly` |
| P8 | YTD 季度数据当独立 Q 用 (Sina IS/CF 是 YTD 累计) | PF-6 | A | Q2=H1−Q1, Q3=Q3_YTD−H1, Q4=FY−Q3_YTD |
| P9 | 颗粒度未确认就开始 Raw_Info | H3 | A | Phase 0 Step 0 锁 IS_GRANULARITY 后再写 |

### _State 一致性

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P10 | RAW_MAP 行号失配 (Raw_Info 被编辑后没更新 _State) | H2 + PF-7 + QC-6 | B/C/D/E | 重建 RAW_MAP |
| P11 | ASM_MAP 行号失配 | H2 + PF-7 + QC-6 | B/C/D/E | 重建 ASM_MAP |
| P12 | FILE_HASH 不匹配 (xlsx 外部编辑后) | Session startup Step 4 | 全 | 重新 hash + 用户确认 |
| P13 | SKILL_VERSION 不匹配 (升级了 skill 但 _State 未刷) | Session startup Step 5 | 全 | 重建 _State |
| P14 | PHASE_DONE 缺失（前一 session 没完成）| Session startup Step 6 | 全 | 补跑前一 session |
| P15 | 用 RAW_MAP 行号但 Raw_Info 已变 | H2 + QC-6 | B/C/D | 跑 Step 9 spot-check |
| P16 | 跨 session 用硬编码行号（没从 _State 读 map）| H2 (间接) | B/C/D | 用 `raw_map[label]` 而非数字 |

### CF / BS 平衡

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P17 | R3 Others 在 CFI/CFF 完成前写 | QC-1 间接 | D | 在 per-year loop 末尾才写 Others |
| P18 | BS Cash 没按年回填（批量末尾才填）| QC-4 | D | 每年 CF 完后立即回填 BS Cash |
| P19 | 自由 plug 强平 BS (`= TLE − NCA − CA_excl`) | QC-1 | C/D | 仅允许 R3 Others 和 R8 CN GAAP plug |
| P20 | CF CHECK 全部年份后才写 | QC-4 间接 | D | 每年 loop 内写 CF CHECK |
| P21 | CF 重复计 interest/tax (forecast 已含在 NI 内) | QC-1 | D | forecast 不要单独 CFO 行 |
| P22 | 建 CF 前 BS 没完成 | QC-7 (BS_DONE 标记) | D | 先确认 BS_DONE 才进入 D |
| P23 | PP&E 用 total D&A 滚动（应该用 PPE 专门折旧率）| QC-1 间接 | C | `PPE_curr = PPE_prior × (1 − PPE_depr_rate) + Capex` |
| P24 | NCI=0 in forecasts (hist NCI ≠ 0) | PF-8 + QC-5 | B/C | Roll forward NCI: `Attr_to_NCI = NI × NCI_Ratio` |

### Raw_Info / 数据源

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P25 | Raw_Info 大面积留空 | PF-4 | A | 95% 非空率才放行 |
| P26 | DATA_SOURCES 没在 _State 登记 | PF-3 | A | 至少 1 个 (NLM/EXCEL/WEB) |
| P27 | yfinance forwardEps 用于 A 股/港股 (USD-distortion) | H4 (eps_yfinance_guard) | 全 | ak-xq-router consensus_fetcher.py |
| P28 | Raw_Info 完成后 re-read 源 PDF/web | Doc-only (R1) | B+ | 都走 `=Raw_Info!` |

### QC / 验证

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| P29 | 跳过 QC Suite | QC-7 (_State 完整性) | E | `per_session_gate.py --session E` |
| P30 | Summary cell 写 float/int | QC-9 | E | 链回模型 cell |
| P31 | A1 不是 `Unit: m XXX` 模式 | QC-14 | A/B/C/D | `ws["A1"] = "Unit: m RMB"` |
| P32 | Σ(segments) ≠ Total Revenue 全期 | QC-11 | B/E | 每个 segment 用独立 source 数据 |
| P33 | _pending_links.json SESSION C 没写 → SESSION D 无法 batch back-fill | per_session_gate (gate-C) | C | SESSION C 末尾写 deferred refs |

---

## WARNING (9 项，软警告，sidecar 报告)

| # | Pitfall | Defense | Session | Fix |
|---|---|---|---|---|
| W1 | \|Others/CFO\| > 15% (但 < 30%) | QC-3 | D | 找缺失的 CF 行明确建模 |
| W2 | WC days vs 3yr avg 偏离 > 30% | QC-10 | E | 复查 Assumptions tab |
| W3 | Effective tax rate 偏离假设 > 5pct | QC-12 | B/E | 校准 Tax Rate 假设 |
| W4 | R3 Others 历史年为 0 当 plug 用 | QC-13 | D | 历史用 Raw_Info 实际值 |
| W5 | 字体非 Book Antiqua/等线（覆盖率 < 90%）| QC-15 | B/C/D/E | 重设字体 |
| W6 | Input cell 颜色非 FF0070C0 蓝 | QC-16 | A | Assumptions 输入用蓝 |
| W7 | 数字 cell number_format 不达 70% accounting | QC-17 | B/C/D/E | 用 `_ * #,##0_ ;_ * \-#,##0_ ;_ * "-"??_ ;_ @_ ` |
| W8 | Zoom 不在 [60, 90] | QC-18 | E | `ws.sheet_view.zoomScale = 70` |
| W9 | 无冻结窗格 | QC-19 | E | `ws.freeze_panes = 'B3'` |
| W10 | NLM_0B_DONE 未确认 (操作 KPI 缺失) | PF-5 | A | NLM 问 0B 问题后标 TRUE |
| W11 | YTD_CONVERTED 未标 (Quarterly + Sina) | PF-6 | A | Q1=YTD_Q1, Q2=H1−Q1... 然后标 TRUE |
| W12 | Gridlines 未关 | QC-8 | 任意 | `ws.sheet_view.showGridLines = False` |
| W13 | HK ticker 设 Annual (罕见但可能合法) | H5 | A | preflight 多源验证 |

---

## Doc-only (6 项，不进 gate，Claude 写代码时遵循)

- **Code block ≤ 350 行** — `CODE GENERATION PROTOCOL` (SKILL.md L89-118)
- **`_model_log.md` 写入完整性** — 每个 tab section 完成后 append
- **`_pending_links.json` SESSION C 写入** — gate-C 间接检查写入；内容质量靠 Doc
- **Format 细节**: navy/black 配色规则、light blue bg on inputs、Book Antiqua 10/11pt
- **Number 显示规则** (SKILL.md §6G): <100 → 2dp · 100+ → integer w/ comma · % → 1dp
- **Note 注释完整性**: 每个 Assumptions 行有 source / rationale / H-M-L flag

---

## 总览

| 类别 | 数量 | 防御层分布 |
|---|---|---|
| BLOCKER | 33 | Hook: 8 (P1-P9, P15-P16, P27)；Gate: 25 |
| WARNING | 13 | Gate: 13 |
| Doc-only | 6 | 不进 gate |
| **合计** | **52** | hook 占 15%，gate 占 73%，doc 占 12% |

H1/H4 hook 命中率最高的 4 项是 Rule Zero 系列 (P1-P4)，单这 4 项就占历史故障 ≥40%。
