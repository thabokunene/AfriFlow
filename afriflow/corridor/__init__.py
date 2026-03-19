"""
Corridor Module - Cross-Border Intelligence

Identifies, maps, and analyzes payment corridors between countries.
Tracks revenue attribution per corridor and detects competitive
leakage where flows are being captured by competitors.

Key Capabilities:
- Corridor identification and mapping
- Revenue attribution per corridor, per domain
- Leakage detection (formal vs informal flows)
- Corridor health scoring

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .corridor_engine import CorridorEngine, Corridor
from .revenue_attribution import RevenueAttribution
from .leakage_detector import LeakageDetector
from .formal_vs_informal import FormalVsInformalAnalyzer

__version__ = "1.0.0"
__author__ = "Thabo Kunene"

__all__ = [
    "CorridorEngine",
    "Corridor",
    "RevenueAttribution",
    "LeakageDetector",
    "FormalVsInformalAnalyzer",
]
