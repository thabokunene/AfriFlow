import argparse
import os
import re
import sys
from pathlib import Path


PATTERNS = [
    (re.compile(r"^\s*from\s+domains\."), "from afriflow.domains."),
    (re.compile(r"^\s*import\s+domains\b"), "import afriflow.domains"),
]


def scan_file(path: Path) -> list[str]:
    failures: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            for rx, _ in PATTERNS:
                if rx.search(line):
                    failures.append(f"{path}:{i}:{line.strip()}")
                    break
    return failures


def fix_file(path: Path) -> int:
    changed = 0
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for idx, line in enumerate(lines):
        for rx, replacement in PATTERNS:
            if rx.search(line):
                # Replace only the leading token "from domains." / "import domains"
                lines[idx] = rx.sub(replacement, line)
                changed += 1
                break
    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


def iter_py_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if p.is_file()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Check/fix import conventions in domain modules")
    ap.add_argument("--fix", action="store_true", help="Apply in-place fixes")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Check-only mode (default if --fix is not provided)",
    )
    ap.add_argument("--path", default="domains/cib", help="Relative directory to scan")
    args = ap.parse_args()

    base = Path(__file__).resolve().parents[1]
    target = (base / args.path).resolve()
    if not target.exists():
        print(f"Target path not found: {target}", file=sys.stderr)
        return 2

    failures: list[str] = []
    changed_total = 0
    for py in iter_py_files(target):
        if args.fix:
            changed_total += fix_file(py)
            continue
        failures.extend(scan_file(py))

    if args.fix:
        print(f"Imports normalized; files changed: {changed_total}")
        return 0

    if failures:
        print("Import convention violations found:", file=sys.stderr)
        for msg in failures:
            print(f"  {msg}", file=sys.stderr)
        return 1

    print("Import convention check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
