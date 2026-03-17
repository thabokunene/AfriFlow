"""
Governance - FAIS Compliance Checker

The Financial Advisory and Intermediary Services (FAIS)
Act regulates the provision of financial advice and
intermediary services in South Africa. We track all
advice given to clients and ensure compliance with
FAIS requirements.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.fais_compliance")


class AdviceType(Enum):
    """Type of financial advice."""
    INVESTMENT = "investment"
    INSURANCE = "insurance"
    RETIREMENT = "retirement"
    TAX = "tax"
    ESTATE_PLANNING = "estate_planning"
    GENERAL = "general"


class AdviceStatus(Enum):
    """Status of advice record."""
    DRAFT = "draft"
    GIVEN = "given"
    IMPLEMENTED = "implemented"
    DECLINED = "declined"
    SUPERSEDED = "superseded"


@dataclass
class FAISAdviceRecord:
    """
    Record of financial advice given to a client.

    Attributes:
        advice_id: Unique advice identifier
        client_id: Client identifier
        advisor_id: Advisor identifier (FAIS registered)
        advice_type: Type of advice
        description: Advice description
        status: Current status
        given_at: When advice was given
        needs_analysis: Whether needs analysis was done
        risk_profile: Client risk profile
        product_recommendations: Recommended products
    """
    advice_id: str
    client_id: str
    advisor_id: str
    advice_type: AdviceType
    description: str
    status: AdviceStatus = AdviceStatus.DRAFT
    given_at: Optional[datetime] = None
    needs_analysis: bool = False
    risk_profile: Optional[str] = None
    product_recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate advice record."""
        if not self.advisor_id:
            raise ValueError("advisor_id is required (FAIS registration)")
        if not self.client_id:
            raise ValueError("client_id is required")

    def mark_given(self) -> None:
        """Mark advice as given."""
        self.status = AdviceStatus.GIVEN
        self.given_at = datetime.utcnow()
        logger.info(f"Advice {self.advice_id} marked as given")

    def mark_implemented(self) -> None:
        """Mark advice as implemented."""
        if self.status != AdviceStatus.GIVEN:
            raise ValueError("Advice must be given before implementation")
        self.status = AdviceStatus.IMPLEMENTED
        logger.info(f"Advice {self.advice_id} marked as implemented")


class FAISComplianceChecker:
    """
    Checks FAIS compliance for financial advice.

    We ensure all advice is given by registered
    representatives, documented properly, and
    suitable for the client's needs and risk profile.

    Attributes:
        records: Advice records by ID
        registered_advisors: Set of registered advisor IDs
    """

    def __init__(self) -> None:
        """Initialize FAIS compliance checker."""
        self.records: Dict[str, FAISAdviceRecord] = {}
        self.registered_advisors: Set[str] = set()

        logger.info("FAISComplianceChecker initialized")

    def register_advisor(self, advisor_id: str) -> None:
        """
        Register a FAIS advisor.

        Args:
            advisor_id: FAIS registration number
        """
        self.registered_advisors.add(advisor_id)
        logger.info(f"Registered FAIS advisor: {advisor_id}")

    def is_advisor_registered(self, advisor_id: str) -> bool:
        """
        Check if advisor is registered.

        Args:
            advisor_id: FAIS registration number

        Returns:
            True if registered
        """
        return advisor_id in self.registered_advisors

    def create_advice_record(
        self,
        client_id: str,
        advisor_id: str,
        advice_type: AdviceType,
        description: str,
        needs_analysis: bool = False,
        risk_profile: Optional[str] = None,
        product_recommendations: Optional[List[str]] = None
    ) -> FAISAdviceRecord:
        """
        Create a new advice record.

        Args:
            client_id: Client identifier
            advisor_id: FAIS registered advisor ID
            advice_type: Type of advice
            description: Advice description
            needs_analysis: Whether needs analysis was done
            risk_profile: Client risk profile
            product_recommendations: Recommended products

        Returns:
            Created advice record

        Raises:
            ConfigurationError: If advisor not registered
        """
        log_operation(
            logger,
            "create_advice_record",
            "started",
            client_id=client_id,
            advisor_id=advisor_id,
        )

        if not self.is_advisor_registered(advisor_id):
            raise ConfigurationError(
                f"Advisor {advisor_id} is not FAIS registered"
            )

        advice_id = f"FAIS-{client_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        record = FAISAdviceRecord(
            advice_id=advice_id,
            client_id=client_id,
            advisor_id=advisor_id,
            advice_type=advice_type,
            description=description,
            needs_analysis=needs_analysis,
            risk_profile=risk_profile,
            product_recommendations=product_recommendations or []
        )

        self.records[advice_id] = record

        log_operation(
            logger,
            "create_advice_record",
            "completed",
            advice_id=advice_id,
        )

        return record

    def check_compliance(
        self,
        advice_id: str
    ) -> Dict[str, Any]:
        """
        Check FAIS compliance for an advice record.

        Args:
            advice_id: Advice record ID

        Returns:
            Compliance check results

        Raises:
            ConfigurationError: If advice not found
        """
        if advice_id not in self.records:
            raise ConfigurationError(f"Advice {advice_id} not found")

        record = self.records[advice_id]
        issues = []
        warnings = []

        # Check advisor registration
        if not self.is_advisor_registered(record.advisor_id):
            issues.append("Advisor not FAIS registered")

        # Check needs analysis for investment/insurance advice
        if record.advice_type in [AdviceType.INVESTMENT, AdviceType.INSURANCE]:
            if not record.needs_analysis:
                warnings.append("Needs analysis not documented")

        # Check risk profile for investment advice
        if record.advice_type == AdviceType.INVESTMENT:
            if not record.risk_profile:
                warnings.append("Risk profile not documented")

        # Check status
        if record.status == AdviceStatus.DRAFT:
            warnings.append("Advice still in draft status")

        is_compliant = len(issues) == 0

        return {
            "advice_id": advice_id,
            "is_compliant": is_compliant,
            "issues": issues,
            "warnings": warnings,
            "checked_at": datetime.utcnow().isoformat(),
        }

    def get_advice_history(
        self,
        client_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get advice history for a client.

        Args:
            client_id: Client identifier

        Returns:
            List of advice records
        """
        history = []

        for record in self.records.values():
            if record.client_id == client_id:
                history.append({
                    "advice_id": record.advice_id,
                    "advice_type": record.advice_type.value,
                    "description": record.description,
                    "status": record.status.value,
                    "given_at": (
                        record.given_at.isoformat()
                        if record.given_at else None
                    ),
                    "advisor_id": record.advisor_id,
                })

        return sorted(
            history,
            key=lambda x: x["given_at"] or "",
            reverse=True
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get compliance statistics.

        Returns:
            Statistics dictionary
        """
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for record in self.records.values():
            type_key = record.advice_type.value
            status_key = record.status.value

            by_type[type_key] = by_type.get(type_key, 0) + 1
            by_status[status_key] = by_status.get(status_key, 0) + 1

        return {
            "total_records": len(self.records),
            "registered_advisors": len(self.registered_advisors),
            "by_advice_type": by_type,
            "by_status": by_status,
        }


if __name__ == "__main__":
    # Demo usage
    checker = FAISComplianceChecker()

    # Register an advisor
    checker.register_advisor("FAIS-12345")

    # Create advice record
    record = checker.create_advice_record(
        client_id="CLIENT-001",
        advisor_id="FAIS-12345",
        advice_type=AdviceType.INVESTMENT,
        description="Recommend diversified portfolio",
        needs_analysis=True,
        risk_profile="moderate",
        product_recommendations=["Equity Fund A", "Bond Fund B"]
    )

    # Mark as given
    record.mark_given()

    # Check compliance
    compliance = checker.check_compliance(record.advice_id)
    print(f"Compliance: {compliance}")

    # Get statistics
    stats = checker.get_statistics()
    print(f"\nStatistics: {stats}")
