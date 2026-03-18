import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _normalize(p: str) -> str:
    return p.replace("\\", "/")


def _changed_in_subtree(changed: List[str], subtree: str) -> List[str]:
    n = _normalize(subtree)
    return [c for c in changed if n in _normalize(c)]


def _match_patterns(files: List[str], patterns: List[str]) -> bool:
    if not patterns:
        return True
    for f in files:
        if any(fnmatch.fnmatch(_normalize(f), pat) for pat in patterns):
            return True
    return False


def _match_types(files: List[str], types: List[str]) -> bool:
    if not types:
        return True
    for f in files:
        ext = os.path.splitext(f)[1].lstrip(".").lower()
        if ext in {t.lower() for t in types}:
            return True
    return False


def _match_naming(files: List[str], regex: str | None) -> bool:
    if not regex:
        return True
    r = re.compile(regex)
    for f in files:
        if r.search(os.path.basename(f)):
            return True
    return False


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="afriflow/config/coverage_gates.json")
    p.add_argument("--coverage-xml", default="coverage.xml")
    p.add_argument("--coverage-json", default="coverage.json")
    p.add_argument("--changed-files", default="coverage/changed_files.json")
    p.add_argument("--log-json", default="coverage/gating_log.json")
    return p.parse_args()


def _effective_threshold(value: int, env_key: str | None) -> int:
    if not env_key:
        return value
    v = os.environ.get(env_key, "").strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return value
    return 0


def _run_gate(
    subtree: Dict[str, Any],
    cov_xml: str,
    cov_json: str,
) -> Tuple[int, float]:
    gates = subtree["gates"]
    cond = subtree.get("conditions", {})
    line_min = gates.get("line_min", 0)
    branch_min = _effective_threshold(gates.get("branch_min", 0), cond.get("branch_gate_env"))
    func_min = _effective_threshold(gates.get("func_min", 0), cond.get("function_gate_env"))
    # coverage_subpath overrides path for XML matching; path uses the domains/ prefix
    # which is correct for git-diff change detection but wrong for coverage.xml paths
    # (XML paths are relative to afriflow/domains/, not afriflow/).
    include_subpath = gates.get("coverage_subpath", subtree["path"])
    include_file_pattern = gates.get("include_file_pattern")
    write_md = gates.get("write_md", f"coverage/{subtree['name']}_coverage.md")
    write_json = gates.get("write_json", f"coverage/{subtree['name']}_coverage_summary.json")
    t0 = time.time()
    cmd = [
        sys.executable,
        "scripts/cell_coverage_report.py",
        "--xml",
        cov_xml,
        "--json",
        cov_json,
        "--include-subpath",
        include_subpath,
        "--line-min",
        str(line_min),
        "--branch-min",
        str(branch_min),
        "--func-min",
        str(func_min),
        "--write-md",
        write_md,
        "--write-json",
        write_json,
    ]
    if include_file_pattern:
        cmd.extend(["--include-file-pattern", include_file_pattern])
    rc = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__))).returncode
    dt = time.time() - t0
    return rc, dt


def run_cli(argv: List[str] | None = None) -> int:
    args = _parse_args() if argv is None else argparse.Namespace(**argv)
    config = _load_json(args.config)
    changed_obj = _load_json(args.changed_files) if os.path.exists(args.changed_files) else {"files": []}
    changed_files = changed_obj.get("files", [])
    log: Dict[str, Any] = {"entries": [], "started_at": time.time()}
    overall_rc = 0
    for subtree in config.get("subtrees", []):
        start = time.time()
        affected = _changed_in_subtree(changed_files, subtree["path"])
        filters = subtree.get("filters", {})
        f_patterns = filters.get("file_patterns") or []
        f_types = filters.get("file_types") or []
        f_naming = filters.get("naming_regex")
        match = bool(affected) and _match_patterns(affected, f_patterns) and _match_types(affected, f_types) and _match_naming(affected, f_naming)
        filter_dt = time.time() - start
        if match:
            rc, gate_dt = _run_gate(subtree, args.coverage_xml, args.coverage_json)
            status = "passed" if rc == 0 else "failed"
            overall_rc = rc if rc != 0 else overall_rc
        else:
            rc = 0
            gate_dt = 0.0
            status = "skipped"
        log["entries"].append(
            {
                "subtree": subtree["name"],
                "path": subtree["path"],
                "affected_count": len(affected),
                "filters_match": match,
                "conditions": subtree.get("conditions", {}),
                "filter_duration_ms": int(filter_dt * 1000),
                "gate_status": status,
                "gate_duration_ms": int(gate_dt * 1000),
            }
        )
    log["finished_at"] = time.time()
    _write_json(args.log_json, log)
    return overall_rc


if __name__ == "__main__":
    raise SystemExit(run_cli())
