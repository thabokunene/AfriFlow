"""
@file __init__.py
@description Public API surface for the client_briefing package. Exposes the
             core dataclasses and the BriefingGenerator class so that any
             consumer can import everything they need from a single namespace:
             ``from afriflow.client_briefing import BriefingGenerator``.
@author Thabo Kunene
@created 2026-03-17
"""

"""
Client Briefing Module

We generate pre-meeting intelligence briefings that
synthesize cross-domain signals, data shadow gaps,
seasonal context, and currency event impacts into a
single 2-minute readable artifact for Relationship
Managers.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# ---------------------------------------------------------------------------
# Internal imports — pull the public symbols up from the implementation
# module so callers never need to know the internal submodule path.
# ---------------------------------------------------------------------------
from afriflow.client_briefing.briefing_generator import (
    BriefingGenerator,   # Orchestrates briefing assembly from raw inputs
    ClientBriefing,      # Top-level dataclass: the complete briefing artifact
    BriefingSection,     # A titled, prioritised block within a briefing
    ChangeEvent,         # Represents one change detected since the last meeting
    Opportunity,         # A ranked revenue opportunity for the RM to act on
    RiskAlert,           # A flagged risk the RM needs to discuss with the client
)

# ---------------------------------------------------------------------------
# __all__ controls what is re-exported when a consumer does
# ``from afriflow.client_briefing import *``.  Keep it in sync with the
# imports above so the public contract is explicit and auditable.
# ---------------------------------------------------------------------------
__all__ = [
    "BriefingGenerator",
    "ClientBriefing",
    "BriefingSection",
    "ChangeEvent",
    "Opportunity",
    "RiskAlert",
]
