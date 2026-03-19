"""
@file __init__.py
@description Initialization for the Lekgotla collective intelligence module,
    providing a platform for knowledge sharing, discussion, and institutional
    memory creation across AfriFlow domains.
@author Thabo Kunene
@created 2026-03-19
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
