"""
Lekgotla Knowledge Card Store

Manages the curation, graduation, and retrieval of Knowledge Cards -
validated approaches that have been proven to generate revenue or
prevent risk.

Knowledge Cards graduate from successful thread discussions where
multiple practitioners have validated the approach.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.knowledge_card_store")


class CardStatus(Enum):
    """Knowledge Card lifecycle status."""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CardCategory(Enum):
    """Knowledge Card categories."""
    PROVEN = "proven"
    EXPERIMENTAL = "experimental"
    REGULATORY = "regulatory"
    ONBOARDING = "onboarding"


@dataclass
class KnowledgeCard:
    """A validated approach document."""
    card_id: str
    title: str
    category: CardCategory
    signal_type: str
    countries: List[str]
    products: List[str]
    approach: List[str]
    avoid: List[str]
    evidence: List[str]
    source_thread_ids: List[str]
    contributors: List[str]
    created_at: datetime
    status: CardStatus = CardStatus.DRAFT
    win_rate: Optional[float] = None
    uses_count: int = 0
    revenue_attributed: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    attachments: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "card_id": self.card_id,
            "title": self.title,
            "category": self.category.value,
            "signal_type": self.signal_type,
            "countries": self.countries,
            "products": self.products,
            "approach": self.approach,
            "avoid": self.avoid,
            "evidence": self.evidence,
            "source_thread_ids": self.source_thread_ids,
            "contributors": self.contributors,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "win_rate": self.win_rate,
            "uses_count": self.uses_count,
            "revenue_attributed": self.revenue_attributed,
            "last_updated": self.last_updated.isoformat(),
            "attachments": self.attachments,
        }


class KnowledgeCardStore:
    """
    Knowledge Card storage and curation.

    Attributes:
        cards: Dictionary of card_id to KnowledgeCard
        signal_index: Dictionary of signal_type to list of card_id
        country_index: Dictionary of country to list of card_id
    """

    def __init__(self):
        self._cards: Dict[str, KnowledgeCard] = {}
        self._signal_index: Dict[str, List[str]] = {}
        self._country_index: Dict[str, List[str]] = {}
        self._category_index: Dict[str, List[str]] = {}

        logger.info("KnowledgeCardStore initialized")

    def create_card(
        self,
        title: str,
        category: CardCategory,
        signal_type: str,
        approach: List[str],
        avoid: List[str],
        evidence: List[str],
        source_thread_ids: List[str],
        contributors: List[str],
        countries: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> KnowledgeCard:
        """
        Create a new Knowledge Card.

        Args:
            title: Card title
            category: Card category
            signal_type: Associated signal type
            approach: List of recommended actions
            avoid: List of actions to avoid
            evidence: Supporting evidence
            source_thread_ids: Threads this graduated from
            contributors: List of contributor names
            countries: Applicable countries
            products: Related products
            attachments: Supporting documents

        Returns:
            Created KnowledgeCard
        """
        import uuid

        card_id = f"KC-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now()

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

        cat_key = category.value
        if cat_key not in self._category_index:
            self._category_index[cat_key] = []
        self._category_index[cat_key].append(card_id)

        logger.info(f"Knowledge Card created: {card_id} - '{title}'")

        return card

    def get_card(self, card_id: str) -> Optional[KnowledgeCard]:
        """Get a card by ID."""
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
        card.last_updated = datetime.now()

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
        card.last_updated = datetime.now()

        logger.debug(
            f"Card {card_id} used by {user_id}"
            f"{' - won' if won else ''}"
        )

    def search_cards(
        self,
        signal_type: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[CardCategory] = None,
        status: Optional[CardStatus] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[KnowledgeCard]:
        """
        Search Knowledge Cards.

        Args:
            signal_type: Filter by signal type
            country: Filter by country
            category: Filter by category
            status: Filter by status
            query: Full-text search
            limit: Maximum results

        Returns:
            List of matching KnowledgeCard objects
        """
        results = list(self._cards.values())

        if signal_type and signal_type in self._signal_index:
            signal_cards = set(self._signal_index[signal_type])
            results = [
                c for c in results if c.card_id in signal_cards
            ]

        if country and country in self._country_index:
            country_cards = set(self._country_index[country])
            results = [
                c for c in results if c.card_id in country_cards
            ]

        if category:
            results = [c for c in results if c.category == category]

        if status:
            results = [c for c in results if c.status == status]

        if query:
            query_lower = query.lower()
            results = [
                c for c in results
                if (
                    query_lower in c.title.lower()
                    or query_lower in c.signal_type.lower()
                    or any(query_lower in a.lower() for a in c.approach)
                )
            ]

        # Sort by uses_count (most used first)
        results.sort(key=lambda c: c.uses_count, reverse=True)

        return results[:limit]

    def get_cards_for_signal(
        self, signal_type: str, limit: int = 10
    ) -> List[KnowledgeCard]:
        """Get cards relevant to a signal type."""
        return self.search_cards(signal_type=signal_type, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get card store statistics."""
        category_counts = {}
        status_counts = {}

        for card in self._cards.values():
            cat = card.category.value
            status = card.status.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1

        total_revenue = sum(
            c.revenue_attributed for c in self._cards.values()
        )
        total_uses = sum(c.uses_count for c in self._cards.values())

        return {
            "total_cards": len(self._cards),
            "category_breakdown": category_counts,
            "status_breakdown": status_counts,
            "total_revenue_attributed": total_revenue,
            "total_uses": total_uses,
            "avg_revenue_per_card": (
                total_revenue / len(self._cards)
                if self._cards else 0
            ),
        }
