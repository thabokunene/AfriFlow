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
        lookback_days: int,
    ) -> FlowComparison:
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
        return None

    def get_all_divergences(self) -> List[FlowComparison]:
        return []

    def interpret_divergence(
        self,
        comparison: FlowComparison,
        country_context: Dict,
    ) -> str:
        return "No divergence"
