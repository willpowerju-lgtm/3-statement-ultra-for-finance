# SESSION C — Balance Sheet
# Load this file at Step 7 of session startup for SESSION C only.

---

## SESSION C Steps

**Steps:**
1. Run session startup protocol — verify PHASE_DONE: SESSION_B
2. Read RAW_MAP, ASM_MAP, KEY_CELLS_IS, BS_COL_MAP from _State
3. Build BS tab **one section per code block** (see CODE GENERATION PROTOCOL in SKILL.md):
   - Write one code block → execute → verify print marker → write next block
   - Never batch multiple BS sections into one script — BS has 90+ rows, easily hits 32k token cap
   - Cash row = 0 placeholder in every block that touches it; NCI must roll from IS — never 0
   - End each block with save → write_state_key → print marker:
```python
# Section blocks and their markers (one execution per block):
# Block 1 — Current Assets:
write_state_key(wb, "BS_PROGRESS", "CA");                    wb.save(filepath); print("BS_DONE: Current Assets")
# Block 2 — Non-Current Assets:
write_state_key(wb, "BS_PROGRESS", "CA,NCA");               wb.save(filepath); print("BS_DONE: Non-Current Assets")
# Block 3 — Total Assets row:
write_state_key(wb, "BS_PROGRESS", "CA,NCA,TA");            wb.save(filepath); print("BS_DONE: Total Assets")
# Block 4 — Current Liabilities:
write_state_key(wb, "BS_PROGRESS", "CA,NCA,TA,CL");        wb.save(filepath); print("BS_DONE: Current Liabilities")
# Block 5 — Non-Current Liabilities:
write_state_key(wb, "BS_PROGRESS", "CA,NCA,TA,CL,NCL");    wb.save(filepath); print("BS_DONE: Non-Current Liabilities")
# Block 6 — Equity section:
write_state_key(wb, "BS_PROGRESS", "CA,NCA,TA,CL,NCL,EQ"); wb.save(filepath); print("BS_DONE: Equity")
# Block 7 — BS_CHECK row:
write_state_key(wb, "BS_PROGRESS", "CA,NCA,TA,CL,NCL,EQ,CHECK"); wb.save(filepath); print("BS_DONE: BS_CHECK row")
```
4. BS Cash: write `ws_bs.cell(cash_row, col).value = 0` for ALL columns — do NOT link to CF yet
5. BS CHECK formula must be present (`=TA_cell - TLE_cell`) but will NOT equal 0 until SESSION D — this is expected
6. Write KEY_CELLS_BS to _State:
```
KEY_CELLS_BS: {"AR_row": N, "Inv_row": N, "AP_row": N, "OtherCL_row": N, "Cash_row": N, "NCA_tot_row": N, "CA_excl_start_row": N, "CA_excl_end_row": N, "TLE_row": N, "NCI_row": N, "BS_CHECK_row": N, "first_hist_col": 2, "first_fcst_col": 5}
```
7. Save. Update FILE_HASH. Write `PHASE_DONE: SESSION_C`

**End condition:** All 7 BS_DONE markers printed. Do NOT validate BS CHECK = 0 here.

---

# Phase 3 — Balance Sheet Templates

Reflect the granularity from Phase 0's source comparison. Include every material line item. Items consistently "--" across all years can be omitted.

## Equity Section — Never Omit (PHASE 3 Detail)

```python
share_capital      # flat unless issuance schedule
apic               # Prior + SBC + Issuance
treasury_stock     # carry or buyback (negative equity)
oci                # flat or FX
surplus_reserve    # CN GAAP only: Prior + 10%×NI until = 50% share capital
retained_earnings  # Prior + Attr_Owners − Dividends − Surplus_appropriation
nci                # Prior + Attr_NCI − NCI_Dividends  ← NEVER 0 if hist NCI ≠ 0
equity_total       # sum of above
```

**Equity notes:**
- 盈余公积: statutory 10% of NI until 50% of registered capital (intra-equity transfer, not cash)
- 库存股: negative equity for buybacks
- 资本公积: share premium + SBC; 其他综合收益: FX translation for overseas subs

## IFRS / US GAAP BS

```
NCA: PP&E net = Prior+Capex−D&A · ROU = Prior+New−Amort · Intangibles = Prior+Capex−Amort
     Goodwill (flat) · LT Investments = Prior+JV · DTA (carry) · Other NCA (carry)

CA:  Inventories = COGS×Inv_Days/365 · AR = Rev×AR_Days/365
     Contract Assets / Prepayments / Other (% rev or carry) · Restricted Cash (carry)
     Cash — BLANK until CF → = CF!Ending_Cash

CL:  AP = COGS×AP_Days/365 · Contract Liab / Accrued (% rev or carry)
     ST Borrowings + Current LT (debt sched) · Current Lease · Tax Payable (carry)

NCL: LT Borrowings · NC Lease · DTL · Other NCL (carry)

Equity: Share Capital (flat) · APIC = Prior+SBC+Issuance
        Reserves = Prior+Attr_Owners−Div · OCI (flat/FX) · NCI = Prior+Attr_NCI−Div_NCI

BS CHECK = TA − TLE = 0
```

## Chinese GAAP BS (中国会计准则)

```
流动资产 CA:
  货币资金 Cash                    → BLANK → CF!Ending_Cash
  交易性金融资产                    (carry or % cash)
  应收票据 Notes receivable         = Rev × Note_Days/365 or carry
  应收账款 AR                       = Rev × AR_Days/365
  应收款项融资 Recv financing        (carry — bank acceptance notes)
  预付款项 Prepayments              = COGS × Prepay_Days/365
  其他应收款 Other recv              (carry or % rev)
  存货 Inventories                  = COGS × Inv_Days/365
  其他流动资产 Other CA              (carry — often VAT input)
  流动资产合计

非流动资产 NCA:
  长期股权投资 LT equity inv         = Prior + JV profit
  投资性房地产 Inv property          (carry, D&A if material)
  固定资产净额 PP&E net              = Prior + Capex − D&A
  在建工程 CIP                       = Prior + Additions − Transfers to PP&E
  使用权资产 ROU                     = Prior + New − Amort
  无形资产 Intangibles               = Prior + Additions − Amort
  开发支出 Dev expenditure           (carry or capitalized R&D)
  商誉 Goodwill                      (flat unless impairment)
  长期待摊费用 LT prepaid            (carry − amort)
  递延所得税资产 DTA                  (carry → Others plug)
  其他非流动资产 Other NCA           (carry)
  非流动资产合计

资产总计 TOTAL ASSETS

流动负债 CL:
  短期借款 ST borrowings             (debt schedule)
  应付票据 Notes payable             = COGS × NotePay_Days/365
  应付账款 AP                        = COGS × AP_Days/365
  合同负债 Contract liab             (% rev or carry)
  应付职工薪酬 Employee payable      (% opex or carry)
  应交税费 Taxes payable             (carry or % tax)
  其他应付款 Other payables          (carry or % rev)
  一年内到期非流动负债               (debt maturity schedule)
  其他流动负债 Other CL              (carry)
  流动负债合计

非流动负债 NCL:
  长期借款 LT borrowings             (debt schedule)
  应付债券 Bonds payable             (maturity schedule)
  租赁负债 Lease liab                = Prior + New − Principal
  递延所得税负债 DTL                  (carry)
  长期递延收益 Deferred income        (carry — govt grants amortization)
  其他非流动负债 Other NCL           (carry)
  非流动负债合计

负债合计 TOTAL LIABILITIES

所有者权益 EQUITY:
  实收资本 Share capital              (flat unless issuance)
  资本公积 Capital reserve (APIC)     = Prior + SBC + Issuance
  库存股 Treasury stock               (carry or buyback schedule)
  其他综合收益 OCI                    (flat or FX)
  盈余公积 Surplus reserve            = Prior + 10%×NI (until = 50% share capital)
  未分配利润 Retained earnings        = Prior + Attr_Owners − Dividends − Surplus appropriation
  归属母公司合计
  少数股东权益 NCI                     = Prior + Attr_NCI − NCI Dividends
  所有者权益合计

BS CHECK = 资产总计 − (负债+权益) = 0
```

**Quarterly models:** BS stays annual. References IS FY columns via `is_fy_cl(year)`.

## WC Assumptions Block (below BS CHECK)

```
                         H Y-2  H Y-1  H Y0   F Y+1E  F Y+2E  Note
AR Days                  [x]    [x]    [x]    [input] [input]  AR/Rev×365; 3yr avg; mgmt commentary
Contract Asset Days      [x]    [x]    [x]    [input] [input]
Prepayment %Rev          [x]    [x]    [x]    [input] [input]
Inventory Days           [x]    [x]    [x]    [input] [input]  Inv/COGS×365; RM/WIP/FG breakdown
AP Days                  [x]    [x]    [x]    [input] [input]  AP/COGS×365; 3yr avg
Contract Liab %Rev       [x]    [x]    [x]    [input] [input]
Cash Conversion Cycle    [calc] [calc] [calc]  [calc]  [calc]   = AR + Inv − AP (calculated)
NWC                      [calc] [calc] [calc]  [calc]  [calc]   = CA excl Cash − CL excl Debt
```
Historical [x]: black formula. Forecast [input]: navy, light blue bg, links Assumptions.
