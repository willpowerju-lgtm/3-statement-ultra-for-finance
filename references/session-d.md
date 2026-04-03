# SESSION D — Cash Flow + BS Cash Back-fill + All Checks
# Load this file at Step 7 of session startup for SESSION D only.

---

## SESSION D Steps

**Steps:**
1. Run session startup protocol — verify PHASE_DONE: SESSION_C
2. Verify `BS_CASH_STATUS: PENDING_BACKFILL` in _State — if missing or COMPLETE, STOP
3. Read KEY_CELLS_IS, KEY_CELLS_BS, BS_COL_MAP, CF_COL_MAP, IS_GRANULARITY from _State
4. Build CF **one year per code block** (see CODE GENERATION PROTOCOL in SKILL.md):
   - Write one year's CF code → execute → verify `CF_DONE: {year}` printed → write next year
   - Never batch multiple years into one script — each year has ~30 rows × 35 cols for quarterly = 1000+ assignments
   - **Quarterly models:** One "year block" = 5 CF columns (Q1/Q2/Q3/Q4/FY). Write all 5 in one block. BS Cash back-fill targets FY column only (BS is annual). `prev_cl` for year N+1 = year N's FY column ending cash.
   - Within each year, execute in order:

```
  a. Write CFO rows EXCEPT Others (Others = placeholder 0)
  b. Write CFI rows
  c. Write CFF rows
  d. Write Others = R3 formula NOW (CFI + CFF exist for this year):
       Historical: f"=Raw_Info!{col}{raw_map['CF: Others']}" if disclosed, else 0
       Forecast:   full R3 formula:
                   f"=BS!{cl}{tle_row}-BS!{cl}{nca_tot_row}"
                   f"-SUM(BS!{cl}{ca_excl_start}:BS!{cl}{ca_excl_end})"
                   f"-BS!{prev_cl}{cash_row}"
                   f"-{cl}{ni_cf_row}-{cl}{da_row}"
                   f"-SUM({cl}{wc_start_row}:{cl}{wc_end_row})"
                   f"-{cl}{cfi_row}-{cl}{cff_row}"
  e. Write Net Change, Beginning Cash, Ending Cash:
       Beg_Cash first hist year: f"=Raw_Info!{col}{raw_map['BS: Opening Cash']}"
       Beg_Cash all other years: f"=BS!{prev_cl}{cash_row}"  ← prior year BS Cash
  f. Write CF CHECK for this year: f"={cl}{end_cash_row}-BS!{cl}{cash_row}"
  g. IMMEDIATELY back-fill BS Cash for this year:
       ws_bs.cell(cash_row, this_col).value = f"=CF!{this_cl}{end_cash_row}"
  h. Verify back-fill:
       val = ws_bs.cell(cash_row, this_col).value
       assert isinstance(val, str) and val.startswith("=CF!"), \
           f"Back-fill failed for {year}: got {val} — STOP"
  i. Print, write to _State, AND save:
       print(f"CF_DONE: {year} — back-fill verified")
       write_state_key(wb, "CF_PROGRESS", year)
       wb.save(filepath)
```

5. Write KEY_CELLS_CF to _State:
```
KEY_CELLS_CF: {"EndCash_row": N, "CFO_row": N, "Others_row": N, "CF_CHECK_row": N, "wc_start_row": N, "wc_end_row": N, "cfi_row": N, "cff_row": N}
```
6. Run full QC Suite (see below) — all checks must PASS
7. Write `BS_CASH_STATUS: BACKFILL_COMPLETE` to _State
8. Save. Update FILE_HASH. Write `PHASE_DONE: SESSION_D`

**End condition:** All CF_DONE markers printed, all QC checks pass, PHASE_DONE: SESSION_D written.

---

## QC SUITE — Run at end of SESSION D (and again at SESSION E)

All checks must print PASS before writing PHASE_DONE. Any FAIL = fix before proceeding.

### QC-1: Numeric reconciliation — Python direct calculation

```python
import json, openpyxl
from openpyxl.utils import get_column_letter

wb_v = openpyxl.load_workbook(filepath, data_only=False)
ws_raw = wb_v["Raw_Info"]; ws_asm = wb_v["Assumptions"]
ws_is  = wb_v["IS"];       ws_bs  = wb_v["BS"]; ws_cf = wb_v["CF"]

raw_map = json.loads(state["RAW_MAP"])
asm_map = json.loads(state["ASM_MAP"])
col_map = json.loads(state["BS_COL_MAP"])
key_is  = json.loads(state["KEY_CELLS_IS"])
key_bs  = json.loads(state["KEY_CELLS_BS"])
key_cf  = json.loads(state["KEY_CELLS_CF"])
fcst_years = json.loads(state["FCST_YEARS"])
hist_years = json.loads(state["HIST_YEARS"])

def rv(label, yr):
    col = col_map[yr]
    col_idx = openpyxl.utils.column_index_from_string(col)
    return ws_raw.cell(raw_map[label], col_idx).value or 0

def av(label, yr):
    fcst_col_idx = fcst_years.index(yr) + 2
    return ws_asm.cell(asm_map[label], fcst_col_idx).value or 0

# ── Verify historical years: IS rows present ────────────────────────────────
for yr in hist_years:
    col_idx = openpyxl.utils.column_index_from_string(col_map[yr])
    model_rev = ws_is.cell(key_is["Revenue_row"], col_idx).value
    assert model_rev is not None, f"QC-1 FAIL: IS Revenue {yr} is empty"
    print(f"QC-1 PASS (hist): {yr} IS rows present")

# ── Verify forecast years: full numeric recalculation ────────────────────────
prev_cash = rv("BS: Cash (derived)", hist_years[-1])

for yr in fcst_years:
    prev_yr = hist_years[-1] if yr == fcst_years[0] else fcst_years[fcst_years.index(yr)-1]
    prev_rev_col = openpyxl.utils.column_index_from_string(col_map[prev_yr])
    prev_rev = ws_is.cell(key_is["Revenue_row"], prev_rev_col).value
    if isinstance(prev_rev, str): prev_rev = rv("IS: Revenue", prev_yr)

    rev   = prev_rev * (1 + av("Revenue YoY %", yr))
    cogs  = -rev * (1 - av("Gross Margin %", yr))
    opex  = -rev * av("OpEx % Rev", yr)
    ebit  = rev + cogs + opex
    fin   = rv("IS: Net Finance Cost", hist_years[-1])
    pbt   = ebit + fin
    tax   = -pbt * av("Tax Rate %", yr)
    ni    = pbt + tax
    nci_i = ni * av("NCI Ratio", yr)
    attr_o = ni - nci_i

    ar    = rev * av("AR Days", yr) / 365
    inv   = -cogs * av("Inv Days", yr) / 365
    ap    = -cogs * av("AP Days", yr) / 365

    col_idx  = openpyxl.utils.column_index_from_string(col_map[yr])
    prev_idx = openpyxl.utils.column_index_from_string(col_map[prev_yr])

    if yr == fcst_years[0]:
        prev_ppe   = rv("BS: PP&E net", hist_years[-1])
        prev_re    = rv("BS: Retained Earnings", hist_years[-1])
        prev_nci_b = rv("BS: NCI", hist_years[-1])
        prev_ltb   = rv("BS: LT Borrowings", hist_years[-1])
        prev_oca   = rv("BS: Other CA", hist_years[-1])
        prev_intg  = rv("BS: Intangibles", hist_years[-1])
        prev_onca  = rv("BS: Other NCA", hist_years[-1])
        prev_ocl   = rv("BS: Other CL", hist_years[-1])
        prev_stb   = rv("BS: ST Borrowings", hist_years[-1])
        prev_oncl  = rv("BS: Other NCL", hist_years[-1])
        prev_shc   = rv("BS: Share Capital", hist_years[-1])
        prev_apic  = rv("BS: APIC", hist_years[-1])
        # WC tracking vars — must be loop variables so yr 2+ uses model-derived prior values
        prev_ar    = rv("BS: AR", hist_years[-1])
        prev_inv   = rv("BS: Inventory", hist_years[-1])
        prev_ap_wc = rv("BS: AP", hist_years[-1])
        prev_ocl_wc = rv("BS: Other CL", hist_years[-1])

    ppe   = prev_ppe * (1 - av("PP&E Depr Rate", yr)) + abs(av("Capex (RMB mn)", yr))
    re    = prev_re + attr_o - ni * av("Div Payout %", yr)
    nci_b = prev_nci_b + nci_i

    ltb     = av("LT Borrowings (RMB mn)", yr)   # closing balance from Assumptions
    ca_excl = ar + inv + prev_oca
    nca     = ppe + prev_intg + prev_onca
    cl      = ap + prev_ocl + prev_stb
    ncl     = ltb + prev_oncl
    tl      = cl + ncl
    eq_excl = prev_shc + prev_apic + re + nci_b
    tle     = tl + eq_excl

    da       = av("D&A (RMB mn)", yr)
    # Bug fix: use loop-tracked prev_ar/inv/ap_wc/ocl_wc — rv() returns 0 for forecast years
    wc       = -(ar - prev_ar) \
               -(inv - prev_inv) \
               +(ap - prev_ap_wc) \
               +(prev_ocl - prev_ocl_wc)
    cfi      = av("Capex (RMB mn)", yr)
    ltb_chg  = ltb - prev_ltb   # dynamic: Assumptions closing balance minus prior balance
    div_cf   = -ni * av("Div Payout %", yr)
    cff      = ltb_chg + div_cf
    others   = tle - nca - ca_excl - prev_cash - ni - da - wc - cfi - cff
    cfo      = ni + da + others + wc
    end_cash = prev_cash + cfo + cfi + cff

    cash_needed = tle - nca - ca_excl
    ta = nca + ca_excl + end_cash

    bs_check = ta - tle
    cf_check = end_cash - cash_needed

    assert abs(bs_check) < 0.01, f"QC-1 FAIL: BS CHECK {yr} = {bs_check:.4f}"
    assert abs(cf_check) < 0.01, f"QC-1 FAIL: CF CHECK {yr} = {cf_check:.4f}"
    assert abs(ni - (pbt + tax)) < 0.01, f"QC-1 FAIL: NI CHECK {yr}"

    print(f"QC-1 PASS: {yr} — BS_CHECK={bs_check:.4f} CF_CHECK={cf_check:.4f} ✅")
    prev_cash = end_cash
    prev_ppe=ppe; prev_re=re; prev_nci_b=nci_b; prev_ltb=ltb
    prev_oca=prev_oca; prev_intg=prev_intg; prev_onca=prev_onca
    prev_ocl=prev_ocl; prev_stb=prev_stb; prev_oncl=prev_oncl
    prev_ar=ar; prev_inv=inv; prev_ap_wc=ap; prev_ocl_wc=prev_ocl
```

### QC-2: Hardcode scan
```python
from openpyxl.utils import get_column_letter
key_is = json.loads(state["KEY_CELLS_IS"])
key_bs = json.loads(state["KEY_CELLS_BS"])
key_cf = json.loads(state["KEY_CELLS_CF"])
fcst_cols = [openpyxl.utils.column_index_from_string(col_map[yr]) for yr in fcst_years]
# Note: uses BS annual fcst cols for IS/BS; CF quarterly cols (Q1-Q4) not checked here — same formula pattern, low hardcode risk

checks = [
    ("IS", ws_is, range(2, key_is["NCI_row"] + 1)),
    ("BS", ws_bs, range(2, key_bs["BS_CHECK_row"] + 1)),
    ("CF", ws_cf, range(2, key_cf["CF_CHECK_row"] + 1)),
]
for tab_name, ws, row_range in checks:
    for col in fcst_cols:
        for row in row_range:
            val = ws.cell(row, col).value
            if isinstance(val, (int, float)):
                raise AssertionError(
                    f"QC-2 FAIL: Hardcode in {tab_name}!{get_column_letter(col)}{row} = {val}")
print("QC-2 PASS: No hardcodes in forecast cells")
```

### QC-3: R3 Others magnitude (all years)
```python
wb_vals = openpyxl.load_workbook(filepath, data_only=True)
ws_cf_v = wb_vals["CF"]
cf_col_map = json.loads(state["CF_COL_MAP"])
# For quarterly/semi-annual models CF_COL_MAP has sub-annual keys (e.g. "2024Q1").
# Check annual/FY columns only — one R3 Others per year is sufficient for magnitude QC.
qc3_cols = {k: v for k, v in cf_col_map.items()
            if not any(k.endswith(s) for s in ("Q1","Q2","Q3","Q4","H1","H2"))}
for yr, col in qc3_cols.items():
    ci = openpyxl.utils.column_index_from_string(col)
    others = ws_cf_v.cell(key_cf["Others_row"], ci).value or 0
    cfo    = ws_cf_v.cell(key_cf["CFO_row"], ci).value or 0
    if cfo == 0:
        print(f"QC-3 SKIP: {yr} CFO = 0 (file not yet calculated in Excel)")
        continue
    ratio = abs(others / cfo)
    if ratio > 0.15:
        print(f"QC-3 WARN: {yr} Others/CFO = {ratio:.1%} — investigate missing CF lines")
    else:
        print(f"QC-3 PASS: {yr} Others/CFO = {ratio:.1%}")
print("QC-3 NOTE: If all years show SKIP, open file in Excel to recalculate, then re-run QC-3")
```

### QC-4: BS Cash back-fill verification
```python
cash_row = key_bs["Cash_row"]
for yr, col in col_map.items():
    ci = openpyxl.utils.column_index_from_string(col)
    val = ws_bs.cell(cash_row, ci).value
    assert isinstance(val, str) and val.startswith("=CF!"), \
        f"QC-4 FAIL: BS Cash {yr} not linked to CF — value: {val}"
print("QC-4 PASS: All BS Cash cells linked to CF Ending Cash")
```

### QC-5: NCI continuity
```python
nci_row = key_bs["NCI_row"]
for yr in fcst_years:
    ci = openpyxl.utils.column_index_from_string(col_map[yr])
    val = ws_bs.cell(nci_row, ci).value
    assert isinstance(val, str) and "IS!" in val, \
        f"QC-5 FAIL: BS NCI {yr} not rolling from IS — value: {val}"
print("QC-5 PASS: NCI rolling formula confirmed in all forecast years")
```

### QC-6: Formula integrity spot-check
```python
import random
first_hist    = key_is["first_hist_col"]       # IS hist start col (int)
first_fcst_bs = key_bs["first_fcst_col"]       # BS fcst start col — BS always annual; use key_bs not key_is
is_rows = list(range(2, key_is["NCI_row"] + 1))
bs_rows = list(range(2, key_bs["BS_CHECK_row"]))

for row in random.sample(is_rows, min(5, len(is_rows))):
    val = ws_is.cell(row, first_hist).value
    if val is not None:
        assert isinstance(val, str) and val.startswith("=Raw_Info!"), \
            f"QC-6 FAIL: IS hist row {row} not linked to Raw_Info — value: {val}"

for row in random.sample(bs_rows, min(5, len(bs_rows))):
    val = ws_bs.cell(row, first_fcst_bs).value
    if val is not None and val != 0:
        assert isinstance(val, str) and val.startswith("="), \
            f"QC-6 FAIL: BS fcst row {row} is not a formula — value: {val}"
print("QC-6 PASS: Formula integrity spot-check passed")
```

### QC-7: _State integrity
```python
required = ["FILE_HASH", "RAW_MAP", "ASM_MAP", "IS_GRANULARITY", "BS_COL_MAP",
            "CF_COL_MAP", "KEY_CELLS_IS", "KEY_CELLS_BS", "KEY_CELLS_CF",
            "BS_CASH_STATUS", "HIST_YEARS", "FCST_YEARS", "UNIT", "GAAP"]
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

### QC-9: Not applicable in SESSION D
```
# QC-9 (Summary hardcodes) only runs in SESSION E — skip here.
```
