"""
Formal vs Informal Flow Analyzer

Compares formal CIB payment flows with informal MoMo flows
to identify corridors where informal channels dominate.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.formal_vs_informal")


@dataclass
class FlowComparison:
    """Comparison of formal vs informal flows."""
    corridor_id: str
    period: str
    formal_volume: float
    informal_volume: float
    formal_transaction_count: int
    informal_transaction_count: int
    informal_ratio: float
    analysis_date: datetime

    @property
    def total_volume(self) -> float:
        return self.formal_volume + self.informal_volume

    @property
    def formal_percentage(self) -> float:
        if self.total_volume == 0:
            return 0
        return (self.formal_volume / self.total_volume) * 100

    @property
    def informal_percentage(self) -> float:
        if self.total_volume == 0:
            return 0
        return (self.informal_volume / self.total_volume) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corridor_id": self.corridor_id,
            "period": self.period,
            "formal_volume": self.formal_volume,
            "informal_volume": self.informal_volume,
            "formal_transaction_count": self.formal_transaction_count,
            "informal_transaction_count": self.informal_transaction_count,
            "informal_ratio": self.informal_ratio,
            "formal_percentage": self.formal_percentage,
            "informal_percentage": self.informal_percentage,
            "total_volume": self.total_volume,
            "analysis_date": self.analysis_date.isoformat(),
        }


class FormalVsInformalAnalyzer:
    """
    Formal vs informal flow analysis.

    Compares CIB payment volumes with MoMo transaction
    volumes to identify corridors where informal channels
    may be dominating.
    """

    def __init__(self):
        self._comparisons: Dict[str, FlowComparison] = {}
        self._corridor_history: Dict[str, List[FlowComparison]] = {}

        logger.info("FormalVsInformalAnalyzer initialized")

    def analyze_corridor(
        self,
        corridor_id: str,
        period: str,
        cib_volume: float,
        cib_transactions: int,
        momo_volume: float,
        momo_transactions: int,
    ) -> FlowComparison:
        """
        Analyze formal vs informal flows for a corridor.

        Args:
            corridor_id: Corridor to analyze
            period: Period identifier (e.g., "2025-03")
            cib_volume: Formal CIB payment volume
            cib_transactions: CIB transaction count
            momo_volume: Informal MoMo volume
            momo_transactions: MoMo transaction count

        Returns:
            FlowComparison object
        """
        # Calculate informal ratio
        if cib_volume > 0:
            informal_ratio = momo_volume / cib_volume
        else:
            informal_ratio = float('inf') if momo_volume > 0 else 0

        comparison = FlowComparison(
            corridor_id=corridor_id,
            period=period,
            formal_volume=cib_volume,
            informal_volume=momo_volume,
            formal_transaction_count=cib_transactions,
            informal_transaction_count=momo_transactions,
            informal_ratio=informal_ratio,
            analysis_date=datetime.now(),
        )

        # Store comparison
        key = f"{corridor_id}:{period}"
        self._comparisons[key] = comparison

        # Update history
        if corridor_id not in self._corridor_history:
            self._corridor_history[corridor_id] = []
        self._corridor_history[corridor_id].append(comparison)

        logger.debug(
            f"Analyzed corridor {corridor_id}: "
            f"formal={cib_volume}, informal={momo_volume}, "
            f"ratio={informal_ratio:.2f}"
        )

        return comparison

    def get_comparison(
        self, corridor_id: str, period: str
    ) -> Optional[FlowComparison]:
        """Get comparison for a specific corridor and period."""
        key = f"{corridor_id}:{period}"
        return self._comparisons.get(key)

    def get_corridor_history(
        self, corridor_id: str
    ) -> List[FlowComparison]:
        """Get historical comparisons for a corridor."""
        return self._corridor_history.get(corridor_id, [])

    def get_high_informal_corridors(
        self, threshold: float = 1.0
    ) -> List[FlowComparison]:
        """
        Get corridors where informal > formal.

        Args:
            threshold: Informal ratio threshold (default 1.0 = equal)

        Returns:
            List of FlowComparison objects
        """
        return [
            c for c in self._comparisons.values()
            if c.informal_ratio > threshold
        ]

    def get_migration_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify opportunities to migrate informal to formal.

        Returns corridors with high informal volume that could
        potentially be migrated to formal channels.
        """
        opportunities = []

        for comparison in self._comparisons.values():
            if comparison.informal_ratio > 0.5:
                opportunities.append({
                    "corridor_id": comparison.corridor_id,
                    "period": comparison.period,
                    "informal_volume": comparison.informal_volume,
                    "formal_volume": comparison.formal_volume,
                    "informal_ratio": comparison.informal_ratio,
                    "migration_potential": comparison.informal_volume * 0.3,
                    "priority": (
                        "high" if comparison.informal_ratio > 2.0
                        else "medium" if comparison.informal_ratio > 1.0
                        else "low"
                    ),
                })

        # Sort by migration potential
        opportunities.sort(
            key=lambda x: x["migration_potential"], reverse=True
        )

        return opportunities

    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        comparisons = list(self._comparisons.values())

        if not comparisons:
            return self._empty_stats()

        total_formal = sum(c.formal_volume for c in comparisons)
        total_informal = sum(c.informal_volume for c in comparisons)
        avg_ratio = sum(c.informal_ratio for c in comparisons) / len(comparisons)

        high_informal = [
            c for c in comparisons if c.informal_ratio > 1.0
        ]

        return {
            "total_corridors_analyzed": len(
                self._corridor_history
            ),
            "total_comparisons": len(comparisons),
            "total_formal_volume": total_formal,
            "total_informal_volume": total_informal,
            "overall_informal_ratio": (
                total_informal / total_formal
                if total_formal > 0 else float('inf')
            ),
            "avg_informal_ratio": avg_ratio,
            "high_informal_corridors": len(high_informal),
            "migration_potential": sum(
                c.informal_volume * 0.3 for c in high_informal
            ),
        }

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "total_corridors_analyzed": 0,
            "total_comparisons": 0,
            "total_formal_volume": 0,
            "total_informal_volume": 0,
            "overall_informal_ratio": 0,
            "avg_informal_ratio": 0,
            "high_informal_corridors": 0,
            "migration_potential": 0,
        }
