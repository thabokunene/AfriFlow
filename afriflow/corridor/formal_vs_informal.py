"""
@file formal_vs_informal.py
@description Corridor Formal vs Informal Flow Analysis - CIB vs MoMo flow comparison
@author Thabo Kunene
@created 2026-03-19

This module compares formal CIB payment flows with informal mobile money (MoMo)
flows to identify corridors where informal channels dominate. This helps identify
opportunities to migrate informal flows to formal banking channels.

Key Classes:
- FlowComparison: Comparison results for a corridor
- FormalVsInformalAnalyzer: Main analysis engine

Features:
- Formal vs informal flow comparison
- Informal ratio calculation
- Migration opportunity identification
- Trend analysis over time

Usage:
    >>> from afriflow.corridor.formal_vs_informal import FormalVsInformalAnalyzer
    >>> analyzer = FormalVsInformalAnalyzer()
    >>> comparison = analyzer.analyze_corridor(
    ...     corridor_id="ZA-NG",
    ...     cib_volume=1000000,
    ...     momo_volume=3000000
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.formal_informal")


@dataclass
class FlowComparison:
    """
    Formal vs informal flow comparison for a corridor.

    Captures the split between formal banking channels (CIB)
    and informal channels (mobile money, cash).

    Attributes:
        corridor_id: Corridor identifier
        period: Analysis period (e.g., "2026-03")
        cib_volume: Formal CIB volume
        momo_volume: Informal MoMo volume
        informal_ratio: MoMo/CIB ratio
        analysis_date: Analysis timestamp

    Example:
        >>> comparison = FlowComparison(
        ...     corridor_id="ZA-NG",
        ...     period="2026-03",
        ...     cib_volume=1000000,
        ...     momo_volume=3000000
        ... )
        >>> print(f"Informal ratio: {comparison.informal_ratio}")
    """
    corridor_id: str  # Corridor identifier
    period: str  # Analysis period (YYYY-MM)
    cib_volume: float  # Formal CIB volume
    momo_volume: float  # Informal MoMo volume
    informal_ratio: float = 0.0  # MoMo/CIB ratio
    analysis_date: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_volume(self) -> float:
        """Calculate total volume (formal + informal)."""
        return self.cib_volume + self.momo_volume

    @property
    def formal_percentage(self) -> float:
        """Calculate formal channel percentage."""
        if self.total_volume == 0:
            return 0.0
        return (self.cib_volume / self.total_volume) * 100

    @property
    def informal_percentage(self) -> float:
        """Calculate informal channel percentage."""
        if self.total_volume == 0:
            return 0.0
        return (self.momo_volume / self.total_volume) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "corridor_id": self.corridor_id,
            "period": self.period,
            "cib_volume": self.cib_volume,
            "momo_volume": self.momo_volume,
            "total_volume": self.total_volume,
            "formal_percentage": self.formal_percentage,
            "informal_percentage": self.informal_percentage,
            "informal_ratio": self.informal_ratio,
            "analysis_date": self.analysis_date,
        }


class FormalVsInformalAnalyzer:
    """
    Formal vs informal flow analysis engine.

    Compares CIB payment volumes with MoMo transaction
    volumes to identify corridors where informal channels
    dominate, indicating migration opportunities.

    Attributes:
        _comparisons: Dictionary mapping corridor-period to FlowComparison
        _corridor_history: Historical comparisons per corridor

    Example:
        >>> analyzer = FormalVsInformalAnalyzer()
        >>> comparison = analyzer.analyze_corridor(
        ...     corridor_id="ZA-NG",
        ...     cib_volume=1000000,
        ...     momo_volume=3000000
        ... )
    """

    def __init__(self) -> None:
        """Initialize analyzer with empty comparison store."""
        self._comparisons: Dict[str, FlowComparison] = {}
        self._corridor_history: Dict[str, List[FlowComparison]] = {}
        logger.info("FormalVsInformalAnalyzer initialized")

    def analyze_corridor(
        self,
        corridor_id: str,
        period: str,
        cib_volume: float,
        momo_volume: float
    ) -> FlowComparison:
        """
        Analyze formal vs informal flows for a corridor.

        Args:
            corridor_id: Corridor identifier
            period: Analysis period (YYYY-MM format)
            cib_volume: Formal CIB volume in ZAR
            momo_volume: Informal MoMo volume in ZAR

        Returns:
            FlowComparison object with analysis results

        Example:
            >>> comparison = analyzer.analyze_corridor(
            ...     corridor_id="ZA-NG",
            ...     period="2026-03",
            ...     cib_volume=1000000,
            ...     momo_volume=3000000
            ... )
            >>> print(f"Informal ratio: {comparison.informal_ratio}")
        """
        # Calculate informal ratio (MoMo / CIB)
        # Higher ratio means more informal activity
        if cib_volume > 0:
            informal_ratio = momo_volume / cib_volume
        else:
            # If no CIB volume, ratio is infinite (all informal)
            informal_ratio = float('inf') if momo_volume > 0 else 0.0

        # Create comparison object
        comparison = FlowComparison(
            corridor_id=corridor_id,
            period=period,
            cib_volume=cib_volume,
            momo_volume=momo_volume,
            informal_ratio=informal_ratio,
        )

        # Store comparison
        key = f"{corridor_id}:{period}"
        self._comparisons[key] = comparison

        # Update corridor history
        if corridor_id not in self._corridor_history:
            self._corridor_history[corridor_id] = []
        self._corridor_history[corridor_id].append(comparison)

        logger.debug(
            f"Analyzed {corridor_id}: CIB={cib_volume}, MoMo={momo_volume}, "
            f"ratio={informal_ratio:.2f}"
        )

        return comparison

    def get_comparison(
        self,
        corridor_id: str,
        period: str
    ) -> Optional[FlowComparison]:
        """
        Get comparison for a specific corridor and period.

        Args:
            corridor_id: Corridor identifier
            period: Period (YYYY-MM)

        Returns:
            FlowComparison if found, None otherwise
        """
        key = f"{corridor_id}:{period}"
        return self._comparisons.get(key)

    def get_corridor_history(
        self,
        corridor_id: str
    ) -> List[FlowComparison]:
        """
        Get historical comparisons for a corridor.

        Args:
            corridor_id: Corridor identifier

        Returns:
            List of FlowComparison objects sorted by period
        """
        history = self._corridor_history.get(corridor_id, [])
        return sorted(history, key=lambda x: x.period)

    def get_high_informal_corridors(
        self,
        threshold: float = 1.0
    ) -> List[FlowComparison]:
        """
        Get corridors where informal > formal.

        Args:
            threshold: Informal ratio threshold (default 1.0 = equal)

        Returns:
            List of FlowComparison objects with high informal ratio
        """
        return [
            c for c in self._comparisons.values()
            if c.informal_ratio > threshold
        ]

    def get_migration_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify opportunities to migrate informal to formal.

        Returns corridors with high informal volume that could
        potentially be migrated to formal banking channels.

        Returns:
            List of opportunity dictionaries sorted by potential
        """
        opportunities = []

        for comparison in self._comparisons.values():
            # Only consider corridors with significant informal activity
            if comparison.informal_ratio > 0.5:
                # Estimate migration potential (30% of informal is achievable)
                migration_potential = comparison.momo_volume * 0.3

                # Determine priority based on ratio
                if comparison.informal_ratio > 2.0:
                    priority = "HIGH"
                elif comparison.informal_ratio > 1.0:
                    priority = "MEDIUM"
                else:
                    priority = "LOW"

                opportunities.append({
                    "corridor_id": comparison.corridor_id,
                    "period": comparison.period,
                    "informal_volume": comparison.momo_volume,
                    "formal_volume": comparison.cib_volume,
                    "informal_ratio": comparison.informal_ratio,
                    "migration_potential": migration_potential,
                    "priority": priority,
                })

        # Sort by migration potential (highest first)
        opportunities.sort(
            key=lambda x: x["migration_potential"], reverse=True
        )

        return opportunities

    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        comparisons = list(self._comparisons.values())

        if not comparisons:
            return {
                "total_corridors_analyzed": 0,
                "total_comparisons": 0,
                "total_formal_volume": 0,
                "total_informal_volume": 0,
                "avg_informal_ratio": 0,
            }

        total_formal = sum(c.cib_volume for c in comparisons)
        total_informal = sum(c.momo_volume for c in comparisons)
        avg_ratio = sum(c.informal_ratio for c in comparisons) / len(comparisons)

        high_informal = [
            c for c in comparisons if c.informal_ratio > 1.0
        ]

        return {
            "total_corridors_analyzed": len(self._corridor_history),
            "total_comparisons": len(comparisons),
            "total_formal_volume": total_formal,
            "total_informal_volume": total_informal,
            "overall_informal_ratio": (
                total_informal / total_formal if total_formal > 0 else float('inf')
            ),
            "avg_informal_ratio": avg_ratio,
            "high_informal_corridors": len(high_informal),
            "migration_potential": sum(
                c.momo_volume * 0.3 for c in high_informal
            ),
        }


# Import Optional for type hints
from typing import Optional

__all__ = [
    "FlowComparison",
    "FormalVsInformalAnalyzer",
]
