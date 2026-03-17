"""
Governance - Consent Manager

We manage user consent for data processing under POPIA,
GDPR, and African data protection regulations. Every
processing activity requires a lawful basis, and we
track consent records for audit purposes.

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
import hashlib

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.consent_manager")


class ConsentStatus(Enum):
    """Status of a consent record."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ProcessingPurpose(Enum):
    """Lawful purposes for data processing."""
    CONTRACT_PERFORMANCE = "contract_performance"
    LEGAL_OBLIGATION = "legal_obligation"
    LEGITIMATE_INTEREST = "legitimate_interest"
    CONSENT = "consent"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"


@dataclass
class ConsentRecord:
    """
    A record of user consent for data processing.

    Attributes:
        subject_id: Data subject identifier
        purpose: Purpose of processing
        status: Current consent status
        granted_at: When consent was granted
        expires_at: When consent expires
        withdrawn_at: When consent was withdrawn (if applicable)
        metadata: Additional consent metadata
    """
    subject_id: str
    purpose: ProcessingPurpose
    status: ConsentStatus = ConsentStatus.PENDING
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate consent record."""
        if not self.subject_id:
            raise ValueError("subject_id is required")

    def grant(self, duration_days: Optional[int] = None) -> None:
        """
        Grant consent.

        Args:
            duration_days: Optional expiration in days
        """
        self.status = ConsentStatus.ACTIVE
        self.granted_at = datetime.utcnow()

        if duration_days:
            self.expires_at = self.granted_at + timedelta(days=duration_days)

        logger.info(
            f"Consent granted for {self.subject_id}: "
            f"{self.purpose.value}"
        )

    def withdraw(self) -> None:
        """Withdraw consent."""
        self.status = ConsentStatus.WITHDRAWN
        self.withdrawn_at = datetime.utcnow()

        logger.info(
            f"Consent withdrawn for {self.subject_id}: "
            f"{self.purpose.value}"
        )

    def is_valid(self) -> bool:
        """
        Check if consent is currently valid.

        Returns:
            True if consent is active and not expired
        """
        if self.status != ConsentStatus.ACTIVE:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            self.status = ConsentStatus.EXPIRED
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject_id": self.subject_id,
            "purpose": self.purpose.value,
            "status": self.status.value,
            "granted_at": (
                self.granted_at.isoformat() if self.granted_at else None
            ),
            "expires_at": (
                self.expires_at.isoformat() if self.expires_at else None
            ),
            "withdrawn_at": (
                self.withdrawn_at.isoformat() if self.withdrawn_at else None
            ),
            "metadata": self.metadata,
        }


class ConsentManager:
    """
    Manages user consent for data processing.

    We track consent records per subject per purpose,
    enforce consent requirements, and maintain audit
    trails for regulatory compliance.

    Attributes:
        records: Consent records by subject_id
        default_duration_days: Default consent duration
    """

    def __init__(
        self,
        default_duration_days: int = 730  # 2 years
    ) -> None:
        """
        Initialize consent manager.

        Args:
            default_duration_days: Default consent duration
        """
        self.records: Dict[str, Dict[str, ConsentRecord]] = {}
        self.default_duration_days = default_duration_days

        logger.info(
            f"ConsentManager initialized, "
            f"default duration: {default_duration_days} days"
        )

    def get_or_create_record(
        self,
        subject_id: str,
        purpose: ProcessingPurpose
    ) -> ConsentRecord:
        """
        Get or create a consent record.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose

        Returns:
            Consent record
        """
        if subject_id not in self.records:
            self.records[subject_id] = {}

        if purpose.value not in self.records[subject_id]:
            record = ConsentRecord(
                subject_id=subject_id,
                purpose=purpose
            )
            self.records[subject_id][purpose.value] = record
            logger.debug(f"Created consent record for {subject_id}")
        else:
            record = self.records[subject_id][purpose.value]

        return record

    def grant_consent(
        self,
        subject_id: str,
        purpose: ProcessingPurpose,
        duration_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConsentRecord:
        """
        Grant consent for a purpose.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose
            duration_days: Optional custom duration
            metadata: Optional metadata

        Returns:
            Updated consent record
        """
        log_operation(
            logger,
            "grant_consent",
            "started",
            subject_id=subject_id,
            purpose=purpose.value,
        )

        record = self.get_or_create_record(subject_id, purpose)

        if metadata:
            record.metadata.update(metadata)

        record.grant(duration_days or self.default_duration_days)

        log_operation(
            logger,
            "grant_consent",
            "completed",
            subject_id=subject_id,
            purpose=purpose.value,
            expires_at=(
                record.expires_at.isoformat()
                if record.expires_at else None
            ),
        )

        return record

    def withdraw_consent(
        self,
        subject_id: str,
        purpose: ProcessingPurpose
    ) -> ConsentRecord:
        """
        Withdraw consent for a purpose.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose

        Returns:
            Updated consent record
        """
        log_operation(
            logger,
            "withdraw_consent",
            "started",
            subject_id=subject_id,
            purpose=purpose.value,
        )

        if subject_id not in self.records:
            raise ValueError(f"No consent records for {subject_id}")

        if purpose.value not in self.records[subject_id]:
            raise ValueError(
                f"No consent record for {subject_id} / {purpose.value}"
            )

        record = self.records[subject_id][purpose.value]
        record.withdraw()

        log_operation(
            logger,
            "withdraw_consent",
            "completed",
            subject_id=subject_id,
            purpose=purpose.value,
        )

        return record

    def check_consent(
        self,
        subject_id: str,
        purpose: ProcessingPurpose
    ) -> bool:
        """
        Check if valid consent exists for a purpose.

        Args:
            subject_id: Data subject identifier
            purpose: Processing purpose

        Returns:
            True if valid consent exists
        """
        if subject_id not in self.records:
            return False

        if purpose.value not in self.records[subject_id]:
            return False

        record = self.records[subject_id][purpose.value]
        return record.is_valid()

    def get_all_records(
        self,
        subject_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all consent records for a subject.

        Args:
            subject_id: Data subject identifier

        Returns:
            List of consent record dictionaries
        """
        if subject_id not in self.records:
            return []

        return [
            record.to_dict()
            for record in self.records[subject_id].values()
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get consent statistics.

        Returns:
            Statistics dictionary
        """
        total_records = sum(
            len(records) for records in self.records.values()
        )

        status_counts: Dict[str, int] = {}
        for records in self.records.values():
            for record in records.values():
                status = record.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_subjects": len(self.records),
            "total_records": total_records,
            "by_status": status_counts,
            "default_duration_days": self.default_duration_days,
        }


if __name__ == "__main__":
    # Demo usage
    manager = ConsentManager(default_duration_days=365)

    # Grant consent
    record = manager.grant_consent(
        subject_id="USER-001",
        purpose=ProcessingPurpose.LEGITIMATE_INTEREST,
        metadata={"channel": "web"}
    )
    print(f"Consent granted: {record.to_dict()}")

    # Check consent
    is_valid = manager.check_consent(
        subject_id="USER-001",
        purpose=ProcessingPurpose.LEGITIMATE_INTEREST
    )
    print(f"Consent valid: {is_valid}")

    # Withdraw consent
    manager.withdraw_consent(
        subject_id="USER-001",
        purpose=ProcessingPurpose.LEGITIMATE_INTEREST
    )
    print(f"Consent withdrawn")
