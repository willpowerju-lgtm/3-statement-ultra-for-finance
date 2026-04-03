3-Statements-Ultra — Public Edition
Version: 4.7 · Public Edition
Build date: April 2026
Compatibility: Claude Code / Cowork (Anthropic)

What This Skill Does
Builds a complete, institutional-grade three-statement financial model (Income Statement, Balance Sheet, Cash Flow Statement) in Excel from scratch — with full formula linkage, zero hardcoded forecast cells, and a 9-step QC validation suite.
Output quality targets: IPO prospectus / equity research initiating coverage.
Key features:

CN GAAP / IFRS / US GAAP — all three accounting standards supported
Quarterly / Semi-annual / Annual granularity auto-detected from source data
Formula-only forecasts — every IS/BS/CF cell is an Excel formula, never a hardcoded number
State persistence — 5-session build with full resume-after-interruption support
9 QC checks — BS CHECK, CF CHECK, NI CHECK, REV CHECK, hardcode scan, NCI continuity, formula integrity, gridlines, Summary links
Data registry — built-in lineage tracking for every input and derived number


Prerequisites
bashpip install openpyxl yfinance pandas
pip install notebooklm   # optional — only if you use NotebookLM as a data source
Python 3.9+ required.

Installation
Cowork / Claude Code (skill file)

Download 3-statements-ultra-public.skill
In Cowork: Settings → Skills → Install from file → select the .skill file
In Claude Code CLI: place the unzipped folder under your .claude/skills/ directory

Manual (Claude Code)
bash# Unzip the skill
unzip 3-statements-ultra-public.skill -d ~/.claude/skills/3-statements-ultra/

Recommended Setup — User Preference
Before your first session, add the following to your Claude user preferences (Settings → Profile → Custom Instructions, or your CLAUDE.md file). This prevents state loss after context compaction mid-session:
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

Quick Start
Just say one of these trigger phrases and the skill takes over:
三表模型
financial model
3-statement model
建模
从零建模
build a 3-statement model for [company name]
The skill will ask you which data sources you have available, then guide you through the 5 sessions.

5-Session Build Flow
SessionTab(s) BuiltWhat HappensTimeARaw_Info + AssumptionsData extraction from NLM / Excel / Web; granularity detection; assumptions setup15–30 minBISIncome Statement, all segments, CN GAAP R8 plug, NCI15–20 minCBSBalance Sheet, Cash as placeholder; writes _pending_links.json15–20 minDCFCash Flow, year-by-year; R3 Others plug; BS Cash back-fill; 9 QC checks15–25 minEReturns + Cross_Check + SummaryROIC/ROE/DuPont; assumption validation; linked Summary tab15–20 min
Each session is fully independent — you can close the chat between sessions. State is stored in the Excel _State tab and two sidecar files (_model_log.md, _pending_links.json).

Data Sources
SourceToken CostSetupVerdictNotebookLM notebook (filings pre-loaded)Very low — NLM absorbs PDFs, Claude only reads answersOne-time OAuth (5 min)✅ Best pathExcel (historical IS/BS/CF) + short PDF excerptsLowNone✅ GoodWeb fallback (Sina / Yahoo Finance)LowNone✅ FallbackFull PDF upload (annual report, prospectus)🔴 Very high — 200+ page filings burn through context fastNone⚠️ Avoid on Pro
NotebookLM one-time auth setup (~5 min):
bashpip install notebooklm
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
If you skip NLM: upload a structured Excel with 3–5 years of IS/BS/CF as your primary source, and supplement with short PDF excerpts (earnings release key pages, not full filings). This keeps token consumption low while still getting good data quality.

Output — Excel File Structure
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

Key Rules (Summary)
RuleDescriptionRule ZeroEvery IS/BS/CF forecast cell must be an Excel formula string — never a float or intR3 Others plugOnly permitted non-cash CF plug; keeps BS CHECK and CF CHECK both = 0R6 Cash lastBS Cash is always 0 placeholder until SESSION D back-fills from CF Ending CashCode block limitMax 400 lines per Python block; execute before writing the nextOne sourceAfter Raw_Info is complete, all data flows via =Raw_Info! links only

Frequently Asked Questions
Q: Can I use this without NotebookLM?
Yes. NotebookLM is optional. If you don't have it, the skill falls back to Web (Sina / Yahoo Finance) as the primary data source.
Q: What if I only have annual data but the company reports quarterly?
The skill auto-detects granularity using yfinance. If quarterly data is available from any source, it uses quarterly. You can override with a manual answer during Phase 0.
Q: Can I pause mid-session and resume later?
Yes. Every code block writes a progress marker to the _State tab in Excel. The startup protocol at the beginning of each session automatically finds the last completed step and resumes from there.
Q: Why do I need to run 5 separate sessions instead of one?
Quarterly IS models produce 300+ lines of Python code per section. A single large script hits the LLM output cap and is silently truncated — the Excel file ends up partially written with no error. The 5-session, one-section-at-a-time approach prevents this entirely.
Q: What if BS CHECK ≠ 0 after Session C?
This is expected and correct. BS Cash is a placeholder (0) until Session D back-fills it from CF Ending Cash. Do not try to force-balance BS in Session C.
Q: Does this work for US GAAP companies (e.g., NYSE/NASDAQ-listed)?
Yes. Use ticker = "TICKER" format (e.g. "AAPL") in Phase 0. The skill detects IFRS/US GAAP from the source and applies the correct IS template.

What Was Removed in the Public Edition
This is a sanitized version of the original private skill. The following have been removed or replaced:

Bark push notification module — bark-notify.md and all bark() function calls removed. The original skill sent push notifications to a private device during long-running sessions; this is not needed for general use.
Internal session paths — hardcoded internal deployment paths (e.g. Python package install locations specific to the original environment) replaced with standard pip install instructions.
Internal data pipeline references — references to a proprietary external data-validator script replaced with a self-contained openpyxl implementation in R11.

All core modeling logic, QC checks, templates, and session protocols are unchanged.

License
This skill is shared for personal and research use. No warranty is provided. Financial models produced by this skill should be independently verified before use in investment decisions.
