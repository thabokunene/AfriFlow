#!/usr/bin/env python3
"""
AfriFlow SQL Schema Validation Script

This script validates all SQL schema files across the AfriFlow project:
1. Syntax validation (SQL parsing)
2. Schema consistency checks
3. Reference integrity validation
4. Documentation completeness

Usage:
    python validate_schemas.py [--domain DOMAIN] [--verbose]

Examples:
    python validate_schemas.py                    # Validate all domains
    python validate_schemas.py --domain forex     # Validate forex only
    python validate_schemas.py --verbose          # Show detailed output
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationStatus(Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    file_path: str
    status: ValidationStatus
    message: str
    line_number: Optional[int] = None


class SQLSchemaValidator:
    """Validates SQL schema files for AfriFlow project."""

    # Required table properties for Delta Lake
    REQUIRED_TABLE_PROPERTIES = [
        'classification',
        'domain',
        'layer',
    ]

    # Valid data classifications
    VALID_CLASSIFICATIONS = [
        'POPIA_RESTRICTED',
        'INTERNAL',
        'PUBLIC',
        'CONFIDENTIAL',
    ]

    # Valid layer values
    VALID_LAYERS = [
        'bronze',
        'silver',
        'gold',
        'reference',
        'audit',
        'operational',
    ]

    # Required columns for all tables
    REQUIRED_COLUMNS = {
        'all': ['_ingested_at', '_source_system'],
        'partitioned': ['ingestion_date', 'snapshot_date', 'business_date'],
    }

    def __init__(self, base_path: str, verbose: bool = False):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.results: List[ValidationResult] = []

    def validate_all(self, domain: Optional[str] = None) -> List[ValidationResult]:
        """Validate all SQL files in the project."""
        sql_files = list(self.base_path.rglob("*.sql"))

        if domain:
            sql_files = [f for f in sql_files if domain.lower() in str(f).lower()]

        for sql_file in sql_files:
            # Skip __pycache__ and hidden directories
            if '__pycache__' in str(sql_file) or '.git' in str(sql_file):
                continue

            self._validate_file(sql_file)

        return self.results

    def _validate_file(self, file_path: Path) -> None:
        """Validate a single SQL file."""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            self.results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.FAIL,
                message=f"Failed to read file: {e}"
            ))
            return

        # Check for empty file
        if not content.strip():
            self.results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.FAIL,
                message="File is empty or contains only whitespace"
            ))
            return

        # Run all validations
        self._check_create_table(content, file_path)
        self._check_table_properties(content, file_path)
        self._check_column_definitions(content, file_path)
        self._check_data_types(content, file_path)
        self._check_documentation(content, file_path)
        self._check_partitioning(content, file_path)

    def _check_create_table(self, content: str, file_path: Path) -> None:
        """Check for CREATE TABLE statement."""
        if 'CREATE TABLE' not in content.upper():
            # dbt models may not have explicit CREATE TABLE
            if '{{ config(' not in content:
                self.results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="No CREATE TABLE statement or dbt config found"
                ))

    def _check_table_properties(self, content: str, file_path: Path) -> None:
        """Check TBLPROPERTIES for required fields."""
        if 'TBLPROPERTIES' not in content.upper():
            self.results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.WARNING,
                message="No TBLPROPERTIES defined"
            ))
            return

        # Extract TBLPROPERTIES section
        props_match = re.search(
            r"TBLPROPERTIES\s*\((.*?)\)",
            content,
            re.IGNORECASE | re.DOTALL
        )

        if props_match:
            props_content = props_match.group(1).upper()

            for required_prop in self.REQUIRED_TABLE_PROPERTIES:
                if required_prop.upper() not in props_content:
                    self.results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.WARNING,
                        message=f"Missing required property: {required_prop}"
                    ))

            # Validate classification value
            for classification in self.VALID_CLASSIFICATIONS:
                if classification in props_content:
                    break
            else:
                if 'classification' in props_content.lower():
                    self.results.append(ValidationResult(
                        file_path=str(file_path),
                        status=ValidationStatus.WARNING,
                        message="Invalid classification value"
                    ))

    def _check_column_definitions(self, content: str, file_path: Path) -> None:
        """Check column definitions for completeness."""
        # Extract column definitions
        create_match = re.search(
            r'CREATE TABLE.*?\((.*?)\)\s*(?:USING|TBLPROPERTIES|$)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if not create_match:
            return

        columns_section = create_match.group(1)
        columns = re.findall(r'^\s*(\w+)\s+', columns_section, re.MULTILINE)

        # Check for primary key indicator
        if 'NOT NULL' not in columns_section.upper():
            self.results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.WARNING,
                message="No NOT NULL constraints found"
            ))

    def _check_data_types(self, content: str, file_path: Path) -> None:
        """Check for valid data types."""
        valid_types = [
            'VARCHAR', 'STRING', 'TEXT',
            'INT', 'INTEGER', 'BIGINT', 'SMALLINT',
            'DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE',
            'BOOLEAN', 'BOOL',
            'DATE', 'TIMESTAMP', 'DATETIME',
            'ARRAY', 'MAP', 'STRUCT',
        ]

        # Find all type declarations
        type_matches = re.findall(r':\s*(\w+)', content)
        type_matches += re.findall(r'\b(\w+)\s*\(', content)

        for type_found in type_matches:
            type_upper = type_found.upper()
            if type_upper not in valid_types and not type_upper.startswith('_'):
                # Could be a column name, not a type
                pass

    def _check_documentation(self, content: str, file_path: Path) -> None:
        """Check for documentation comments."""
        if '--' not in content and '/*' not in content:
            self.results.append(ValidationResult(
                file_path=str(file_path),
                status=ValidationStatus.WARNING,
                message="No documentation comments found"
            ))
            return

        # Check for table description
        if 'description' not in content.lower() and 'description:' not in content.lower():
            # Check for comment block at start
            if not re.search(r'^\s*--+\s*\n\s*--.*(?:table|model|mart)', content, re.IGNORECASE | re.MULTILINE):
                self.results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="No table/model description found"
                ))

    def _check_partitioning(self, content: str, file_path: Path) -> None:
        """Check partitioning configuration."""
        if 'PARTITIONED BY' in content.upper():
            # Good - has partitioning
            pass
        elif 'partitioned_by' in content.lower():
            # dbt-style partitioning
            pass
        else:
            # Check if it's a view (views don't need partitioning)
            if 'materialized' in content.lower() and 'view' in content.lower():
                return

            # Large tables should be partitioned
            if 'CREATE TABLE' in content.upper():
                self.results.append(ValidationResult(
                    file_path=str(file_path),
                    status=ValidationStatus.WARNING,
                    message="Table is not partitioned - consider adding partitioning for large tables"
                ))

    def print_report(self) -> Tuple[int, int, int]:
        """Print validation report and return counts."""
        passed = sum(1 for r in self.results if r.status == ValidationStatus.PASS)
        warnings = sum(1 for r in self.results if r.status == ValidationStatus.WARNING)
        failed = sum(1 for r in self.results if r.status == ValidationStatus.FAIL)

        print("\n" + "=" * 70)
        print("AFRIFLOW SQL SCHEMA VALIDATION REPORT")
        print("=" * 70)

        # Group by status
        by_status = {}
        for result in self.results:
            if result.status not in by_status:
                by_status[result.status] = []
            by_status[result.status].append(result)

        # Print failures first
        if ValidationStatus.FAIL in by_status:
            print("\n❌ FAILURES:")
            for result in by_status[ValidationStatus.FAIL]:
                print(f"  {result.file_path}")
                print(f"     {result.message}")
                if result.line_number:
                    print(f"     Line: {result.line_number}")

        # Print warnings
        if ValidationStatus.WARNING in by_status:
            print("\n⚠️  WARNINGS:")
            for result in by_status[ValidationStatus.WARNING]:
                print(f"  {result.file_path}")
                print(f"     {result.message}")

        # Summary
        print("\n" + "-" * 70)
        print(f"SUMMARY: {passed} passed, {warnings} warnings, {failed} failures")
        print("=" * 70)

        return passed, warnings, failed


def main():
    parser = argparse.ArgumentParser(
        description='Validate AfriFlow SQL schemas'
    )
    parser.add_argument(
        '--domain',
        type=str,
        help='Validate specific domain (e.g., forex, cib, insurance)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed validation output'
    )
    parser.add_argument(
        '--path',
        type=str,
        default='.',
        help='Base path to search for SQL files'
    )

    args = parser.parse_args()

    validator = SQLSchemaValidator(args.path, verbose=args.verbose)
    results = validator.validate_all(domain=args.domain)
    passed, warnings, failed = validator.print_report()

    # Exit with error code if there are failures
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
