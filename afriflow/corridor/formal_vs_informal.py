"""
@file formal_vs_informal.py
@description Compares formal banking flows (CIB) with informal mobile money
             flows (MoMo) across trade corridors. Detects divergences where
             clients may be shifting business away from formal banking channels,
             providing interpretation of these shifts based on country-specific
             economic or regulatory context.
@author Thabo Kunene
@created 2026-03-19
"""

# Formal vs Informal Flow Comparison
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data modeling and type hinting
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

# Centralised platform logging
from afriflow.logging_config import get_logger

# Initialise a module-scoped logger for flow analysis events
logger = get_logger("corridor.formal_informal")


@dataclass
class FlowComparison:
    """
    Represents the comparison between formal and informal flows for a corridor.

    :param corridor_id: The ID of the corridor being analyzed
    :param formal_volume: Aggregate CIB payment volume in ZAR
    :param formal_change_pct: Percentage change in formal volume vs prior period
    :param informal_volume: Aggregate MoMo payment volume in ZAR
    :param informal_change_pct: Percentage change in informal volume vs prior period
    :param divergence_detected: True if the shift between channels exceeds threshold
    :param divergence_interpretation: Plain-English explanation of the divergence
    """

    corridor_id: str
    formal_volume: float
    formal_change_pct: float
    informal_volume: float
    informal_change_pct: float
    divergence_detected: bool
    divergence_interpretation: str


class FormalVsInformalAnalyzer:
    """
    Analyses and interprets shifts between formal banking and informal channels.
    """

    def __init__(self) -> None:
        """
        Initialise the analyzer component.
        """
        logger.info("FormalVsInformalAnalyzer initialized")

    def compare_flows(
        self,
        corridor_id: str,
        cib_data: Dict,
        momo_data: Dict,
        lookback_days: int,
    ) -> FlowComparison:
        """
        Perform a side-by-side comparison of CIB and MoMo flows.

        :param corridor_id: ID of the corridor to analyze
        :param cib_data: Aggregated formal banking data
        :param momo_data: Aggregated mobile money data
        :param lookback_days: Period for the comparison
        :return: A FlowComparison object with calculated metrics.
        """
        # --- Logic to calculate volumes and changes would be implemented here ---
        return FlowComparison(
            corridor_id=corridor_id,
            formal_volume=0.0,
            formal_change_pct=0.0,
            informal_volume=0.0,
            informal_change_pct=0.0,
            divergence_detected=False,
            divergence_interpretation="No data",
        )

    def detect_divergence(
        self,
        corridor_id: str,
        threshold_pct: float,
    ) -> Optional[FlowComparison]:
        """
        Check if a specific corridor shows significant flow divergence.

        :param corridor_id: The ID of the corridor
        :param threshold_pct: The divergence threshold (e.g., 10.0 for 10%)
        :return: FlowComparison if divergence exists, else None.
        """
        return None

    def get_all_divergences(self) -> List[FlowComparison]:
        """
        Retrieve all corridors currently showing significant flow shifts.

        :return: A list of FlowComparison objects for divergent corridors.
        """
        return []

    def interpret_divergence(
        self,
        comparison: FlowComparison,
        country_context: Dict,
    ) -> str:
        """
        Apply regional expertise to explain why a flow shift might be occurring.

        :param comparison: The calculated flow comparison data
        :param country_context: External factors (e.g., devaluations, new taxes)
        :return: A narrative interpretation string.
        """
        return "No divergence"
