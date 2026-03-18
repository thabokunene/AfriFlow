#!/usr/bin/env python3
"""CI Benchmark Monitor for AfriFlow.

Runs each configured test suite under a hard 5-minute timeout, records
execution durations against a rolling baseline, and emits a detailed
Markdown timing report with suite-by-suite breakdowns and historical
trend comparisons.

Exit codes:
  0  All suites completed within the threshold.
  1  One or more suites exceeded the 5-minute threshold.
  2  Configuration or environment error (script cannot proceed).

Usage (from afriflow/ directory):
  python scripts/benchmark_ci.py \\
      --suites-config config/benchmark_suites.json \\
      --baseline      config/benchmark_baselines.json \\
      --output-json   coverage/benchmark_report.json
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes per suite
MAX_BASELINE_HISTORY = 10  # rolling window stored in the baseline file
TREND_WINDOW = 5  # runs used to compute the moving average for trend display

# Percentage change thresholds for trend classification
REGRESSION_PCT = 20  # >20% slower than average → regression
IMPROVEMENT_PCT = -10  # >10% faster than average → improvement


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="AfriFlow CI benchmark monitor — enforces a 5-minute per-suite timeout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--suites-config",
        default="config/benchmark_suites.json",
        help="Suite definitions JSON (default: config/benchmark_suites.json)",
    )
    p.add_argument(
        "--baseline",
        default="config/benchmark_baselines.json",
        help="Baseline history JSON — read, updated, and written back (default: config/benchmark_baselines.json)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Override hard timeout in seconds (0 = use value from suites config, fallback 300)",
    )
    p.add_argument(
        "--github-summary",
        default=os.environ.get("GITHUB_STEP_SUMMARY", ""),
        help="Append Markdown report to this file (auto-populated from $GITHUB_STEP_SUMMARY)",
    )
    p.add_argument(
        "--output-json",
        default="coverage/benchmark_report.json",
        help="Write full results JSON to this path (default: coverage/benchmark_report.json)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Config / baseline I/O
# ---------------------------------------------------------------------------


def load_suites_config(path: str) -> dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        _fatal(f"Suite config not found: {path}")
    with open(cfg_path, encoding="utf-8") as fh:
        return json.load(fh)


def load_baselines(path: str) -> dict:
    bl_path = Path(path)
    if not bl_path.exists():
        return {"generated": None, "runs": {}}
    with open(bl_path, encoding="utf-8") as fh:
        return json.load(fh)


def save_baselines(path: str, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data["generated"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _fatal(msg: str) -> None:
    print(f"[benchmark] ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Suite execution
# ---------------------------------------------------------------------------


def _build_pytest_cmd(suite: dict, timeout: int) -> list[str]:
    """Construct the pytest command for a suite.

    Coverage is explicitly disabled (-p no:cov) so we measure pure test
    execution time without coverage-instrumentation overhead.
    """
    base = [
        sys.executable,
        "-m",
        "pytest",
        suite["path"],
        "-q",
        "--tb=short",
        "--no-header",
        "-p",
        "no:cov",  # disable coverage — benchmark only
    ]
    base += suite.get("extra_args", [])
    return base


def run_suite(suite: dict, timeout: int, dry_run: bool) -> dict:
    """Execute one test suite and return a result record."""
    name = suite["name"]
    cmd = _build_pytest_cmd(suite, timeout)

    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return _make_result(suite, 0.0, False, 0, "")

    t0 = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        returncode = proc.returncode
        raw_output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = -1
        out_bytes = (exc.stdout or b"") + (exc.stderr or b"")
        if isinstance(out_bytes, bytes):
            raw_output = out_bytes.decode("utf-8", errors="replace")
        else:
            raw_output = out_bytes

    duration = time.perf_counter() - t0

    # Truncate captured output — we only need context for failures
    stdout_tail = raw_output[-800:].strip() if raw_output else ""

    return _make_result(suite, duration, timed_out, returncode, stdout_tail)


def _make_result(
    suite: dict,
    duration: float,
    timed_out: bool,
    returncode: int,
    stdout_tail: str,
) -> dict:
    exceeded = timed_out or (duration > 0 and duration > DEFAULT_TIMEOUT_SECONDS)
    return {
        "name": suite["name"],
        "path": suite["path"],
        "description": suite.get("description", suite["name"]),
        "duration_seconds": round(duration, 3),
        "timed_out": timed_out,
        "returncode": returncode,
        "passed": returncode == 0,
        "exceeded_threshold": exceeded,
        "stdout_tail": stdout_tail,
    }


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------


def compute_trend(history: list, current: float) -> dict:
    if not history:
        return {
            "status": "no_baseline",
            "delta_pct": None,
            "avg_historical": None,
            "window_size": 0,
        }
    window = history[-TREND_WINDOW:]
    avg = sum(window) / len(window)
    delta_pct = ((current - avg) / avg * 100) if avg > 0 else 0.0

    if delta_pct > REGRESSION_PCT:
        status = "regression"
    elif delta_pct < IMPROVEMENT_PCT:
        status = "improvement"
    else:
        status = "stable"

    return {
        "status": status,
        "delta_pct": round(delta_pct, 1),
        "avg_historical": round(avg, 3),
        "window_size": len(window),
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

_TREND_LABEL = {
    "regression": "⚠ regression",
    "improvement": "↓ faster",
    "stable": "→ stable",
    "no_baseline": "NEW",
}

_STATUS_ICON = {
    "pass": "PASS",
    "timeout": "TIMEOUT",
    "exceeded": "EXCEEDED",
    "test_fail": "TEST_FAIL",
}


def _fmt(seconds: float) -> str:
    """Human-readable duration string."""
    if seconds >= 60:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}m {s:.1f}s"
    return f"{seconds:.2f}s"


def build_report(results: list, baselines: dict, timeout: int) -> tuple:
    """Return (markdown_string, list_of_violation_messages)."""
    violations = []
    lines = []
    threshold_str = _fmt(timeout)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines += [
        "## AfriFlow CI Benchmark Report",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Hard timeout threshold** | `{threshold_str}` per suite |",
        f"| **Run timestamp** | {now_str} |",
        f"| **Suites evaluated** | {len(results)} |",
        "",
    ]

    # ------------------------------------------------------------------
    # Suite-by-suite timing table
    # ------------------------------------------------------------------
    lines += [
        "### Suite-by-Suite Timing",
        "",
        "| Suite | Description | Duration | vs Threshold | Trend | Status |",
        "|-------|-------------|----------|-------------|-------|--------|",
    ]

    for r in results:
        name = r["name"]
        desc = r["description"]
        dur_str = _fmt(r["duration_seconds"])
        history = baselines.get("runs", {}).get(name, {}).get("history", [])
        trend = compute_trend(history, r["duration_seconds"])

        # vs-threshold column
        if r["timed_out"]:
            vs_threshold = f"KILLED (>{threshold_str})"
        elif r["exceeded_threshold"]:
            over = r["duration_seconds"] - timeout
            vs_threshold = f"+{_fmt(over)} over"
        else:
            remaining = timeout - r["duration_seconds"]
            vs_threshold = f"{_fmt(remaining)} remaining"

        trend_label = _TREND_LABEL.get(trend["status"], "?")
        if trend["delta_pct"] is not None:
            trend_label += f" ({trend['delta_pct']:+.1f}%)"

        if r["timed_out"]:
            status_cell = "[TIMEOUT]"
        elif r["exceeded_threshold"]:
            status_cell = "[EXCEEDED]"
        elif not r["passed"]:
            status_cell = "[TEST_FAIL]"
        else:
            status_cell = "[PASS]"

        lines.append(
            f"| `{name}` | {desc} | **{dur_str}** | {vs_threshold} | {trend_label} | {status_cell} |"
        )

        if r["exceeded_threshold"] or r["timed_out"]:
            if r["timed_out"]:
                msg = (
                    f"Suite '{name}' ({r['path']}) TIMED OUT — process was killed "
                    f"after {threshold_str}. Reduce test volume or move slow tests "
                    f"to a nightly job with @pytest.mark.slow."
                )
            else:
                over_str = _fmt(r["duration_seconds"] - timeout)
                msg = (
                    f"Suite '{name}' ({r['path']}) ran for {dur_str}, "
                    f"exceeding the {threshold_str} threshold by {over_str}."
                )
            violations.append(msg)

    lines.append("")

    # ------------------------------------------------------------------
    # Historical trend comparison
    # ------------------------------------------------------------------
    lines += ["### Historical Trend Comparison", ""]

    trend_rows = []
    for r in results:
        name = r["name"]
        history = baselines.get("runs", {}).get(name, {}).get("history", [])
        if not history:
            continue
        window = history[-TREND_WINDOW:]
        avg = sum(window) / len(window)
        best = min(window)
        worst = max(window)
        runs_n = len(history)
        trend = compute_trend(history, r["duration_seconds"])
        delta_str = (
            f"{trend['delta_pct']:+.1f}%" if trend["delta_pct"] is not None else "—"
        )
        trend_rows.append(
            f"| `{name}` | {_fmt(avg)} | {_fmt(best)} | {_fmt(worst)} "
            f"| {runs_n} | {delta_str} |"
        )

    if trend_rows:
        lines += [
            "| Suite | Avg (last 5) | Best | Worst | Total runs | vs Avg |",
            "|-------|-------------|------|-------|-----------|--------|",
        ]
        lines += trend_rows
    else:
        lines += [
            "_No historical data available — baselines will be established after this run._"
        ]
    lines.append("")

    # ------------------------------------------------------------------
    # Violations summary
    # ------------------------------------------------------------------
    if violations:
        lines += [
            "### Violations — Pipeline Blocked",
            "",
        ]
        for v in violations:
            lines.append(f"> **FAIL** {v}")
        lines += [
            "",
            "**Remediation options:**",
            "- Split the suite into smaller logical groups.",
            "- Mark slow tests with `@pytest.mark.slow` and skip them via `-m 'not slow'` in CI.",
            "- Parallelize with `pytest-xdist` (`-n auto`).",
            "- Move integration/data-quality suites to a scheduled nightly workflow.",
        ]
    else:
        lines += [
            "### All suites passed within the time threshold",
            "",
            f"No suite exceeded `{threshold_str}`. Pipeline is unblocked.",
        ]

    return "\n".join(lines), violations


# ---------------------------------------------------------------------------
# Baseline update
# ---------------------------------------------------------------------------


def update_baselines(baselines: dict, results: list, max_history: int) -> dict:
    runs = baselines.setdefault("runs", {})
    for r in results:
        name = r["name"]
        entry = runs.setdefault(name, {"history": [], "last_exceeded": None})
        entry["history"].append(r["duration_seconds"])
        entry["history"] = entry["history"][-max_history:]
        entry["last_duration"] = r["duration_seconds"]
        entry["last_run"] = datetime.now(timezone.utc).isoformat()
        if r["exceeded_threshold"]:
            entry["last_exceeded"] = datetime.now(timezone.utc).isoformat()
    return baselines


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    config = load_suites_config(args.suites_config)
    suites = config.get("suites")
    if not suites:
        _fatal("No suites defined in config.")

    timeout = args.timeout or config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    baselines = load_baselines(args.baseline)

    _banner(f"AfriFlow CI Benchmark Monitor — threshold {_fmt(timeout)} per suite")
    print(f"  Suites : {len(suites)}")
    print(f"  Config : {args.suites_config}")
    print(f"  Baseline: {args.baseline}\n")

    results = []
    for suite in suites:
        name = suite["name"]
        print(f"[benchmark] → {name}  ({suite['path']}) ...", flush=True)
        r = run_suite(suite, timeout, args.dry_run)
        results.append(r)

        if r["timed_out"]:
            label = "TIMEOUT"
        elif r["exceeded_threshold"]:
            label = "EXCEEDED"
        elif not r["passed"]:
            label = "TEST FAILURES"
        else:
            label = "pass"

        print(
            f"[benchmark]   {name}: {_fmt(r['duration_seconds'])}  [{label}]",
            flush=True,
        )
        if not r["passed"] and r["stdout_tail"]:
            # Print a compact tail so engineers see failures inline
            print("  --- output tail ---")
            print("  " + r["stdout_tail"].replace("\n", "\n  "))
            print("  ---")

    # Build and emit the Markdown report
    report_md, violations = build_report(results, baselines, timeout)

    _banner("Benchmark Report")
    print(report_md)

    # Write to GitHub step summary when running in Actions
    if args.github_summary:
        try:
            with open(args.github_summary, "a", encoding="utf-8") as fh:
                fh.write("\n" + report_md + "\n")
        except OSError as exc:
            print(
                f"[benchmark] Warning: could not write to GITHUB_STEP_SUMMARY: {exc}",
                file=sys.stderr,
            )

    # Update rolling baseline and persist
    updated = update_baselines(baselines, results, MAX_BASELINE_HISTORY)
    save_baselines(args.baseline, updated)
    print(f"\n[benchmark] Baseline saved → {args.baseline}")

    # Write JSON artifact for downstream steps / archiving
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timeout_seconds": timeout,
        "threshold_exceeded": bool(violations),
        "total_suites": len(results),
        "passed_suites": sum(1 for r in results if not r["exceeded_threshold"]),
        "violated_suites": len(violations),
        "violations": violations,
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)
    print(f"[benchmark] JSON artifact  → {out_path}")

    if violations:
        _banner("BENCHMARK VIOLATIONS — PIPELINE BLOCKED", err=True)
        for v in violations:
            print(f"  FAIL  {v}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            f"  {len(violations)} suite(s) exceeded the {_fmt(timeout)} threshold.",
            file=sys.stderr,
        )
        print(
            "  Fix the violations above before this PR can be merged.",
            file=sys.stderr,
        )
        _banner("", err=True)
        return 1

    print(
        f"\n[benchmark] All {len(results)} suite(s) completed within {_fmt(timeout)}."
    )
    return 0


def _banner(msg: str, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    width = 60
    bar = "=" * width
    print(bar, file=stream)
    if msg:
        print(msg, file=stream)
        print(bar, file=stream)


if __name__ == "__main__":
    sys.exit(main())
