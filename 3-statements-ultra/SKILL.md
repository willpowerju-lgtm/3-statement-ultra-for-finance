---
name: 3-statements-ultra
description: >
  从零构建机构级三表模型（IS/BS/CF）— 完整公式联动、美股/A股强制季度·港股强制半年度、IFRS/US GAAP/中国准则。
  触发词：三表模型、financial model、3-statement、建模、从零建模、收入预测。
  ❌ 填写已有模板请用 financial-analysis:3-statements
---

# 3-Statement Model — IPO / Equity Research Quality (v4.8 · Public Edition)

---

## 🚀 Quick Start — New Users

**This skill builds:** A complete institutional-grade 3-statement financial model (IS / BS / CF) in Excel,
with full formula linkage, zero hardcoded forecast cells, and 9-step QC validation.

**Prerequisites — install before starting:**
```bash
pip install openpyxl yfinance pandas
pip install notebooklm   # optional — only needed if you have a NotebookLM notebook
```

**How to trigger:** Just say `"建个三表模型"` / `"build a 3-statement model for [Company]"` and the skill guides you step by step.

**What to prepare:**
- Company ticker (e.g. `BABA`, `0700.HK`, `600519.SS`)
- A data source — see recommendations below
- ~1–2 hours across 5 sessions (each session is independent — pause and resume anytime)

**⚠️ Data Source Guide — Read Before Starting**

| Option | Setup | Token Cost | Recommended? |
|--------|-------|-----------|--------------|
| **NotebookLM notebook** (annual reports / prospectus pre-loaded) | One-time OAuth auth setup | Very low — NLM handles the PDF; Claude only receives answers | ✅ Best path |
| **Excel upload** (historical IS/BS/CF already structured) + short PDF excerpts | None | Low | ✅ Good |
| **Direct PDF upload** (full annual report, prospectus) | None | 🔴 Very high — a single A-share annual report can be 200+ pages | ⚠️ Pro users: avoid |
| **Web only** (Sina / Yahoo Finance fallback) | None | Low | ✅ Fallback |

**Strongly recommended for new users: set up NotebookLM first.**
The one-time auth flow takes ~5 minutes and saves significant token consumption for every future model:
```bash
pip install notebooklm

# Run once interactively — browser will open for Google OAuth
python3 -c "
import asyncio
from notebooklm import NotebookLMClient

async def auth():
    async with await NotebookLMClient.from_storage() as client:
        nbs = await client.notebooks.list()
        print(f'Auth OK — {len(nbs)} notebooks accessible')

asyncio.run(auth())
"
# After login, session is saved to ~/.notebooklm/storage_state.json
# You only need to do this once (re-auth if session expires, typically ~7 days)
```

**If you skip NLM:** the most token-efficient alternative is to upload a clean **Excel file with historical IS/BS/CF** (3–5 years) plus any short PDF excerpts (earnings release, key pages only). Uploading a full 300-page annual report in one go is the worst option for token consumption — especially on Claude Pro.

**5-session build flow:**
```
SESSION A  — Raw data extraction + Assumptions setup   (~15–30 min)
SESSION B  — Income Statement                           (~15–20 min)
SESSION C  — Balance Sheet                              (~15–20 min)
SESSION D  — Cash Flow + reconciliation checks          (~15–25 min)
SESSION E  — Returns + Cross-check + Summary            (~15–20 min)
```
State is preserved in the Excel `_State` tab between sessions. If a session is interrupted, the startup protocol automatically resumes from the last checkpoint.

**Supported:** CN GAAP / IFRS / US GAAP · US & A-share: Quarterly (forced) · HK: Semi-annual (forced)

---

## 📋 Recommended User Preference — Copy-Paste Before First Use

To prevent state loss after context compaction, add the following block to your **Claude User Preferences** (Settings → Profile → Custom Instructions, or your `CLAUDE.md` file):

```
## 3-Statements-Ultra — Compaction Recovery Protocol
When I am building a 3-statement financial model using the 3-statements-ultra skill,
after ANY context compaction event, you MUST:
1. Re-read the 3-statements-ultra SKILL.md before writing any code
2. Read the state.json sidecar (auto-migrates from legacy _State sheet) — determine exact resume point
3. Read _model_log.md — recover prior session outputs (key totals, check results)
4. Read _pending_links.json — check if BS→CF back-fill is pending
5. Run RAW_MAP + ASM_MAP spot-check before using any row numbers
6. Never hardcode any IS/BS/CF forecast cell — every cell must be a string formula
7. Resume from the next incomplete step only — never re-run completed sections
Do not rely on conversation memory for row numbers or intermediate calculation results.
Disk state (_State, _model_log.md, _pending_links.json) is always authoritative.
```

This prevents the most common failure mode: resuming from memory after compaction and writing wrong row numbers or hardcoded values.

---

## ██ RULE ZERO — HARDCODE BAN ██
## ██ Read this first. Read again after every compact. No exceptions. ██

**THE #1 FAILURE MODE OF THIS SKILL IS HARDCODED FORECAST CELLS.**

```
CORRECT — historical IS/BS/CF cell:  ws["B5"].value = '=Raw_Info!C12'
CORRECT — forecast non-revenue:      ws["E5"].value = '=Assumptions!B8'
CORRECT — forecast IS revenue row:   ws["E5"].value = '=Revenue_Build!E36'   ← when REVENUE_BUILD=TRUE
CORRECT — forecast Revenue_Build:    ws["E5"].value = '=D5*(1+Assumptions!B12)'

BROKEN:   ws["E5"].value = 0.30                     ← hardcode, model is dead
BROKEN:   ws["E5"].value = float(revenue * 0.30)    ← hardcode, model is dead
BROKEN:   ws["E5"].value = prev_value * growth       ← hardcode, model is dead
BROKEN — IS forecast Revenue row when Revenue_Build exists:
          ws_is["E5"].value = '=D5*(1+Assumptions!B12)'   ← bypasses Revenue_Build (R12 violation)
```

**Formula reference rules — two modes, never mix:**
- **Direct assignment** (cell gets the formula itself): value must be a string starting with `=`
  - Historical: `ws["B5"].value = f"=Raw_Info!C{raw_map['IS: Revenue']}"`
  - Forecast standalone: `ws["E5"].value = f"=Assumptions!B{asm_map['Revenue YoY %']}"`
  - **IS forecast Revenue (when REVENUE_BUILD=TRUE)**: `ws_is["E5"].value = f"=Revenue_Build!{col}{rev_build_map['Auto: Total']}"`
- **Embedded in compound formula**: reference without leading `=`
  - `ws["E5"].value = f"=D5*(1+Assumptions!B{asm_map['Revenue YoY %']})"`
- **NEVER mix**: `f"=D5*(1+=Assumptions!B2)"` → Excel parse error (extra `=` inside)

**Inline ↳ pattern (mandatory on all tabs with forecast formulas):**
Forecast formulas reference SAME-SHEET rows only. Every Assumptions driver gets an inline `↳`
mirror row (`=Assumptions!<col><row>`). The forecast formula references the ↳ row on the same sheet.

**Before writing Python code for any IS / BS / CF / Revenue_Build tab, run this self-check:**
- [ ] Every forecast formula references SAME-SHEET rows only (inline ↳ pattern)
- [ ] `↳` rows are the ONLY cells with cross-tab `=Assumptions!*` references
- [ ] Every historical column cell → string starting with `=Raw_Info!`
- [ ] When `REVENUE_BUILD=TRUE`, IS Q forecast Revenue cells → `=Revenue_Build!*` (R12 strict)
- [ ] When `REVENUE_BUILD=TRUE`, IS FY forecast Revenue cells → `=SUM(Q1:Q4)` (summary exception)
- [ ] Zero raw floats or ints assigned to IS/BS/CF non-input rows

**The ONLY cells permitted to hold hardcoded numeric values:**
- Assumptions tab input rows (navy text, light-blue bg) ← these ARE the model inputs
- Raw_Info tab (source extraction) ← historical facts by definition
- Column headers, row labels, check labels

---

## ██ COMPACT RESUME PROTOCOL ██
## ██ For context compaction within an active session — different from session startup ██

After context compaction fires mid-session, BEFORE writing any more code:
```
Step 1: Re-read this SKILL.md             ← re-internalize Rule Zero + Code Gen Protocol
Step 2: Open Excel file → read _State tab
Step 3: Read current session's last completed step from _State
Step 4: Read RAW_MAP + ASM_MAP from _State, run spot-check
Step 5: Read _model_log.md                ← recover intermediate results (key numbers per tab)
Step 6: Read _pending_links.json          ← check if deferred cross-sheet refs need back-fill
Step 7: Continue from the next incomplete step within the current session only
```
Do NOT re-verify PHASE_DONE of prior sessions — that is the session startup protocol below.
Do NOT reload reference files unless actively needed for the current step.

**Why Steps 5-6 exist:** Context compaction loses intermediate calculation results. Without
_model_log.md, you cannot cross-validate the next tab's outputs against prior tabs. Without
_pending_links.json, you may forget which BS cells still need CF back-fill references.

---

## ██ CODE GENERATION PROTOCOL ██
## ██ One complete tab section per code block. Execute before writing the next. No exceptions. ██

**THE #2 FAILURE MODE IS GENERATING TOO MUCH CODE AT ONCE.**

Quarterly IS tabs produce 300+ lines of Python. A single truncated output = silently broken model.

**Rule: Write ONE code block per logical tab section → execute it → verify output → checkpoint to _model_log.md → write the NEXT code block.**

```
Each code block should cover ONE complete tab section:
  IS:  All Revenue rows  |  COGS through GP  |  OpEx block  |  EBIT+below+NCI+checks
  BS:  All Current Assets  |  All Non-Current Assets  |  All Current Liab  |  NCL+Equity
  CF:  One full year at a time (CFO → CFI → CFF → Others → Cash → back-fill)

Target: ~200–350 lines per code block (one tab section).
If a section exceeds 350 lines, split at natural boundaries (e.g., Revenue vs COGS).
NEVER exceed 400 lines in a single code block.
```

**After every code block:**
1. Execute it — read the output for errors
2. Verify the progress marker printed (e.g., `IS_DONE: Revenue`)
3. Verify `wb.save()` completed (file mtime updated)
4. **Write checkpoint to _model_log.md** (see Checkpoint Protocol below)
5. Only then write the next block

**If output is truncated mid-code-block:** the partial code was NOT executed. Re-generate that section only (not the full session). Read _State to find where to resume.

**Why this limit exists:** Quarterly IS = 35 cols × 50 rows = 1750 cell assignments. At ~20 tokens/line, a single script easily hits the 32k-token Bash output cap. The script is silently truncated — no error, no exception — and the Excel file ends up partially written. Tab-section-level blocks prevent this entirely while avoiding the fragmentation of overly small (≤100 line) blocks.

---

## ██ _model_log.md — CHECKPOINT PROTOCOL ██
## ██ Disk is truth, context is lossy. Every tab section writes results to disk. ██

**Purpose:** After each tab section completes, write key output numbers to `_model_log.md`.
The next tab section reads from this file for cross-validation — NOT from context memory.

**Format:**
```markdown
# 3-Statement Model Log

## SESSION A — Raw_Info + Assumptions
- Completed: 2026-03-28 14:30
- Revenue segments: [Freight matching: ¥12.3B, Commission: ¥2.1B, ...]
- Historical periods: FY2021, FY2022, FY2023, H1 2024
- Unit: 百万元
- Granularity: semi-annual

## SESSION B — IS
### Revenue block
- Completed: 2026-03-28 15:00
- FY2023 Total Rev (model): ¥18,432M → matches Raw_Info ✓
- FY2025E Total Rev: ¥24,100M (YoY +15.2%)

### COGS+GP block
- Completed: 2026-03-28 15:15
- FY2023 GP Margin (model): 52.3% → matches source 52.4% (rounding ±0.1%) ✓

### OpEx block
- ...

### EBIT+below+checks block
- FY2023 NI (model): ¥5,210M → NI CHECK = 0 ✓
- REV CHECK = 0 ✓

## SESSION C — BS
### Current Assets
- Completed: ...
- FY2023 Total CA (model): ¥xx,xxxM
- Cash cell: PLACEHOLDER (pending CF back-fill)
- ⚠ Pending links written to _pending_links.json: [Cash row refs]

### Non-Current Assets
- ...
```

**Rules:**
1. Append after every code block execution — never overwrite prior entries
2. Include at least: completion timestamp, 1-2 key totals, check results
3. Flag any PLACEHOLDER cells explicitly
4. Next session reads this file at startup to cross-validate (e.g., SESSION C reads IS totals from log to verify BS Retained Earnings linkage makes sense)

---

## ██ _pending_links.json — DEFERRED CROSS-SHEET REFERENCES ██
## ██ BS cells that depend on CF (built later) are recorded here, back-filled in SESSION D. ██

**Problem:** SESSION C builds BS, but Cash = CF Ending Cash (built in SESSION D).
Other cells may also depend on CF outputs (e.g., lease liability changes).
Writing placeholder values risks forgetting to back-fill after compaction.

**Mechanism:**
```python
import json

# --- SESSION C: when writing BS Cash as placeholder ---
pending = []
# For each year's Cash cell:
pending.append({
    "target_sheet": "BS",
    "target_cell": "E15",       # e.g., FY2023 Cash
    "formula": "=CF!E42",       # will be filled when CF row 42 exists
    "depends_on": "CF",
    "description": "BS Cash = CF Ending Cash FY2023"
})
# ... repeat for each forecast year

with open("_pending_links.json", "w") as f:
    json.dump(pending, f, indent=2)

# Also record in _State:
write_state_key(wb, "PENDING_LINKS", str(len(pending)))

# --- SESSION D: after CF is complete, batch back-fill ---
with open("_pending_links.json") as f:
    pending = json.load(f)

for link in pending:
    ws = wb[link["target_sheet"]]
    ws[link["target_cell"]].value = link["formula"]
    print(f"✅ Back-filled: {link['target_sheet']}!{link['target_cell']} = {link['formula']}")

# Clear pending
with open("_pending_links.json", "w") as f:
    json.dump([], f)
write_state_key(wb, "PENDING_LINKS", "0")
wb.save(filepath)
```

**Rules:**
1. SESSION C writes `_pending_links.json` with all BS→CF deferred references
2. SESSION C writes `PENDING_LINKS: N` to _State (N = count of pending items)
3. SESSION D reads `_pending_links.json` FIRST, then builds CF, then batch back-fills
4. After back-fill, clear the file and update _State to `PENDING_LINKS: 0`
5. SESSION E startup: if `PENDING_LINKS` > 0, STOP — SESSION D incomplete

---

## ██ GLOBAL BUILD SEQUENCE ██
## ██ Mandatory. No skipping. No parallel tabs. ██

The model is built across **5–6 sessions** (SESSION A2 is conditional). Each session starts with a clean context, loads
**only its own reference file**, and communicates state through the `_State` tab in Excel
**plus two sidecar files: `_model_log.md` and `_pending_links.json`**.

**Build principle:** Each session writes only what it needs for that session — some sessions
build one tab, others build several. Never write all tabs at once within a session. Tabs and
sections are added incrementally across sessions, with _State + sidecar files carrying state between them.

**Assumptions is append-only across sessions** — SESSION A creates core drivers. SESSION A2 appends per-segment Vol/ASP YoY drivers. SESSION B/C may append additional rows. Never delete existing rows; update ASM_MAP after every append.

```
PRE-FLIGHT  — ① MARKET_GATE (mandatory first step, see below)
              ② NLM kickoff 问答 (首次运行必做，结果写入 _State)
              └─ included in references/session-a.md

SESSION A   — Raw_Info + Assumptions(core)       → Read references/session-a.md
              └─ Phase 2.5: set REVENUE_BUILD TRUE/FALSE
SESSION A2  — Revenue_Build (CONDITIONAL)        → Read references/session-a2.md
              └─ Triggered if REVENUE_BUILD=TRUE (default for multi-segment models)
              └─ Builds Vol×ASP / Q YoY / guide+ramp per segment
              └─ IS forecast Revenue will link here (R12)
SESSION B   — IS                                 → Read references/session-b.md
              └─ If REVENUE_BUILD=TRUE: Q forecast Revenue = =Revenue_Build!* (R12)
SESSION C   — BS (Cash placeholder)            → Read references/session-c.md
               └─ writes _pending_links.json for Cash + any CF-dependent cells
SESSION D   — CF + back-fill _pending_links    → Read references/session-d.md
               └─ reads _pending_links.json → builds CF → batch back-fills BS → checks
SESSION E   — Returns + Cross_Check + Summary  → Read references/session-e.md
               └─ verifies PENDING_LINKS = 0 before proceeding
```

---

## ██ MARKET_GATE — MANDATORY PRE-FLIGHT STEP ZERO ██
## ██ Must execute before any model file is created. No exceptions. ██

**Purpose:** Lock the listing venue and time granularity into `_State` before any column
headers or data cells are written. All subsequent sessions read from `_State` — never
re-derive or override. This prevents the #1 structural error: building quarterly columns
for an HK name or semi-annual columns for a US/A-share name.

### Step 0A — Ask (SESSION A first run only)

Before creating the Excel file, ask the user ONE question:

```
"What market is this company listed on?
  [1] US-listed (NYSE / NASDAQ / ADR)
  [2] A-share (Shanghai / Shenzhen)
  [3] HK-listed (HKEX main board / GEM)
  [4] Dual-listed → specify primary listing venue"
```

Do NOT proceed until the user answers. Do NOT infer from the ticker symbol alone.

### Step 0B — Write to _State (immediately after user confirms)

```python
MARKET_MAP = {
    "US":  {"granularity": "quarterly",    "periods": ["Q1","Q2","Q3","Q4"]},
    "A":   {"granularity": "quarterly",    "periods": ["Q1","Q2","Q3","Q4"]},
    "HK":  {"granularity": "semi-annual",  "periods": ["H1","H2"]},
}

# user_answer is "US", "A", or "HK"
market    = user_answer.upper()
gran      = MARKET_MAP[market]["granularity"]
periods   = MARKET_MAP[market]["periods"]

write_state_key(wb, "MARKET",       market)           # e.g. "HK"
write_state_key(wb, "GRANULARITY",  gran)             # e.g. "semi-annual"
write_state_key(wb, "PERIODS",      ",".join(periods))# e.g. "H1,H2"
write_state_key(wb, "MARKET_GATE",  "LOCKED")
wb.save(filepath)
print(f"✅ MARKET_GATE LOCKED — {market} / {gran} / {periods}")
```

### Step 0C — Gate enforcement function (used in EVERY session before writing column headers)

```python
def enforce_market_gate(state: dict) -> dict:
    """Call this before writing any IS/BS/CF column headers. Raises if gate not set."""
    gate   = state.get("MARKET_GATE", "")
    market = state.get("MARKET", "")
    gran   = state.get("GRANULARITY", "")
    raw_p  = state.get("PERIODS", "")

    if gate != "LOCKED" or not market or not gran or not raw_p:
        raise RuntimeError(
            "❌ MARKET_GATE not locked — run PRE-FLIGHT Step 0 before building any tab."
        )

    periods = raw_p.split(",")
    valid = {
        "US": ("quarterly",   ["Q1","Q2","Q3","Q4"]),
        "A":  ("quarterly",   ["Q1","Q2","Q3","Q4"]),
        "HK": ("semi-annual", ["H1","H2"]),
    }
    expected_gran, expected_periods = valid[market]
    if gran != expected_gran or periods != expected_periods:
        raise RuntimeError(
            f"❌ MARKET_GATE mismatch — _State says {gran}/{periods} "
            f"but {market} requires {expected_gran}/{expected_periods}. "
            f"Do NOT proceed. Fix _State or restart PRE-FLIGHT."
        )

    print(f"✅ MARKET_GATE OK — {market} / {gran} / {periods}")
    return {"market": market, "granularity": gran, "periods": periods}
```

**Usage in SESSION B/C/D (before writing any column header row):**
```python
state  = read_state(wb)
mgate  = enforce_market_gate(state)   # raises on any violation
periods = mgate["periods"]            # ["Q1","Q2","Q3","Q4"] or ["H1","H2"]
# ... use `periods` to build column headers — never hardcode "Q1" etc.
```

---

**Step 7 of session startup = Read ONLY the reference file for THIS session. No others.**

### Session startup protocol (every session, no exceptions)

```
Step 1: Re-read this SKILL.md                        ← re-internalize Rule Zero + MARKET_GATE
Step 2: Open Excel file → read _State tab
        ⚠ SESSION A first run exception: if the file does not exist yet,
          skip Steps 3–11 entirely. Create the file. Run MARKET_GATE Step 0A first.
Step 3: Parse _State into dict (format: "KEY: value" per line)
Step 3b: ██ MARKET_GATE CHECK ██ — call enforce_market_gate(state)
         If it raises → STOP. Do not write any tab until gate is locked.
         (SESSION A first-run exception: gate will be written in Step 0B before Raw_Info)
Step 4: Verify FILE_HASH matches current file mtime  ← if mismatch, STOP and alert user
Step 5: Verify SKILL_VERSION in _State matches current skill version ← if mismatch, STOP
Step 6: Verify previous session PHASE_DONE exists    ← if missing, STOP
        (Exception: SESSION A — if no PHASE_DONE at all, run PRE-FLIGHT first
         from references/session-a.md before building Raw_Info)
Step 7: Read ONLY references/session-[X].md for this session
Step 8: Read RAW_MAP + ASM_MAP from _State
        ⚠ SESSION A exception: if "RAW_MAP" key is absent from _State (mid-session crash
          before Raw_Info was written), skip Steps 8–11 and resume from session-a.md Step 2.
Step 9: Run spot-check on RAW_MAP + ASM_MAP (see below)
        ⚠ SESSION A exception: only run spot-check if Raw_Info tab already exists in wb.
Step 10: Read _model_log.md                          ← recover prior session outputs
Step 11: Read _pending_links.json                    ← check deferred refs status
         ⚠ SESSION E: if PENDING_LINKS > 0, STOP — SESSION D did not complete back-fill
Step 12: Continue from next incomplete step only
```

**_State format — one key per row, parsed with:**
```python
import openpyxl, os

def read_state(wb):
    ws = wb["_State"]
    state = {}
    for row in ws.iter_rows(values_only=True):
        if row[0] and ": " in str(row[0]):
            k, v = str(row[0]).split(": ", 1)
            state[k.strip()] = v.strip()
    return state

def write_state_key(wb, key, value):
    ws = wb["_State"]
    for row in ws.iter_rows():
        if row[0].value and str(row[0].value).startswith(key + ": "):
            row[0].value = f"{key}: {value}"
            return
    ws.append([f"{key}: {value}"])
```

**RAW_MAP / ASM_MAP format in _State:**
```
RAW_MAP: {"IS: Revenue": 15, "IS: COGS": 16, "BS: AR": 28, ...}
ASM_MAP: {"Revenue YoY %": 2, "Gross Margin %": 3, "AR Days": 7, ...}
```
Parse with `json.loads(state["RAW_MAP"])`.

**RAW_MAP / ASM_MAP spot-check (Step 9) — mandatory before using any map entry:**
```python
import json
raw_map = json.loads(state["RAW_MAP"])
asm_map = json.loads(state["ASM_MAP"])
for label, row in list(raw_map.items())[:3]:
    actual = ws_raw.cell(row, 1).value
    assert actual == label, f"RAW_MAP stale: expected '{label}' at row {row}, got '{actual}' — STOP"
for label, row in list(asm_map.items())[:3]:
    actual = ws_asm.cell(row, 1).value
    assert actual == label, f"ASM_MAP stale: expected '{label}' at row {row}, got '{actual}' — STOP"
```
If assertion fails: file was externally edited or _State is stale. Rebuild _State before proceeding.

---

## TAB ARCHITECTURE

```
[1] Summary        ← built last; all figures link to model cells
[2] Assumptions    ← every forecast driver; single source of truth; APPEND-ONLY across sessions
[3] Revenue_Build  ← (CONDITIONAL) Vol×ASP per segment → segment totals; IS pulls forecast Revenue from here
[4] IS             ← Income Statement
[5] BS             ← Balance Sheet
[6] CF             ← Cash Flow Statement (indirect)
[7] Returns        ← ROE / ROA / ROIC / DuPont
[8] Cross_Check    ← assumption validation + revision log
[8] Raw_Info       ← source extraction (built first; never re-read source after)
[_State]           ← session metadata; last tab; delete after MODEL_COMPLETE
```

**Sidecar files (same directory as Excel):**
```
_model_log.md        ← checkpoint results per tab section (append-only)
_pending_links.json  ← deferred cross-sheet references (written by C, consumed by D)
```

---

## CORE RULES

**R1 — One source:** After Raw_Info is complete, never re-read the source. All data flows via `=Raw_Info!` links.

**R2 — No free plugs:** Never use `= Total_LE − Total_Assets` to force-balance BS. One permitted plug only: `Non-cash Adj – Others` row in CFO (R3). One IS plug for CN GAAP (R8).

**R3 — Others plug (non-circular):**
```
CF!Others = BS!Total_LE − BS!Total_NCA − SUM(BS!CA_excl_Cash) − BS!Prior_Cash
          − CF!NI − CF!DA − CF!SBC − CF!Impairment − CF!JV
          − CF!WC_Total − CF!CFI_Total − CF!CFF_Total
```
Non-circular by construction. Guarantees `BS CHECK = 0` and `CF CHECK = 0` simultaneously.
- Write Others ONLY after CFI and CFF rows for that year are complete (within each year's loop)
- Historical years: use Raw_Info actual value if disclosed; else 0
- Forecast years: always use full R3 formula
- `|Others| ≤ 15% of |CFO|` → accept ✓
- `|Others| > 15% of |CFO|` → material CF line missing; find and model it explicitly

**R4 — NCI persists:** If historical NCI ≠ 0, it appears in every forecast period.
- `Attr_to_NCI = NI × NCI_Ratio`
- `BS NCI_end = Prior + Attr_to_NCI − NCI_Dividends`
- `BS Reserves_end = Prior + Attr_to_Owners − Owner_Dividends` ← NOT total NI

**R5 — No double-count in CF:** Interest/tax paid are already in NI. No separate CFO rows in forecasts.

**R6 — Cash last:** All BS items built → CF complete year by year → `BS!Cash = CF!Ending_Cash` back-filled immediately after each year's CF is complete.

**R7 — Every BS Δ has a CF home:**

| BS Item | CF Line |
|---|---|
| PP&E net | CFI −Capex + CFO +D&A_PPE only |
| ROU Assets | CFO +ROU amort + CFF −Lease principal; if flat → Others |
| Intangibles | CFI −capex + CFO +amort; if flat → Others |
| LT Investments | CFI other investing |
| DTA / DTL | Others plug |
| Inventory / AR / Contract Assets / Prepayments | CFO WC (asset ↑ = cash out) |
| AP / Contract Liab / Accrued | CFO WC (liab ↑ = cash in) |
| ST + LT Borrowings | CFF draws / repayments |
| Lease Liabilities | CFF lease principal |
| Share Capital / APIC | CFF equity issuance + SBC |
| Reserves | IS Attr. to Owners (rolling) |
| NCI | IS Attr. to NCI (rolling) |
| Cash | CF Ending Cash — back-filled via _pending_links.json in SESSION D |

**PP&E note:** Use PP&E-specific depreciation rate (e.g. 20%), NOT total D&A. R3 absorbs the residual.

**R8 — CN GAAP IS plug:**
```
Historical: Other Op Inc = Source 营业利润 − (Model Rev − COGS − OpEx − Impairment)
Forecast:   % of revenue or absolute from Assumptions tab
```
If |Other Op Inc| > 10% of EBIT → investigate; model the largest component explicitly.

**R9 — Four reconciliation checks (all must = 0):**
- `BS CHECK = Total Assets − Total L+E`
- `CF CHECK = Ending Cash − BS Cash`
- `NI CHECK = Model NI − Source NI` (tolerance ±10 for quarterly rounding)
- `REV CHECK = Model Total Revenue − Source Total Revenue`

**R10 — Granularity is determined by listing venue, not disclosure pattern (mandatory):**

| Market | IS / CF granularity | BS granularity |
|---|---|---|
| US-listed (NYSE / NASDAQ / ADR) | **Quarterly — Q1, Q2, Q3, Q4 (forced)** | Annual |
| A-share (Shanghai / Shenzhen) | **Quarterly — Q1, Q2, Q3, Q4 (forced)** | Annual |
| HK-listed (HKEX main board / GEM) | **Semi-annual — H1, H2 (forced)** | Annual |

**No exceptions.** Do not auto-detect or adapt based on what the company happens to disclose. Even if a US or A-share company only publishes annual data, the model columns must be quarterly (fill missing quarters with `—` or interpolated placeholders). Even if a HK company voluntarily publishes quarterly updates, the model granularity remains semi-annual.

BS is always annual. Quarterly CF: Beg_Cash Q1 = prior FY BS Cash; Q2/Q3/Q4 = prior quarter CF Ending Cash (back-filled within SESSION D year-by-year loop).

**R12 — Revenue_Build is the source of forecast segment revenue (when triggered):**

Revenue_Build is built in SESSION A2 (before IS). IS forecast Revenue rows link back to it.
This separates "how revenue is built" (Vol/ASP/Q YoY/guide+ramp) from "what flows to IS" (totals).

- **Trigger**: SESSION A Phase 2.5 sets `REVENUE_BUILD: TRUE` (default-on for ≥2 segments or any vol×price)
- **Quarterly architecture**: forecast at Q level (Q YoY for mature, guide+ramp for new biz), FY = SUM(Q)
- **IS link**: Q forecast Revenue = `=Revenue_Build!<Q_col><total_row>` (strict R12). FY = `=SUM(Q1:Q4)`.
- **Inline ↳ pattern**: Revenue_Build forecast formulas reference same-sheet `↳` mirror rows only. `↳` rows are the sole cross-tab link to Assumptions.
- **QC defense**: QC-20 (Revenue_Build integrity), QC-21 (IS→Revenue_Build link), QC-22 (historical ↳ completeness)

See `references/session-a2.md` for full spec.

---

## KEY FORMULAS

```
Inline ↳ pattern (ALL tabs):
  Data row forecast:      =same_sheet_formula (references ↳ row, Vol row, ASP row, etc.)
  ↳ row (inline mirror):  =Assumptions!<col><row>    ← ONLY cross-tab link per driver

Revenue_Build (quarterly, mature segment Q YoY):
  Vol Q forecast:   =prior_yr_same_Q * (1 + same_sheet_↳_Vol_YoY_row)
  ASP Q forecast:   =prior_yr_same_Q * (1 + same_sheet_↳_ASP_YoY_row)
  Rev Q:            =Vol_row * ASP_row
  FY:               =SUM(Q1:Q4)     ← FY is ALWAYS derived

Revenue_Build (new biz, guide + ramp):
  Q forecast:       =same_sheet_↳_FY_guide * same_sheet_↳_Q_share%
  FY:               =SUM(Q1:Q4)

IS Revenue (REVENUE_BUILD=TRUE, quarterly):
  Q forecast:       =Revenue_Build!<Q_col><seg_total_row>   ← R12 strict
  FY forecast:      =SUM(IS Q1:Q4)                          ← summary exception

IS COGS/SGA/R&D (inline ↳ pattern):
  COGS Q forecast:  =-Rev * (1 - same_sheet_↳_GM%)
  ↳ GM %:           =Assumptions!<col><gm_row>

WC → BS:   AR = Rev × AR_Days/365  |  Inv = COGS × Inv_Days/365  |  AP = COGS × AP_Days/365
CF WC:     Δ Asset = −(curr − prior)  |  Δ Liability = +(curr − prior)
PP&E:      Net = Prior × (1 − Depr_Rate) + |Capex|   ← PPE-specific rate, NOT total D&A
Equity:    Reserves = Prior + Attr_Owners − Div  |  NCI = Prior + Attr_NCI − Div_NCI
CN GAAP:   Other Op Inc = Source 营业利润 − (Rev − COGS − Tax&Surcharge − OpEx − Impairment)
Quarterly: FY = SUM(Q1:Q4)  ← Q-level is the driver, FY is derived
YTD→Q:    Q1=YTD_Q1 · Q2=H1−Q1 · Q3=YTD_Q3−H1 · Q4=FY−YTD_Q3
ROIC:      NOPAT / AVERAGE(IC_curr, IC_prior)
Checks:    BS: TA−TLE=0 | CF: EndCash−BSCash=0 | NI: Model−Source=0 | Rev: Model−Source=0
```

---

## PITFALLS & DEFENSE INVENTORY

58+ pitfall index is now in **`references/pitfalls.md`** (categorized BLOCKER / WARNING / Doc-only). Each pitfall is mapped to either a PreToolUse Bash hook (preventive) or a `qc_suite.py` QC check (detective).

Severity model:
- **BLOCKER** (exit 2) — next session cannot start; durable marker not written
- **WARNING** (exit 1) — logged in JSON sidecar; session continues with caution
- **PASS** (exit 0) — clean

## GATE INVENTORY

Each session ends with `per_session_gate.py` running the right QC subset.

| Session | Gate entry | QC subset |
|---|---|---|
| 启动前 | hooks auto-fire | H1 hardcode_guard / H2 state_guard / H3 unit_guard / H5 granularity_guard |
| A 末尾 | `python scripts/per_session_gate.py --session A --xlsx <p>` | PF-1..9 (preflight, incl. REVENUE_BUILD flag) |
| A2 末尾 (conditional) | `python scripts/per_session_gate.py --session A2 --xlsx <p>` | QC-2 / 20 / 22 (Revenue_Build integrity + hist inline completeness) |
| B 末尾 | `python scripts/per_session_gate.py --session B --xlsx <p>` | QC-2 / 5 / 6 / 11 / 12 / 14 / 15 / 17 / 21 / 22 (IS→Revenue_Build link) |
| C 末尾 | `python scripts/per_session_gate.py --session C --xlsx <p>` | QC-2 / 6 / 7 + `_pending_links.json` written |
| D 末尾 | `python scripts/per_session_gate.py --session D --xlsx <p>` | QC-1 / 2 / 3 / 4 / 6 / 13 + `_pending_links.json` cleared |
| E 末尾 | `python scripts/per_session_gate.py --session E --xlsx <p>` | QC-1..22 full + data-validator |

Each session's startup runs `per_session_gate.py --verify-prev --session <X> --xlsx <p>` to check the previous gate's `GATE_<prev>_PASSED` marker in state.json.

See `references/gate-spec.md` for JSON schema and exit code conventions; `references/pitfalls.md` for the full mapping.
---

## R11 — Data Registry (_Registry sheet, SESSION E 完成后执行)

v1.1 note: state persistence has moved from the in-xlsx `_State` sheet to a `state.json` sidecar file (`<xlsx_stem>.state.json` alongside the xlsx). Auto-migrates from legacy `_State` sheet on first load. See `references/registry-integration.md` for the full SOP and `scripts/state_io.py` for the API.


**三表模型完成、QC Suite全部通过后，在同一 Excel 文件内建 `_Registry` sheet 登记数据来源。**

### 哪些行进 _Registry

| 数据类型 | 分类 | derived | 处理方式 |
|---|---|---|---|
| Raw_Info 从原始报告提取的历史值（Revenue、COGS、NI 等） | 原始数据 | FALSE | 登记 tier/source/timestamp |
| Assumptions tab 的输入参数（YoY%、Margin%、AR Days 等） | 原始数据 | FALSE | tier 按来源判断（analyst=T4，consensus=T3） |
| IS/BS/CF 中由公式算出的行（GP、EBIT、FCF、Net Debt 等） | 派生数据 | TRUE | 登记 formula + inputs |

### Tier 说明

| Tier | 含义 |
|---|---|
| T1 | 公司官方原始申报文件（年报、10-K、招股书） |
| T2 | 经审计/交易所数据库（Wind、Bloomberg raw feed） |
| T3 | 市场一致预期（卖方 consensus） |
| T4 | 分析师内部估算（自研假设） |

### 重点派生行必须登记（不可省略）

```
gross_profit, ebit, ebitda, net_income, adj_eps
cfo_total, cfi_total, cff_total, fcf
net_debt, ev, roic, roe
```

### 登记方式（SESSION E 最后步骤）

```python
# 批量登记 _Registry — 纯 openpyxl，无外部脚本依赖
import openpyxl, json
from datetime import date as today_date

# 创建或获取 _Registry sheet
if "_Registry" not in wb.sheetnames:
    ws_reg = wb.create_sheet("_Registry")
    ws_reg.append(["data_point_id", "value_cell", "tier", "source", "timestamp",
                   "data_category", "derived", "formula", "inputs"])
else:
    ws_reg = wb["_Registry"]

# 原始数据行：每个 Raw_Info 和 Assumptions 输入行各一条
raw_inputs = [
    # (id, value_cell, tier, source, timestamp, data_category)
    ("revenue_fy2023a", "=Raw_Info!C15", "T1", "Annual Report 2023 p.48", "2023-12-31", "revenue"),
    ("rev_yoy_fy2025e", "=Assumptions!B3", "T4", "analyst internal estimate",
     str(today_date.today()), "consensus_estimate"),
    # ... 补全所有 Raw_Info 和 Assumptions 行
]

# 派生数据行：所有 IS/BS/CF 计算行
derived_rows = [
    # (id, formula, inputs_list)
    ("gross_profit_fy2025e", "=IS!E8-IS!E9",   ["revenue_fy2025e", "cogs_fy2025e"]),
    ("ebit_fy2025e",         "=IS!E15",         ["gross_profit_fy2025e", "opex_fy2025e"]),
    ("fcf_fy2025e",          "=CF!E42-CF!E28",  ["cfo_fy2025e", "capex_fy2025e"]),
    # ... 补全所有关键派生行
]

for row in raw_inputs:
    ws_reg.append([row[0], row[1], row[2], row[3], row[4], row[5], "FALSE", "", ""])

for row in derived_rows:
    ws_reg.append([row[0], "", "", "", str(today_date.today()), "", "TRUE",
                   row[1], ",".join(row[2])])

wb.save(filepath)
print(f"✅ _Registry: {len(raw_inputs)} raw inputs + {len(derived_rows)} derived rows 登记完成")
```

### Validation Gate（_Registry 写完后强制执行）

```python
# 内置验证：不需要外部脚本
from datetime import datetime, date as today_date
issues_fail = []
issues_warn = []

for row in ws_reg.iter_rows(min_row=2, values_only=True):
    if not row[0]: continue
    data_id, value_cell, tier, source, timestamp, category, derived, formula, inputs = (list(row) + [None]*9)[:9]

    # derived 行必须有 formula
    if derived == "TRUE" and not formula:
        issues_fail.append(f"❌ FAIL: derived '{data_id}' has no formula")

    # raw 行必须有 source
    if derived == "FALSE" and not source:
        issues_fail.append(f"❌ FAIL: raw input '{data_id}' has no source")

    # 数据超过365天 → warn
    if timestamp:
        try:
            ts = datetime.strptime(str(timestamp)[:10], "%Y-%m-%d").date()
            age = (today_date.today() - ts).days
            if age > 365:
                issues_warn.append(f"🟡 WARN: '{data_id}' timestamp is {age} days old")
        except: pass

if issues_fail:
    for i in issues_fail: print(i)
    print(f"\n❌ FAIL: {len(issues_fail)} errors — MODEL_COMPLETE 不得写入")
else:
    for w in issues_warn: print(w)
    if issues_warn:
        print(f"🟡 {len(issues_warn)} stale items — 记录在 _model_log.md")
    write_state_key(wb, "REGISTRY_VALIDATED", "TRUE")
    wb.save(filepath)
    print("✅ Registry validated — REGISTRY_VALIDATED: TRUE written")
```

**写入顺序（SESSION E 末尾）：**
```
QC Suite (9 checks pass) → _Registry 登记 → Validation Gate → REGISTRY_VALIDATED: TRUE → MODEL_COMPLETE
```

---

任何需要读取 PDF 的场景（年报、季报、半年报、卖方报告、招股书等），
**禁止直接用 `web_fetch` 抓 PDF**——已知问题：内容截断、解析不全、遇 bot 检测返回空。

**推荐 PDF 读取方式：**

```
触发条件（满足任意一条）：
① URL 以 .pdf 结尾
② web_fetch 返回 403 / timeout / 空内容
③ IR 列表页面需要提取 PDF 链接
④ 需要读取年报/季报等完整财务原文

执行路径（任选其一）：
→ 使用 pdfplumber 本地解析（pip install pdfplumber）：
     import pdfplumber
     with pdfplumber.open("report.pdf") as pdf:
         text = "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())

→ 使用 curl + browser headers 绕过 bot 检测后再 pdfplumber 解析：
     curl -L -A "Mozilla/5.0" -o report.pdf "[URL]"

→ 若使用 Cowork 模式：调用 web-pdf-fetcher skill（如已安装）
```
