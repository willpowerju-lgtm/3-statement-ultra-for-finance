# 3-Statements-Ultra — Public Edition

**English** | [中文](README.zh.md)

**Version:** 5.0 · Public Edition
**Build date:** May 2026 — v5.0 ships the **three-layer defense system** (preventive hooks + 19-QC gate suite + state.json sidecar)
**Compatibility:** Claude Code / Cowork (Anthropic)

---

## What This Skill Does

Builds a complete, institutional-grade **three-statement financial model** (Income Statement, Balance Sheet, Cash Flow Statement) in Excel from scratch — with full formula linkage, zero hardcoded forecast cells, and a **19-check QC gate suite enforced at the end of every session**.

Output quality targets: IPO prospectus / equity research initiating coverage.

Key features:
- **CN GAAP / IFRS / US GAAP** — all three accounting standards supported
- **Quarterly / Semi-annual / Annual** granularity auto-detected from source data
- **Formula-only forecasts** — every IS/BS/CF cell is an Excel formula, never a hardcoded number
- **State persistence** — 5-session build with full resume-after-interruption support; state stored in a `state.json` sidecar file (auto-migrates from legacy in-xlsx `_State` sheet)
- **19 QC checks with BLOCKER / WARNING severity tiers** — BS / CF / NI / REV reconciliation, forecast-cell hardcode scan, NCI continuity, formula integrity, R3 Others/CFO dual-threshold, BS Cash back-fill, segment-sum vs Total Revenue, WC days sanity, tax rate consistency, format/gridlines/font/zoom checks, Summary linkage, and more
- **Preventive PreToolUse hooks** (optional, Claude Code only) — Rule Zero hardcode interception, RAW_MAP spot-check, unit/granularity prerequisite enforcement, A-share/US ticker → Quarterly enforcement
- **Per-session gate enforcement** — each session ends with a `per_session_gate.py` call that writes a durable `GATE_<X>_PASSED` marker only if QC subset passes; next session refuses to start without the previous marker
- **Data registry** — built-in lineage tracking for every input and derived number

---

## Prerequisites

```bash
pip install openpyxl yfinance pandas
pip install "notebooklm-py[browser]" && playwright install chromium   # optional — only if you use NotebookLM as a data source (see "Recommended — Upgrade NLM" below)
```

Python 3.9+ required.

---

## Installation

The repo ships the skill in two forms: an unzipped `3-statements-ultra/` folder (for Claude Code) and a `3-statements-ultra-public.skill` zip bundle (for Cowork). Pick whichever matches your client.

### Claude Code — recommended (`git clone` + symlink)

This is the most convenient path: `git pull` picks up future updates automatically, no re-install needed.

```bash
# 1. Clone anywhere you like (not inside ~/.claude/skills/)
git clone https://github.com/willpowerju-lgtm/3-statement-ultra-for-finance.git
cd 3-statement-ultra-for-finance

# 2. Symlink the skill folder into Claude Code's skills directory
# Linux / macOS:
ln -s "$PWD/3-statements-ultra" ~/.claude/skills/3-statements-ultra

# Windows (PowerShell — needs admin OR Developer Mode enabled):
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\3-statements-ultra" -Target "$PWD\3-statements-ultra"
```

**Verify Claude Code picked it up:**

```bash
# In any Claude Code session:
/skills
# Expected: "3-statements-ultra" appears in the list
```

Then just trigger it from any session:

```
建个三表模型 for BABA
# or
build a 3-statement model for Tencent (0700.HK)
```

**Updating later:** `cd 3-statement-ultra-for-finance && git pull` — the symlink means Claude Code sees the new version immediately.

### Claude Code — alternative (plain copy, no symlink)

If you can't or don't want to create symlinks:

```bash
git clone https://github.com/willpowerju-lgtm/3-statement-ultra-for-finance.git
cp -r 3-statement-ultra-for-finance/3-statements-ultra ~/.claude/skills/
```

You'll need to re-copy when the skill updates.

### Cowork (`.skill` zip bundle)

1. Download `3-statements-ultra-public.skill` from this repo (raw file or Releases).
2. In Cowork: **Settings → Skills → Install from file** → select the `.skill` file.

### Manual unzip (legacy Claude Code path)

Still works if you prefer a zip over the folder:

```bash
unzip 3-statements-ultra-public.skill -d ~/.claude/skills/3-statements-ultra/
```

---

## Recommended Setup — User Preference

**Before your first session**, add the Compaction Recovery Protocol below to your Claude user preferences. This prevents state loss if context compaction fires *mid-session* — skill auto-load only re-injects SKILL.md when a trigger phrase hits, so a compaction that happens while you're already deep in the model won't re-load it on its own. Without this protocol, the LLM may try to rebuild row numbers from memory and silently corrupt the model.

Where to paste it depends on your client:

- **Claude Code** → append to `~/.claude/CLAUDE.md` (or a project-level `CLAUDE.md`).
- **Cowork** → Settings → Profile → Custom Instructions.
- **Claude.ai** (web/desktop) → Settings → Profile → Custom Instructions.

```
## 3-Statements-Ultra — Compaction Recovery Protocol
When I am building a 3-statement financial model using the 3-statements-ultra skill,
after ANY context compaction event, you MUST:
1. Re-read the 3-statements-ultra SKILL.md before writing any code
2. Read the state.json sidecar (auto-migrates from legacy _State sheet) — determine exact resume point
3. Read _model_log.md — recover prior session outputs (key totals, check results)
4. Read _pending_links.json — check if BS→CF back-fill is pending
5. Run RAW_MAP + ASM_MAP spot-check before using any row numbers (H2 hook does this automatically when you reference the maps)
6. Never hardcode any IS/BS/CF forecast cell — every cell must be a string formula (H1 hook will block this before bash executes)
7. Resume from the next incomplete step only — never re-run completed sections
Do not rely on conversation memory for row numbers or intermediate calculation results.
Disk state (state.json, _model_log.md, _pending_links.json) is always authoritative.
```

---

## Quick Start

Just say one of these trigger phrases and the skill takes over:

```
三表模型
financial model
3-statement model
建模
从零建模
build a 3-statement model for [company name]
```

The skill will ask you which data sources you have available, then guide you through the 5 sessions.

---

## 5-Session Build Flow

| Session | Tab(s) Built | What Happens | Time |
|---------|-------------|--------------|------|
| **A** | Raw_Info + Assumptions | Data extraction from NLM / Excel / Web; granularity detection; assumptions setup | 15–30 min |
| **B** | IS | Income Statement, all segments, CN GAAP R8 plug, NCI | 15–20 min |
| **C** | BS | Balance Sheet, Cash as placeholder; writes `_pending_links.json` | 15–20 min |
| **D** | CF | Cash Flow, year-by-year; R3 Others plug; BS Cash back-fill; 9 QC checks | 15–25 min |
| **E** | Returns + Cross_Check + Summary | ROIC/ROE/DuPont; assumption validation; linked Summary tab | 15–20 min |

Each session is **fully independent** — you can close the chat between sessions. State is stored in the Excel `_State` tab and two sidecar files (`_model_log.md`, `_pending_links.json`).

---

## Data Sources

| Priority | Source | Setup | Token Cost | Notes |
|----------|--------|-------|-----------|-------|
| ✅ **1st choice** | **Excel** (historical IS/BS/CF already structured) | None | Low | Fastest to start — upload and go |
| ✅ **2nd choice** | **NotebookLM notebook** (annual reports / filings pre-loaded) | Two steps (see below) | Very low | Higher assumption quality — worth the setup |
| ✅ **Fallback** | **Web** (Sina / Yahoo Finance) | None | Low | Automatic — always runs as cross-check layer |
| ⚠️ **Avoid on Pro** | **Full PDF upload** (complete annual report, prospectus) | None | 🔴 Very high | 200+ page filings consume context fast |

**Why Excel first?** No auth, no pre-loading — just upload a spreadsheet with 3–5 years of IS/BS/CF and the skill reads it directly. Supplement with short PDF excerpts (earnings release key pages) if you have them.

**Why NLM second — and why it's worth it?** NotebookLM's 12-question parallel batch extracts far richer operational intelligence than structured financials alone: segment drivers, management guidance, capex plans, working capital commentary, competitive dynamics. This directly feeds the Assumptions tab, resulting in meaningfully better forecast quality. The tradeoff is a two-step setup:

1. **Upload your filings into NotebookLM first** — annual reports, quarterly reports, prospectus, or any sell-side research you find useful. NLM handles the PDF parsing so Claude never has to read the raw files.
2. **One-time OAuth auth** (~5 min, done once). We use [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) — an unofficial Python client for NotebookLM:

```bash
pip install "notebooklm-py[browser]"
playwright install chromium

# CLI auth — browser opens, Google login, session saved locally
notebooklm login

# Verify it works
python3 -c "
import asyncio
from notebooklm import NotebookLMClient
async def check():
    async with await NotebookLMClient.from_storage() as client:
        nbs = await client.notebooks.list()
        print(f'Auth OK — {len(nbs)} notebooks accessible')
asyncio.run(check())
"
# Re-auth when session expires (~7 days) by re-running `notebooklm login`
```

> ⚠️ `notebooklm-py` is unofficial and relies on undocumented Google APIs that may change without notice. It's fine for personal research / prototyping (which is our use case here), but don't build production pipelines on it.

---

## Output — Excel File Structure

```
[1] Summary        ← business profile, financial highlights, catalysts, risks
[2] Assumptions    ← all forecast drivers (single source of truth)
[3] IS             ← Income Statement
[4] BS             ← Balance Sheet
[5] CF             ← Cash Flow (indirect method)
[6] Returns        ← ROIC / ROE / ROA / DuPont
[7] Cross_Check    ← assumption validation log vs external sources
[8] Raw_Info       ← extracted historical data (never re-read after build)
[_Registry]        ← data lineage registry (built in Session E)
```

Sidecar files (alongside the xlsx in the same folder):
```
<model>.state.json            ← session metadata, GATE_<X>_PASSED markers, all
                                row/column maps (replaces in-xlsx _State sheet
                                as of v1.1; legacy _State auto-migrates)
_model_log.md                 ← append-only checkpoint log of every tab section
_pending_links.json           ← deferred BS->CF references (written by Session C,
                                consumed and cleared by Session D)
<model>.preflight.json        ← Session A gate sidecar report (8 PF checks)
<model>.qc_<X>.json           ← Session B/C/D/E gate sidecar reports (QC findings)
```

---

## v5.0 Defense Layers

Three-layer architecture to catch model defects early. The further left a defect is caught, the less rework it costs.

### Layer 1 — PreToolUse Hooks (optional, preventive)

Four self-gated PreToolUse Bash hooks intercept common mistakes *before* the bash command runs:

| Hook | Catches | Why preventive matters |
|---|---|---|
| `three_stmt_hardcode_guard.py` | `ws_is['E5'].value = 0.30` and alias variants (`ws = wb['IS']; ws['E5'].value = 0.30`) | Rule Zero violation — once written, entire forecast tab is dead |
| `three_stmt_state_guard.py` | RAW_MAP / ASM_MAP row-number drift after Raw_Info or Assumptions is edited | Stale row maps silently corrupt session outputs |
| `three_stmt_unit_guard.py` | Writes to Raw_Info before UNIT + IS_GRANULARITY are locked in state.json | Wrong unit = silent 100× error invisible until QC |
| `three_stmt_granularity_guard.py` | A-share / US ticker set to non-Quarterly granularity | COL_MAP structure dependent on granularity — wrong choice = rebuild |

Hooks live in `3-statements-ultra/hooks/`. To enable on Claude Code, symlink or copy into `~/.claude/hooks/`:

```bash
ln -sf "$PWD/3-statements-ultra/hooks/"three_stmt_*.py ~/.claude/hooks/
```

Hooks are self-gated by context regex — they only fire when bash commands reference 3-statements-ultra concepts (RAW_MAP / Raw_Info / _State / IS_GRANULARITY / etc.). Other skills are unaffected.

### Layer 2 — Gate Scripts (detective, severity-tiered)

Each session ends with `python scripts/per_session_gate.py --session <A|B|C|D|E> --xlsx <path>`. The gate writes a durable `GATE_<X>_PASSED` marker to `state.json` only if its QC subset returns BLOCKER=0. Next session refuses to start without the previous marker.

| Session | Gate runs | Writes on PASS |
|---|---|---|
| **A** | `preflight_check.py` 8-item PF | `GATE_A_PASSED` |
| **B** | `qc_suite.py --full --tabs IS` (QC-2/5/6/11/12/14/15/17) | `GATE_B_PASSED` |
| **C** | `qc_suite.py --full --tabs BS` + `_pending_links.json` written | `GATE_C_PASSED` |
| **D** | `qc_suite.py --full --tabs CF` (QC-1/2/3/4/6/13) + `_pending_links.json` cleared | `GATE_D_PASSED` |
| **E** | `qc_suite.py --full --tabs all` (QC-1..19) + data-validator | `GATE_E_PASSED` then `MODEL_COMPLETE` |

Severity tiers (per `references/gate-spec.md`):
- **BLOCKER** (exit 2) — durable marker not written; next session can't start
- **WARNING** (exit 1) — marker written with `(with warnings)` suffix; session proceeds
- **PASS** (exit 0) — clean

Session startup validates the previous gate's marker:
```bash
python scripts/per_session_gate.py --verify-prev --session B --xlsx <model.xlsx>
# exit 0 if GATE_A_PASSED present; exit 2 otherwise
```

### Layer 3 — Reference Docs

| File | Contents |
|---|---|
| `references/pitfalls.md` | 52-item pitfall index, each mapped to a Layer 1 hook or Layer 2 QC |
| `references/gate-spec.md` | Severity rubric, JSON sidecar schema, exit-code conventions, implementation status |
| `references/format-spec.md` | QC-14..19 format baseline (Book Antiqua, gridlines off, FF0070C0 input blue, accounting number formats) |
| `references/registry-integration.md` | Detailed R11 Data Registry SOP for the final Session E acceptance step |

---

## Key Rules (Summary)

| Rule | Description |
|------|-------------|
| **Rule Zero** | Every IS/BS/CF forecast cell must be an Excel formula string — never a float or int |
| **R3 Others plug** | Only permitted non-cash CF plug; keeps BS CHECK and CF CHECK both = 0 |
| **R6 Cash last** | BS Cash is always 0 placeholder until SESSION D back-fills from CF Ending Cash |
| **Code block limit** | Max 400 lines per Python block; execute before writing the next |
| **One source** | After Raw_Info is complete, all data flows via `=Raw_Info!` links only |

---

## Frequently Asked Questions

**Q: Can I use this without NotebookLM?**
Yes. NotebookLM is optional. If you don't have it, the skill falls back to Web (Sina / Yahoo Finance) as the primary data source.

**Q: What if I only have annual data but the company reports quarterly?**
The skill auto-detects granularity using yfinance. If quarterly data is available from any source, it uses quarterly. You can override with a manual answer during Phase 0.

**Q: Can I pause mid-session and resume later?**
Yes. Every code block writes a progress marker to the `_State` tab in Excel. The startup protocol at the beginning of each session automatically finds the last completed step and resumes from there.

**Q: Why do I need to run 5 separate sessions instead of one?**
Quarterly IS models produce 300+ lines of Python code per section. A single large script hits the LLM output cap and is silently truncated — the Excel file ends up partially written with no error. The 5-session, one-section-at-a-time approach prevents this entirely.

**Q: What if BS CHECK ≠ 0 after Session C?**
This is expected and correct. BS Cash is a placeholder (0) until Session D back-fills it from CF Ending Cash. Do not try to force-balance BS in Session C.

**Q: Does this work for US GAAP companies (e.g., NYSE/NASDAQ-listed)?**
Yes. Use `ticker = "TICKER"` format (e.g. `"AAPL"`) in Phase 0. The skill detects IFRS/US GAAP from the source and applies the correct IS template.

---

## What Was Removed in the Public Edition

This is a sanitized version of the original private skill. The following have been removed or replaced:

- **Bark push notification module** — `bark-notify.md` and all `bark()` function calls removed. The original skill sent push notifications to a private device during long-running sessions; this is not needed for general use.
- **Internal session paths** — hardcoded internal deployment paths (e.g. Python package install locations specific to the original environment) replaced with standard `pip install` instructions.
- **`WorkflowState` / `SessionLog` integration blocks** — the original skill's top and bottom blocks hooked into an internal workflow/audit-log system (fixed paths under `/tmp/repo/session-log/src` and `~/.claude/skills/session-log/`). These have no meaning outside that environment and were removed. The 5-session build flow now stores state in a `state.json` sidecar file plus `_model_log.md` and `_pending_links.json`.
- **Internal tickers in examples** — portfolio-specific tickers (e.g. A-share / HK names the original author was covering) replaced with neutral public-company tickers (`BABA`, `0700.HK`, `600519.SS`, `PDD`).
- **Internal review attribution** — internal cross-model audit annotations stripped from code comments; the underlying defect fixes are kept.

What's **included** in v5.0 (was not in earlier public editions):

- **`scripts/qc_suite.py`** — 19 QC checks (was 9 inline in session-e.md; now extracted to a callable script with BLOCKER/WARNING severity tiers and JSON sidecar output)
- **`scripts/preflight_check.py`** — Session A 8-item PF gate
- **`scripts/per_session_gate.py`** — session dispatcher + `GATE_<X>_PASSED` durable markers + `--verify-prev` startup check
- **`scripts/state_io.py`** — state.json sidecar I/O with automatic migration from legacy in-xlsx `_State` sheet
- **`hooks/three_stmt_*.py`** — 4 optional PreToolUse Bash hooks (Rule Zero / state spot-check / unit prereq / ticker granularity)
- **`references/{pitfalls, gate-spec, format-spec, registry-integration}.md`** — full pitfall index, severity rubric + JSON schema, format baseline, and R11 Data Registry SOP

All core modeling logic, templates, and session protocols are unchanged.

---

## vs. the Official `financial-analysis:3-statements` Skill

There is an official 3-statement skill available in the Claude marketplace (`financial-analysis:3-statements`). The two skills serve different purposes and have meaningfully different quality standards. Here is an honest comparison.

### What the official skill does well

It is fast. If you already have a partially filled Excel template and just need the formulas linked up, the official skill does that job in a single session without setup. It works well for quick, rough-cut models where speed matters more than structural correctness.

### Where this skill differs — and why it matters for serious work

**1. Cash is never plugged.**

This is the most fundamental difference. The official skill calculates Cash by plugging: `Cash = Total Liabilities + Equity − Non-Cash Assets`. This forces the balance sheet to balance, but it is structurally wrong. Cash derived this way has no connection to actual cash generation — it is a residual that will be wildly incorrect whenever any other balance sheet item is even slightly off. In a real model, Cash must equal CF Ending Cash, derived from the full cash flow waterfall. This skill enforces that rule unconditionally: Cash is left as a placeholder in Session C and back-filled from the CF statement in Session D, period.

**2. Revenue is split by segment with independent drivers.**

The official skill treats revenue as a single line. This skill builds each business segment as an independently driven row — separate YoY growth %, separate volume × ASP structure if applicable, separate seasonality percentages for quarterly models. A single-line revenue assumption is adequate for a back-of-envelope; it is not adequate for an equity research or IC memo-quality model where you need to stress individual product lines or geography.

**3. Every forecast cell is an Excel formula — no exceptions.**

Rule Zero of this skill is that no forecast cell in IS/BS/CF may hold a hardcoded number. Every cell must be a string formula referencing the Assumptions tab or another cell. The official skill routinely writes numeric values directly into forecast cells, which means the model breaks silently the moment any assumption changes — the cell does not recalculate because it contains a number, not a formula.

**4. CN GAAP is modelled natively.**

Chinese GAAP income statements have items between 营业总成本 and 营业利润 (其他收益, 信用减值损失, 资产减值损失, etc.) that are not present in IFRS or US GAAP. This skill handles them with a dedicated R8 plug row that captures the residual between source 营业利润 and model-derived EBIT. Ignoring these items — as a generic template will — produces systematically wrong EBIT for A-share and HK-listed CN GAAP companies.

**5. Nineteen QC checks must pass before the model is marked complete (v5.0).**

The model cannot be finished without all 19 QCs passing: numeric reconciliation (BS CHECK, CF CHECK, NI CHECK, REV CHECK read from the model's own data_only-computed cells), forecast-cell hardcode scan, NCI continuity, formula integrity spot-check, _State 14-key integrity, R3 Others/CFO dual threshold (15% WARN / 30% BLOCKER), BS Cash back-fill, segment-sum vs Total Revenue equality, working-capital-days sanity vs 3-year historical average, effective tax rate consistency, R3 Others historical source check, and format/gridlines/font/number-format/zoom/freeze-panes checks. Each session ends with a gate that writes a durable marker only on PASS; the next session refuses to start without it. The official skill has no equivalent QC gate.

**6. NCI is always rolled forward.**

If a company has minority interest, NCI on the balance sheet must compound each period: `NCI_end = NCI_prior + Attr_to_NCI − NCI_Dividends`. Setting forecast NCI to zero — or flat at the last historical value — is a common error that makes both the BS and the IS attribution wrong. This skill enforces the roll-forward and validates it in QC-5.

### Summary table

| | `3-statements-ultra` | `financial-analysis:3-statements` (official) |
|---|---|---|
| Cash derivation | `= CF Ending Cash` (always) | Plugged from BS residual |
| Revenue structure | Per-segment, independent drivers | Single line |
| Forecast cells | 100% Excel formulas | Mix of formulas and hardcodes |
| CN GAAP support | Native (R8 plug, 营业利润 reconciliation) | Generic template |
| QC validation | 19 mandatory checks with BLOCKER/WARNING tiers | None |
| Preventive hooks | 4 PreToolUse hooks (Rule Zero, state, unit, granularity) | None |
| Per-session gates | Each session writes durable marker; next session refuses to start without it | None |
| NCI roll-forward | Enforced | Not guaranteed |
| Quarterly granularity | Full (35 IS columns per year) | Annual only |
| Setup required | 5 sessions, ~1–2 hours total | Single session |
| Best for | IPO / equity research quality models | Quick template population |

### When to use which

Use the official skill if you need a rough model in 20 minutes and the numbers do not need to hold up to scrutiny.

Use this skill if the model will be used in an IC memo, a research note, an investor presentation, or any context where someone will actually check whether it balances — and whether the assumptions flow through correctly.

---

## License

This skill is shared for personal and research use. No warranty is provided. Financial models produced by this skill should be independently verified before use in investment decisions.
