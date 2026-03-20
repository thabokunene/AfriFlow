"""
@file revenue_attribution.py
@description Outcome Revenue Attribution - Revenue tracking per signal and RM
@author Thabo Kunene
@created 2026-03-19

This module tracks revenue attribution from signals to booked business.
It enables measurement of ROI for signal detection and RM performance.

Key Classes:
- RevenueAttribution: Main engine for revenue tracking and reporting

Features:
- Revenue attribution per signal
- Revenue attribution per RM
- Revenue attribution per signal type
- Cumulative revenue tracking
- ROI calculation

Usage:
    >>> from afriflow.outcome_tracking.revenue_attribution import RevenueAttribution
    >>> attribution = RevenueAttribution()
    >>> attribution.attribute_revenue("SIG-001", 50000.0, "user-123")
    >>> total = attribution.get_total_revenue()

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("outcome_tracking.revenue")


class RevenueAttribution:
    """
    Revenue attribution tracking engine.

    Tracks revenue from signals through to booking and
    provides analytics on signal ROI and RM performance.

    Attributes:
        _revenues: Dictionary mapping signal_id to revenue records
        _rm_revenues: Dictionary mapping rm_id to total revenue

    Example:
        >>> attribution = RevenueAttribution()
        >>> attribution.attribute_revenue("SIG-001", 50000.0, "user-123")
        >>> attribution.get_total_revenue()
    """

    def __init__(self) -> None:
        """Initialize revenue attribution with empty stores."""
        self._revenues: Dict[str, Dict[str, Any]] = {}
        self._rm_revenues: Dict[str, float] = {}
        self._signal_type_revenues: Dict[str, float] = {}
        logger.info("RevenueAttribution initialized")

    def attribute_revenue(
        self,
        signal_id: str,
        amount: float,
        rm_id: str,
        signal_type: str = "UNKNOWN",
        client_id: Optional[str] = None,
        booking_date: Optional[str] = None
    ) -> None:
        """
        Attribute revenue to a signal.

        Args:
            signal_id: Signal identifier
            amount: Revenue amount in ZAR
            rm_id: RM user ID
            signal_type: Type of signal
            client_id: Optional client ID
            booking_date: Optional booking date (default: now)

        Example:
            >>> attribution.attribute_revenue(
            ...     signal_id="SIG-001",
            ...     amount=50000.0,
            ...     rm_id="user-123",
            ...     signal_type="EXPANSION"
            ... )
        """
        if booking_date is None:
            booking_date = datetime.now().isoformat()

        # Store revenue record
        self._revenues[signal_id] = {
            "signal_id": signal_id,
            "amount": amount,
            "rm_id": rm_id,
            "signal_type": signal_type,
            "client_id": client_id,
            "booking_date": booking_date,
        }

        # Update RM total
        current_rm = self._rm_revenues.get(rm_id, 0.0)
        self._rm_revenues[rm_id] = current_rm + amount

        # Update signal type total
        current_type = self._signal_type_revenues.get(signal_type, 0.0)
        self._signal_type_revenues[signal_type] = current_type + amount

        logger.info(
            f"Revenue attributed: {signal_id} - {amount} ZAR ({rm_id})"
        )

    def get_revenue_for_signal(
        self,
        signal_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get revenue record for a specific signal."""
        return self._revenues.get(signal_id)

    def get_revenue_for_rm(
        self,
        rm_id: str
    ) -> float:
        """Get total revenue for a specific RM."""
        return self._rm_revenues.get(rm_id, 0.0)

    def get_revenue_by_signal_type(
        self,
        signal_type: str
    ) -> float:
        """Get total revenue for a specific signal type."""
        return self._signal_type_revenues.get(signal_type, 0.0)

    def get_total_revenue(self) -> float:
        """Get total revenue across all signals."""
        return sum(self._revenues.values())

    def get_top_rms(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top RMs by revenue.

        Args:
            limit: Number of RMs to return

        Returns:
            List of RM revenue dictionaries sorted by revenue
        """
        rms = [
            {"rm_id": rm_id, "revenue": revenue}
            for rm_id, revenue in self._rm_revenues.items()
        ]
        rms.sort(key=lambda x: x["revenue"], reverse=True)
        return rms[:limit]

    def get_top_signal_types(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top signal types by revenue.

        Args:
            limit: Number of types to return

        Returns:
            List of signal type revenue dictionaries
        """
        types = [
            {"signal_type": stype, "revenue": revenue}
            for stype, revenue in self._signal_type_revenues.items()
        ]
        types.sort(key=lambda x: x["revenue"], reverse=True)
        return types[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get revenue attribution statistics."""
        total_revenue = sum(self._revenues.values())
        total_signals = len(self._revenues)

        return {
            "total_revenue": total_revenue,
            "total_signals": total_signals,
            "avg_revenue_per_signal": (
                total_revenue / total_signals if total_signals > 0 else 0.0
            ),
            "total_rms": len(self._rm_revenues),
            "total_signal_types": len(self._signal_type_revenues),
        }


__all__ = [
    "RevenueAttribution",
]
