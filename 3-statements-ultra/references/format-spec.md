# Format Spec — QC-14..19 Baseline

Format conventions extracted from a representative institutional A-share IPO 3-statement model (quarterly disclosure, RMB-denominated, Book Antiqua–styled). This is the reference standard for `qc_suite.py` format checks (QC-8 / QC-14 / QC-15 / QC-16 / QC-17 / QC-18 / QC-19).

## Workbook overview

- Currency: RMB (m, 百万元)
- Granularity: Quarterly (A-share, 季报披露)
- Typical tabs of interest: `IS & drivers`, `BS`, `CFS`, `Comps`, `Historical IS`, `Historical BS`, `Historical CFS`

## Sheet view (QC-8, QC-18, QC-19)

| Tab | Gridlines | Zoom | Freeze |
|---|---|---|---|
| IS & drivers | OFF | 70% | Z24 |
| BS | OFF | 64% | D51 |
| CFS | OFF | 85% | B3 |
| Comps | OFF | 70% | G52 |
| Historical IS | OFF | 70% | AI4 |
| Historical BS | OFF | 70% | AB53 |
| Historical CFS | OFF | 55% | AJ4 |

Acceptable ranges:
- **Gridlines** — must be OFF on all financial tabs (QC-8 WARNING)
- **Zoom** — 60–90% (QC-18 WARNING)
- **Freeze panes** — any anchor; just needs to exist (QC-19 WARNING)

## A1 unit declaration (QC-14, BLOCKER)

- `IS & drivers!A1` = `"Unit: m RMB"`
- `BS!A1` = `"Unit: m RMB"`
- `CFS!A1` = `"Unit: m RMB"`

Regex pattern enforced (accepts both English and Chinese unit syntax):
```
(?:Unit|单位)\s*[:：]?\s*(?:m|mn|百万|千万|千|万|百萬|千萬).{0,30}?(?:RMB|CNY|USD|HKD|EUR|JPY|元)
```

## Fonts (QC-15, WARNING)

Typical distribution on representative model:

| Sheet | Dominant fonts |
|---|---|
| IS & drivers | Book Antiqua 10pt normal / Book Antiqua 10pt italic / 等线 11pt |
| BS | Book Antiqua 11pt normal / 等线 11pt |
| CFS | 等线 11pt / Book Antiqua 10pt normal / Book Antiqua 10pt bold |

Rule: ≥ 90% of populated cells must use a font in `{Book Antiqua, 等线}`. Other allowed fallbacks: Arial, 微软雅黑, 宋体, Calibri.

## Cell colors (QC-16, WARNING)

| Hex | Meaning |
|---|---|
| `FF0070C0` | **Input / hardcoded number** (blue text — the canonical Assumptions input color) |
| `FF006BBB` | Input variant (slightly different blue) |
| `FFFFFF00` | Highlight / review-needed (yellow fill) |
| `FF002060` | Header band (dark navy fill) |
| `FFFFFFFF` | Background blank cells (white fill) |

Rule:
- **Input cells in Assumptions tab** should use blue text close to `FF0070C0` (RGB distance < 30)
- **Non-input cells should NOT use blue text** — blue is reserved for hardcoded inputs only

## Number formats (QC-17, WARNING)

Dominant formats by tab (in representative model):

| Tab | Format | Use case |
|---|---|---|
| IS & drivers | `_ * #,##0_ ;_ * \-#,##0_ ;_ * "-"??_ ;_ @_ ` | thousands accounting |
| IS & drivers | `0%` / `0.0%` | percent |
| BS | `#,##0` | thousands integer |
| BS | `_ * #,##0_ ;_ * \-#,##0_ ;_ * "-"??_ ;_ @_ ` | thousands accounting |
| CFS | `_ * #,##0_ ;_ * \-#,##0_ ;_ * "-"??_ ;_ @_ ` | thousands accounting |
| Comps | `_ * #,##0.00_ ;_ * \-#,##0.00_ ;_ * "-"??_ ;_ @_ ` | thousands w/ 2 decimal |

Rule: ≥ 70% of numeric cells in financial tabs must use:
- Accounting format containing `#,##0` or `_ * #,##0` patterns
- OR percentage formats (`0%`, `0.0%`, `0.00%`)
- OR plain decimal formats (`0`, `0.0`, `0.00`) for cells with `|value| < 100`

Per SKILL.md §6G:
- `value < 100` → 2 decimal places
- `value ≥ 100` → integer with comma separator
- Percent → 1 decimal place

## Notes

1. The `等线` font appears alongside Book Antiqua because it's Excel's default Chinese-script fallback. Both are acceptable.
2. Some tabs (e.g. data-import or pasted-from-web sources) may use `Google Sans Text 8pt` — these are not core model tabs and are excluded from QC-15 via tab-name filter.
3. The blue-text input convention (`FF0070C0`) is critical for the Rule Zero contract: blue = hardcoded input cell (allowed in Assumptions/Raw_Info), black = formula (required in IS/BS/CF forecast & historical).
