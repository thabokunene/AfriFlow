"""
@file __init__.py
@description Public API surface for the client_briefing package. Exposes the
             core dataclasses and the BriefingGenerator class so that any
             consumer can import everything they need from a single namespace.
@author Thabo Kunene
@created 2026-03-19
"""

# ---------------------------------------------------------------------------
# Client Briefing Module
#
# We generate pre-meeting intelligence briefings that
# synthesise cross-domain signals, data shadow gaps,
# seasonal context, and currency event impacts into a
# single 2-minute readable artifact for Relationship
# Managers.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.
# ---------------------------------------------------------------------------

# --- Internal imports: pull public symbols up for consumer convenience ---
# Orchestrates briefing assembly from raw inputs
from afriflow.client_briefing.briefing_generator import BriefingGenerator
# Top-level dataclass representing the complete briefing artifact
from afriflow.client_briefing.briefing_generator import ClientBriefing
# A titled, prioritised content block within a briefing
from afriflow.client_briefing.briefing_generator import BriefingSection
# Represents one change detected since the last meeting
from afriflow.client_briefing.briefing_generator import ChangeEvent
# A ranked revenue opportunity for the RM to act on
from afriflow.client_briefing.briefing_generator import Opportunity
# A flagged risk the RM needs to discuss with the client
from afriflow.client_briefing.briefing_generator import RiskAlert

# --- Public API surface control ---
# Lists all symbols exported when using 'from afriflow.client_briefing import *'
__all__ = [
    # Core generator class
    "BriefingGenerator",
    # Data models for briefing components
    "ClientBriefing",
    "BriefingSection",
    "ChangeEvent",
    "Opportunity",
    "RiskAlert",
]
