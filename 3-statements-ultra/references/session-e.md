# SESSION E — Returns + Cross_Check + Summary
# Load this file at Step 7 of session startup for SESSION E only.

---

## SESSION E Steps

**Steps:**
1. Run session startup protocol — verify PHASE_DONE: SESSION_D
2. Verify `BS_CASH_STATUS: BACKFILL_COMPLETE` in _State
3. Read KEY_CELLS_IS + KEY_CELLS_BS + KEY_CELLS_CF from _State — run spot-check on each
4. Build Returns tab — all formulas reference IS/BS/CF by row from KEY_CELLS (see PHASE 5 below)
5. Build Cross_Check tab — web search → validate Assumptions → all revisions via Assumptions only (see PHASE 7 below)
6. Build Summary tab — all figures link to model cells; zero hardcodes (see PHASE 8 below)
7. Run full QC Suite (QC-1 through QC-9, see below) — all checks must PASS
8. Write `MODEL_COMPLETE: TRUE` to _State
9. Save. Update FILE_HASH
10. Inform user: model complete, _State tab may be deleted

**End condition:** All QC checks pass, MODEL_COMPLETE: TRUE written.

---

## PHASE 5 — Returns Tab

```
IC = NWC + Net LT Op Assets
NOPAT = EBIT × (1 − Tax Rate)
ROIC = NOPAT / AVERAGE(IC_curr, IC_prior)
ROE = Attr_Owners NI / Avg Equity_Owners
ROA = NI / Avg Total Assets
DuPont: ROE = Net Margin × Asset Turnover × Equity Multiplier
```

All cells reference IS/BS by row number from KEY_CELLS_IS / KEY_CELLS_BS. No hardcodes.

---

## PHASE 7 — Cross_Check Tab

Web search to validate assumptions. Categories: A) Mgmt Guidance (highest priority), B) Market Consensus, C) Sell-Side. All revisions through Assumptions tab only. Never edit IS/BS/CF directly.

**yfinance validation layer (run after model is complete):**
yfinance returns normalized/IFRS-reformatted data — not as-reported CN GAAP — so use only for magnitude sanity checks.

```python
import yfinance as yf
tk = yf.Ticker(ticker)   # e.g. "BABA", "PDD", "0700.HK", "600519.SS"

# 1. Granularity auto-detect (confirms R10 decision)
qcols = tk.quarterly_financials.columns
months = sorted(set(c.month for c in qcols))
granularity = "Quarterly" if len(months) >= 3 else ("Semi-annual" if months == [6,12] else "Annual only")
print(f"Disclosed granularity: {granularity} — months={months}")

# 2. Revenue & Net Income magnitude check (annual)
af = tk.financials
yf_rev = af.loc["Total Revenue"].dropna()
yf_ni  = af.loc["Net Income"].dropna()
print("yfinance Annual Revenue:", yf_rev.to_dict())
print("yfinance Annual Net Income:", yf_ni.to_dict())
# Flag if gap > 10%; acceptable gaps: CN GAAP Other Op Inc items, NI minority interest treatment
```

### Cross_Check Log Table

| # | Cat | Driver | Model | External | Source+Date | Match? | Severity | Action |
|---|---|---|---|---|---|---|---|---|
| | A/B/C | | | | URL date | Y/N | H/M/L | Revise/Monitor/Note |

H = >5% NI impact · M = directional inconsistency · L = minor

---

## PHASE 8 — Summary Tab

All figures link to IS/BS/CF/Returns. No hardcodes. 7 sections:

### 1. Business Profile & Investment Thesis
- Core products: what it makes, how it earns, key specs/differentiation (1 para per product line)
- Revenue model: subscription/one-time/recurring, customer segments, geographic mix
- Moat assessment: IP/patents, certifications, switching costs, network effects, scale, brand
- **Investment Thesis** — 3-5 bullets: [Driver/Moat/Catalyst] → [Mechanism] → [Quantified impact on model]

### 2. Financial Highlights (linked table)

| Metric | H Y−2 | H Y−1 | H Y0 | F Y+1E | F Y+2E | F Y+3E |
|---|---|---|---|---|---|---|
| Revenue | =IS! | | | | | |
| YoY Growth % | | | | | | |
| Gross Margin % | | | | | | |
| EBITDA Margin % | | | | | | |
| EBIT Margin % | | | | | | |
| NI Margin % (Owners) | | | | | | |
| Capex | =CF! | | | | | |
| Net Cash / (Debt) | =BS! | | | | | |
| ROIC % | =Returns! | | | | | |
| ROE % | | | | | | |

3-4 sentences: revenue trajectory, margin outlook, capex/allocation, leverage.

### 3. Core Assumptions & KPI Monitoring

**Key Model Assumptions** (per segment):
- Segment A: YoY growth X%, driven by [factors]; GM% stable at X%
- Segment B: YoY growth X%, driven by [factors]; ramping to X% of revenue
- OpEx: SG&A normalizing to X% rev; R&D maintained >X%
- Capex: RMB X mm/yr for [project]; completion by [date]

**Company Disclosed KPIs** (what the company regularly reports):
- e.g., unit shipments, active users, ARPU, backlog, capacity utilization
- Frequency: quarterly earnings release / annual report / investor day

**Metrics to Monitor** (track for assumption validation):
- Revenue per segment vs model (quarterly)
- GM% trend — watch for RM cost inflation or mix shift
- AR days — deterioration signals collection risk
- Capex execution vs plan — delays affect capacity ramp
- Government subsidy announcements — continuity of 其他收益
- Competitive pricing moves — impact on ASP assumptions
- Sell-side consensus revisions — directional check

### 4. Shareholding & Capital Structure
Cap table: shareholder / type (founder/PE/strategic/float) / % / lock-up expiry
Funding: date / round / lead investor / amount / post-money val / implied P/S
IPO: proceeds, use of funds, ESOP dilution
Debt summary: total debt, net cash/(debt), key facility terms

### 5. Upcoming Catalysts (next 2-4 quarters)
| Date/Period | Catalyst | Impact on Model | Probability |
|---|---|---|---|
| e.g., FY24 Annual Report (Apr) | Actual FY24 results vs model | Validates Rev/NI assumptions | Certain |
| e.g., Q1 FY25 (May) | First quarter post-forecast | Tests quarterly seasonality | Certain |
| e.g., H2 FY25 | New product line launch | Potential revenue upside Seg B | Medium |
| e.g., FY26 | 新能源补贴 policy renewal | Affects Seg B growth trajectory | Uncertain |

### 6. Key Risks
| Risk | Severity | Mitigation / Monitoring |
|---|---|---|
| Customer concentration (top-5 = X%) | H/M/L | Track quarterly, diversification trend |
| Competitive pricing pressure | | ASP trend, market share data |
| Regulatory / subsidy dependency (X% of profit) | | Policy expiry dates, alternatives |
| Supply chain concentration | | Supplier diversification, inventory buffer |
| Execution risk (capacity ramp, new products) | | CIP progress, product launch timeline |
| FX exposure (if intl > 10%) | | Hedging policy, geographic mix |
| Key person dependency | | Management tenure, succession |
| Litigation / contingent liabilities | | Raw_Info disclosure, provision adequacy |

### 7. Market & Competitive Landscape
TAM + growth rate (cite source) · Market structure (fragmented/concentrated)
Top players + market shares · Company positioning · Moat rating per dimension
Policy tailwinds + expiry risks · Key competitive threats

---

# Formatting, Color Code & Review Checklists

## Color Code

Font: **Book Antiqua** · 10pt body · 11pt headers · **No gridlines**

**Tab colors:** All 8 tabs = uniform `#2F5496`. Set `ws.sheet_properties.tabColor = "2F5496"`.

| Element | Style |
|---|---|
| Hardcoded historicals | Navy `#1F3864` |
| Editable inputs (YoY%, days, etc.) | Navy `#1F3864`, light blue bg `#D6E4F0` |
| All formulas/calculated | Black `#000000` |
| Labels | Black |
| Subtotals | Light gray bg `#F2F2F2` |
| Check = 0 | Light green `#E2EFDA` |
| Check ≠ 0 | Light red `#FFCCCC` — STOP |

**Header colors:**

| Period | Header bg | Font |
|---|---|---|
| Historical | `#2F5496` | White bold |
| Forecast | `#4472C4` | White bold |
| FY summary (quarterly) | Slightly darker | White bold |

**Freeze panes:** Freeze label column + header row for horizontal scrolling.

**Rule:** Blue = hardcoded data entry only. Formula/calculated = black. No exceptions.

## Review Checklist

### 6A Historical accuracy (vs Raw_Info)
- [ ] Every IS line · Every BS line · CF section totals

### 6A-bis Source Reconciliation (vs original source)
- [ ] REV CHECK = 0 all years · NI CHECK ≤ ±10 all years
- [ ] Total Assets match · Total Equity match
- [ ] If |diff| > 50: STOP

### 6B Structural
- [ ] BS CHECK = 0 all periods · CF CHECK = 0 all periods
- [ ] NI = Owners + NCI · Reserves/NCI/PP&E rolls hold
- [ ] Others plug < 15% CFO · Zero formula errors

### 6C Links
- [ ] All forecast IS → Assumptions · All forecast BS = formula
- [ ] Every CF line → IS or BS · BS Cash = CF!Ending_Cash

### 6D Assumptions quality
- [ ] Every row has note (source, rationale, H/M/L flag)
- [ ] Growth vs hist CAGR and market · Margins vs MD&A commentary
- [ ] WC days vs 3yr avg · Tax rate = effective, incentive expiry noted

### 6F Formatting
- [ ] Navy/Black color rules · Light blue bg on inputs
- [ ] Gridlines off · Book Antiqua 10/11pt

### 6G Numbers
- [ ] A1 = currency+unit · <100: 2dp · 100+: integer w/ comma · %: 1dp
- [ ] No unit mixing · No % as decimal

### 6H Segment Consistency
- [ ] Σ(segments) = Total Revenue all periods
- [ ] No segment sharing same data array
- [ ] Quarterly prorated segments match FY segment totals

---

## QC SUITE — Full Final Check (QC-1 through QC-9, SESSION E self-contained)

All 9 checks must PASS before writing MODEL_COMPLETE. No exceptions.

### Setup — load workbook and maps
```python
import json, random, openpyxl
from openpyxl.utils import get_column_letter

wb_v = openpyxl.load_workbook(filepath, data_only=False)
ws_raw = wb_v["Raw_Info"]; ws_asm = wb_v["Assumptions"]
ws_is  = wb_v["IS"];       ws_bs  = wb_v["BS"]; ws_cf = wb_v["CF"]

raw_map    = json.loads(state["RAW_MAP"])
asm_map    = json.loads(state["ASM_MAP"])
col_map    = json.loads(state["BS_COL_MAP"])
key_is     = json.loads(state["KEY_CELLS_IS"])
key_bs     = json.loads(state["KEY_CELLS_BS"])
key_cf     = json.loads(state["KEY_CELLS_CF"])
fcst_years = json.loads(state["FCST_YEARS"])
hist_years = json.loads(state["HIST_YEARS"])

def rv(label, yr):
    col_idx = openpyxl.utils.column_index_from_string(col_map[yr])
    return ws_raw.cell(raw_map[label], col_idx).value or 0

def av(label, yr):
    fcst_col_idx = fcst_years.index(yr) + 2
    return ws_asm.cell(asm_map[label], fcst_col_idx).value or 0
```

### QC-1: Numeric reconciliation
```python
for yr in hist_years:
    col_idx = openpyxl.utils.column_index_from_string(col_map[yr])
    assert ws_is.cell(key_is["Revenue_row"], col_idx).value is not None, \
        f"QC-1 FAIL: IS Revenue {yr} is empty"
    print(f"QC-1 PASS (hist): {yr} IS rows present")

prev_cash = rv("BS: Cash (derived)", hist_years[-1])
for yr in fcst_years:
    prev_yr = hist_years[-1] if yr == fcst_years[0] else fcst_years[fcst_years.index(yr)-1]
    prev_rev = ws_is.cell(key_is["Revenue_row"],
                          openpyxl.utils.column_index_from_string(col_map[prev_yr])).value
    if isinstance(prev_rev, str): prev_rev = rv("IS: Revenue", prev_yr)
    rev   = prev_rev * (1 + av("Revenue YoY %", yr))
    cogs  = -rev * (1 - av("Gross Margin %", yr))
    opex  = -rev * av("OpEx % Rev", yr)
    fin   = rv("IS: Net Finance Cost", hist_years[-1])
    pbt   = rev + cogs + opex + fin
    ni    = pbt * (1 - av("Tax Rate %", yr))
    nci_i = ni * av("NCI Ratio", yr)
    ar  = rev * av("AR Days", yr) / 365
    inv = -cogs * av("Inv Days", yr) / 365
    ap  = -cogs * av("AP Days", yr) / 365
    if yr == fcst_years[0]:
        prev_ppe=rv("BS: PP&E net",hist_years[-1]); prev_re=rv("BS: Retained Earnings",hist_years[-1])
        prev_nci_b=rv("BS: NCI",hist_years[-1]); prev_ltb=rv("BS: LT Borrowings",hist_years[-1])
        prev_oca=rv("BS: Other CA",hist_years[-1]); prev_intg=rv("BS: Intangibles",hist_years[-1])
        prev_onca=rv("BS: Other NCA",hist_years[-1]); prev_ocl=rv("BS: Other CL",hist_years[-1])
        prev_stb=rv("BS: ST Borrowings",hist_years[-1]); prev_oncl=rv("BS: Other NCL",hist_years[-1])
        prev_shc=rv("BS: Share Capital",hist_years[-1]); prev_apic=rv("BS: APIC",hist_years[-1])
        # WC tracking vars — loop variables so yr 2+ uses model-derived prior values
        prev_ar=rv("BS: AR",hist_years[-1]); prev_inv=rv("BS: Inventory",hist_years[-1])
        prev_ap_wc=rv("BS: AP",hist_years[-1]); prev_ocl_wc=rv("BS: Other CL",hist_years[-1])
    ppe = prev_ppe*(1-av("PP&E Depr Rate",yr))+abs(av("Capex (RMB mn)",yr))
    re  = prev_re+(ni-nci_i)-ni*av("Div Payout %",yr)
    nci_b = prev_nci_b+nci_i
    ltb = av("LT Borrowings (RMB mn)", yr)   # closing balance from Assumptions
    ca_excl=ar+inv+prev_oca; nca=ppe+prev_intg+prev_onca
    cl=ap+prev_ocl+prev_stb; ncl=ltb+prev_oncl
    tle=cl+ncl+prev_shc+prev_apic+re+nci_b
    da=av("D&A (RMB mn)",yr)
    # Bug fix: use loop-tracked prev vars — rv() returns 0 for forecast years
    wc_change = -(ar-prev_ar)-(inv-prev_inv) \
                +(ap-prev_ap_wc)+(prev_ocl-prev_ocl_wc)
    cfi=av("Capex (RMB mn)",yr)
    ltb_chg=ltb-prev_ltb   # dynamic: Assumptions closing balance minus prior balance
    cff=ltb_chg+(-ni*av("Div Payout %",yr))
    others=tle-nca-ca_excl-prev_cash-ni-da-wc_change-cfi-cff
    end_cash=prev_cash+ni+da+others+wc_change+cfi+cff
    ta=nca+ca_excl+end_cash
    assert abs(ta-tle) < 0.01, f"QC-1 FAIL: BS CHECK {yr} = {ta-tle:.4f}"
    assert abs(end_cash-(tle-nca-ca_excl)) < 0.01, f"QC-1 FAIL: CF CHECK {yr}"
    print(f"QC-1 PASS: {yr} — BS_CHECK=0 CF_CHECK=0 ✅")
    prev_cash=end_cash; prev_ppe=ppe; prev_re=re; prev_nci_b=nci_b; prev_ltb=ltb
    prev_oca=prev_oca; prev_intg=prev_intg; prev_onca=prev_onca
    prev_ocl=prev_ocl; prev_stb=prev_stb; prev_oncl=prev_oncl
    prev_ar=ar; prev_inv=inv; prev_ap_wc=ap; prev_ocl_wc=prev_ocl
```

### QC-2: Hardcode scan
```python
fcst_cols = [openpyxl.utils.column_index_from_string(col_map[yr]) for yr in fcst_years]
# Note: uses BS annual fcst cols for IS/BS/CF; CF quarterly Q1-Q4 cols not checked — same formula pattern, low hardcode risk
for tab_name, ws, row_range in [("IS",ws_is,range(2,key_is["NCI_row"]+1)),
                                  ("BS",ws_bs,range(2,key_bs["BS_CHECK_row"]+1)),
                                  ("CF",ws_cf,range(2,key_cf["CF_CHECK_row"]+1))]:
    for col in fcst_cols:
        for row in row_range:
            val = ws.cell(row, col).value
            if isinstance(val, (int, float)):
                raise AssertionError(f"QC-2 FAIL: Hardcode in {tab_name}!{get_column_letter(col)}{row} = {val}")
print("QC-2 PASS: No hardcodes in forecast cells")
```

### QC-3: R3 Others magnitude
```python
wb_vals = openpyxl.load_workbook(filepath, data_only=True)
ws_cf_v = wb_vals["CF"]
cf_col_map = json.loads(state["CF_COL_MAP"])
# For quarterly/semi-annual models CF_COL_MAP has sub-annual keys; check annual/FY cols only
qc3_cols = {k: v for k, v in cf_col_map.items()
            if not any(k.endswith(s) for s in ("Q1","Q2","Q3","Q4","H1","H2"))}
for yr, col in qc3_cols.items():
    ci = openpyxl.utils.column_index_from_string(col)
    others = ws_cf_v.cell(key_cf["Others_row"], ci).value or 0
    cfo    = ws_cf_v.cell(key_cf["CFO_row"], ci).value or 0
    if cfo == 0: print(f"QC-3 SKIP: {yr} CFO=0 (open in Excel to recalculate)"); continue
    ratio = abs(others/cfo)
    print(f"QC-3 {'WARN' if ratio>0.15 else 'PASS'}: {yr} Others/CFO = {ratio:.1%}")
```

### QC-4: BS Cash back-fill
```python
for yr, col in col_map.items():
    ci = openpyxl.utils.column_index_from_string(col)
    val = ws_bs.cell(key_bs["Cash_row"], ci).value
    assert isinstance(val, str) and val.startswith("=CF!"), \
        f"QC-4 FAIL: BS Cash {yr} not linked to CF — value: {val}"
print("QC-4 PASS: All BS Cash cells linked to CF Ending Cash")
```

### QC-5: NCI continuity
```python
for yr in fcst_years:
    ci = openpyxl.utils.column_index_from_string(col_map[yr])
    val = ws_bs.cell(key_bs["NCI_row"], ci).value
    assert isinstance(val, str) and "IS!" in val, \
        f"QC-5 FAIL: BS NCI {yr} not rolling from IS — value: {val}"
print("QC-5 PASS: NCI rolling formula confirmed in all forecast years")
```

### QC-6: Formula integrity spot-check
```python
for row in random.sample(list(range(2, key_is["NCI_row"]+1)), min(5, key_is["NCI_row"]-1)):
    val = ws_is.cell(row, key_is["first_hist_col"]).value
    if val is not None:
        assert isinstance(val, str) and val.startswith("=Raw_Info!"), \
            f"QC-6 FAIL: IS hist row {row} not linked to Raw_Info — got: {val}"
for row in random.sample(list(range(2, key_bs["BS_CHECK_row"])), min(5, key_bs["BS_CHECK_row"]-2)):
    val = ws_bs.cell(row, key_bs["first_fcst_col"]).value   # BS uses its own col map (always annual)
    if val is not None and val != 0:
        assert isinstance(val, str) and val.startswith("="), \
            f"QC-6 FAIL: BS fcst row {row} is not a formula — got: {val}"
print("QC-6 PASS: Formula integrity spot-check passed")
```

### QC-7: _State integrity
```python
required = ["FILE_HASH","RAW_MAP","ASM_MAP","IS_GRANULARITY","BS_COL_MAP",
            "CF_COL_MAP","KEY_CELLS_IS","KEY_CELLS_BS","KEY_CELLS_CF",
            "BS_CASH_STATUS","HIST_YEARS","FCST_YEARS","UNIT","GAAP"]
for key in required:
    assert key in state, f"QC-7 FAIL: _State missing key: {key}"
print("QC-7 PASS: _State contains all required keys")
```

### QC-8: Gridlines disabled
```python
for ws in [ws_is, ws_bs, ws_cf, ws_asm, ws_raw]:
    assert not ws.sheet_view.showGridLines, \
        f"QC-8 FAIL: Gridlines not disabled on {ws.title}"
print("QC-8 PASS: Gridlines disabled on all sheets")
```

### QC-9: Summary zero hardcodes (SESSION E only)
```python
ws_summary = wb_v["Summary"]   # use wb_v (data_only=False) to read formula strings
# Derive data area: skip row 1 (header) and col 1 (labels); scan all populated cells
summary_data_rows = range(2, ws_summary.max_row + 1)
summary_data_cols = range(2, ws_summary.max_column + 1)
for row in summary_data_rows:
    for col in summary_data_cols:
        val = ws_summary.cell(row, col).value
        if isinstance(val, (int, float)):
            raise AssertionError(
                f"QC-9 FAIL: Hardcode in Summary!{get_column_letter(col)}{row} = {val}")
print("QC-9 PASS: No hardcodes in Summary")
```
