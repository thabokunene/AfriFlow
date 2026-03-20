"""
Leakage Detector for Corridors

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

logger = get_logger("corridor.leakage")


@dataclass
class LeakageSignal:
    corridor_id: str
    product: str
    cib_volume: float
    product_volume: float
    capture_rate_pct: float
    estimated_leakage_zar: float
    likely_competitor: str


class LeakageDetector:
    def __init__(self) -> None:
        logger.info("LeakageDetector initialized")

    def detect_leakage(
        self,
        corridor_id: str,
        cib_data: Dict,
        forex_data: Dict,
        insurance_data: Dict,
        cell_data: Dict,
        pbb_data: Dict,
    ) -> List[LeakageSignal]:
        """
        Detects leakage by comparing CIB payment volume against 
        product-specific volumes in the destination country.
        """
        signals = []
        cib_vol = cib_data.get("volume", 0.0)
        
        # Forex Leakage
        fx_vol = forex_data.get("volume", 0.0)
        if cib_vol > 0 and fx_vol < cib_vol * 0.8:  # We expect 80% coverage
            leakage = (cib_vol * 0.8) - fx_vol
            signals.append(LeakageSignal(
                corridor_id=corridor_id,
                product="Forex Hedging",
                cib_volume=cib_vol,
                product_volume=fx_vol,
                capture_rate_pct=(fx_vol / cib_vol) * 100 if cib_vol > 0 else 0,
                estimated_leakage_zar=leakage * 0.003, # 30bps spread
                likely_competitor=self.estimate_competitor("Forex", corridor_id.split("-")[1])
            ))

        # Insurance Leakage
        ins_vol = insurance_data.get("volume", 0.0)
        if cib_vol > 0 and ins_vol < cib_vol * 0.05: # We expect 5% premium/asset ratio
            leakage = (cib_vol * 0.05) - ins_vol
            signals.append(LeakageSignal(
                corridor_id=corridor_id,
                product="Marine/Trade Insurance",
                cib_volume=cib_vol,
                product_volume=ins_vol,
                capture_rate_pct=(ins_vol / (cib_vol * 0.05)) * 100 if cib_vol > 0 else 0,
                estimated_leakage_zar=leakage,
                likely_competitor=self.estimate_competitor("Insurance", corridor_id.split("-")[1])
            ))

        return signals

    def estimate_competitor(self, product: str, country: str) -> str:
        competitors = {
            "NG": {"Forex": "Access Bank", "Insurance": "AIICO"},
            "KE": {"Forex": "Equity Bank", "Insurance": "Jubilee"},
            "GH": {"Forex": "Ecobank", "Insurance": "Enterprise"},
        }
        return competitors.get(country, {}).get(product, "Local Tier 2 Bank")

    def calculate_total_leakage(self, signals: List[LeakageSignal]) -> float:
        return sum(s.estimated_leakage_zar for s in signals)

    def get_leakage_by_corridor(self) -> Dict[str, float]:
        return {}
