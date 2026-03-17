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

from afriflow.client_briefing.briefing_generator import (
    BriefingGenerator,
    ClientBriefing,
    BriefingSection,
    ChangeEvent,
    Opportunity,
    RiskAlert,
)

__all__ = [
    "BriefingGenerator",
    "ClientBriefing",
    "BriefingSection",
    "ChangeEvent",
    "Opportunity",
    "RiskAlert",
]
