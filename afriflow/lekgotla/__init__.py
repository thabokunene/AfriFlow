"""
Lekgotla Module - Collective Intelligence Platform

Lekgotla is a Setswana word meaning "a gathering place for community
decision-making and knowledge sharing." This module implements the
collective intelligence layer of AfriFlow where Relationship Managers,
product specialists, and domain experts share insights, validate
approaches, and build institutional memory.

Core Components:
- Thread Store: Discussion management and search
- Knowledge Card Store: Validated approach curation
- Context Matching Engine: Signal-anchored thread matching
- Notification Engine: Push relevant threads to practitioners
- Regulatory Channel: Compliance intelligence posts
- Contribution Tracker: Gamification and scoring
- Moderation: Content governance and review
- Analytics: Platform health metrics

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .thread_store import ThreadStore, Thread, Reply
from .knowledge_card_store import KnowledgeCardStore, KnowledgeCard
from .context_matching_engine import ContextMatchingEngine
from .notification_engine import NotificationEngine
from .regulatory_channel import RegulatoryChannel
from .contribution_tracker import ContributionTracker
from .moderation import ContentModerator
from .analytics import LekgotlaAnalytics

__version__ = "1.0.0"
__author__ = "Thabo Kunene"

__all__ = [
    "ThreadStore",
    "Thread",
    "Reply",
    "KnowledgeCardStore",
    "KnowledgeCard",
    "ContextMatchingEngine",
    "NotificationEngine",
    "RegulatoryChannel",
    "ContributionTracker",
    "ContentModerator",
    "LekgotlaAnalytics",
]
