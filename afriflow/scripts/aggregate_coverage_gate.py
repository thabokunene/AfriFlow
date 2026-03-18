"""
@file aggregate_coverage_gate.py
@description Aggregate branch coverage parser and gating mechanism for AfriFlow.
             Processes multiple Cobertura XML files to calculate the global
             branch coverage percentage across the entire test matrix.
             Fails the build if global branch coverage is below the threshold.
             Provides detailed reporting on the largest branch coverage gaps.
@author Thabo Kunene
@created 2026-03-18
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class FileCoverage:
    filename: str
    branches_covered: int
    branches_valid: int

    @property
    def branch_rate(self) -> float:
        if self.branches_valid == 0:
            return 100.0
        return (self.branches_covered / self.branches_valid) * 100.0


def parse_cobertura_xml(xml_path: str) -> List[FileCoverage]:
    """Parses a Cobertura XML file and extracts per-file branch coverage data."""
    if not os.path.exists(xml_path):
        print(f"Warning: Coverage report not found at {xml_path}")
        return []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        file_coverages = []

        # Cobertura XML structure: coverage -> packages -> package -> classes -> class
        for cls in root.findall(".//class"):
            filename = cls.get("filename")
            branches_covered = int(cls.get("branches-covered", 0))
            branches_valid = int(cls.get("branches-valid", 0))
            
            if filename:
                file_coverages.append(FileCoverage(
                    filename=filename,
                    branches_covered=branches_covered,
                    branches_valid=branches_valid
                ))
        
        return file_coverages
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Global Branch Coverage Gate")
    parser.add_argument("--xml", action="append", required=True, help="Path to coverage.xml files (can be repeated)")
    parser.add_argument("--min-branch-coverage", type=float, default=75.0, help="Minimum global branch coverage percentage")
    parser.add_argument("--show-gaps", type=int, default=10, help="Number of top gaps to show")
    args = parser.parse_args()

    all_file_coverages: Dict[str, FileCoverage] = {}

    for xml_path in args.xml:
        file_coverages = parse_cobertura_xml(xml_path)
        for fc in file_coverages:
            if fc.filename in all_file_coverages:
                # If we have multiple reports for the same file, we take the max (assuming different test suites)
                # Alternatively, we could sum them if they are disjoint, but Cobertura reports usually 
                # reflect the state after all tests in that run. If we have multiple XMLs from different 
                # engines, we want to see the combined effect. 
                # For simplicity in aggregation across multiple engines/runs, we'll track the best coverage 
                # seen for each file across all reports.
                existing = all_file_coverages[fc.filename]
                all_file_coverages[fc.filename] = FileCoverage(
                    filename=fc.filename,
                    branches_covered=max(existing.branches_covered, fc.branches_covered),
                    branches_valid=max(existing.branches_valid, fc.branches_valid)
                )
            else:
                all_file_coverages[fc.filename] = fc

    total_branches_covered = sum(fc.branches_covered for fc in all_file_coverages.values())
    total_branches_valid = sum(fc.branches_valid for fc in all_file_coverages.values())

    if total_branches_valid == 0:
        print("Error: No branch data found in the provided coverage reports.")
        sys.exit(1)

    global_branch_coverage = (total_branches_covered / total_branches_valid) * 100.0

    print("=" * 60)
    print("GLOBAL BRANCH COVERAGE REPORT")
    print("-" * 60)
    print(f"Total Branches Valid:   {total_branches_valid}")
    print(f"Total Branches Covered: {total_branches_covered}")
    print(f"Global Branch Coverage: {global_branch_coverage:.2f}%")
    print(f"Minimum Required:       {args.min_branch_coverage:.2f}%")
    print("-" * 60)

    if global_branch_coverage < args.min_branch_coverage:
        print(f"STATUS: \u274c FAILED")
        print(f"Error: Global branch coverage {global_branch_coverage:.2f}% is below the threshold of {args.min_branch_coverage:.2f}%")
        
        # Show top gaps
        gaps = sorted(
            [fc for fc in all_file_coverages.values() if fc.branches_valid > 0],
            key=lambda x: x.branch_rate
        )
        
        print("\nTOP COVERAGE GAPS (Files with lowest branch coverage):")
        for i, gap in enumerate(gaps[:args.show_gaps], 1):
            missing = gap.branches_valid - gap.branches_covered
            print(f"  {i}. {gap.filename}: {gap.branch_rate:.1f}% ({missing} branches missing)")
        
        print("=" * 60)
        sys.exit(1)
    else:
        print(f"STATUS: \u2705 PASSED")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
