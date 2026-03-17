import argparse
import os
import sys
import xml.etree.ElementTree as ET


def parse_args():
    p = argparse.ArgumentParser(description="Per-file coverage gate")
    p.add_argument("--report", default="coverage.xml")
    p.add_argument("--min", type=float, default=90.0)
    p.add_argument(
        "--include-subpath",
        action="append",
        default=["domains"],
        help="Only enforce for files containing this subpath (can be repeated)",
    )
    p.add_argument(
        "--exclude-subpath",
        action="append",
        default=["tests", "site-packages", ".venv", "venv"],
        help="Exclude files containing this subpath (can be repeated)",
    )
    return p.parse_args()


def normalize(path: str) -> str:
    return path.replace("\\", "/")


def should_check(path: str, includes, excludes) -> bool:
    n = normalize(path)
    if any(e in n for e in excludes):
        return False
    return any(i in n for i in includes)


def main():
    args = parse_args()
    if not os.path.exists(args.report):
        print(f"Coverage report not found: {args.report}", file=sys.stderr)
        sys.exit(2)
    tree = ET.parse(args.report)
    root = tree.getroot()
    failures = []
    for pkg in root.findall(".//packages/package"):
        for cls in pkg.findall("./classes/class"):
            filename = cls.attrib.get("filename")
            if not filename:
                continue
            if not should_check(filename, args.include_subpath, args.exclude_subpath):
                continue
            rate = cls.attrib.get("line-rate")
            try:
                pct = float(rate) * 100.0
            except Exception:
                pct = 0.0
            if pct + 1e-9 < args.min:
                failures.append((filename, pct))
    if failures:
        print("Per-file coverage gate failed:", file=sys.stderr)
        for fn, pct in sorted(failures):
            print(f"  {fn}: {pct:.1f}% < {args.min:.1f}%", file=sys.stderr)
        sys.exit(1)
    print(f"Per-file coverage gate passed (>= {args.min:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
