"""
Lekgotla Regulatory Channel

Specialized channel for compliance and regulatory intelligence posts.
Posts in this channel are reviewed by compliance officers and
surface regulatory changes that affect client strategies.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.regulatory_channel")


class RegulatoryAlertType(Enum):
    """Types of regulatory alerts."""
    POLICY_CHANGE = "policy_change"
    COMPLIANCE_DEADLINE = "compliance_deadline"
    ENFORCEMENT_ACTION = "enforcement_action"
    GUIDANCE_UPDATE = "guidance_update"
    LICENSING_CHANGE = "licensing_change"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RegulatoryAlert:
    """A regulatory alert post."""
    alert_id: str
    title: str
    content: str
    alert_type: RegulatoryAlertType
    severity: AlertSeverity
    country: str
    regulation_name: str
    effective_date: Optional[datetime]
    compliance_deadline: Optional[datetime]
    affected_products: List[str]
    affected_clients: List[str]
    source_authority: str
    source_url: Optional[str]
    created_at: datetime
    created_by: str
    status: str = "draft"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    attachments: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "content": self.content,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "country": self.country,
            "regulation_name": self.regulation_name,
            "effective_date": (
                self.effective_date.isoformat()
                if self.effective_date else None
            ),
            "compliance_deadline": (
                self.compliance_deadline.isoformat()
                if self.compliance_deadline else None
            ),
            "affected_products": self.affected_products,
            "affected_clients": self.affected_clients,
            "source_authority": self.source_authority,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": (
                self.reviewed_at.isoformat()
                if self.reviewed_at else None
            ),
            "attachments": self.attachments,
        }


class RegulatoryChannel:
    """
    Regulatory intelligence channel.

    Manages regulatory alerts that require compliance review
    before publication.
    """

    def __init__(self):
        self._alerts: Dict[str, RegulatoryAlert] = {}
        self._country_index: Dict[str, List[str]] = {}
        self._type_index: Dict[str, List[str]] = {}

        logger.info("RegulatoryChannel initialized")

    def create_alert(
        self,
        title: str,
        content: str,
        alert_type: RegulatoryAlertType,
        severity: AlertSeverity,
        country: str,
        regulation_name: str,
        affected_products: List[str],
        source_authority: str,
        created_by: str,
        effective_date: Optional[datetime] = None,
        compliance_deadline: Optional[datetime] = None,
        affected_clients: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> RegulatoryAlert:
        """Create a new regulatory alert."""
        import uuid

        alert_id = f"REG-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now()

        alert = RegulatoryAlert(
            alert_id=alert_id,
            title=title,
            content=content,
            alert_type=alert_type,
            severity=severity,
            country=country,
            regulation_name=regulation_name,
            effective_date=effective_date,
            compliance_deadline=compliance_deadline,
            affected_products=affected_products,
            affected_clients=affected_clients or [],
            source_authority=source_authority,
            source_url=source_url,
            created_at=now,
            created_by=created_by,
            attachments=attachments or [],
        )

        self._alerts[alert_id] = alert

        # Update indexes
        if country not in self._country_index:
            self._country_index[country] = []
        self._country_index[country].append(alert_id)

        type_key = alert_type.value
        if type_key not in self._type_index:
            self._type_index[type_key] = []
        self._type_index[type_key].append(alert_id)

        logger.info(f"Regulatory alert created: {alert_id} - '{title}'")

        return alert

    def review_alert(
        self,
        alert_id: str,
        reviewer_id: str,
        approved: bool,
        comments: Optional[str] = None,
    ) -> None:
        """Review and approve/reject an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        if approved:
            alert.status = "published"
        else:
            alert.status = "rejected"

        alert.reviewed_by = reviewer_id
        alert.reviewed_at = datetime.now()

        logger.info(
            f"Alert {alert_id} {'approved' if approved else 'rejected'} "
            f"by {reviewer_id}"
        )

    def get_alert(self, alert_id: str) -> Optional[RegulatoryAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def search_alerts(
        self,
        country: Optional[str] = None,
        alert_type: Optional[RegulatoryAlertType] = None,
        severity: Optional[AlertSeverity] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[RegulatoryAlert]:
        """Search regulatory alerts."""
        results = list(self._alerts.values())

        if country and country in self._country_index:
            country_alerts = set(self._country_index[country])
            results = [
                a for a in results if a.alert_id in country_alerts
            ]

        if alert_type:
            type_key = alert_type.value
            if type_key in self._type_index:
                type_alerts = set(self._type_index[type_key])
                results = [
                    a for a in results if a.alert_id in type_alerts
                ]

        if severity:
            results = [a for a in results if a.severity == severity]

        if status:
            results = [a for a in results if a.status == status]

        # Sort by severity then created_at
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3,
        }

        results.sort(
            key=lambda a: (
                severity_order.get(a.severity, 4),
                a.created_at,
            ),
            reverse=True,
        )

        return results[:limit]

    def get_pending_reviews(self) -> List[RegulatoryAlert]:
        """Get alerts pending compliance review."""
        return [
            a for a in self._alerts.values()
            if a.status == "draft"
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get regulatory channel statistics."""
        status_counts = {}
        type_counts = {}
        severity_counts = {}

        for alert in self._alerts.values():
            status_counts[alert.status] = status_counts.get(
                alert.status, 0
            ) + 1

            type_key = alert.alert_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

            sev_key = alert.severity.value
            severity_counts[sev_key] = severity_counts.get(
                sev_key, 0
            ) + 1

        return {
            "total_alerts": len(self._alerts),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "severity_breakdown": severity_counts,
            "pending_reviews": len(self.get_pending_reviews()),
            "countries_covered": len(self._country_index),
        }
