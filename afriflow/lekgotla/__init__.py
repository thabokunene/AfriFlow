"""
@file __init__.py
@description Lekgotla Module - Collective Intelligence Platform initialization
@author Thabo Kunene
@created 2026-03-19

Lekgotla is a Setswana word meaning "a gathering place for community
decision-making and knowledge sharing." This module implements the
collective intelligence layer of AfriFlow where Relationship Managers,
product specialists, and domain experts share insights, validate
approaches, and build institutional memory.

Core Components:
- ThreadStore: Discussion thread management and search
- KnowledgeCardStore: Validated approach curation and graduation
- ContextMatchingEngine: Signal-anchored thread matching
- NotificationEngine: Push relevant threads to practitioners
- RegulatoryChannel: Compliance intelligence posts
- ContributionTracker: Gamification and scoring
- ContentModerator: Content filtering and review
- LekgotlaAnalytics: Platform health metrics

Key Features:
- Signal-anchored discussions (threads linked to expansion signals, etc.)
- Knowledge Card graduation (validated approaches from successful threads)
- Contribution scoring (points for threads, replies, solutions)
- Regulatory alerts (compliance officer reviewed posts)
- Content moderation (PII detection, spam filtering)

Usage:
    >>> from afriflow.lekgotla import ThreadStore, KnowledgeCardStore
    >>> thread_store = ThreadStore()
    >>> thread = thread_store.create_thread(
    ...     title="Ghana expansion approach",
    ...     content="What worked for your Ghana expansions?",
    ...     author_id="user-123",
    ...     author_name="Sipho Mabena",
    ...     signal_type="EXPANSION"
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Import core Lekgotla components for re-export at package level
# These are the main classes users will interact with
from .thread_store import ThreadStore, Thread, Reply  # Thread management
from .knowledge_card_store import KnowledgeCardStore, KnowledgeCard  # Knowledge curation
from .context_matching_engine import ContextMatchingEngine  # Signal-thread matching
from .notification_engine import NotificationEngine  # User notifications
from .regulatory_channel import RegulatoryChannel  # Compliance posts
from .contribution_tracker import ContributionTracker  # Gamification
from .moderation import ContentModerator  # Content filtering
from .analytics import LekgotlaAnalytics  # Platform metrics

# Package metadata
__version__ = "1.0.0"  # Lekgotla module version (semantic versioning)
__author__ = "Thabo Kunene"  # Module author

# Public API - defines what's exported for 'from afriflow.lekgotla import *'
# This makes the main classes available at the package level
__all__ = [
    # Thread management classes
    "ThreadStore",  # Main thread CRUD and search
    "Thread",  # Thread data model
    "Reply",  # Reply data model
    # Knowledge card classes
    "KnowledgeCardStore",  # Knowledge card CRUD and graduation
    "KnowledgeCard",  # Knowledge card data model
    # Matching and notification
    "ContextMatchingEngine",  # Signal-thread matching engine
    "NotificationEngine",  # User notification delivery
    # Regulatory and gamification
    "RegulatoryChannel",  # Compliance alert management
    "ContributionTracker",  # Points and leaderboard tracking
    # Moderation and analytics
    "ContentModerator",  # Content filtering and review
    "LekgotlaAnalytics",  # Platform health metrics
]
