"""
Lekgotla Context Matching Engine

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from afriflow.logging_config import get_logger
from afriflow.lekgotla.thread_store import Thread, ThreadStore

logger = get_logger("lekgotla.context_matching")


@dataclass
class ContextQuery:
    signal_type: Optional[str] = None
    signal_id: Optional[str] = None
    countries: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    client_golden_id: Optional[str] = None
    corridor: Optional[str] = None
    sector: Optional[str] = None


@dataclass
class ContextMatch:
    item_type: str  # 'thread' or 'card'
    item_id: str
    relevance_score: float  # 0 to 100
    match_reasons: List[str]


class ContextMatchingEngine:
    def __init__(self, thread_store: ThreadStore, card_store: Any) -> None:
        self.thread_store = thread_store
        self.card_store = card_store
        logger.info("ContextMatchingEngine initialized")

    def find_relevant(self, query: ContextQuery, limit: int = 10) -> List[ContextMatch]:
        matches: List[ContextMatch] = []

        # Find relevant threads
        all_threads = self.thread_store.search_threads("", {})
        for thread in all_threads:
            score, reasons = self._score_thread(thread, query)
            if score > 0:
                matches.append(ContextMatch("thread", thread.thread_id, score, reasons))

        # Sort and limit
        matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return matches[:limit]

    def _score_thread(self, thread: Thread, query: ContextQuery) -> tuple[float, List[str]]:
        score = 0.0
        reasons = []

        # Signal match (highest weight)
        if query.signal_id and thread.signal_id == query.signal_id:
            score += 50
            reasons.append("Exact signal match")
        elif query.signal_type and thread.signal_type == query.signal_type:
            score += 30
            reasons.append(f"Signal type match: {query.signal_type}")

        # Country match
        country_overlap = set(query.countries) & set(thread.countries)
        if country_overlap:
            score += 20 * len(country_overlap)
            reasons.append(f"Country match: {', '.join(country_overlap)}")

        # Product match
        product_overlap = set(query.products) & set(thread.products)
        if product_overlap:
            score += 15 * len(product_overlap)
            reasons.append(f"Product match: {', '.join(product_overlap)}")

        # Corridor match
        if query.corridor and thread.signal_id:
             # In a real system, we'd lookup the corridor of the thread's signal
             pass

        # Recency boost
        try:
            created_at = datetime.fromisoformat(thread.created_at)
            days_old = (datetime.now() - created_at).days
            if days_old < 30:
                score += 10
                reasons.append("Recent activity")
        except:
            pass

        # Upvote boost
        if thread.upvote_count > 10:
            score += min(10, thread.upvote_count / 5)
            reasons.append("Highly upvoted")

        # Cap at 100
        return min(100.0, score), reasons

    def _score_card(self, card: Any, query: ContextQuery) -> float:
        # Placeholder for knowledge card scoring
        return 0.0

    def _calculate_relevance(
        self,
        tag_overlap: int,
        country_match: bool,
        signal_match: bool,
        recency_days: int,
        upvotes: int,
        author_credibility: float,
    ) -> float:
        score = (tag_overlap * 5) + (30 if country_match else 0) + (40 if signal_match else 0)
        # Apply decay for recency
        decay = max(0.5, 1 - (recency_days / 365))
        score *= decay
        return min(100.0, score)
