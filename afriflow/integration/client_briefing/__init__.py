"""
@file __init__.py
@description Client-briefing sub-package initialisation. Exposes the primary
             public classes so callers can import from a single namespace
             without knowing the internal module layout.
@author Thabo Kunene
@created 2026-03-19
"""

# ---------------------------------------------------------------------------
# Client Briefing Integration Sub-package
#
# Provides the integration-ready version of the briefing generator and
# its associated talking points engine. This sub-package is designed
# for use within production data pipelines.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.
# ---------------------------------------------------------------------------

# --- Internal imports: pull primary symbols up for consumer convenience ---
# Core briefing generator class for integration pipelines
from .briefing_generator import BriefingGenerator
# Lexical engine for generating conversation starters
from .talking_points_engine import TalkingPointsEngine

# --- Public API surface control ---
# Lists symbols exported when using 'from afriflow.integration.client_briefing import *'
__all__ = [
    "BriefingGenerator",
    "TalkingPointsEngine",
]
