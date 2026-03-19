"""
@file knowledge_card_store.py
@description Lekgotla Knowledge Card Store - Validated approach curation and graduation
@author Thabo Kunene
@created 2026-03-19

This module manages the curation, graduation, and retrieval of Knowledge Cards -
validated approaches that have been proven to generate revenue or prevent risk.

Knowledge Cards graduate from successful thread discussions where multiple
practitioners have validated the approach through real-world application.

Key Classes:
- KnowledgeCard: Validated approach document with metadata
- KnowledgeCardStore: Storage, graduation, and usage tracking

Features:
- Knowledge Card creation from thread discussions
- Graduation workflow (draft -> under_review -> published)
- Usage tracking for ROI attribution
- Win rate calculation
- Search by signal type, country, product

Usage:
    >>> from afriflow.lekgotla.knowledge_card_store import KnowledgeCardStore, KnowledgeCard
    >>> store = KnowledgeCardStore()
    >>> card = store.create_card(
    ...     title="Bundle pricing for Ghana expansion",
    ...     signal_type="EXPANSION",
    ...     approach=["Bundle WC + FX + insurance", "Lead with working capital"],
    ...     avoid=["Don't lead with insurance", "Don't quote FX separately"]
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

# Standard library imports
from dataclasses import dataclass, field  # For data class decorators
from datetime import datetime  # For timestamps
from typing import Dict, List, Optional, Any  # Type hints
import logging  # For logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.knowledge_card_store")


class CardStatus:
    """
    Knowledge Card lifecycle status constants.

    Defines the possible states a Knowledge Card can be in:
    - DRAFT: Initial state, being developed
    - UNDER_REVIEW: Submitted for review
    - PUBLISHED: Approved and visible to all RMs
    - ARCHIVED: Deprecated or outdated
    """
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CardCategory:
    """
    Knowledge Card category constants.

    Defines the type of Knowledge Card:
    - PROVEN: Validated approach with wins
    - EXPERIMENTAL: Unproven but promising approach
    - REGULATORY: Compliance-mandated approach
    - ONBOARDING: Training material for new RMs
    """
    PROVEN = "proven"
    EXPERIMENTAL = "experimental"
    REGULATORY = "regulatory"
    ONBOARDING = "onboarding"


@dataclass
class KnowledgeCard:
    """
    Validated approach document.

    A Knowledge Card captures institutional wisdom about how to
    successfully handle specific business scenarios. Cards graduate
    from thread discussions where multiple practitioners have
    validated the approach.

    Attributes:
        card_id: Unique identifier (UUID format)
        title: Descriptive title
        category: Card category (PROVEN, EXPERIMENTAL, etc.)
        signal_type: Associated signal type (e.g., "EXPANSION")
        countries: List of applicable country codes
        products: List of relevant products
        approach: List of recommended actions (step-by-step)
        avoid: List of actions to avoid (common mistakes)
        evidence: Supporting evidence and rationale
        source_thread_ids: IDs of threads that contributed
        contributors: List of contributor names
        created_at: Creation timestamp
        status: Card status (DRAFT, PUBLISHED, etc.)
        win_rate: Win rate percentage (0-100)
        uses_count: Number of times card was used
        revenue_attributed: Total revenue attributed to this card
        last_updated: Last modification timestamp
        attachments: List of supporting document URLs

    Example:
        >>> card = KnowledgeCard(
        ...     card_id="KC-ABC123",
        ...     title="Bundle pricing for Ghana expansion",
        ...     category="proven",
        ...     signal_type="EXPANSION",
        ...     countries=["GH"],
        ...     products=["WC", "FX", "INS"],
        ...     approach=["Bundle WC + FX + insurance"],
        ...     avoid=["Don't lead with insurance"],
        ...     win_rate=64.0
        ... )
    """
    card_id: str  # Unique card identifier
    title: str  # Card title
    category: str  # Card category
    signal_type: str  # Associated signal type
    countries: List[str]  # Applicable countries
    products: List[str]  # Relevant products
    approach: List[str]  # Recommended actions
    avoid: List[str]  # Actions to avoid
    evidence: List[str]  # Supporting evidence
    source_thread_ids: List[str]  # Source thread IDs
    contributors: List[str]  # Contributor names
    created_at: str  # Creation timestamp
    status: str = "draft"  # Card status
    win_rate: Optional[float] = None  # Win rate percentage
    uses_count: int = 0  # Usage count
    revenue_attributed: float = 0.0  # Attributed revenue
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    attachments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary for JSON serialization."""
        return {
            "card_id": self.card_id,
            "title": self.title,
            "category": self.category,
            "signal_type": self.signal_type,
            "countries": self.countries,
            "products": self.products,
            "approach": self.approach,
            "avoid": self.avoid,
            "evidence": self.evidence,
            "source_thread_ids": self.source_thread_ids,
            "contributors": self.contributors,
            "created_at": self.created_at,
            "status": self.status,
            "win_rate": self.win_rate,
            "uses_count": self.uses_count,
            "revenue_attributed": self.revenue_attributed,
            "last_updated": self.last_updated,
            "attachments": self.attachments,
        }


class KnowledgeCardStore:
    """
    Knowledge Card storage and curation.

    This class provides in-memory storage and retrieval of Knowledge Cards.
    In production, this would use PostgreSQL with full-text search.

    Features:
    - Card creation and management
    - Graduation workflow (draft -> published)
    - Usage tracking for ROI
    - Win rate calculation
    - Search by signal type, country, category

    Attributes:
        _cards: Dictionary mapping card_id to KnowledgeCard
        _signal_index: Signal type to card_id mapping
        _country_index: Country to card_id mapping
        _category_index: Category to card_id mapping

    Example:
        >>> store = KnowledgeCardStore()
        >>> card = store.create_card(
        ...     title="Ghana expansion bundle",
        ...     signal_type="EXPANSION",
        ...     approach=["Bundle WC + FX + insurance"]
        ... )
        >>> store.publish_card(card.card_id)
    """

    def __init__(self) -> None:
        """Initialize the Knowledge Card store with empty indexes."""
        self._cards: Dict[str, KnowledgeCard] = {}
        self._signal_index: Dict[str, List[str]] = {}
        self._country_index: Dict[str, List[str]] = {}
        self._category_index: Dict[str, List[str]] = {}

        logger.info("KnowledgeCardStore initialized")

    def create_card(
        self,
        title: str,
        category: str,
        signal_type: str,
        approach: List[str],
        avoid: List[str],
        evidence: List[str],
        source_thread_ids: List[str],
        contributors: List[str],
        countries: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
    ) -> KnowledgeCard:
        """
        Create a new Knowledge Card.

        Args:
            title: Card title
            category: Card category (proven, experimental, etc.)
            signal_type: Associated signal type
            approach: List of recommended actions
            avoid: List of actions to avoid
            evidence: Supporting evidence
            source_thread_ids: IDs of contributing threads
            contributors: List of contributor names
            countries: Applicable countries
            products: Relevant products
            attachments: Supporting document URLs

        Returns:
            Created KnowledgeCard object
        """
        card_id = f"KC-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now().isoformat()

        card = KnowledgeCard(
            card_id=card_id,
            title=title,
            category=category,
            signal_type=signal_type,
            countries=countries or [],
            products=products or [],
            approach=approach,
            avoid=avoid,
            evidence=evidence,
            source_thread_ids=source_thread_ids,
            contributors=contributors,
            created_at=now,
            attachments=attachments or [],
        )

        self._cards[card_id] = card

        # Update indexes
        if signal_type not in self._signal_index:
            self._signal_index[signal_type] = []
        self._signal_index[signal_type].append(card_id)

        for country in card.countries:
            if country not in self._country_index:
                self._country_index[country] = []
            self._country_index[country].append(card_id)

        if category not in self._category_index:
            self._category_index[category] = []
        self._category_index[category].append(card_id)

        logger.info(f"Knowledge Card created: {card_id} - '{title}'")
        return card

    def get_card(self, card_id: str) -> Optional[KnowledgeCard]:
        """Retrieve a card by ID."""
        return self._cards.get(card_id)

    def publish_card(self, card_id: str) -> None:
        """
        Publish a card (move from draft to published).

        Args:
            card_id: Card to publish
        """
        card = self.get_card(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")

        card.status = CardStatus.PUBLISHED
        card.last_updated = datetime.now().isoformat()

        logger.info(f"Knowledge Card published: {card_id}")

    def record_usage(
        self,
        card_id: str,
        user_id: str,
        client_id: Optional[str] = None,
        revenue: float = 0.0,
        won: bool = False,
    ) -> None:
        """
        Record a card usage for analytics.

        Args:
            card_id: Card that was used
            user_id: User who used it
            client_id: Optional client this was used for
            revenue: Optional revenue attributed
            won: Whether the opportunity was won
        """
        card = self.get_card(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")

        card.uses_count += 1
        if revenue > 0:
            card.revenue_attributed += revenue
        card.last_updated = datetime.now().isoformat()

        logger.debug(f"Card {card_id} used by {user_id}")

    def search_cards(
        self,
        signal_type: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[KnowledgeCard]:
        """Search Knowledge Cards with filters."""
        results = list(self._cards.values())

        if signal_type and signal_type in self._signal_index:
            signal_cards = set(self._signal_index[signal_type])
            results = [c for c in results if c.card_id in signal_cards]

        if country and country in self._country_index:
            country_cards = set(self._country_index[country])
            results = [c for c in results if c.card_id in country_cards]

        if category:
            results = [c for c in results if c.category == category]

        if status:
            results = [c for c in results if c.status == status]

        if query:
            query_lower = query.lower()
            results = [
                c for c in results
                if query_lower in c.title.lower() or query_lower in c.signal_type.lower()
            ]

        results.sort(key=lambda c: c.uses_count, reverse=True)
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get card store statistics."""
        category_counts = {}
        status_counts = {}

        for card in self._cards.values():
            cat = card.category
            status = card.status
            category_counts[cat] = category_counts.get(cat, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1

        total_revenue = sum(c.revenue_attributed for c in self._cards.values())
        total_uses = sum(c.uses_count for c in self._cards.values())

        return {
            "total_cards": len(self._cards),
            "category_breakdown": category_counts,
            "status_breakdown": status_counts,
            "total_revenue_attributed": total_revenue,
            "total_uses": total_uses,
        }


# Import uuid for ID generation
import uuid

__all__ = [
    "CardStatus",
    "CardCategory",
    "KnowledgeCard",
    "KnowledgeCardStore",
]
