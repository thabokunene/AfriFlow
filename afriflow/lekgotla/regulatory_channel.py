"""
Lekgotla Regulatory Channel

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
import uuid

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.regulatory")


class ReviewStatus(Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    EXPIRED = "EXPIRED"


@dataclass
class RegulatoryAlert:
    alert_id: str
    reference_number: str
    title: str
    country: str
    regulator: str
    severity: str
    effective_date: str
    summary: str
    posted_by: str
    posted_at: str
    review_status: ReviewStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    affected_clients: int = 0
    affected_value_zar: float = 0.0
    domain_impacts: List[Dict] = field(default_factory=list)
    deadline_days: Optional[int] = None
    knowledge_card_id: Optional[str] = None


class RegulatoryChannel:
    def __init__(self) -> None:
        self._alerts: Dict[str, RegulatoryAlert] = {}
        logger.info("RegulatoryChannel initialized")

    def post_alert(self, alert: RegulatoryAlert) -> RegulatoryAlert:
        if not alert.alert_id:
            alert.alert_id = f"REG-{uuid.uuid4().hex[:8].upper()}"
        self._alerts[alert.alert_id] = alert
        logger.info(f"Regulatory alert posted: {alert.alert_id}")
        return alert

    def auto_calculate_affected(self, alert: RegulatoryAlert, client_data: List[Dict]) -> Dict:
        """
        Calculates affected client count and exposure based on country.
        """
        affected = [c for c in client_data if c.get("country") == alert.country]
        alert.affected_clients = len(affected)
        alert.affected_value_zar = sum(c.get("exposure", 0.0) for c in affected)
        
        return {
            "count": alert.affected_clients,
            "value": alert.affected_value_zar
        }

    def review_alert(self, alert_id: str, reviewer_id: str) -> None:
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.review_status = ReviewStatus.REVIEWED
            alert.reviewed_by = reviewer_id
            alert.reviewed_at = datetime.now().isoformat()
            logger.info(f"Regulatory alert {alert_id} reviewed by {reviewer_id}")

    def get_alerts_by_country(self, country: str) -> List[RegulatoryAlert]:
        return [a for a in self._alerts.values() if a.country == country]

    def get_pending_review(self) -> List[RegulatoryAlert]:
        return [a for a in self._alerts.values() if a.review_status == ReviewStatus.PENDING]

    def get_upcoming_deadlines(self, days: int) -> List[RegulatoryAlert]:
        return [a for a in self._alerts.values() if a.deadline_days and a.deadline_days <= days]
