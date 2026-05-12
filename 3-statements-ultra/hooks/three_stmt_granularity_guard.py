#!/usr/bin/env python3
"""
PreToolUse Bash hook — 3-Statements Granularity Pattern Guard

Catches the load-bearing wrong-granularity bug at the moment IS_GRANULARITY
is written to _State. The COL_MAP structure depends on this value — wrong
choice means the entire IS/CF column scaffold has to be rebuilt later.

Rules (regex-only, no API calls — keeps hook fast):
  A-share ticker (.SS / .SZ / SZ###### / SH###### / 6-digit SSE/SZSE code)
    → MUST be Quarterly (CSRC requirement)
  US ticker (4-letter NYSE/NASDAQ-listed, not ending in .HK/.SS/.SZ)
    → MUST be Quarterly (SEC 10-Q)
  HK-only ticker (.HK / 4-5 digit HK code)
    → Quarterly OR Semi-annual allowed; Annual = WARNING (rare valid case)
    → Multi-source API validation deferred to preflight_check.py

Fires only when bash command pattern matches:
  write_state_key(.., 'IS_GRANULARITY', '<value>')
  or:
  state["IS_GRANULARITY"] = '<value>'  (less common)

Exit codes:
  0  PASS — granularity matches ticker class
  2  BLOCKER — A-share/US ticker with non-Quarterly value
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


GRANULARITY_WRITE_PATTERNS = [
    re.compile(
        r'write_state_key\s*\([^,]*,\s*["\']IS_GRANULARITY["\']\s*,\s*["\'](\w[\w\-]*)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'IS_GRANULARITY["\']\s*[:=]\s*["\'](\w[\w\-]*)["\']',
        re.IGNORECASE,
    ),
    re.compile(
        r'state\s*\[\s*["\']IS_GRANULARITY["\']\s*\]\s*=\s*["\'](\w[\w\-]*)["\']',
        re.IGNORECASE,
    ),
]


def extract_granularity(cmd: str) -> str | None:
    for pat in GRANULARITY_WRITE_PATTERNS:
        m = pat.search(cmd)
        if m:
            return m.group(1)
    return None


A_SHARE_PATTERNS = [
    re.compile(r'["\']SZ\d{6}["\']'),
    re.compile(r'["\']SH\d{6}["\']'),
    re.compile(r'\b\d{6}\.(SZ|SS)\b'),
    re.compile(r'["\'](?:00[0-3]|300|600|601|603|605|688)\d{3}["\']'),
]
HK_PATTERNS = [
    re.compile(r'["\']HK\d{4,5}["\']'),
    re.compile(r'\b\d{4,5}\.HK\b'),
    re.compile(r'["\']0\d{3,4}\.HK["\']'),
]
US_PATTERN = re.compile(r'["\']([A-Z]{2,5})["\']\s*(?:,|\)|\s|$)')

ALLOWED_GRANULARITIES = {
    "quarterly": "Quarterly",
    "semi-annual": "Semi-annual",
    "semiannual": "Semi-annual",
    "annual": "Annual",
}


def classify_ticker(cmd: str) -> str:
    for p in A_SHARE_PATTERNS:
        if p.search(cmd):
            return "A_SHARE"
    for p in HK_PATTERNS:
        if p.search(cmd):
            return "HK"
    for m in US_PATTERN.finditer(cmd):
        sym = m.group(1)
        if sym.upper() in {"IS", "BS", "CF", "PASS", "FAIL", "JSON", "HTTP",
                            "TRUE", "FALSE", "NULL", "NONE", "OK", "USD",
                            "CNY", "HKD", "RMB", "GAAP", "IFRS"}:
            continue
        return "US"
    return "UNKNOWN"


def main():
    hook = read_hook_input()
    cmd = (hook.get("tool_input", {}) or {}).get("command", "") or ""

    granularity = extract_granularity(cmd)
    if granularity is None:
        sys.exit(0)
    g_norm = ALLOWED_GRANULARITIES.get(granularity.lower())
    if g_norm is None:
        sys.stderr.write(
            f"[3stmt-granularity-guard] BLOCKER: invalid IS_GRANULARITY value '{granularity}'.\n"
            f"  Allowed: Quarterly | Semi-annual | Annual\n"
        )
        sys.exit(2)

    ticker_class = classify_ticker(cmd)

    if ticker_class == "A_SHARE" and g_norm != "Quarterly":
        sys.stderr.write(
            f"[3stmt-granularity-guard] BLOCKER: A-share ticker but IS_GRANULARITY='{g_norm}'.\n"
            "  A-shares must be Quarterly (CSRC mandates quarterly reporting).\n"
            "  Setting Annual/Semi-annual will discard Q1/Q3 disclosures and break COL_MAP.\n"
            "\n"
            "  Fix: write_state_key(wb, 'IS_GRANULARITY', 'Quarterly')\n"
        )
        sys.exit(2)

    if ticker_class == "US" and g_norm != "Quarterly":
        sys.stderr.write(
            f"[3stmt-granularity-guard] BLOCKER: US-listed ticker but IS_GRANULARITY='{g_norm}'.\n"
            "  US tickers must be Quarterly (SEC 10-Q filing requirement).\n"
            "\n"
            "  Fix: write_state_key(wb, 'IS_GRANULARITY', 'Quarterly')\n"
        )
        sys.exit(2)

    if ticker_class == "HK" and g_norm == "Annual":
        sys.stderr.write(
            f"[3stmt-granularity-guard] WARNING: HK ticker with IS_GRANULARITY='Annual'.\n"
            "  HK listings disclose at least Semi-annual (HKEx 中报 + 年报).\n"
            "  Annual-only is rare; verify via yfinance / AKShare / Xueqiu.\n"
            "  preflight_check.py will do multi-source validation.\n"
            "  (not blocking — proceed if you have intentional reason)\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
