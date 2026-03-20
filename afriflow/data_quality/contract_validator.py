"""
@file contract_validator.py
@description Contract Validator - Validate data against YAML contracts
@author Thabo Kunene
@created 2026-03-19

This module validates incoming data against domain contracts defined
in YAML format. It ensures data conforms to expected schemas and
business rules.

Key Classes:
- ContractViolation: Data contract violation record
- ContractValidator: Main validation engine

Features:
- YAML contract loading
- Schema validation (required fields, types)
- Business rule validation
- Violation tracking and reporting
- Per-domain contract enforcement

Usage:
    >>> from afriflow.data_quality.contract_validator import ContractValidator
    >>> validator = ContractValidator()
    >>> validator.load_contract("cib", "contracts/cib_contract.yml")
    >>> violations = validator.validate("cib", {"amount": 1000})

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import yaml

from afriflow.logging_config import get_logger

logger = get_logger("data_quality.contract")


@dataclass
class ContractViolation:
    """
    Data contract violation record.

    Represents a single violation of a data contract.

    Attributes:
        violation_id: Unique identifier
        domain: Domain name
        contract_version: Contract version violated
        field: Field that violated contract
        violation_type: Type of violation
        expected: Expected value/type
        actual: Actual value/type
        severity: Violation severity (WARNING, ERROR, CRITICAL)
        timestamp: Violation timestamp

    Example:
        >>> violation = ContractViolation(
        ...     domain="cib",
        ...     field="amount",
        ...     violation_type="type_mismatch",
        ...     expected="float",
        ...     actual="str"
        ... )
    """
    violation_id: str  # Unique identifier
    domain: str  # Domain name
    contract_version: str  # Contract version
    field: str  # Field that violated
    violation_type: str  # Type of violation
    expected: Any  # Expected value/type
    actual: Any  # Actual value/type
    severity: str = "ERROR"  # Severity level
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "violation_id": self.violation_id,
            "domain": self.domain,
            "contract_version": self.contract_version,
            "field": self.field,
            "violation_type": self.violation_type,
            "expected": str(self.expected),
            "actual": str(self.actual),
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


class ContractValidator:
    """
    Data contract validation engine.

    Validates incoming data against domain contracts
    defined in YAML format.

    Attributes:
        _contracts: Dictionary mapping domain to contract definition
        _violations: List of contract violations

    Example:
        >>> validator = ContractValidator()
        >>> validator.load_contract("cib", "contracts/cib_contract.yml")
        >>> violations = validator.validate("cib", {"amount": 1000})
    """

    def __init__(self) -> None:
        """Initialize contract validator with empty contract store."""
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._violations: List[ContractViolation] = []
        logger.info("ContractValidator initialized")

    def load_contract(
        self,
        domain: str,
        contract_path: str
    ) -> Dict[str, Any]:
        """
        Load contract from YAML file.

        Args:
            domain: Domain name
            contract_path: Path to YAML contract file

        Returns:
            Loaded contract dictionary

        Example:
            >>> contract = validator.load_contract(
            ...     "cib", "contracts/cib_contract.yml"
            ... )
        """
        try:
            with open(contract_path, 'r') as f:
                contract = yaml.safe_load(f)

            self._contracts[domain] = contract
            logger.info(
                f"Contract loaded for {domain} from {contract_path}"
            )
            return contract

        except FileNotFoundError:
            logger.error(f"Contract file not found: {contract_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in contract: {e}")
            raise

    def load_contract_from_dict(
        self,
        domain: str,
        contract: Dict[str, Any]
    ) -> None:
        """
        Load contract from dictionary.

        Args:
            domain: Domain name
            contract: Contract dictionary

        Example:
            >>> validator.load_contract_from_dict("cib", {
            ...     "version": "1.0",
            ...     "required_fields": ["amount", "currency"]
            ... })
        """
        self._contracts[domain] = contract
        logger.info(f"Contract loaded for {domain} from dictionary")

    def validate(
        self,
        domain: str,
        data: Dict[str, Any]
    ) -> List[ContractViolation]:
        """
        Validate data against domain contract.

        Args:
            domain: Domain name
            data: Data dictionary to validate

        Returns:
            List of ContractViolation objects

        Example:
            >>> violations = validator.validate(
            ...     "cib", {"amount": 1000, "currency": "ZAR"}
            ... )
        """
        contract = self._contracts.get(domain)
        if not contract:
            logger.warning(f"No contract found for {domain}")
            return []

        violations = []
        version = contract.get("version", "unknown")

        # Check required fields
        required_fields = contract.get("required_fields", [])
        for field in required_fields:
            if field not in data:
                violation = self._create_violation(
                    domain=domain,
                    version=version,
                    field=field,
                    violation_type="missing_required_field",
                    expected="present",
                    actual="missing"
                )
                violations.append(violation)

        # Check field types
        field_types = contract.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in data:
                actual_type = type(data[field]).__name__
                if not self._is_valid_type(data[field], expected_type):
                    violation = self._create_violation(
                        domain=domain,
                        version=version,
                        field=field,
                        violation_type="type_mismatch",
                        expected=expected_type,
                        actual=actual_type
                    )
                    violations.append(violation)

        # Check business rules
        rules = contract.get("rules", [])
        for rule in rules:
            rule_violations = self._check_rule(data, rule, domain, version)
            violations.extend(rule_violations)

        # Store violations
        self._violations.extend(violations)

        if violations:
            logger.warning(
                f"Contract validation failed for {domain}: "
                f"{len(violations)} violations"
            )
        else:
            logger.debug(f"Contract validation passed for {domain}")

        return violations

    def _is_valid_type(self, value: Any, expected_type: str) -> bool:
        """
        Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type name

        Returns:
            True if type matches
        """
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": (int, float),
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
        }

        expected = type_map.get(expected_type.lower())
        if expected:
            return isinstance(value, expected)
        return True  # Unknown type, assume valid

    def _check_rule(
        self,
        data: Dict[str, Any],
        rule: Dict[str, Any],
        domain: str,
        version: str
    ) -> List[ContractViolation]:
        """
        Check a business rule against data.

        Args:
            data: Data dictionary
            rule: Rule definition
            domain: Domain name
            version: Contract version

        Returns:
            List of violations
        """
        violations = []
        rule_type = rule.get("type")

        if rule_type == "min_value":
            field = rule.get("field")
            min_val = rule.get("value")
            if field in data and data[field] < min_val:
                violation = self._create_violation(
                    domain=domain,
                    version=version,
                    field=field,
                    violation_type="min_value_violation",
                    expected=f">= {min_val}",
                    actual=str(data[field])
                )
                violations.append(violation)

        elif rule_type == "max_value":
            field = rule.get("field")
            max_val = rule.get("value")
            if field in data and data[field] > max_val:
                violation = self._create_violation(
                    domain=domain,
                    version=version,
                    field=field,
                    violation_type="max_value_violation",
                    expected=f"<= {max_val}",
                    actual=str(data[field])
                )
                violations.append(violation)

        elif rule_type == "allowed_values":
            field = rule.get("field")
            allowed = rule.get("values")
            if field in data and data[field] not in allowed:
                violation = self._create_violation(
                    domain=domain,
                    version=version,
                    field=field,
                    violation_type="allowed_values_violation",
                    expected=str(allowed),
                    actual=str(data[field])
                )
                violations.append(violation)

        return violations

    def _create_violation(
        self,
        domain: str,
        version: str,
        field: str,
        violation_type: str,
        expected: Any,
        actual: Any,
        severity: str = "ERROR"
    ) -> ContractViolation:
        """Create a contract violation record."""
        import uuid
        violation_id = f"VIOL-{uuid.uuid4().hex[:8].upper()}"
        return ContractViolation(
            violation_id=violation_id,
            domain=domain,
            contract_version=version,
            field=field,
            violation_type=violation_type,
            expected=expected,
            actual=actual,
            severity=severity
        )

    def get_violations(
        self,
        domain: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[ContractViolation]:
        """
        Get contract violations with optional filters.

        Args:
            domain: Filter by domain (optional)
            severity: Filter by severity (optional)

        Returns:
            List of matching violations
        """
        violations = self._violations

        if domain:
            violations = [v for v in violations if v.domain == domain]
        if severity:
            violations = [v for v in violations if v.severity == severity]

        return violations

    def get_statistics(self) -> Dict[str, Any]:
        """Get contract validation statistics."""
        violations = self._violations
        severity_counts = {}
        domain_counts = {}

        for v in violations:
            severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1
            domain_counts[v.domain] = domain_counts.get(v.domain, 0) + 1

        return {
            "total_violations": len(violations),
            "severity_breakdown": severity_counts,
            "domain_breakdown": domain_counts,
            "contracts_loaded": len(self._contracts),
        }


__all__ = [
    "ContractViolation",
    "ContractValidator",
]
