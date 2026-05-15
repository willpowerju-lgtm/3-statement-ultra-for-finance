#!/usr/bin/env python3
"""
per_session_gate.py — Per-session dispatch wrapper

Selects the appropriate QC subset for each session and writes
GATE_<X>_PASSED marker to _State on success.

Severity: BLOCKER (exit 2) | WARNING (exit 1) | PASS (exit 0)

Usage:
  python per_session_gate.py --session A --xlsx <path>
  python per_session_gate.py --session A2 --xlsx <path>
  python per_session_gate.py --session B --xlsx <path>
  python per_session_gate.py --session E --xlsx <path> --full

Behavior:
  --session A  → delegate to preflight_check.py
  --session A2 → qc_suite.py --full --tabs Revenue_Build (QC-2,20) — conditional, only if REVENUE_BUILD=TRUE
  --session B  → qc_suite.py --full --tabs IS    (QC-2,5,6,11,12,21)
  --session C  → qc_suite.py --full --tabs BS    (QC-2,6,7) + _pending_links written check
  --session D  → qc_suite.py --full --tabs CF    (QC-1,2,3,4,6,13) + back-fill complete
  --session E  → qc_suite.py --full --tabs all   (QC-1..21) → data-validator → MODEL_COMPLETE

On PASS (exit 0): writes 'GATE_<X>_PASSED: <ts>' to _State and saves.
On WARNING (exit 1): writes the marker but appends '(with warnings)'.
On BLOCKER (exit 2): does NOT write marker; next session is blocked.
"""
from __future__ import annotations
import sys
import io
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import openpyxl
except ImportError:
    sys.stderr.write("openpyxl not installed. Run: pip install openpyxl\n")
    sys.exit(127)


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import state_io  # v1.1: state.json sidecar

QC_SUITE = SCRIPT_DIR / "qc_suite.py"
PREFLIGHT = SCRIPT_DIR / "preflight_check.py"
DATA_VALIDATOR = Path.home() / ".claude" / "skills" / "data-validator" / "scripts" / "validate.py"

PREV_GATE = {"A2": "A", "B": "A", "C": "B", "D": "C", "E": "D"}
# Note: SESSION B verify-prev is dynamic — if REVENUE_BUILD=TRUE in state, the required
# previous gate is A2 (not A). verify_prev_gate() handles this conditional override.

SESSION_ORDER = ["A", "A2", "B", "C", "D", "E"]


def read_state(xlsx_path) -> dict:
    """v1.1: read state.json sidecar (auto-migrates from legacy _State sheet)."""
    return state_io.load_state(xlsx_path)


def write_state_key(xlsx_path, key: str, value: str) -> None:
    """v1.1: write to state.json sidecar (atomic)."""
    state_io.write_key(xlsx_path, key, value)


def _delete_stale_sidecar(path: Path) -> None:
    """Codex round-3 fix: delete the expected JSON sidecar before subprocess invocation
    so a stale file from a prior run can never be mistaken for the current run's output."""
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        sys.stderr.write(f"[gate] could not remove stale sidecar {path}: {e}\n")


def session_a(args) -> int:
    if not PREFLIGHT.exists():
        sys.stderr.write(f"preflight_check.py not found at {PREFLIGHT}\n")
        return 127
    sidecar = Path(args.json) if args.json else Path(args.xlsx).with_suffix(".preflight.json")
    _delete_stale_sidecar(sidecar)
    r = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--xlsx", args.xlsx, "--json", str(sidecar)],
        capture_output=False,
    )
    return r.returncode


def run_qc_suite(args, tabs: str | None) -> int:
    if not QC_SUITE.exists():
        sys.stderr.write(f"qc_suite.py not found at {QC_SUITE}\n")
        return 127
    cmd = [sys.executable, str(QC_SUITE), "--xlsx", args.xlsx]
    cmd.append("--full" if args.full else "--smoke")
    if tabs:
        cmd += ["--tabs", tabs]
    if args.json:
        sidecar = Path(args.json)
    else:
        sidecar = Path(args.xlsx).with_suffix(f".qc_{args.session}.json")
    cmd += ["--json", str(sidecar)]
    _delete_stale_sidecar(sidecar)
    r = subprocess.run(cmd, capture_output=False)
    return r.returncode


def check_pending_links_written(args) -> tuple[bool, str]:
    """SESSION C must produce _pending_links.json as proof it considered deferred BS->CF refs.
    Empty list is acceptable (model with no Cash placeholder); missing file is a BLOCKER."""
    xlsx_dir = Path(args.xlsx).parent
    pending_json = xlsx_dir / "_pending_links.json"
    if not pending_json.exists():
        return False, "_pending_links.json missing (SESSION C must register deferred BS->CF refs, even if list is empty — write [] to signal 'considered, none needed')"
    try:
        data = json.loads(pending_json.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"_pending_links.json unreadable: {e}"
    if not isinstance(data, list):
        return False, f"_pending_links.json must be a JSON list (got {type(data).__name__})"
    return True, f"_pending_links.json has {len(data)} entries"


def check_pending_links_cleared(args) -> tuple[bool, str]:
    """SESSION D back-fill complete = _pending_links.json must parse to an EMPTY list.
    Missing-file path is acceptable (deletion-on-clear convention), but any parse
    failure or non-empty list is a BLOCKER — we never silently treat unreadable
    as cleared (Codex B3)."""
    xlsx_dir = Path(args.xlsx).parent
    pending_json = xlsx_dir / "_pending_links.json"
    if not pending_json.exists():
        return True, "_pending_links.json absent (consumed by back-fill)"
    try:
        data = json.loads(pending_json.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"_pending_links.json unreadable: {e} — cannot confirm back-fill complete"
    if not isinstance(data, list):
        return False, f"_pending_links.json must be a JSON list (got {type(data).__name__})"
    if len(data) == 0:
        return True, "_pending_links.json cleared (0 entries)"
    return False, f"_pending_links.json still has {len(data)} pending entries (SESSION D back-fill incomplete)"


def qc_report_path(args) -> Path:
    """Mirror of the json-path logic in run_qc_suite / session_a."""
    if args.json:
        return Path(args.json)
    xlsx = Path(args.xlsx)
    if args.session == "A":
        return xlsx.with_suffix(".preflight.json")
    return xlsx.with_suffix(f".qc_{args.session}.json")


def has_qc_full_coverage_warning(args) -> tuple[bool, str]:
    """Codex B1: detect the QC-FULL-COVERAGE WARNING stub. Its presence means
    the numeric/full QCs never actually ran — we must NOT advance the session.
    Returns (has_stub, message)."""
    report = qc_report_path(args)
    if not report.exists():
        return False, "no report file to inspect"
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"report unreadable: {e}"
    for f in data.get("findings", []):
        if f.get("qc") == "QC-FULL-COVERAGE":
            return True, "qc_suite emitted QC-FULL-COVERAGE WARNING (numeric QCs not implemented)"
    return False, "no QC-FULL-COVERAGE in findings"


def run_data_validator(args) -> tuple[int, str]:
    """Codex B2 + round-3: SESSION E must run data-validator after qc_suite.
    Per SKILL.md R11: FAIL and RECALC both block MODEL_COMPLETE. We treat any
    non-zero exit (including dv_rc=1) as BLOCKER to disambiguate
    crash-vs-warning and to match documented behavior. Returns (rc, msg)."""
    if not DATA_VALIDATOR.exists():
        return 2, f"data-validator not found at {DATA_VALIDATOR}"
    xlsx = Path(args.xlsx)
    candidates = list(xlsx.parent.glob("*_3statements_data_registry.json"))
    if not candidates:
        return 2, ("no *_3statements_data_registry.json found alongside xlsx — "
                   "SESSION E must build the _Registry sheet first (see SKILL.md R11)")
    registry = candidates[0]
    cmd = [sys.executable, str(DATA_VALIDATOR), "--json", str(registry), "--mode", "full"]
    sys.stderr.write(f"[gate-E] running data-validator: {' '.join(cmd)}\n")
    r = subprocess.run(cmd, capture_output=False)
    dv_rc = r.returncode
    # Elevate any non-zero (crash OR WARN OR FAIL) to BLOCKER per SKILL.md R11.
    elevated = 2 if dv_rc != 0 else 0
    return elevated, (f"data-validator exit {dv_rc} (elevated to {elevated} per R11) "
                       f"on {registry.name}")


def session_a2(args) -> int:
    """SESSION A2 — Revenue_Build tab QC.

    Codex B1+B2+B5 fix:
      - REVENUE_BUILD normalized via state_io.normalize_revenue_build (handles bool/str/None).
      - REVENUE_BUILD=FALSE → write typed GATE_A2_SKIPPED marker (NOT GATE_A2_PASSED), set
        args._a2_skipped=True so main() suppresses the GATE_A2_PASSED auto-write. If later
        the user changes REVENUE_BUILD to TRUE and runs SESSION B, verify_prev rejects the
        SKIPPED marker and requires a real GATE_A2_PASSED from a real A2 run.
      - REVENUE_BUILD=TRUE → run qc_suite + verify REV_BUILD_MAP populated. Re-read state
        immediately before each branch decision to avoid stale-snapshot routing.
      - REVENUE_BUILD=UNSET/INVALID → BLOCKER (don't paper over a bad Phase 2.5 answer).
    """
    args._a2_skipped = False
    xlsx_p = Path(args.xlsx)
    # Always read fresh inside the handler — no cached state from main()
    state = read_state(xlsx_p)
    rb_norm = state_io.normalize_revenue_build(state.get("REVENUE_BUILD"))
    if rb_norm == "INVALID":
        sys.stderr.write(
            f"[gate-A2] BLOCKER: REVENUE_BUILD={state.get('REVENUE_BUILD')!r} is invalid.\n"
            f"  Expected TRUE or FALSE (string) or boolean. "
            f"Re-run SESSION A Phase 2.5 to set the value.\n"
        )
        return 2
    if rb_norm == "UNSET":
        sys.stderr.write(
            f"[gate-A2] BLOCKER: REVENUE_BUILD not set in state.\n"
            f"  Run SESSION A Phase 2.5 first to decide TRUE/FALSE before running A2.\n"
        )
        return 2
    if rb_norm == "FALSE":
        # Typed skip marker. main() must NOT also write GATE_A2_PASSED.
        try:
            stamp = datetime.now().isoformat(timespec="seconds")
            write_state_key(xlsx_p, "GATE_A2_SKIPPED",
                f"{stamp}: REVENUE_BUILD=FALSE — A2 intentionally not run")
            sys.stderr.write(
                f"[gate-A2] REVENUE_BUILD=FALSE — SESSION A2 skipped (no Revenue_Build tab).\n"
                f"  Wrote GATE_A2_SKIPPED to state. SESSION B verify-prev will require "
                f"GATE_A_PASSED (NOT GATE_A2_PASSED).\n"
            )
        except Exception as e:
            sys.stderr.write(f"[gate-A2] WARNING: could not write GATE_A2_SKIPPED: {e}\n")
        args._a2_skipped = True
        return 0
    # rb_norm == "TRUE" → actually run QC on Revenue_Build tab.
    try:
        wb_check = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=False)
        present = "Revenue_Build" in wb_check.sheetnames
        wb_check.close()
        if not present:
            sys.stderr.write(
                f"[gate-A2] BLOCKER: REVENUE_BUILD=TRUE but Revenue_Build tab missing in xlsx.\n"
                f"  Build the tab per references/session-a2.md before running this gate.\n"
            )
            return 2
    except Exception as e:
        sys.stderr.write(f"[gate-A2] BLOCKER: cannot open xlsx: {e}\n")
        return 2
    args.full = True
    raw_rc = run_qc_suite(args, tabs="Revenue_Build")
    # SESSION A2 scope: only QC-2 (no hardcode) + QC-20 (Revenue_Build integrity).
    # qc_suite runs the full QC list, which includes QC-4 (BS Cash), QC-11 (segment sum),
    # etc. — those fire on other tabs and are pre-existing issues unrelated to A2.
    # Filter the JSON report to A2-scoped QCs only.
    A2_QC_SCOPE = {"QC-2", "QC-20", "QC-22"}
    report = qc_report_path(args)
    if report.exists():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            a2_findings = [f for f in data.get("findings", [])
                           if f.get("qc") in A2_QC_SCOPE]
            a2_blockers = [f for f in a2_findings if f.get("severity") == "BLOCKER"]
            a2_warnings = [f for f in a2_findings if f.get("severity") == "WARNING"]
            if a2_blockers:
                rc = 2
                for f in a2_blockers:
                    sys.stderr.write(f"  [gate-A2 BLOCKER] {f.get('qc')} {f.get('cell','')}: {f.get('msg','')}\n")
            elif a2_warnings:
                rc = 1
            else:
                rc = 0
            # Report scope filter for transparency
            all_blockers = sum(1 for f in data.get("findings", []) if f.get("severity") == "BLOCKER")
            if all_blockers != len(a2_blockers):
                sys.stderr.write(
                    f"[gate-A2] scope filter: {all_blockers} total BLOCKERs across all QCs, "
                    f"{len(a2_blockers)} in A2 scope ({', '.join(A2_QC_SCOPE)}). "
                    f"Out-of-scope BLOCKERs deferred to their owning session.\n"
                )
        except Exception as e:
            sys.stderr.write(f"[gate-A2] WARNING: could not parse report {report}: {e}\n")
            rc = raw_rc
    else:
        rc = raw_rc
    # Verify REV_BUILD_MAP key is written (SESSION A2 Step 11). Re-read state fresh.
    state2 = read_state(xlsx_p)
    rbm = state2.get("REV_BUILD_MAP")
    if not isinstance(rbm, dict) or not rbm:
        sys.stderr.write(
            "[gate-A2] BLOCKER: REV_BUILD_MAP missing or empty in state. "
            "SESSION A2 Step 11 must write {segment_name: total_row} mapping.\n"
        )
        rc = max(rc, 2)
    return rc


def session_b(args) -> int:
    args.full = True
    raw_rc = run_qc_suite(args, tabs="IS")
    # SESSION B scope: QC-2,5,6,11,12,14,15,17,21 (per GATE INVENTORY).
    # Filter out BLOCKERs from QCs that belong to other sessions (e.g. QC-4 BS Cash = SESSION D).
    B_QC_SCOPE = {"QC-2", "QC-5", "QC-6", "QC-11", "QC-12", "QC-14", "QC-15", "QC-17", "QC-21", "QC-22"}
    report = qc_report_path(args)
    if report.exists():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            b_findings = [f for f in data.get("findings", []) if f.get("qc") in B_QC_SCOPE]
            b_blockers = [f for f in b_findings if f.get("severity") == "BLOCKER"]
            b_warnings = [f for f in b_findings if f.get("severity") == "WARNING"]
            if b_blockers:
                rc = 2
            elif b_warnings:
                rc = 1
            else:
                rc = 0
            all_blockers = sum(1 for f in data.get("findings", []) if f.get("severity") == "BLOCKER")
            if all_blockers != len(b_blockers):
                sys.stderr.write(
                    f"[gate-B] scope filter: {all_blockers} total BLOCKERs, "
                    f"{len(b_blockers)} in B scope ({', '.join(sorted(B_QC_SCOPE))}). "
                    f"Out-of-scope deferred.\n"
                )
        except Exception:
            rc = raw_rc
    else:
        rc = raw_rc
    return rc


def session_c(args) -> int:
    args.full = True
    rc = run_qc_suite(args, tabs="BS")
    ok, msg = check_pending_links_written(args)
    if not ok:
        sys.stderr.write(f"[gate-C] BLOCKER: {msg}\n")
        return max(rc, 2)
    sys.stderr.write(f"[gate-C] {msg}\n")
    return rc


def session_d(args) -> int:
    args.full = True
    rc = run_qc_suite(args, tabs="CF")
    ok, msg = check_pending_links_cleared(args)
    if not ok:
        sys.stderr.write(f"[gate-D] BLOCKER: {msg}\n")
        return max(rc, 2)
    sys.stderr.write(f"[gate-D] {msg}\n")
    return rc


def session_e(args) -> int:
    args.full = True
    rc = run_qc_suite(args, tabs=None)
    if rc >= 2:
        return rc
    dv_rc, dv_msg = run_data_validator(args)
    sys.stderr.write(f"[gate-E] {dv_msg}\n")
    return max(rc, dv_rc)


HANDLERS = {
    "A": session_a,
    "A2": session_a2,
    "B": session_b,
    "C": session_c,
    "D": session_d,
    "E": session_e,
}


def verify_prev_gate(args) -> int:
    """Codex B4: session startup check — verify previous session's GATE_<X>_PASSED.
    Called via --verify-prev. SESSION A has no prerequisite.

    SESSION B has dynamic prerequisite:
      - REVENUE_BUILD=TRUE  → require GATE_A2_PASSED
      - REVENUE_BUILD=FALSE → require GATE_A_PASSED
      - REVENUE_BUILD unset → require GATE_A_PASSED + warn (Phase 2.5 was skipped in SESSION A)
    """
    if args.session == "A":
        print(f"[verify-prev] SESSION A has no prerequisite gate.")
        return 0
    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        sys.stderr.write(f"[verify-prev] xlsx not found: {xlsx_path}\n")
        return 2
    state = read_state(xlsx_path)
    if not state:
        sys.stderr.write(
            f"[verify-prev] BLOCKER: no state.json sidecar and no legacy _State sheet — "
            f"run SESSION A first\n"
        )
        return 2
    # Resolve previous gate. SESSION B is dynamic; others come from PREV_GATE table.
    # Codex B4 fix: strict normalizer; INVALID values are BLOCKER (don't silently fall back).
    if args.session == "B":
        rb_norm = state_io.normalize_revenue_build(state.get("REVENUE_BUILD"))
        if rb_norm == "TRUE":
            prev = "A2"
            print(f"[verify-prev] SESSION B (REVENUE_BUILD=TRUE) requires GATE_A2_PASSED")
        elif rb_norm == "FALSE":
            prev = "A"
            print(f"[verify-prev] SESSION B (REVENUE_BUILD=FALSE) requires GATE_A_PASSED "
                  f"(GATE_A2_SKIPPED is informational, not required)")
        elif rb_norm == "UNSET":
            prev = "A"
            sys.stderr.write(
                f"[verify-prev] WARNING: REVENUE_BUILD unset in state — "
                f"SESSION A Phase 2.5 may have been skipped on a legacy model. "
                f"Falling back to GATE_A_PASSED check.\n"
            )
        else:  # INVALID
            sys.stderr.write(
                f"[verify-prev] BLOCKER: REVENUE_BUILD={state.get('REVENUE_BUILD')!r} is invalid "
                f"(expected TRUE/FALSE string or boolean). Re-run SESSION A Phase 2.5 to fix.\n"
            )
            return 2
    else:
        prev = PREV_GATE.get(args.session)
    if not prev:
        sys.stderr.write(f"[verify-prev] unknown session {args.session}\n")
        return 2
    gate_key = f"GATE_{prev}_PASSED"
    if gate_key in state and state[gate_key]:
        msg = state[gate_key]
        if "(with warnings)" in msg:
            sys.stderr.write(f"[verify-prev] OK: {gate_key} = {msg} (PASS with warnings — proceed with caution)\n")
        else:
            print(f"[verify-prev] OK: {gate_key} = {msg}")
        return 0
    legacy_val = f"SESSION_{prev}"
    if state.get("PHASE_DONE") == legacy_val or any(
        k.startswith("PHASE_DONE") and legacy_val in (v or "")
        for k, v in state.items()
    ):
        print(f"[verify-prev] OK: legacy PHASE_DONE marker for SESSION {prev} present")
        return 0
    sys.stderr.write(
        f"[verify-prev] BLOCKER: missing {gate_key} in _State — SESSION {prev} did not pass its gate.\n"
        f"  Run: python scripts/per_session_gate.py --session {prev} --xlsx {xlsx_path}\n"
    )
    return 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, choices=["A", "A2", "B", "C", "D", "E"])
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--full", action="store_true",
        help="Force qc_suite full mode (only meaningful for B/C/D; auto for E)")
    ap.add_argument("--json", default=None,
        help="Write report JSON to this path (default: auto-named alongside xlsx)")
    ap.add_argument("--verify-prev", action="store_true",
        help="Verify previous session's GATE_<X>_PASSED marker (startup check, no QC run)")
    args = ap.parse_args()

    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        sys.stderr.write(f"file not found: {xlsx_path}\n")
        sys.exit(127)

    if args.verify_prev:
        sys.exit(verify_prev_gate(args))

    print(f"=== per_session_gate: SESSION {args.session} ===")
    rc = HANDLERS[args.session](args)
    print()

    # Codex round-2 BLOCKER fix: rc=1 from subprocess could mean (a) legitimate
    # WARNING-only gate result, or (b) Python uncaught exception (also exit 1).
    # Distinguish by verifying the JSON sidecar exists and parses with expected schema.
    if rc == 1:
        report = qc_report_path(args)
        report_ok = False
        if report.exists():
            try:
                rdata = json.loads(report.read_text(encoding="utf-8"))
                if isinstance(rdata, dict) and "summary" in rdata and "findings" in rdata:
                    report_ok = True
            except Exception:
                pass
        if not report_ok:
            sys.stderr.write(
                f"[gate-{args.session}] BLOCKER (Codex round-2): subprocess exited 1 but the JSON sidecar "
                f"({report}) is missing or malformed — treating as crash, not WARNING.\n"
            )
            rc = 2

    has_stub, stub_msg = has_qc_full_coverage_warning(args)
    if has_stub and args.session in ("A2", "B", "C", "D", "E"):
        sys.stderr.write(
            f"[gate-{args.session}] BLOCKER (Codex B1): {stub_msg}.\n"
            f"  GATE_{args.session}_PASSED will NOT be written. "
            f"Numeric QCs (QC-1/3/4/5/6/7/9/10/11/12/13/16) must be implemented "
            f"in qc_suite.py before {args.session} can pass — see references/gate-spec.md\n"
        )
        rc = max(rc, 2)

    if rc == 0 or rc == 1:
        # Codex B5 fix: SESSION A2 skip path already wrote GATE_A2_SKIPPED (typed marker).
        # Do NOT also write GATE_A2_PASSED, or SESSION B will accept the skip when
        # REVENUE_BUILD is later flipped to TRUE.
        a2_skipped = (args.session == "A2" and getattr(args, "_a2_skipped", False))
        if a2_skipped:
            print(f"[gate-A2] SESSION A2 skip path completed; GATE_A2_SKIPPED already written. "
                  f"NOT writing GATE_A2_PASSED.")
        else:
            try:
                stamp = datetime.now().isoformat(timespec="seconds")
                suffix = " (with warnings)" if rc == 1 else ""
                write_state_key(xlsx_path, f"GATE_{args.session}_PASSED", stamp + suffix)
                print(f"state.json updated: GATE_{args.session}_PASSED = {stamp}{suffix}")
            except Exception as e:
                # Codex v1.1 WARNING fix: if durable marker write fails, escalate to BLOCKER.
                # Otherwise caller may treat gate as passed when next session's verify-prev will fail.
                sys.stderr.write(
                    f"[gate-{args.session}] BLOCKER: could not write GATE_{args.session}_PASSED "
                    f"to state.json: {e}\n  Next session's --verify-prev will fail.\n"
                )
                rc = 2

    print(f"=== per_session_gate exit: {rc} ===")
    sys.exit(rc)


if __name__ == "__main__":
    main()
