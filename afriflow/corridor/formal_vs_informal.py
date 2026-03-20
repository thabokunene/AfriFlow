"""
Formal vs Informal Flow Comparison

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.formal_informal")


@dataclass
class FlowComparison:
    corridor_id: str
    formal_volume: float
    formal_change_pct: float
    informal_volume: float
    informal_change_pct: float
    divergence_detected: bool
    divergence_interpretation: str


class FormalVsInformal:
    def __init__(self) -> None:
        logger.info("FormalVsInformal initialized")

    def compare_flows(
        self,
        corridor_id: str,
        cib_data: Dict,
        momo_data: Dict,
        lookback_days: int = 90,
    ) -> FlowComparison:
        """
        Compares formal (CIB) vs informal (MoMo) flows.
        If CIB drops and MoMo rises, it signals capital flight
        to informal channels.
        """
        formal_vol = cib_data.get("volume", 0.0)
        formal_prev = cib_data.get("previous_volume", formal_vol)
        informal_vol = momo_data.get("volume", 0.0)
        informal_prev = momo_data.get("previous_volume", informal_vol)

        formal_change = ((formal_vol - formal_prev) / formal_prev * 100) if formal_prev > 0 else 0
        informal_change = ((informal_vol - informal_prev) / informal_prev * 100) if informal_prev > 0 else 0

        divergence = formal_change < -10 and informal_change > 10
        interpretation = "Neutral"
        if divergence:
            interpretation = "CAPITAL_FLIGHT_TO_INFORMAL"
        elif formal_change < -20 and informal_change < -20:
            interpretation = "GENERAL_ECONOMIC_SLOWDOWN"

        return FlowComparison(
            corridor_id=corridor_id,
            formal_volume=formal_vol,
            formal_change_pct=formal_change,
            informal_volume=informal_vol,
            informal_change_pct=informal_change,
            divergence_detected=divergence,
            divergence_interpretation=interpretation,
        )

    def detect_divergence(
        self,
        corridor_id: str,
        threshold_pct: float,
    ) -> Optional[FlowComparison]:
        # Implementation to detect significant divergence across corridors
        return None

    def get_all_divergences(self) -> List[FlowComparison]:
        return []

    def interpret_divergence(
        self,
        comparison: FlowComparison,
        country_context: Dict,
    ) -> str:
        if comparison.divergence_interpretation == "CAPITAL_FLIGHT_TO_INFORMAL":
            if country_context.get("capital_controls") == "SEVERE":
                return "Regulatory arbitrage due to severe capital controls"
            return "Shift to informal trade settlement"
        return "No significant divergence"
