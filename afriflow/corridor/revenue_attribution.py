"""
Revenue Attribution

Attributes revenue to specific corridors, tracking
per-domain contribution and total corridor value.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.revenue_attribution")


@dataclass
class RevenueRecord:
    """A revenue attribution record."""
    record_id: str
    corridor_id: str
    domain: str
    revenue_type: str
    amount: float
    currency: str
    client_id: Optional[str]
    transaction_id: Optional[str]
    recorded_at: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "corridor_id": self.corridor_id,
            "domain": self.domain,
            "revenue_type": self.revenue_type,
            "amount": self.amount,
            "currency": self.currency,
            "client_id": self.client_id,
            "transaction_id": self.transaction_id,
            "recorded_at": self.recorded_at.isoformat(),
            "attributes": self.attributes,
        }


class RevenueAttribution:
    """
    Revenue attribution tracking.

    Tracks revenue per corridor, per domain, enabling
    analysis of which domains contribute most to
    corridor profitability.
    """

    DOMAIN_REVENUE_TYPES = {
        "CIB": ["transaction_fee", "spread", "facility_fee"],
        "FOREX": ["fx_spread", "forward_fee", "swap_points"],
        "INSURANCE": ["premium", "policy_fee"],
        "CELL": ["transaction_fee", "float_income"],
        "PBB": ["account_fee", "payroll_fee", "lending_interest"],
    }

    def __init__(self):
        self._records: Dict[str, List[RevenueRecord]] = {}
        self._corridor_totals: Dict[str, float] = {}
        self._domain_totals: Dict[str, Dict[str, float]] = {}

        logger.info("RevenueAttribution initialized")

    def record_revenue(
        self,
        corridor_id: str,
        domain: str,
        revenue_type: str,
        amount: float,
        currency: str = "ZAR",
        client_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> RevenueRecord:
        """
        Record revenue for a corridor.

        Args:
            corridor_id: Corridor this revenue is for
            domain: Domain that generated the revenue
            revenue_type: Type of revenue
            amount: Revenue amount
            currency: Currency code
            client_id: Optional client identifier
            transaction_id: Optional transaction reference
            attributes: Optional additional attributes

        Returns:
            RevenueRecord created
        """
        import uuid

        record_id = f"REV-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now()

        record = RevenueRecord(
            record_id=record_id,
            corridor_id=corridor_id,
            domain=domain,
            revenue_type=revenue_type,
            amount=amount,
            currency=currency,
            client_id=client_id,
            transaction_id=transaction_id,
            recorded_at=now,
            attributes=attributes or {},
        )

        # Store record
        if corridor_id not in self._records:
            self._records[corridor_id] = []
        self._records[corridor_id].append(record)

        # Update totals
        self._corridor_totals[corridor_id] = (
            self._corridor_totals.get(corridor_id, 0) + amount
        )

        if corridor_id not in self._domain_totals:
            self._domain_totals[corridor_id] = {}
        if domain not in self._domain_totals[corridor_id]:
            self._domain_totals[corridor_id][domain] = 0
        self._domain_totals[corridor_id][domain] += amount

        logger.debug(
            f"Revenue recorded: {amount} {currency} for "
            f"corridor {corridor_id} ({domain})"
        )

        return record

    def get_corridor_revenue(
        self, corridor_id: str
    ) -> Dict[str, Any]:
        """Get revenue breakdown for a corridor."""
        records = self._records.get(corridor_id, [])
        total = self._corridor_totals.get(corridor_id, 0)
        domain_breakdown = self._domain_totals.get(
            corridor_id, {}
        )

        return {
            "corridor_id": corridor_id,
            "total_revenue": total,
            "transaction_count": len(records),
            "domain_breakdown": domain_breakdown,
            "records": [r.to_dict() for r in records[-10:]],
        }

    def get_domain_attribution(
        self, corridor_id: str
    ) -> Dict[str, float]:
        """Get revenue attribution by domain for a corridor."""
        return self._domain_totals.get(corridor_id, {})

    def get_top_corridors(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top revenue-generating corridors."""
        sorted_corridors = sorted(
            self._corridor_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            {
                "corridor_id": cid,
                "total_revenue": revenue,
                "domain_breakdown": self._domain_totals.get(
                    cid, {}
                ),
            }
            for cid, revenue in sorted_corridors[:limit]
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get revenue attribution statistics."""
        total_revenue = sum(self._corridor_totals.values())
        total_records = sum(
            len(records) for records in self._records.values()
        )

        return {
            "total_corridors_with_revenue": len(
                self._corridor_totals
            ),
            "total_revenue": total_revenue,
            "total_records": total_records,
            "avg_revenue_per_corridor": (
                total_revenue / len(self._corridor_totals)
                if self._corridor_totals else 0
            ),
        }
