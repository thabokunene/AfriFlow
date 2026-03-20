"""
@file __init__.py
@description Corridor Module - Cross-Border Intelligence. Identifies, maps,
             and analyses payment corridors between countries. Tracks revenue
             attribution per corridor and detects competitive leakage where
             flows are being captured by competitors.
@author Thabo Kunene
@created 2026-03-19
"""

# ---------------------------------------------------------------------------
# Corridor Module - Cross-Border Intelligence
#
# Key Capabilities:
#   - Corridor identification and mapping
#   - Revenue attribution per corridor, per domain
#   - Leakage detection (formal vs informal flows)
#   - Corridor health scoring
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.
# ---------------------------------------------------------------------------

# --- Internal imports: pull public symbols up for consumer convenience ---
# Core engine for corridor discovery and management
from .corridor_engine import CorridorEngine, Corridor
# Multi-domain revenue attribution logic
from .revenue_attribution import RevenueAttribution
# Detection of client flow leakage to competitors
from .leakage_detector import LeakageDetector
# Analysis of formal banking vs mobile money (informal) flows
from .formal_vs_informal import FormalVsInformal

# Current version of the corridor module
__version__ = "1.0.0"
# Primary author and maintainer
__author__ = "Thabo Kunene"

# Public API surface — controls what 'from afriflow.corridor import *' exposes
__all__ = [
    # Engine and data model
    "CorridorEngine",
    "Corridor",
    # Attribution and detection logic
    "RevenueAttribution",
    "LeakageDetector",
    "FormalVsInformal",
]
