# SESSION A2 — Revenue Build-Up (conditional)
# Load this file at Step 7 of session startup for SESSION A2 only.
# Triggered only if REVENUE_BUILD: TRUE in _State (set by SESSION A Phase 2.5).

---

## Purpose

SESSION A2 builds the `Revenue_Build` tab — a dedicated sheet that derives segment
revenue from Volume × ASP (or pure YoY%) BEFORE the IS is written.

**The bargain (R12):** every IS forecast Revenue-by-segment cell becomes
`=Revenue_Build!<col><row>` instead of a direct Assumptions YoY ref. This separates
"how revenue is built" (Vol/ASP/seasonality/mix) from "what flows to IS" (segment totals).

Without this discipline, multi-driver revenue logic gets crammed into IS rows that
don't have room for it, OR a Revenue_Build tab is built but never wired in — sitting
as an orphan reconciliation table while IS pulls forecasts directly from Assumptions.
(Real-world example: a 10-sub-brand vol×ASP build-up was complete but IS!Auto forecast
directly referenced Raw_Info + seasonality, while Revenue_Build reversed-referenced IS for
reconciliation. The entire build-up was an orphan check table — the exact anti-pattern R12 prevents.)

---

## When SESSION A2 runs

`REVENUE_BUILD: TRUE` is set in _State by SESSION A's Phase 2.5 question. Default-on rules:

```
DEFAULT ON if any of:
  - ≥2 forecast revenue segments
  - Any segment has explicit Volume × ASP disclosure in Raw_Info
  - User explicitly opts in

DEFAULT OFF if all of:
  - Single revenue line (no segment breakout)
  - Pure YoY% forecast (no vol×price logic)
  - User opts out (e.g., quick screening model)
```

If `REVENUE_BUILD: FALSE` → SESSION A2 is **SKIPPED**, SESSION B builds IS revenue rows using
compound formula `=D5*(1+Assumptions!*YoY%)` directly (legacy behavior preserved for single-segment models).

---

## Architecture: Revenue_Build tab layout

**Critical: Revenue_Build COL_MAP should match IS COL_MAP** (same period columns in same order).
If retrofitting a model with mismatched columns, set `REV_BUILD_COL_MAP` in state.json separately.

### ██ INLINE ↳ PATTERN (mandatory) ██

**Forecast formulas reference SAME-SHEET rows only.** Every driver from Assumptions gets an
inline `↳` mirror row directly below the data row. The `↳` row is `=Assumptions!<col><row>` —
the SOLE cross-tab link. The forecast formula above references the same-sheet `↳` row.

```
Widget Volume Q          | hist: =Raw_Info!   | fcst: =prior_same_Q*(1+<same_sheet_↳_row>)
  ↳ Vol Q YoY %          | =Assumptions!<col><vol_yoy_row>     ← only cross-tab link
Widget ASP Q             | hist: =Raw_Info!   | fcst: =prior_same_Q*(1+<same_sheet_↳_row>)
  ↳ ASP Q YoY %          | =Assumptions!<col><asp_yoy_row>

Services Total           | hist: =Raw_Info!   | fcst: =<same_sheet_↳_guide> * <same_sheet_↳_share>
  ↳ FY Guide (m)         | =Assumptions!<FY_col><guide_row>    ← only cross-tab link
  ↳ Q Share % of FY      | =Assumptions!<Q_col><share_row>
```

Why: one-glance audit — all inputs visible on same sheet; Assumptions changes auto-propagate
through the `↳` mirror; formulas never cross 2+ tabs in one cell.

### Quarterly forecasting architecture

**Q-level forecast is the driver. FY = SUM(Q). Never forecast at FY then split to Q.**

| Segment type | Q forecast formula | FY formula |
|---|---|---|
| **Mature (Q YoY)** | `=same_Q_prior_yr * (1 + ↳_Q_YoY%)` | `=SUM(Q1:Q4)` |
| **New biz (guide + ramp)** | `=↳_FY_guide * ↳_Q_share%` | `=SUM(Q1:Q4)` |
| **New biz (QoQ)** | `=prior_Q * (1 + ↳_QoQ%)` | `=SUM(Q1:Q4)` |

- Q YoY: compares same season → seasonality is baked in (Q1'26 vs Q1'25)
- Guide + ramp: management FY target → quarterly ramp-up curve (typically back-loaded)
- FY = SUM(Q1:Q4) — FY is ALWAYS derived, never the driver
- After building: reconcile FY_model vs FY_guidance; adjust Q assumptions if delta > 5%

### Tab layout (quarterly, with ↳ rows)

```
Header rows (1-2):
  R1: Unit: m RMB
  R2: | | 1Q24 | 2Q24 | 3Q24 | 4Q24 | FY2024 | 1Q25 | ... | 1Q26E | ... | FY2026E |

WIDGET VOLUME ('000, Q YoY)
  Widget Volume Q         | hist Q: =Raw_Info!  | hist FY: =SUM(Q)  | fcst Q: =prior_yr_Q*(1+↳row below)  | fcst FY: =SUM(Q)
  ↳ Vol Q YoY %           | hist: implied =(curr/prior-1)  | fcst: =Assumptions!*  ← ONLY cross-tab link

WIDGET ASP (RMB '000, Q YoY)
  Widget ASP Q            | same pattern as Vol
  ↳ ASP Q YoY %           | =Assumptions!*

WIDGET REVENUE (Q = Vol × ASP)
  Widget Revenue Q        | all: =Vol_row * ASP_row  | FY: =SUM(Q)

SEGMENT TOTALS
  Widget Total            | =Widget Revenue Q (passthrough for IS reference)
  Services Total          | hist: =Raw_Info!  | fcst Q: =↳Guide * ↳Share  | FY: =SUM(Q)
    ↳ FY Guide (m)        | =Assumptions!<FY_col><guide_row>   ← Q-only row (FY has data, Q blank = structural)
    ↳ Q Share % of FY     | =Assumptions!<Q_col><share_row>    ← Q-only row (FY blank = structural)
  Grand Total Revenue     | =Widget_Total + Services_Total

RECONCILIATION
  FY Model (SUM Q)        | =Grand Total FY col
  Services FY Guide       | =↳Guide FY col
  Services Delta          | =Model FY - Guide FY    ← should be ~0 by construction
```

### Annual layout (simpler, same inline ↳ principle)

Same structure but columns are annual (FY2021, FY2022, ..., FY2026E).
No Q/FY distinction — all columns are "summary" type for QC-20/21 purposes.
Vol × ASP segments still use `↳ YoY %` inline mirrors.

---

## SESSION A2 Steps

```
Step 1: Run session startup protocol
        - verify GATE_A_PASSED present
        - verify REVENUE_BUILD: TRUE in _State (else: skip A2, jump to B)
Step 2: Read RAW_MAP, ASM_MAP, COL_MAP, REV_BUILD_SEGMENTS from _State
        - REV_BUILD_SEGMENTS: list of {name, type: "vol_price"|"yoy", sub_segments: [...]}
        - set by SESSION A Phase 2.5
Step 3: Create Revenue_Build tab. Apply IS column structure:
        - Read COL_MAP from _State (built by SESSION A)
        - Set header row 3 to match IS exactly (col letters + period labels)
        - Apply format (font, number format) per format-spec.md
Step 4: Build Volume rows + ↳ inline YoY mirrors — ONE code block
        - For each segment/sub-segment in REV_BUILD_SEGMENTS:
          - Data row: Historical Q = =Raw_Info!*, Historical FY = =SUM(Q)
          - Data row: Forecast Q = =prior_yr_same_Q * (1 + SAME_SHEET_↳_row)
          - Data row: Forecast FY = =SUM(forecast Q1:Q4)
          - ↳ row (directly below data row):
              Historical = implied =(curr/prior-1)
              Forecast = =Assumptions!<col><vol_yoy_row>  ← ONLY cross-tab link
        - End block: save; print "A2_DONE: Volume"
Step 5: Build ASP rows + ↳ inline YoY mirrors — ONE code block
        - Same pattern as Step 4 for ASP
        - Historical FY ASP = implied =FY_Rev/FY_Vol
        - End block: save; print "A2_DONE: ASP"
Step 6: Build Revenue rows (= Vol × ASP) — ONE code block
        - Q cells: =<same_sheet_vol_row> * <same_sheet_asp_row>
        - FY cells: =SUM(Q1:Q4)
        - No cross-tab references needed (Vol and ASP already on same sheet)
        - End block: save; print "A2_DONE: Rev"
Step 7: Build Section 4 (Segment Totals + Grand Total) — ONE code block
        - Total Seg A = =SUM(<rev_row_first>:<rev_row_last>)  for each segment
        - Grand Total = =SUM(<seg_total_first>:<seg_total_last>)
        - YoY% row = =<grand>/<prev_col_grand> - 1
        - End block: write_state_key(wb, "A2_PROGRESS", "Volume,ASP,Rev,Totals"); print "A2_DONE: Totals"
Step 8: Build Section 5 (Reconciliation, historical years only) — ONE code block
        - Source Rev = =Raw_Info!<total_rev_row>
        - Built Rev = =<Grand Total row>
        - Δ = Built - Source; Δ% = Δ/Source
        - Assert |Δ%| < 1% for every historical year (raise if not)
Step 9: Append Vol/ASP drivers to Assumptions tab (if not already there)
        - New section: "--- Revenue Build-Up Drivers (added in SESSION A2) ---"
        - Per sub-segment: "[Seg] Volume YoY %" row + "[Seg] ASP YoY %" row
        - Forecast cells: hardcoded driver inputs (these ARE the model inputs)
        - Historical cells: implied = (curr - prior) / prior (formula, dashed style)
Step 10: Re-read Assumptions tab → rebuild ASM_MAP → write back to _State
Step 11: Write REV_BUILD_MAP to _State as JSON:
         {
           "Segment A Total": <total_row>,         ← non-aggregate; QC-21 expects matching IS row
           "Segment B Total": <total_row>,
           ...
           "Grand Total": <grand_row>,             ← aggregate; QC-21 ignores
           "Reconciliation Delta %": <delta_pct_row>   ← aggregate; QC-21 ignores
         }

         QC-21 excludes aggregate-row keys via anchored regex match, so legitimate
         segment names that happen to start with "Total" (e.g., "Total Vehicles" as
         a NEV+ICE breakdown total used as a segment driver) are NOT excluded. The
         filter matches the following patterns (case-insensitive) as aggregates:
           - `Grand Total` (exact)
           - `Total Revenue` (exact)
           - any key starting with `Reconciliation` (e.g., "Reconciliation Delta %")
           - any key ending with `Delta` / `Δ` / `Delta %` (reconciliation deltas)
           - any key starting with `Check ...` or `Sum ...`

         For each NON-aggregate segment name, SESSION B must register the corresponding
         IS row in KEY_CELLS_IS["Revenue_segment_rows"]. Match is exact REV_BUILD_MAP key
         first, then key with trailing " Total" stripped (e.g., REV_BUILD_MAP
         `"Auto Total"` → Revenue_segment_rows `"Auto"`). Row values should be Python
         integers; numeric strings ("5") are auto-coerced via `int()` but integers
         are the documented and preferred type.
Step 12: Save. Update FILE_HASH. Run end-of-session gate.
```

---

## Trigger logic (called from SESSION A Phase 2.5)

Phase 2.5 in SESSION A runs this question via `AskUserQuestion`:

```
本模型是否需要单独建 Revenue_Build tab?
(用 Vol × ASP 或多 segment YoY% 驱动 forecast revenue, IS 强制链回 Revenue_Build)

□ A) 默认开（推荐） — ≥2 forecast segments 或任一 vol×price 披露
□ B) 关闭 — 单 segment 模型, 直接走 Assumptions YoY%

如果选 A, 再询问每个 segment 的驱动类型:
  - vol×price: 子品牌/产品线级别有 Volume + ASP 披露
  - yoy:       只有 segment 级 Revenue, 用 YoY% 驱动
```

写入 _State:
```
REVENUE_BUILD: TRUE / FALSE
REV_BUILD_SEGMENTS: [
  {"name": "Auto", "type": "vol_price", "sub_segments": ["Ocean", "Dynasty", ...]},
  {"name": "Handset", "type": "yoy", "sub_segments": []},
  ...
]
```

---

## Assumptions tab — append-only contract

SESSION A2 **adds** rows to Assumptions tab; never edits or deletes existing rows.

Format for new section (appended after SESSION A's core drivers):
```
R(last+2): "--- Revenue Build-Up Drivers (SESSION A2) ---"

For vol×price segments (quarterly):
  R(N):   [Sub1] Vol Q YoY %     | Q1 input | Q2 input | Q3 input | Q4 input
  R(N+1): [Sub1] ASP Q YoY %     | ...

For guide+ramp segments:
  R(M):   [Seg] FY Guide (m)     | FY col only (one number)
  R(M+1): [Seg] Q Share % of FY  | Q1% | Q2% | Q3% | Q4%   (must sum to 100%)

For QoQ segments (new business):
  R(K):   [Seg] QoQ %            | Q1 input | Q2 input | Q3 input | Q4 input
```

After append → rebuild ASM_MAP → write to _State.

**Revenue_Build `↳` rows reference these Assumptions rows directly.** Revenue_Build forecast
formulas then reference the `↳` rows on the same sheet — never Assumptions directly.

---

## Historical inline row fill rules (mandatory — fill every computable cell)

**Principle: if prior period data exists, compute the implied ratio. Only leave blank when there is genuinely no prior data (e.g., first year of a new segment, or FY column for a Q-only metric like QoQ%).**

| Inline row type | Historical Q cell | Historical FY cell |
|---|---|---|
| **Q YoY %** | `=IF(prior_yr_same_Q=0, 0, curr_Q/prior_yr_same_Q - 1)` — first year Q (no prior year) = blank | `=IF(prior_FY=0, 0, curr_FY/prior_FY - 1)` — first year FY = blank |
| **QoQ %** | `=IF(prior_Q=0, 0, curr_Q/prior_Q - 1)` — Q1 uses prior year Q4 as prior | N/A for FY → blank |
| **% of revenue** | `=data_row / Total_Rev_row` for same period | same |
| **FY Guide** | N/A for hist Q → blank | FY cell = actual reported revenue (for comparison) |
| **Q Share % of FY** | `=Q_actual / FY_actual` (shows actual seasonal pattern) | N/A → blank (or =1) |

**Formatting**: historical implied ratios use **black text** (not navy), no light-blue fill.
Forecast driver inputs use **navy text + light-blue fill** (Assumptions input convention).

**QC note**: QC-20 currently checks forecast cells only. Historical ↳ blank cells are not gate-blocked,
but the skill spec REQUIRES filling them for model completeness and analyst review. A human reviewer
will immediately notice empty cells where prior data exists — this is a quality signal, not just cosmetic.

---

## Common pitfalls

1. **COL_MAP mismatch**: Revenue_Build columns ≠ IS columns. Use `REV_BUILD_COL_MAP` in state if they differ.
2. **Reconciliation Δ%>1% historical**: built-up ≠ disclosed total. Check missing sub-segment / eliminations / caliber mismatch.
3. **Volume hardcoded in forecast**: forecast vol must be formula. Use `↳` inline row referencing Assumptions, never hardcode.
4. **ASP unit mismatch**: if ASP in '000 and Revenue in mn, Section 3 cells MUST divide by scale.
5. **Forgetting ASM_MAP update** after appending Vol/ASP drivers → next session spot-check fails.
6. **Building Revenue_Build AFTER IS**: defeats R12. SESSION A2 runs BEFORE SESSION B (gate enforced).
7. **Forecast formula references Assumptions directly** (bypasses ↳ row): violates inline ↳ pattern.
   Every forecast cell references same-sheet rows only. The `↳` row is the sole cross-tab link.
8. **↳ row has Q data but blank FY** (e.g., Q YoY% doesn't SUM to FY): this is structural.
   QC-20 correctly skips blank summary cells in Q-only rows (and vice versa).
9. **FY forecast = =Revenue_Build!FY** instead of **=SUM(Q1:Q4)**: in quarterly models, FY must
   always be SUM(Q). QC-21 accepts any formula in summary (FY/H1/H2) columns.
10. **Historical inline ↳ cells left blank when prior period exists**: e.g., FY2025 Vol YoY%
    computable but empty. Fill every cell where prior data exists (see "Historical inline row fill rules" above). Not gate-blocked, but a quality gap that human reviewers will notice immediately.

---

## END-OF-SESSION GATE (mandatory)

After Revenue_Build is complete:

```bash
python scripts/per_session_gate.py --session A2 --xlsx <model.xlsx>
```

QC subset:
- **QC-2** (no hardcode in forecast cells across the workbook; Revenue_Build forecast also scanned)
- **QC-20** (Revenue_Build integrity — every Section 1/2/3 forecast cell = formula string;
   Section 4 totals = SUM formula; Section 5 reconciliation Δ% < 1% historical)
- **ASM_MAP spot-check** on newly appended Vol/ASP rows
- **REV_BUILD_MAP** populated (BLOCKER if missing)

exit 2 blocks SESSION B; exit 0/1 writes `GATE_A2_PASSED` to _State.

---

## After A2 completes — handoff to SESSION B

SESSION B verify-prev logic:
```python
if state.get("REVENUE_BUILD") == "TRUE":
    require GATE_A2_PASSED
else:
    require GATE_A_PASSED
```

SESSION B reads `REV_BUILD_MAP` from _State. For every forecast Revenue-by-segment cell in IS:
```python
# WRONG (R12 violation, QC-21 BLOCKER):
ws_is[f"{fcst_col}5"].value = f"=D5*(1+Assumptions!{fcst_col}{asm_map['Auto YoY %']})"

# RIGHT:
ws_is[f"{fcst_col}5"].value = f"=Revenue_Build!{fcst_col}{rev_build_map['Auto Total']}"
```

Historical IS Revenue cells still `=Raw_Info!*` — unchanged.
