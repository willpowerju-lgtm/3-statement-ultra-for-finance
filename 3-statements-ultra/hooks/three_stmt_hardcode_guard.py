#!/usr/bin/env python3
"""
PreToolUse Bash hook — 3-Statements Rule Zero Hardcode Guard

3-statements-ultra Rule Zero: IS/BS/CF forecast & historical cells MUST be
Excel formula strings (start with '='). Hardcoded floats/ints silently break
the model — caught by QC-2 too late, often after 200+ lines of bad code.

This hook intercepts the bash command BEFORE it runs.

Self-gated: only activates when bash command references a 3-statements context
(keywords: 3statements / _State / Raw_Info / Assumptions / RAW_MAP / ASM_MAP).
Other skills are unaffected.

Exit codes:
  0   no violation (or out of context, or only formula assignments)
  2   BLOCKER — hardcoded value in IS/BS/CF cell, block the bash call

See: ~/.claude/skills/3-statements-ultra/SKILL.md §RULE ZERO
"""
import sys
import io
import json
import re

try:
    sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass


def read_hook_input() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


# Self-gate: must mention a 3-statements concept to activate.
CTX_PATTERN = re.compile(
    r'3statements|3-statements|three[_-]stmt|_State'
    r'|Raw_Info|Assumptions|RAW_MAP|ASM_MAP'
    r'|KEY_CELLS_(IS|BS|CF)|BS_COL_MAP|CF_COL_MAP',
    re.IGNORECASE,
)

# Strip Python comments so we don't false-positive on examples in docstrings.
COMMENT_PATTERN = re.compile(r'#[^\n]*')
# Strip triple-quoted docstrings (greedy across lines).
DOCSTRING_PATTERN = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', re.MULTILINE)


# Hardcode patterns — assignment to IS/BS/CF cell with non-formula RHS.
HARDCODE_PATTERNS = [
    # Form 1: ws_is["E5"].value = 0.30   /   ws_is["E5"] = 0.30
    re.compile(
        r'ws_(?:is|bs|cf)\s*\[\s*["\'][A-Z]+\d+["\']\s*\]'
        r'(?:\.value)?\s*=\s*'
        r'(?!["\']\s*=)'
        r'(?:[\-\+]?\d+(?:\.\d+)?\b'
        r'|float\s*\('
        r'|int\s*\('
        r'|abs\s*\('
        r'|round\s*\()',
        re.IGNORECASE,
    ),
    # Form 2: wb["IS"]["E5"].value = 0.30
    re.compile(
        r'wb\s*\[\s*["\'](?:IS|BS|CF|CFS)["\']\s*\]'
        r'\s*\[\s*["\'][A-Z]+\d+["\']\s*\]'
        r'(?:\.value)?\s*=\s*'
        r'(?!["\']\s*=)'
        r'(?:[\-\+]?\d+(?:\.\d+)?\b'
        r'|float\s*\(|int\s*\(|abs\s*\(|round\s*\()',
        re.IGNORECASE,
    ),
    # Form 3: ws_is.cell(row=5, column=4).value = 0.30
    re.compile(
        r'ws_(?:is|bs|cf)\s*\.\s*cell\s*\([^)]*\)'
        r'(?:\.value)?\s*=\s*'
        r'(?!["\']\s*=)'
        r'(?:[\-\+]?\d+(?:\.\d+)?\b'
        r'|float\s*\(|int\s*\(|abs\s*\(|round\s*\()',
        re.IGNORECASE,
    ),
    # Form 4: mixed-formula error — string with embedded "=" inside (Excel parse error)
    re.compile(r'f?"[^"]*=[^"=]*\(\s*1\s*\+\s*=', re.IGNORECASE),
]

# Codex B5: alias pattern.
#   ws = wb["IS"]; ws["E5"].value = 0.30
#   sheet = wb['BS']
#   sheet['F10'] = 1000
# We detect the existence of a sheet alias being created from wb["IS"|"BS"|"CF"|"CFS"]
# AND any short-identifier subscript-assignment-with-number elsewhere in the SAME
# command. CTX_PATTERN already gates 3stmt-context, so false-positive risk is low.
ALIAS_BIND_PATTERN = re.compile(
    r'(\b[a-z_][a-z0-9_]*)\s*=\s*wb\s*\[\s*["\'](?:IS|BS|CF|CFS)["\']\s*\]',
    re.IGNORECASE,
)


def detect_alias_hardcode(cmd: str) -> tuple[str, str] | None:
    """If cmd binds an alias `<name> = wb["IS"|"BS"|"CF"|"CFS"]` and later does
    `<name>["E5"].value = 0.30` (or .cell() form), return (alias, match snippet).
    Returns None if no match."""
    aliases = [m.group(1) for m in ALIAS_BIND_PATTERN.finditer(cmd)]
    if not aliases:
        return None
    for alias in aliases:
        # subscript form: alias["E5"].value = <number>
        pat = re.compile(
            r'\b' + re.escape(alias) + r'\s*\[\s*["\'][A-Z]+\d+["\']\s*\]'
            r'(?:\.value)?\s*=\s*'
            r'(?!["\']\s*=)'
            r'(?:[\-\+]?\d+(?:\.\d+)?\b'
            r'|float\s*\(|int\s*\(|abs\s*\(|round\s*\()',
            re.IGNORECASE,
        )
        m = pat.search(cmd)
        if m:
            return alias, m.group(0)
        # .cell() form: alias.cell(...).value = <number>
        pat2 = re.compile(
            r'\b' + re.escape(alias) + r'\s*\.\s*cell\s*\([^)]*\)'
            r'(?:\.value)?\s*=\s*'
            r'(?!["\']\s*=)'
            r'(?:[\-\+]?\d+(?:\.\d+)?\b'
            r'|float\s*\(|int\s*\(|abs\s*\(|round\s*\()',
            re.IGNORECASE,
        )
        m = pat2.search(cmd)
        if m:
            return alias, m.group(0)
    return None


def main():
    hook = read_hook_input()
    cmd = (hook.get("tool_input", {}) or {}).get("command", "") or ""

    if not CTX_PATTERN.search(cmd):
        sys.exit(0)

    cmd_clean = DOCSTRING_PATTERN.sub("", cmd)
    cmd_clean = COMMENT_PATTERN.sub("", cmd_clean)

    for i, pat in enumerate(HARDCODE_PATTERNS, start=1):
        m = pat.search(cmd_clean)
        if m:
            snippet = m.group(0)[:160]
            sys.stderr.write(
                "[3stmt-hardcode-guard] BLOCKER: Rule Zero violation — hardcoded value in IS/BS/CF cell.\n"
                f"  Pattern #{i} matched: {snippet}\n"
                "  IS/BS/CF non-input cells MUST be Excel formula strings (start with '=').\n"
                "  Only Assumptions / Raw_Info / headers may hold raw numbers.\n"
                "\n"
                "  ❌  ws_is['E5'].value = 0.30\n"
                "  ❌  ws_is['E5'].value = float(rev * 0.3)\n"
                "  ✅  ws_is['E5'].value = f\"=Assumptions!B{asm_map['Revenue YoY %']}\"\n"
                "  ✅  ws_is['E5'].value = f\"=D5*(1+Assumptions!B{asm_map['Revenue YoY %']})\"\n"
                "\n"
                "  See: ~/.claude/skills/3-statements-ultra\\SKILL.md §RULE ZERO\n"
            )
            sys.exit(2)

    alias_hit = detect_alias_hardcode(cmd_clean)
    if alias_hit:
        alias, snippet = alias_hit
        sys.stderr.write(
            "[3stmt-hardcode-guard] BLOCKER : Rule Zero violation via sheet alias.\n"
            f"  Alias '{alias}' was bound from wb[\"IS\"|\"BS\"|\"CF\"|\"CFS\"] earlier in command,\n"
            f"  then used to write a hardcoded value: {snippet[:160]}\n"
            "  Aliases inherit the Rule Zero contract — IS/BS/CF non-input cells must be Excel formula strings.\n"
            "\n"
            "  ❌  ws = wb['IS']; ws['E5'].value = 0.30\n"
            "  ✅  ws = wb['IS']; ws['E5'].value = f\"=Assumptions!B{asm_map['Revenue YoY %']}\"\n"
            "\n"
            "  See: ~/.claude/skills/3-statements-ultra\\SKILL.md §RULE ZERO\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
