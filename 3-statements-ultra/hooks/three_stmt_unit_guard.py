#!/usr/bin/env python3
"""
PreToolUse Bash hook — 3-Statements Unit / Granularity Prerequisite Guard

Catches the most expensive silent failure: populating Raw_Info before _State
has UNIT and IS_GRANULARITY locked in. Wrong unit = 100x error invisible
until QC. Wrong granularity = entire COL_MAP structure has to be rebuilt.

Fires only when bash command writes to Raw_Info sheet:
  - ws_raw[...] = ...
  - wb["Raw_Info"][...] = ...
  - ws_raw.cell(...).value = ...

Then opens the xlsx, checks _State for both UNIT and IS_GRANULARITY keys.

Exit codes:
  0  PASS — prereqs in place, or hook out of scope
  2  BLOCKER — Raw_Info write attempted but UNIT or IS_GRANULARITY missing
"""
import sys
import io
import json
import re
from pathlib import Path

try:
    sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass


def read_hook_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


CTX_PATTERN = re.compile(
    r'3statement|3-statement|three[_-]stmt|Raw_Info|RAW_INFO|_State',
    re.IGNORECASE,
)

RAW_INFO_WRITE_PATTERNS = [
    re.compile(r'ws_raw\s*\[\s*["\'][A-Z]+\d+["\']\s*\]\s*(?:\.value)?\s*=', re.IGNORECASE),
    re.compile(r'wb\s*\[\s*["\']Raw_Info["\']\s*\]\s*\[', re.IGNORECASE),
    re.compile(r'ws_raw\s*\.\s*cell\s*\([^)]*\)\s*(?:\.value)?\s*=', re.IGNORECASE),
    re.compile(r'wb\s*\[\s*["\']Raw_Info["\']\s*\]\s*\.cell\s*\(', re.IGNORECASE),
]

XLSX_PATH_PATTERN = re.compile(r'["\']([^"\']{0,400}\.xlsx)["\']')


def is_raw_info_write(cmd: str) -> bool:
    return any(p.search(cmd) for p in RAW_INFO_WRITE_PATTERNS)


def extract_xlsx_path(cmd: str) -> str | None:
    for m in XLSX_PATH_PATTERN.finditer(cmd):
        p = m.group(1)
        path = Path(p)
        if path.exists():
            return p
    matches = list(XLSX_PATH_PATTERN.finditer(cmd))
    return matches[0].group(1) if matches else None


def main():
    hook = read_hook_input()
    cmd = (hook.get("tool_input", {}) or {}).get("command", "") or ""

    if not CTX_PATTERN.search(cmd):
        sys.exit(0)
    if not is_raw_info_write(cmd):
        sys.exit(0)

    xlsx = extract_xlsx_path(cmd)
    if not xlsx:
        sys.exit(0)

    p = Path(xlsx)
    if not p.exists():
        sys.exit(0)

    # v1.1: state via state_io sidecar (auto-migrates from _State sheet)
    state_io_dir = Path.home() / ".claude" / "skills" / "3-statements-ultra" / "scripts"
    if state_io_dir.exists():
        sys.path.insert(0, str(state_io_dir))
    try:
        import state_io  # type: ignore
        state = state_io.load_state(p)
    except Exception:
        sys.exit(0)
    if not state:
        sys.stderr.write(
            "[3stmt-unit-guard] BLOCKER: writing to Raw_Info before state.json sidecar (or _State sheet) exists.\n"
            f"  File: {p.name}\n"
            "  PRE-FLIGHT must run first to lock UNIT + IS_GRANULARITY.\n"
            "  See: ~/.claude/skills/3-statements-ultra/references/session-a.md §Phase 0 Step 0\n"
        )
        sys.exit(2)

    missing = []
    if "UNIT" not in state or not state["UNIT"]:
        missing.append("UNIT")
    if "IS_GRANULARITY" not in state or not state["IS_GRANULARITY"]:
        missing.append("IS_GRANULARITY")

    if missing:
        sys.stderr.write(
            "[3stmt-unit-guard] BLOCKER: missing prerequisite keys in state.json before Raw_Info write.\n"
            f"  File: {p.name}\n"
            f"  Missing: {', '.join(missing)}\n"
            "\n"
            "  PRE-FLIGHT (Phase 0 Step 0 in session-a.md) must lock UNIT and IS_GRANULARITY\n"
            "  before any Raw_Info data extraction. Otherwise:\n"
            "  - Wrong unit (万元 vs 百万元) = silent 100x error invisible until QC\n"
            "  - Wrong granularity = entire COL_MAP structure has to be rebuilt\n"
            "\n"
            "  Fix:\n"
            "    from state_io import write_key\n"
            "    write_key(filepath, 'UNIT', '百万元 RMB')\n"
            "    write_key(filepath, 'IS_GRANULARITY', 'Quarterly')\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
