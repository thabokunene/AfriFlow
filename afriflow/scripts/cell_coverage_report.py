import argparse
import ast
import json
import os
import sys
import xml.etree.ElementTree as ET


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate per-module coverage breakdown for cell domain and enforce thresholds."
    )
    p.add_argument("--xml", default="coverage.xml")
    p.add_argument("--json", dest="json_path", default="coverage.json")
    p.add_argument("--include-subpath", default="domains/cell")
    p.add_argument("--include-file-pattern", default=None)
    p.add_argument(
        "--exclude-subpath",
        action="append",
        default=["tests", "site-packages", ".venv", "venv"],
    )
    p.add_argument("--line-min", type=float, default=80.0)
    p.add_argument("--branch-min", type=float, default=70.0)
    p.add_argument("--func-min", type=float, default=70.0)
    p.add_argument("--write-md", default="coverage/cell_coverage.md")
    p.add_argument("--write-json", default="coverage/cell_coverage_summary.json")
    p.add_argument("--github-summary", default=None)
    return p.parse_args()


def normalize(path: str) -> str:
    return path.replace("\\", "/")


def should_include(path: str, include_subpath: str, excludes: list[str]) -> bool:
    n = normalize(path)
    if any(e in n for e in excludes):
        return False
    return include_subpath in n


def load_cobertura(xml_path: str) -> dict[str, dict]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    by_file: dict[str, dict] = {}
    for cls in root.findall(".//packages/package/classes/class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue
        key = normalize(filename)

        lines_valid = int(cls.attrib.get("lines-valid", "0") or 0)
        lines_covered = int(cls.attrib.get("lines-covered", "0") or 0)
        branches_valid = int(cls.attrib.get("branches-valid", "0") or 0)
        branches_covered = int(cls.attrib.get("branches-covered", "0") or 0)

        line_rate = cls.attrib.get("line-rate")
        branch_rate = cls.attrib.get("branch-rate")

        rec = by_file.get(
            key,
            {
                "lines_valid": 0,
                "lines_covered": 0,
                "branches_valid": 0,
                "branches_covered": 0,
                "line_rate": None,
                "branch_rate": None,
            },
        )
        rec["lines_valid"] += lines_valid
        rec["lines_covered"] += lines_covered
        rec["branches_valid"] += branches_valid
        rec["branches_covered"] += branches_covered
        rec["line_rate"] = line_rate if line_rate is not None else rec["line_rate"]
        rec["branch_rate"] = branch_rate if branch_rate is not None else rec["branch_rate"]
        by_file[key] = rec

    return by_file


def load_coverage_json(json_path: str) -> dict[str, set[int]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    files = data.get("files", {})
    out: dict[str, set[int]] = {}
    for filename, meta in files.items():
        executed = meta.get("executed_lines") or []
        out[normalize(filename)] = set(int(x) for x in executed)
    return out


def parse_functions(file_path: str) -> list[tuple[int, int]]:
    with open(file_path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=file_path)
    funcs: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = int(getattr(node, "lineno", 1) or 1)
            end = int(getattr(node, "end_lineno", start) or start)
            funcs.append((start, end))
    return funcs


def pct(covered: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return (covered / total) * 100.0


def file_for_reading(filename: str) -> str | None:
    # coverage.xml paths are relative to the domains/ source root, so the actual
    # filesystem path (relative to the afriflow/ working directory) needs the
    # domains/ prefix prepended.
    candidates = [
        filename,
        os.path.join(os.getcwd(), filename),
        os.path.join("domains", filename),
        os.path.join(os.getcwd(), "domains", filename),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def format_md_table(rows: list[dict]) -> str:
    lines = [
        "| Module | Line Coverage | Branch Coverage | Function Coverage |",
        "|---|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    r["module"],
                    r["line_str"],
                    r["branch_str"],
                    r["func_str"],
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    if not os.path.exists(args.xml):
        print(f"coverage xml not found: {args.xml}", file=sys.stderr)
        return 2
    if not os.path.exists(args.json_path):
        print(f"coverage json not found: {args.json_path}", file=sys.stderr)
        return 2

    cobertura = load_cobertura(args.xml)
    executed_by_file = load_coverage_json(args.json_path)

    rows: list[dict] = []
    failures: list[str] = []

    for filename, cov in sorted(cobertura.items(), key=lambda x: x[0]):
        if not should_include(filename, args.include_subpath, args.exclude_subpath):
            continue
        if args.include_file_pattern:
            import re
            if not re.search(args.include_file_pattern, normalize(filename)):
                continue

        line_pct = (
            pct(cov["lines_covered"], cov["lines_valid"])
            if cov["lines_valid"] > 0
            else (
                float(cov["line_rate"]) * 100.0
                if cov.get("line_rate") is not None
                else 0.0
            )
        )

        branch_pct = (
            pct(cov["branches_covered"], cov["branches_valid"])
            if cov["branches_valid"] > 0
            else (
                float(cov["branch_rate"]) * 100.0
                if cov.get("branch_rate") is not None
                else 0.0
            )
        )

        readable = file_for_reading(filename)
        funcs = parse_functions(readable) if readable else []
        # coverage.json paths use the full afriflow/ root (e.g. domains/forex/...),
        # while coverage.xml paths are relative to afriflow/domains/ (e.g. forex/...).
        # Try both forms so function-covered counts are correct.
        norm_fn = normalize(filename)
        executed = (
            executed_by_file.get(norm_fn)
            or executed_by_file.get("domains/" + norm_fn)
            or set()
        )
        func_covered = 0
        for start, end in funcs:
            if any((start <= ln <= end) for ln in executed):
                func_covered += 1
        func_pct = pct(func_covered, len(funcs))

        row = {
            "module": filename,
            "line_pct": line_pct,
            "branch_pct": branch_pct,
            "func_pct": func_pct,
            "lines_valid": cov["lines_valid"],
            "lines_covered": cov["lines_covered"],
            "branches_valid": cov["branches_valid"],
            "branches_covered": cov["branches_covered"],
            "func_total": len(funcs),
            "func_covered": func_covered,
        }
        row["line_str"] = (
            f"{line_pct:.1f}% ({cov['lines_covered']}/{cov['lines_valid']})"
            if cov["lines_valid"] > 0
            else f"{line_pct:.1f}%"
        )
        row["branch_str"] = (
            f"{branch_pct:.1f}% ({cov['branches_covered']}/{cov['branches_valid']})"
            if cov["branches_valid"] > 0
            else (
                # pytest-cov emits only branch-rate (a ratio) on <class> elements,
                # not branches-valid / branches-covered counts.  Display the rate
                # so the column is never silently blank.
                f"{branch_pct:.1f}%"
                if cov.get("branch_rate") is not None
                else "n/a"
            )
        )
        row["func_str"] = f"{func_pct:.1f}% ({func_covered}/{len(funcs)})"

        rows.append(row)

        if line_pct + 1e-9 < args.line_min:
            failures.append(f"{filename} line {line_pct:.1f}% < {args.line_min:.1f}%")
        # Enforce branch gate when branch data is available from either count
        # attributes (branches_valid > 0) or the rate attribute (branch_rate).
        # Previously the gate was silently skipped whenever branches_valid == 0,
        # which always happened with pytest-cov's Cobertura output format.
        has_branch_data = cov["branches_valid"] > 0 or cov.get("branch_rate") is not None
        if has_branch_data and args.branch_min > 0 and branch_pct + 1e-9 < args.branch_min:
            failures.append(f"{filename} branch {branch_pct:.1f}% < {args.branch_min:.1f}%")
        if len(funcs) > 0 and func_pct + 1e-9 < args.func_min:
            failures.append(f"{filename} func {func_pct:.1f}% < {args.func_min:.1f}%")

    md = format_md_table(rows)
    os.makedirs(os.path.dirname(args.write_md) or ".", exist_ok=True)
    with open(args.write_md, "w", encoding="utf-8") as f:
        f.write(md)

    os.makedirs(os.path.dirname(args.write_json) or ".", exist_ok=True)
    with open(args.write_json, "w", encoding="utf-8") as f:
        json.dump({"include_subpath": args.include_subpath, "rows": rows}, f, indent=2)

    if args.github_summary:
        with open(args.github_summary, "a", encoding="utf-8") as f:
            f.write(f"\n## Coverage Report: {args.include_subpath} (Per Module)\n\n")
            f.write(md)

    if failures:
        print("Cell domain coverage thresholds failed:", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print("Cell domain coverage thresholds passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
