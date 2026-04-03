# 3-Statements-Ultra — Public Edition

**English** | [中文](README.zh.md)

**Version:** 4.7 · Public Edition
**Build date:** April 2026
**Compatibility:** Claude Code / Cowork (Anthropic)

---

## What This Skill Does

Builds a complete, institutional-grade **three-statement financial model** (Income Statement, Balance Sheet, Cash Flow Statement) in Excel from scratch — with full formula linkage, zero hardcoded forecast cells, and a 9-step QC validation suite.

Output quality targets: IPO prospectus / equity research initiating coverage.

Key features:
- **CN GAAP / IFRS / US GAAP** — all three accounting standards supported
- **Quarterly / Semi-annual / Annual** granularity auto-detected from source data
- **Formula-only forecasts** — every IS/BS/CF cell is an Excel formula, never a hardcoded number
- **State persistence** — 5-session build with full resume-after-interruption support
- **9 QC checks** — BS CHECK, CF CHECK, NI CHECK, REV CHECK, hardcode scan, NCI continuity, formula integrity, gridlines, Summary links
- **Data registry** — built-in lineage tracking for every input and derived number

---

## Prerequisites

```bash
pip install openpyxl yfinance pandas
pip install notebooklm   # optional — only if you use NotebookLM as a data source
```

Python 3.9+ required.

---

## Installation

### Cowork / Claude Code (skill file)

1. Download `3-statements-ultra-public.skill`
2. In Cowork: **Settings → Skills → Install from file** → select the `.skill` file
3. In Claude Code CLI: place the unzipped folder under your `.claude/skills/` directory

### Manual (Claude Code)

```bash
# Unzip the skill
unzip 3-statements-ultra-public.skill -d ~/.claude/skills/3-statements-ultra/
```

---

## Recommended Setup — User Preference

**Before your first session**, add the following to your Claude user preferences (Settings → Profile → Custom Instructions, or your `CLAUDE.md` file). This prevents state loss after context compaction mid-session:

```
## 3-Statements-Ultra — Compaction Recovery Protocol
When I am building a 3-statement financial model using the 3-statements-ultra skill,
after ANY context compaction event, you MUST:
1. Re-read the 3-statements-ultra SKILL.md before writing any code
2. Open the Excel model file and read the _State tab — determine exact resume point
3. Read _model_log.md — recover prior session outputs (key totals, check results)
4. Read _pending_links.json — check if BS→CF back-fill is pending
5. Run RAW_MAP + ASM_MAP spot-check before using any row numbers
6. Never hardcode any IS/BS/CF forecast cell — every cell must be a string formula
7. Resume from the next incomplete step only — never re-run completed sections
Do not rely on conversation memory for row numbers or intermediate calculation results.
Disk state (_State, _model_log.md, _pending_links.json) is always authoritative.
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
2. **One-time OAuth auth** (~5 min, done once):

```bash
pip install notebooklm
python3 -c "
import asyncio
from notebooklm import NotebookLMClient
async def auth():
    async with await NotebookLMClient.from_storage() as client:
        nbs = await client.notebooks.list()
        print(f'Auth OK — {len(nbs)} notebooks accessible')
asyncio.run(auth())
"
# Browser opens → Google login → session saved to ~/.notebooklm/storage_state.json
# Re-auth needed only when session expires (~7 days)
```

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
[_State]           ← session metadata (delete after MODEL_COMPLETE)
```

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
- **Internal data pipeline references** — references to a proprietary external `data-validator` script replaced with a self-contained openpyxl implementation in R11.

All core modeling logic, QC checks, templates, and session protocols are unchanged.

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

**5. Nine QC checks must pass before the model is marked complete.**

The model cannot be finished without all of BS CHECK = 0, CF CHECK = 0, NI CHECK ≈ 0, REV CHECK = 0, a hardcode scan across all forecast columns, NCI continuity check, formula integrity spot-check, gridlines-off check, and Summary zero-hardcode check. The official skill has no equivalent QC gate.

**6. NCI is always rolled forward.**

If a company has minority interest, NCI on the balance sheet must compound each period: `NCI_end = NCI_prior + Attr_to_NCI − NCI_Dividends`. Setting forecast NCI to zero — or flat at the last historical value — is a common error that makes both the BS and the IS attribution wrong. This skill enforces the roll-forward and validates it in QC-5.

### Summary table

| | `3-statements-ultra` | `financial-analysis:3-statements` (official) |
|---|---|---|
| Cash derivation | `= CF Ending Cash` (always) | Plugged from BS residual |
| Revenue structure | Per-segment, independent drivers | Single line |
| Forecast cells | 100% Excel formulas | Mix of formulas and hardcodes |
| CN GAAP support | Native (R8 plug, 营业利润 reconciliation) | Generic template |
| QC validation | 9 mandatory checks | None |
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
