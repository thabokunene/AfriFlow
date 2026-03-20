"""
@file revenue_attribution.py
@description Corridor Revenue Attribution - Multi-domain revenue tracking per corridor
@author Thabo Kunene
@created 2026-03-19

This module tracks revenue attribution across domains (CIB, Forex, Insurance, etc.)
for each payment corridor. It enables analysis of which domains contribute most
to corridor profitability.

Key Classes:
- CorridorRevenue: Revenue data for a single corridor
- RevenueAttribution: Main engine for revenue tracking and reporting

Features:
- Per-domain revenue tracking
- Corridor profitability analysis
- Revenue trend monitoring
- Cross-domain contribution scoring

Usage:
    >>> from afriflow.corridor.revenue_attribution import RevenueAttribution
    >>> attribution = RevenueAttribution()
    >>> attribution.record_revenue("ZA-NG", "CIB", 50000.0)
    >>> stats = attribution.get_corridor_revenue("ZA-NG")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.revenue")


@dataclass
class CorridorRevenue:
    """
    Revenue data for a single corridor.

    Tracks revenue by domain and maintains historical
    records for trend analysis.

    Attributes:
        corridor_id: Corridor identifier (e.g., "ZA-NG")
        revenue_by_domain: Dictionary mapping domain to revenue
        last_updated: Last update timestamp
        history: List of historical revenue snapshots

    Example:
        >>> rev = CorridorRevenue(corridor_id="ZA-NG")
        >>> rev.revenue_by_domain["CIB"] = 50000.0
        >>> rev.revenue_by_domain["FOREX"] = 30000.0
    """
    corridor_id: str  # Corridor identifier
    revenue_by_domain: Dict[str, float] = field(default_factory=dict)  # Domain -> revenue
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())  # Update timestamp
    history: List[Dict] = field(default_factory=list)  # Historical snapshots

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "corridor_id": self.corridor_id,
            "revenue_by_domain": self.revenue_by_domain,
            "total_revenue": sum(self.revenue_by_domain.values()),
            "last_updated": self.last_updated,
            "history": self.history[-10:],  # Last 10 snapshots
        }


class RevenueAttribution:
    """
    Multi-domain revenue attribution engine.

    Tracks revenue across domains (CIB, Forex, Insurance, Cell, PBB)
    for each corridor. Enables analysis of domain contribution to
    corridor profitability.

    Attributes:
        _corridor_revenues: Dictionary mapping corridor_id to CorridorRevenue

    Example:
        >>> attribution = RevenueAttribution()
        >>> attribution.record_revenue("ZA-NG", "CIB", 50000.0)
        >>> attribution.record_revenue("ZA-NG", "FOREX", 30000.0)
        >>> stats = attribution.get_corridor_revenue("ZA-NG")
    """

    # Domain list for consistent reporting
    DOMAINS = ["CIB", "FOREX", "INSURANCE", "CELL", "PBB"]

    def __init__(self) -> None:
        """Initialize revenue attribution with empty corridor store."""
        self._corridor_revenues: Dict[str, CorridorRevenue] = {}
        logger.info("RevenueAttribution initialized")

    def record_revenue(
        self,
        corridor_id: str,
        domain: str,
        amount: float,
        client_id: Optional[str] = None
    ) -> None:
        """
        Record revenue for a corridor and domain.

        Args:
            corridor_id: Corridor identifier (e.g., "ZA-NG")
            domain: Domain name (CIB, FOREX, INSURANCE, CELL, PBB)
            amount: Revenue amount in ZAR
            client_id: Optional client ID for tracking

        Example:
            >>> attribution.record_revenue("ZA-NG", "CIB", 50000.0)
        """
        # Get or create corridor revenue record
        if corridor_id not in self._corridor_revenues:
            self._corridor_revenues[corridor_id] = CorridorRevenue(
                corridor_id=corridor_id
            )

        # Update domain revenue
        rev = self._corridor_revenues[corridor_id]
        current = rev.revenue_by_domain.get(domain, 0.0)
        rev.revenue_by_domain[domain] = current + amount
        rev.last_updated = datetime.now().isoformat()

        logger.debug(
            f"Recorded {amount} ZAR for {corridor_id} ({domain})"
        )

    def get_corridor_revenue(
        self,
        corridor_id: str
    ) -> Dict[str, Any]:
        """
        Get revenue breakdown for a corridor.

        Args:
            corridor_id: Corridor identifier

        Returns:
            Dictionary with revenue by domain and totals
        """
        rev = self._corridor_revenues.get(corridor_id)
        if not rev:
            return {
                "corridor_id": corridor_id,
                "revenue_by_domain": {},
                "total_revenue": 0.0,
            }
        return rev.to_dict()

    def get_domain_breakdown(
        self,
        corridor_id: str
    ) -> Dict[str, float]:
        """
        Get revenue attribution by domain for a corridor.

        Args:
            corridor_id: Corridor identifier

        Returns:
            Dictionary mapping domain to revenue amount
        """
        rev = self._corridor_revenues.get(corridor_id)
        if not rev:
            return {domain: 0.0 for domain in self.DOMAINS}
        return rev.revenue_by_domain

    def get_top_corridors(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top revenue-generating corridors.

        Args:
            limit: Number of corridors to return

        Returns:
            List of corridor revenue dictionaries sorted by total
        """
        corridors = []
        for cid, rev in self._corridor_revenues.items():
            total = sum(rev.revenue_by_domain.values())
            corridors.append({
                "corridor_id": cid,
                "total_revenue": total,
                "revenue_by_domain": rev.revenue_by_domain,
            })

        # Sort by total revenue (highest first)
        corridors.sort(key=lambda x: x["total_revenue"], reverse=True)
        return corridors[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get revenue attribution statistics."""
        if not self._corridor_revenues:
            return {
                "total_corridors": 0,
                "total_revenue": 0.0,
                "avg_revenue_per_corridor": 0.0,
            }

        total_revenue = sum(
            sum(r.revenue_by_domain.values())
            for r in self._corridor_revenues.values()
        )

        return {
            "total_corridors": len(self._corridor_revenues),
            "total_revenue": total_revenue,
            "avg_revenue_per_corridor": (
                total_revenue / len(self._corridor_revenues)
            ),
        }


# Import Optional for type hints
from typing import Optional

__all__ = [
    "CorridorRevenue",
    "RevenueAttribution",
]
