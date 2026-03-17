"""
Governance - Insurance Act Compliance

The Insurance Act and related regulations govern
insurance business in South Africa. We ensure
compliance with policyholder protection rules,
treatment of customers, and fair value requirements.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.insurance_compliance")


class PolicyType(Enum):
    """Type of insurance policy."""
    LIFE = "life"
    SHORT_TERM = "short_term"
    HEALTH = "health"
    RETIREMENT = "retirement"
    INVESTMENT = "investment"


class ComplianceStatus(Enum):
    """Compliance status."""
    COMPLIANT = "compliant"
    REVIEW_REQUIRED = "review_required"
    NON_COMPLIANT = "non_compliant"


@dataclass
class PolicyholderProtectionCheck:
    """
    Policyholder protection compliance check.

    Attributes:
        policy_id: Policy identifier
        check_type: Type of check
        passed: Whether check passed
        checked_at: When check was performed
        issues: List of issues found
    """
    policy_id: str
    check_type: str
    passed: bool
    checked_at: datetime = field(default_factory=datetime.utcnow)
    issues: List[str] = field(default_factory=list)


class InsuranceActCompliance:
    """
    Ensures compliance with Insurance Act requirements.

    We check policyholder protection, fair treatment
    of customers, and regulatory reporting requirements.

    Attributes:
        policies: Policy records by ID
        compliance_checks: Compliance checks by policy
    """

    # Required policyholder protections
    REQUIRED_PROTECTIONS = [
        "free_look_period",
        "disclosure_document",
        "complaints_procedure",
        "cancellation_rights",
        "privacy_notice",
    ]

    def __init__(self) -> None:
        """Initialize Insurance Act compliance checker."""
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.compliance_checks: Dict[str, List[PolicyholderProtectionCheck]] = {}

        logger.info("InsuranceActCompliance initialized")

    def register_policy(
        self,
        policy_id: str,
        policy_type: PolicyType,
        policyholder_id: str,
        sum_assured: float,
        premium: float,
        inception_date: datetime,
        protections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Register an insurance policy.

        Args:
            policy_id: Policy identifier
            policy_type: Type of policy
            policyholder_id: Policyholder identifier
            sum_assured: Sum assured
            premium: Annual premium
            inception_date: Policy inception date
            protections: List of protections applied

        Returns:
            Policy record
        """
        log_operation(
            logger,
            "register_policy",
            "started",
            policy_id=policy_id,
            policy_type=policy_type.value,
        )

        policy = {
            "policy_id": policy_id,
            "policy_type": policy_type.value,
            "policyholder_id": policyholder_id,
            "sum_assured": sum_assured,
            "premium": premium,
            "inception_date": inception_date.isoformat(),
            "protections": protections or [],
            "status": "active",
            "registered_at": datetime.utcnow().isoformat(),
        }

        self.policies[policy_id] = policy
        self.compliance_checks[policy_id] = []

        log_operation(
            logger,
            "register_policy",
            "completed",
            policy_id=policy_id,
        )

        return policy

    def check_policyholder_protections(
        self,
        policy_id: str
    ) -> List[PolicyholderProtectionCheck]:
        """
        Check policyholder protection compliance.

        Args:
            policy_id: Policy identifier

        Returns:
            List of protection checks

        Raises:
            ConfigurationError: If policy not found
        """
        if policy_id not in self.policies:
            raise ConfigurationError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]
        checks = []

        for protection in self.REQUIRED_PROTECTIONS:
            has_protection = protection in policy.get("protections", [])

            check = PolicyholderProtectionCheck(
                policy_id=policy_id,
                check_type=f"protection_{protection}",
                passed=has_protection,
                issues=[] if has_protection else [f"Missing {protection}"]
            )

            checks.append(check)

        self.compliance_checks[policy_id] = checks
        logger.info(f"Completed {len(checks)} protection checks for {policy_id}")

        return checks

    def check_free_look_period(
        self,
        policy_id: str,
        current_date: Optional[datetime] = None
    ) -> bool:
        """
        Check if policy is within free look period.

        Args:
            policy_id: Policy identifier
            current_date: Current date (defaults to now)

        Returns:
            True if within free look period

        Raises:
            ConfigurationError: If policy not found
        """
        if policy_id not in self.policies:
            raise ConfigurationError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]
        inception = datetime.fromisoformat(policy["inception_date"])
        current = current_date or datetime.utcnow()

        # 31-day free look period
        free_look_end = inception + timedelta(days=31)

        is_within = current <= free_look_end
        logger.debug(
            f"Policy {policy_id} free look: {is_within} "
            f"(ends {free_look_end.isoformat()})"
        )

        return is_within

    def check_premium_affordability(
        self,
        policy_id: str,
        policyholder_income: float
    ) -> Dict[str, Any]:
        """
        Check premium affordability (Treating Customers Fairly).

        Args:
            policy_id: Policy identifier
            policyholder_income: Annual policyholder income

        Returns:
            Affordability assessment

        Raises:
            ConfigurationError: If policy not found
        """
        if policy_id not in self.policies:
            raise ConfigurationError(f"Policy {policy_id} not found")

        policy = self.policies[policy_id]
        premium = policy["premium"]

        # Premium should not exceed 30% of income for protection products
        max_affordable = policyholder_income * 0.30
        is_affordable = premium <= max_affordable

        return {
            "policy_id": policy_id,
            "premium": premium,
            "policyholder_income": policyholder_income,
            "max_affordable": max_affordable,
            "is_affordable": is_affordable,
            "premium_to_income_ratio": premium / policyholder_income if policyholder_income > 0 else 0,
        }

    def get_compliance_status(
        self,
        policy_id: str
    ) -> Dict[str, Any]:
        """
        Get overall compliance status for a policy.

        Args:
            policy_id: Policy identifier

        Returns:
            Compliance status dictionary

        Raises:
            ConfigurationError: If policy not found
        """
        if policy_id not in self.policies:
            raise ConfigurationError(f"Policy {policy_id} not found")

        checks = self.compliance_checks.get(policy_id, [])

        passed = sum(1 for c in checks if c.passed)
        total = len(checks)

        if total == 0:
            status = ComplianceStatus.REVIEW_REQUIRED
        elif passed == total:
            status = ComplianceStatus.COMPLIANT
        elif passed >= total * 0.8:
            status = ComplianceStatus.REVIEW_REQUIRED
        else:
            status = ComplianceStatus.NON_COMPLIANT

        return {
            "policy_id": policy_id,
            "status": status.value,
            "checks_passed": passed,
            "checks_total": total,
            "compliance_percentage": (passed / total * 100) if total > 0 else 0,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compliance statistics.

        Returns:
            Statistics dictionary
        """
        by_type: Dict[str, int] = {}
        status_counts: Dict[str, int] = {
            "compliant": 0,
            "review_required": 0,
            "non_compliant": 0,
        }

        for policy_id in self.policies:
            policy = self.policies[policy_id]
            policy_type = policy["policy_type"]
            by_type[policy_type] = by_type.get(policy_type, 0) + 1

            status = self.get_compliance_status(policy_id)
            status_counts[status["status"]] += 1

        return {
            "total_policies": len(self.policies),
            "by_policy_type": by_type,
            "by_compliance_status": status_counts,
        }


if __name__ == "__main__":
    # Demo usage
    compliance = InsuranceActCompliance()

    # Register a policy
    policy = compliance.register_policy(
        policy_id="POL-001",
        policy_type=PolicyType.LIFE,
        policyholder_id="CLIENT-001",
        sum_assured=1_000_000,
        premium=12_000,
        inception_date=datetime.utcnow(),
        protections=["free_look_period", "disclosure_document", "complaints_procedure"]
    )
    print(f"Registered policy: {policy['policy_id']}")

    # Check protections
    checks = compliance.check_policyholder_protections("POL-001")
    print(f"\nProtection checks: {len(checks)}")
    for check in checks:
        print(f"  {check.check_type}: {'PASS' if check.passed else 'FAIL'}")

    # Check affordability
    affordability = compliance.check_premium_affordability(
        "POL-001",
        policyholder_income=500_000
    )
    print(f"\nAffordability: {affordability['is_affordable']}")

    # Get compliance status
    status = compliance.get_compliance_status("POL-001")
    print(f"\nCompliance status: {status['status']}")
