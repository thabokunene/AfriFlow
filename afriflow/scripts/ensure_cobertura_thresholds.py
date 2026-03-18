import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Thresholds:
    line_min: float
    branch_min: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--xml", required=True, help="Path to cobertura coverage.xml")
    p.add_argument("--filename", required=True, help="Cobertura filename attribute to match")
    p.add_argument("--line-min", type=float, required=True)
    p.add_argument("--branch-min", type=float, required=True)
    return p.parse_args()


def _pct(rate: Optional[str]) -> float:
    if rate is None:
        return 0.0
    return float(rate) * 100.0


def find_file_rates(xml_path: str, filename: str) -> Optional[Tuple[float, float]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    classes = root.findall(".//class")
    for cls in classes:
        if cls.get("filename") == filename:
            return (_pct(cls.get("line-rate")), _pct(cls.get("branch-rate")))
    return None


def main() -> int:
    args = parse_args()
    thresholds = Thresholds(line_min=args.line_min, branch_min=args.branch_min)
    rates = find_file_rates(args.xml, args.filename)
    if rates is None:
        print(f"coverage.xml does not contain filename={args.filename}", file=sys.stderr)
        return 2
    line_pct, branch_pct = rates
    failures = []
    if line_pct + 1e-9 < thresholds.line_min:
        failures.append(f"LINE {line_pct:.2f}% < {thresholds.line_min:.2f}%")
    if branch_pct + 1e-9 < thresholds.branch_min:
        failures.append(f"BRANCH {branch_pct:.2f}% < {thresholds.branch_min:.2f}%")
    if failures:
        print("Coverage thresholds failed for %s: %s" % (args.filename, "; ".join(failures)), file=sys.stderr)
        return 1
    print("Coverage thresholds passed for %s: line=%.2f%% branch=%.2f%%" % (args.filename, line_pct, branch_pct))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
