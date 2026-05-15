# SESSION B — Income Statement
# Load this file at Step 7 of session startup for SESSION B only.

---

## SESSION B Steps

**Steps:**
1. Run session startup protocol — verify previous gate
   - If `REVENUE_BUILD: TRUE` in _State → require GATE_A2_PASSED (Revenue_Build must exist)
   - If `REVENUE_BUILD: FALSE` → require GATE_A_PASSED
2. Read IS_GRANULARITY, CF_COL_MAP, RAW_MAP, ASM_MAP, **REV_BUILD_MAP** (if exists) from _State
3. Build IS tab **one section per code block** (see CODE GENERATION PROTOCOL in SKILL.md):
   - Write one code block → execute → verify print marker → write next block
   - Historical columns: every non-header cell = `f"=Raw_Info!{col}{raw_map[label]}"`
   - **Forecast Revenue-by-segment rows** (R12 enforcement):
     - **If REVENUE_BUILD=TRUE**: `f"=Revenue_Build!{col}{rev_build_map['<Segment> Total']}"` — **mandatory**
     - **If REVENUE_BUILD=FALSE**: `f"={prev_col}{row}*(1+Assumptions!{col}{asm_map['<Segment> YoY %']})"`
     - QC-21 will BLOCKER if forecast Revenue cell bypasses Revenue_Build when it should not
   - Forecast non-Revenue columns: every cell = string formula referencing Assumptions, no hardcodes
   - Historical Others (CN GAAP R8): `=Raw_Info!` ref if disclosed; else derive plug from source 营业利润
   - Forecast Others (CN GAAP R8): compound formula using Assumptions driver
   - Suggested splits: **Revenue rows** | **COGS + GP** | **OpEx** | **EBIT + below** | **NCI + checks**
4. End each code block with: save → write_state_key → print marker. Then execute before continuing:
```python
# End of each block (example for Revenue section):
write_state_key(wb, "IS_PROGRESS", "Revenue")
wb.save(filepath)
print("IS_DONE: Revenue")   # ← must appear in output before writing next block

# Sections and their IS_PROGRESS values:
# Revenue   → "Revenue"
# GP        → "Revenue,GP"
# EBIT      → "Revenue,GP,EBIT"
# NI        → "Revenue,GP,EBIT,NI"
# NCI+check → "Revenue,GP,EBIT,NI,NCI"
```
5. Write KEY_CELLS_IS to _State:
```
KEY_CELLS_IS: {
  "Revenue_row": N, "NI_row": N, "AttrOwners_row": N, "AttrNCI_row": N,
  "EBIT_row": N, "COGS_row": N, "first_hist_col": 2, "first_fcst_col": 5,
  "Revenue_segment_rows": {            ← REQUIRED when REVENUE_BUILD=TRUE
    "Auto": 5, "Handset": 6, "Battery": 7   ← {segment_name: is_row_number}
  }
}
```

**`Revenue_segment_rows` contract (R12, when REVENUE_BUILD=TRUE):**
- Every non-aggregate REV_BUILD_MAP segment (i.e., not "Grand Total" / "Reconciliation Δ %" / similar) must appear as a key here
- Segment names should match REV_BUILD_MAP keys, OR the version with trailing " Total" stripped (e.g., REV_BUILD_MAP key `"Auto Total"` → Revenue_segment_rows key `"Auto"` is accepted)
- Row numbers should be Python integers (Excel row numbers). Numeric strings ("5") are auto-coerced by QC-21 via `int()` but integers are preferred.
- QC-21 reads this mapping to verify each segment's forecast cells reference Revenue_Build
- If missing or empty when REVENUE_BUILD=TRUE → QC-21 BLOCKER
- QC-21 aggregate filter is anchored regex (NOT prefix-match): a segment named "Total Vehicles" or "Total Auto" is treated as a non-aggregate segment and MUST be registered in Revenue_segment_rows. See session-a2.md §REV_BUILD_MAP for the exact aggregate patterns.
6. Save. Update FILE_HASH. Write `PHASE_DONE: SESSION_B`

**End condition:** All IS_DONE markers printed. IS NI / Attr_Owners / Attr_NCI cells have formulas.

---

# Phase 2 — Income Statement Templates

## Quarterly Layout (50 columns)

```
Per year: Q1 | Q2 | Q3 | Q4 | FY  →  5 cols × 10 years = 50 data cols + label + note
is_c(year, quarter) = IS_FC + year × 5 + quarter   (quarter: 0=Q1..4=FY)
FY = Q1 + Q2 + Q3 + Q4 for all P&L lines
```

BS/CF remain annual (10 cols), referencing IS FY columns. Historical quarterly: after YTD conversion. Forecast quarterly: FY × seasonality %.

## IFRS / US GAAP IS Template

```
REVENUE BY SEGMENT                                                      Note
  [Segment A]
    Revenue                                                             Raw_Info: rev history; mgmt guidance
    ↳ YoY Growth % [input]                                             CAGR X%; target +X%; TAM CAGR X%
    ↳ % of Total Revenue                                               Trend: [growing/stable/declining]
    (If vol × price:)
      Volume · ↳ Vol YoY % [input]                                     Capacity, utilization, expansion
      ASP · ↳ ASP YoY % [input]                                        Pricing power, competition
  [Segment B]  (same structure)
  [Other Revenue]
Total Revenue | YoY%
REV CHECK = Model − Source  ← GREEN/RED

Cost of Sales · Gross Profit · ↳ GM % [input]

OPEX: Selling ↳ %Rev · Admin ↳ %Rev · R&D ↳ %Rev · [Other]
Total OpEx · EBIT | Margin%

Finance Income/(Costs) · JV · Impairment
PBT · Tax ↳ ETR% · NI | Margin%
  Attr Owners · Attr NCI ↳ NCI% · Check: Own+NCI−NI=0
NI CHECK = Model − Source ← GREEN/RED

MEMO: D&A (PP&E/ROU/Intangibles/Total) · SBC
```

## Chinese GAAP IS Template (中国会计准则)

```
营业总收入 REVENUE                                                       Note
  [Seg A — e.g., 数字维修]
    Revenue                                                             §0A: history; §0B: guidance
    ↳ YoY Growth % [input]                                             CAGR; target; TAM
    ↳ % of Total Revenue                                               占比趋势
    ↳ Quarterly Seasonality % [Q1/Q2/Q3/Q4]                            3yr avg pattern
    (If vol × price:)
      Volume · ↳ Vol YoY %                                             Capacity, product launch
      ASP · ↳ ASP YoY %                                                Pricing, mix shift
  [Seg B — e.g., 数字能源]  (same structure)
  [其他业务]
  Total Revenue | YoY%
  REV CHECK

营业成本 COGS · 毛利润 GP · ↳ GM%

营业税金及附加 · ↳ %Rev

期间费用 OPEX:
  销售费用 ↳ %Rev · 管理费用 ↳ %Rev · 研发费用 ↳ %Rev · 财务费用 ↳ Rate×Debt
Total OpEx

资产减值损失 (often "--"; use 0; real value in CF supplementary)

其他收益等 Other Op Inc ← R8 PLUG
  Hist: = Source 营业利润 − (Rev−COGS−Tax−OpEx−Impairment)
  Fcst: ↳ %Rev or absolute [input]                                     Plug composition; govt grants recurrence

营业利润 EBIT | Margin%

营业外收支 · 利润总额 PBT · 所得税 ↳ ETR% · 净利润 NI
  归母 · 少数 ↳ NCI% · Check
  NI CHECK

MEMO: D&A (固定资产折旧/无形资产摊销/长期待摊摊销/Total) · SBC
```

## Revenue Segment Rules

1. **Separate data per segment** — never share one revenue array across segment rows (causes 2× double-count)
2. **Proration when only annual segment data**: `Q_seg = Q_total × (FY_seg / FY_total)`
3. **Verify**: REV CHECK = Σ(segments) − Source = 0 every period
4. **Forecast source (R12)**:
   - If `REVENUE_BUILD=TRUE`:
     - **Q forecast cells**: `=Revenue_Build!<Q_col><total_row>` — strict R12, QC-21 enforced
     - **FY forecast cells**: `=SUM(IS Q1:Q4)` — FY is derived from Q, not from Revenue_Build directly. QC-21 accepts any formula in summary (FY/H1/H2) columns.
     - **Do NOT** write `=D5*(1+Assumptions!*YoY%)` for Q forecast Revenue — QC-21 blocks.
   - If `REVENUE_BUILD=FALSE`: each segment has its own YoY% in Assumptions; forecast = `=prior * (1+Assumptions!<yoy_row>)`. (Legacy single-segment / quick-screen path.)

**R12 quarterly reference flow:**
```
Assumptions (Q YoY% / FY guide / Q share%)
  ↓ (via ↳ inline rows in Revenue_Build — sole cross-tab link)
Revenue_Build Q cells (=prior_Q * (1+↳row) or =↳guide * ↳share)
  ↓ (via =Revenue_Build!<Q_col><total_row> in IS)
IS Q forecast Revenue cells
  ↓ (=SUM(Q1:Q4))
IS FY forecast Revenue
  ↓
IS Total Revenue → downstream COGS/GP (also use inline ↳ pattern)
```

## Inline ↳ Row Rules (mandatory)

**IS forecast formulas reference SAME-SHEET rows only.** Every Assumptions driver gets an
inline `↳` mirror row. The `↳` row = `=Assumptions!<col><row>` — sole cross-tab link.

```
COGS                     | hist: =Raw_Info!   | fcst Q: =-Rev*(1-<same_sheet_↳_GM%>)  | FY: =SUM(Q)
  ↳ GM %                 | hist: =GP/Rev (implied) | fcst: =Assumptions!<col><gm_row>  ← only cross-tab

SGA                      | hist: =Raw_Info!   | fcst Q: =-Rev*<same_sheet_↳_SGA%>     | FY: =SUM(Q)
  ↳ SGA % rev            | =Assumptions!<col><sga_row>

R&D                      | same pattern
  ↳ R&D % rev            | =Assumptions!*

Tax                      | fcst Q: =-PBT*<same_sheet_↳_ETR>
  ↳ ETR %                | =Assumptions!*

NCI                      | fcst Q: =NI*<same_sheet_↳_NCI_ratio>
  ↳ NCI ratio            | =Assumptions!*
```

- `↳` prefix, indent, light blue bg `#D6E4F0`, navy text, italic
- **Historical `↳` cells**: black formula, implied ratio from actual data. **Fill every cell where prior period exists** (e.g., `=GP/Rev` for GM%, `=-SGA/Rev` for SGA%). First period with no prior → blank. FY = FY implied ratio (not SUM of Q ratios).
- **Forecast `↳` cells**: navy text, light blue bg, `=Assumptions!<col><row>` — sole cross-tab link.
- Note column (rightmost): every `↳` row gets a note explaining the driver

### Note Examples:

**Revenue:** `Mgmt guided +15% FY25; hist CAGR 14.2%; TAM 22% (Frost p.87); +2 new markets`
**Rev Seg B:** `New segment, +53% YoY; policy tailwind 补贴 expires FY27; capacity +50% by FY26`
**Volume:** `1.2M units FY24; 1.5M nameplate, 80% util; new line +0.5M by H2 FY26`
**ASP:** `$185 FY24, stable; mix shift premium +5-8%; competitive pressure low-end`
**Seasonality:** `3yr avg Q1 18%/Q2 24%/Q3 26%/Q4 32%; Q4 heavy year-end procurement`
**Seg % of Rev:** `FY21 2.2% → FY24 22.1%; expect 30%+ by FY28; watch cannibalization`
**GM%:** `29.2% FY24; RM ~92% COGS; stable-to-improving on mix upgrade`
**SG&A %:** `8.1% FY24; normalizing post headcount investment per mgmt p.134`
**R&D %:** `12.3% FY24; committed >10% long-term; capitalization rate X%`
**ETR%:** `5.9% FY24 HNTE preferential; expires [year]; normalizing to 15%`
**Other Op Inc:** `R8 plug — avg 2.1% rev; mainly 其他收益 (govt grants ~60k recurring) + 信用减值`
---

## END-OF-SESSION GATE (mandatory)

After IS is complete:

```bash
python scripts/per_session_gate.py --session B --xlsx <model.xlsx>
```

QC subset: QC-2 (hardcode), QC-5 (NCI), QC-6 (formula integrity), QC-11 (segment sum),
QC-12 (tax rate), QC-14 (A1 unit), QC-15 (font), QC-17 (number format), **QC-21 (IS→Revenue_Build link, if REVENUE_BUILD=TRUE)**.

exit 2 blocks SESSION C; exit 0/1 writes GATE_B_PASSED.
