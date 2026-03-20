"""
Lekgotla Knowledge Card Store

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import logging
import uuid

from afriflow.logging_config import get_logger
from afriflow.lekgotla.thread_store import Thread

logger = get_logger("lekgotla.card_store")


class CardCategory(Enum):
    PROVEN = "PROVEN"
    EXPERIMENTAL = "EXPERIMENTAL"
    REGULATORY = "REGULATORY"
    ONBOARDING = "ONBOARDING"
    PRODUCT = "PRODUCT"


@dataclass
class KnowledgeCard:
    card_id: str
    title: str
    subtitle: str
    category: CardCategory
    signal_type: str
    countries: List[str]
    products: List[str]
    approach_steps: List[str]
    avoid_items: List[str]
    documents: List[Dict]  # {name, type, url}
    source_thread_ids: List[str]
    contributor_ids: List[str]
    win_rate: float
    uses_count: int
    revenue_attributed: float
    rating: float
    created_at: str
    last_updated: str
    last_validated: str


class KnowledgeCardStore:
    def __init__(self) -> None:
        self._cards: Dict[str, KnowledgeCard] = {}
        logger.info("KnowledgeCardStore initialized")

    def create_card(self, card: KnowledgeCard) -> KnowledgeCard:
        if not card.card_id:
            card.card_id = f"KCD-{uuid.uuid4().hex[:8].upper()}"
        self._cards[card.card_id] = card
        return card

    def graduate_from_thread(self, thread: Thread) -> KnowledgeCard:
        """
        Graduates a discussion thread into a Knowledge Card
        if it has a best answer and verified win.
        """
        best_answer = next((p for p in thread.posts if p.is_best_answer), None)
        if not best_answer:
            raise ValueError("Thread must have a best answer to graduate")

        card = KnowledgeCard(
            card_id=f"KCD-{thread.thread_id}",
            title=thread.title,
            subtitle=f"Wisdom from {thread.author_name}",
            category=CardCategory.PROVEN,
            signal_type=thread.signal_type or "GENERAL",
            countries=thread.countries,
            products=thread.products,
            approach_steps=[best_answer.content[:200]],  # Truncated summary
            avoid_items=[],
            documents=[],
            source_thread_ids=[thread.thread_id],
            contributor_ids=[thread.author_id, best_answer.author_id],
            win_rate=1.0 if any(p.is_verified_win for p in thread.posts) else 0.0,
            uses_count=1,
            revenue_attributed=0.0,
            rating=5.0,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            last_validated=datetime.now().isoformat(),
        )
        self._cards[card.card_id] = card
        logger.info(f"Thread {thread.thread_id} graduated to Knowledge Card {card.card_id}")
        return card

    def record_usage(self, card_id: str, user_id: str) -> None:
        if card_id in self._cards:
            self._cards[card_id].uses_count += 1

    def record_outcome(self, card_id: str, won: bool, revenue: float) -> None:
        if card_id in self._cards:
            card = self._cards[card_id]
            card.revenue_attributed += revenue
            self.update_win_rate(card_id)

    def update_win_rate(self, card_id: str) -> float:
        # Placeholder for complex win-rate calculation
        return 0.0

    def search_cards(self, query: str, filters: Dict) -> List[KnowledgeCard]:
        return list(self._cards.values())

    def get_cards_by_signal(self, signal_type: str) -> List[KnowledgeCard]:
        return [c for c in self._cards.values() if c.signal_type == signal_type]

    def get_cards_by_country(self, country: str) -> List[KnowledgeCard]:
        return [c for c in self._cards.values() if country in c.countries]

    def get_top_cards(self, limit: int, sort_by: str) -> List[KnowledgeCard]:
        return list(self._cards.values())[:limit]

    def validate_card(self, card_id: str, validator_id: str) -> None:
        if card_id in self._cards:
            self._cards[card_id].last_validated = datetime.now().isoformat()
