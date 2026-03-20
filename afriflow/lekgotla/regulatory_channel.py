"""
@file regulatory_channel.py
@description Lekgotla Regulatory Channel - Compliance officer reviewed regulatory alerts
@author Thabo Kunene
@created 2026-03-19

This module manages regulatory alerts that require compliance officer review
before being published to RMs. These alerts inform practitioners about
regulatory changes that affect client strategies.

Key Classes:
- ReviewStatus: Alert review states (PENDING, REVIEWED, EXPIRED)
- RegulatoryAlert: Regulatory alert with compliance metadata
- RegulatoryChannel: Alert management and review workflow

Features:
- Alert creation with compliance metadata
- Review workflow (pending -> reviewed)
- Country-specific alerts
- Severity classification
- Deadline tracking
- Domain impact assessment

Usage:
    >>> from afriflow.lekgotla.regulatory_channel import RegulatoryChannel
    >>> channel = RegulatoryChannel()
    >>> alert = channel.create_alert(
    ...     title="NGN repatriation rule change",
    ...     country="NG",
    ...     regulator="CBN",
    ...     severity="HIGH"
    ... )
    >>> channel.review_alert(alert.alert_id, "compliance-001", approved=True)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

# Standard library imports
from dataclasses import dataclass, field  # For data class decorators
from datetime import datetime  # For timestamps
from enum import Enum  # For enumerated types
from typing import Dict, List, Optional, Any  # Type hints
import logging  # For logging
import uuid  # For unique ID generation

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.regulatory")


class ReviewStatus(Enum):
    """
    Regulatory alert review status enumeration.

    Defines the lifecycle states of a regulatory alert:
    - PENDING: Awaiting compliance officer review
    - REVIEWED: Reviewed and approved/rejected
    - EXPIRED: Past effective date or deadline
    """
    PENDING = "PENDING"  # Awaiting review
    REVIEWED = "REVIEWED"  # Reviewed by compliance
    EXPIRED = "EXPIRED"  # Past effective date


@dataclass
class RegulatoryAlert:
    """
    Regulatory alert requiring compliance review.

    Represents a regulatory change that affects client strategies.
    Alerts must be reviewed by a compliance officer before
    being published to RMs.

    Attributes:
        alert_id: Unique identifier (UUID format)
        reference_number: Official regulatory reference number
        title: Alert title (descriptive)
        country: Affected country code (ISO 3166-1 alpha-2)
        regulator: Regulatory authority name (e.g., "CBN", "SARS")
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        effective_date: Date when regulation takes effect (ISO 8601)
        summary: Summary of regulatory change
        posted_by: User ID who posted the alert
        posted_at: ISO 8601 timestamp of posting
        review_status: Review status (PENDING, REVIEWED, EXPIRED)
        reviewed_by: Compliance officer who reviewed (if reviewed)
        reviewed_at: Review timestamp (if reviewed)
        affected_clients: Number of affected clients
        affected_value_zar: Affected value in ZAR
        domain_impacts: List of domain impact dictionaries
        deadline_days: Days until compliance deadline
        knowledge_card_id: Related Knowledge Card ID (if applicable)

    Example:
        >>> alert = RegulatoryAlert(
        ...     alert_id="REG-ABC123",
        ...     reference_number="CBN/2026/001",
        ...     title="NGN repatriation rule change",
        ...     country="NG",
        ...     regulator="CBN",
        ...     severity="HIGH",
        ...     effective_date="2026-04-01"
        ... )
    """
    alert_id: str  # Unique alert identifier
    reference_number: str  # Official regulatory reference
    title: str  # Alert title
    country: str  # Affected country code
    regulator: str  # Regulatory authority name
    severity: str  # Severity level
    effective_date: str  # Effective date (ISO 8601)
    summary: str  # Regulatory change summary
    posted_by: str  # Poster user ID
    posted_at: str  # Posting timestamp
    review_status: ReviewStatus  # Review status
    reviewed_by: Optional[str] = None  # Reviewer user ID
    reviewed_at: Optional[str] = None  # Review timestamp
    affected_clients: int = 0  # Number of affected clients
    affected_value_zar: float = 0.0  # Affected value in ZAR
    domain_impacts: List[Dict] = field(default_factory=list)  # Domain impacts
    deadline_days: Optional[int] = None  # Compliance deadline
    knowledge_card_id: Optional[str] = None  # Related KC ID

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "reference_number": self.reference_number,
            "title": self.title,
            "country": self.country,
            "regulator": self.regulator,
            "severity": self.severity,
            "effective_date": self.effective_date,
            "summary": self.summary,
            "posted_by": self.posted_by,
            "posted_at": self.posted_at,
            "review_status": self.review_status.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at,
            "affected_clients": self.affected_clients,
            "affected_value_zar": self.affected_value_zar,
            "domain_impacts": self.domain_impacts,
            "deadline_days": self.deadline_days,
            "knowledge_card_id": self.knowledge_card_id,
        }


class RegulatoryChannel:
    """
    Regulatory alert management and review workflow.

    This class manages the lifecycle of regulatory alerts from
    creation through compliance review to publication.

    Features:
    - Alert creation with compliance metadata
    - Review workflow (pending -> reviewed)
    - Country-based filtering
    - Severity-based prioritization
    - Expiration tracking

    Attributes:
        _alerts: Dictionary mapping alert_id to RegulatoryAlert

    Example:
        >>> channel = RegulatoryChannel()
        >>> alert = channel.create_alert(
        ...     title="New FX repatriation rule",
        ...     country="NG",
        ...     regulator="CBN",
        ...     severity="HIGH",
        ...     posted_by="compliance-001"
        ... )
        >>> channel.review_alert(alert.alert_id, "compliance-002", approved=True)
    """

    def __init__(self) -> None:
        """Initialize the regulatory channel with empty alert store."""
        self._alerts: Dict[str, RegulatoryAlert] = {}
        self._country_index: Dict[str, List[str]] = {}
        logger.info("RegulatoryChannel initialized")

    def create_alert(
        self,
        title: str,
        country: str,
        regulator: str,
        severity: str,
        effective_date: str,
        summary: str,
        posted_by: str,
        reference_number: Optional[str] = None,
        affected_clients: int = 0,
        affected_value_zar: float = 0.0,
        domain_impacts: Optional[List[Dict]] = None,
        deadline_days: Optional[int] = None,
    ) -> RegulatoryAlert:
        """
        Create a new regulatory alert.

        Args:
            title: Alert title
            country: Affected country code
            regulator: Regulatory authority name
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            effective_date: Effective date (ISO 8601)
            summary: Regulatory change summary
            posted_by: User ID who posted
            reference_number: Official reference number
            affected_clients: Number of affected clients
            affected_value_zar: Affected value in ZAR
            domain_impacts: List of domain impacts
            deadline_days: Compliance deadline in days

        Returns:
            Created RegulatoryAlert object
        """
        alert_id = f"REG-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now().isoformat()

        alert = RegulatoryAlert(
            alert_id=alert_id,
            reference_number=reference_number or f"AUTO-{alert_id}",
            title=title,
            country=country,
            regulator=regulator,
            severity=severity,
            effective_date=effective_date,
            summary=summary,
            posted_by=posted_by,
            posted_at=now,
            review_status=ReviewStatus.PENDING,
            affected_clients=affected_clients,
            affected_value_zar=affected_value_zar,
            domain_impacts=domain_impacts or [],
            deadline_days=deadline_days,
        )

        self._alerts[alert_id] = alert

        # Update country index
        if country not in self._country_index:
            self._country_index[country] = []
        self._country_index[country].append(alert_id)

        logger.info(f"Regulatory alert created: {alert_id} - {title}")
        return alert

    def review_alert(
        self,
        alert_id: str,
        reviewed_by: str,
        approved: bool,
        notes: Optional[str] = None
    ) -> bool:
        """
        Review and approve/reject a regulatory alert.

        Args:
            alert_id: Alert to review
            reviewed_by: Compliance officer user ID
            approved: Whether to approve the alert
            notes: Optional review notes

        Returns:
            True if review successful
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.review_status = ReviewStatus.REVIEWED
        alert.reviewed_by = reviewed_by
        alert.reviewed_at = datetime.now().isoformat()

        if not approved:
            alert.review_status = ReviewStatus.EXPIRED

        logger.info(
            f"Alert {alert_id} {'approved' if approved else 'rejected'} "
            f"by {reviewed_by}"
        )
        return True

    def get_alert(self, alert_id: str) -> Optional[RegulatoryAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def get_alerts_for_country(
        self,
        country: str,
        status: Optional[ReviewStatus] = None
    ) -> List[RegulatoryAlert]:
        """Get alerts for a specific country."""
        alert_ids = self._country_index.get(country, [])
        alerts = [
            self._alerts[aid] for aid in alert_ids
            if aid in self._alerts
        ]

        if status:
            alerts = [a for a in alerts if a.review_status == status]

        return alerts

    def get_pending_reviews(self) -> List[RegulatoryAlert]:
        """Get alerts pending compliance review."""
        return [
            a for a in self._alerts.values()
            if a.review_status == ReviewStatus.PENDING
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get regulatory channel statistics."""
        status_counts = {}
        severity_counts = {}

        for alert in self._alerts.values():
            status = alert.review_status.value
            severity = alert.severity
            status_counts[status] = status_counts.get(status, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_alerts": len(self._alerts),
            "status_breakdown": status_counts,
            "severity_breakdown": severity_counts,
            "pending_reviews": len(self.get_pending_reviews()),
            "countries_covered": len(self._country_index),
        }


__all__ = [
    "ReviewStatus",
    "RegulatoryAlert",
    "RegulatoryChannel",
]
