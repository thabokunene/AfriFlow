"""
Lekgotla Context Matching Engine

Matches incoming signals to relevant threads and Knowledge Cards
based on signal type, client, country, corridor, and tags.

This enables RMs to see relevant discussions when they receive
alerts, providing institutional context for their actions.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging

from afriflow.logging_config import get_logger
from .thread_store import ThreadStore, Thread
from .knowledge_card_store import KnowledgeCardStore, KnowledgeCard

logger = get_logger("lekgotla.context_matching")


@dataclass
class MatchResult:
    """A matched thread or card with relevance score."""
    item_type: str  # 'thread' or 'knowledge_card'
    item_id: str
    item: Any  # Thread or KnowledgeCard
    relevance_score: float
    match_reasons: List[str]


class ContextMatchingEngine:
    """
    Signal-to-content matching engine.

    Matches incoming signals to relevant threads and Knowledge Cards
    using multiple matching strategies:
    - Signal type matching
    - Client matching
    - Country/corridor matching
    - Tag similarity
    """

    def __init__(
        self,
        thread_store: ThreadStore,
        card_store: KnowledgeCardStore,
    ):
        self.thread_store = thread_store
        self.card_store = card_store

        # Weights for different matching factors
        self.weights = {
            "signal_type": 0.40,
            "client": 0.25,
            "country": 0.20,
            "corridor": 0.15,
        }

        logger.info("ContextMatchingEngine initialized")

    def match_signal(
        self,
        signal_id: str,
        signal_type: str,
        client_id: Optional[str] = None,
        client_name: Optional[str] = None,
        country: Optional[str] = None,
        corridor: Optional[str] = None,
        limit: int = 10,
    ) -> List[MatchResult]:
        """
        Find relevant threads and cards for a signal.

        Args:
            signal_id: Signal identifier
            signal_type: Type of signal (e.g., 'EXPANSION')
            client_id: Client this signal is for
            client_name: Client name
            country: Country code
            corridor: Corridor (e.g., 'ZA > GH')
            limit: Maximum results to return

        Returns:
            List of MatchResult objects sorted by relevance
        """
        results: List[MatchResult] = []

        # Match threads
        thread_results = self._match_threads(
            signal_type=signal_type,
            client_id=client_id,
            country=country,
            corridor=corridor,
            limit=limit,
        )
        results.extend(thread_results)

        # Match Knowledge Cards
        card_results = self._match_cards(
            signal_type=signal_type,
            country=country,
            limit=limit // 2,
        )
        results.extend(card_results)

        # Sort by relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        logger.info(
            f"Matched {len(results)} items for signal {signal_id}"
        )

        return results[:limit]

    def _match_threads(
        self,
        signal_type: str,
        client_id: Optional[str],
        country: Optional[str],
        corridor: Optional[str],
        limit: int,
    ) -> List[MatchResult]:
        """Match threads to signal parameters."""
        results: List[MatchResult] = []

        # Search by signal type
        threads = self.thread_store.search_threads(
            signal_type=signal_type.lower() if signal_type else None,
            country=country,
            limit=limit * 2,
        )

        for thread in threads:
            score, reasons = self._calculate_thread_score(
                thread, signal_type, client_id, country, corridor
            )

            if score > 0.3:  # Minimum threshold
                results.append(
                    MatchResult(
                        item_type="thread",
                        item_id=thread.thread_id,
                        item=thread,
                        relevance_score=score,
                        match_reasons=reasons,
                    )
                )

        return results

    def _calculate_thread_score(
        self,
        thread: Thread,
        signal_type: Optional[str],
        client_id: Optional[str],
        country: Optional[str],
        corridor: Optional[str],
    ) -> Tuple[float, List[str]]:
        """Calculate relevance score for a thread."""
        score = 0.0
        reasons = []

        # Signal type match (40%)
        if signal_type and thread.signal_type:
            if signal_type.lower() == thread.signal_type.lower():
                score += self.weights["signal_type"]
                reasons.append(f"Signal type: {signal_type}")

        # Client match (25%)
        if client_id and thread.client_id:
            if client_id == thread.client_id:
                score += self.weights["client"]
                reasons.append(f"Client: {thread.client_name}")

        # Country match (20%)
        if country and thread.country:
            if country == thread.country:
                score += self.weights["country"]
                reasons.append(f"Country: {country}")

        # Corridor match (15%)
        if corridor and thread.corridor:
            if corridor == thread.corridor:
                score += self.weights["corridor"]
                reasons.append(f"Corridor: {corridor}")

        return score, reasons

    def _match_cards(
        self,
        signal_type: str,
        country: Optional[str],
        limit: int,
    ) -> List[MatchResult]:
        """Match Knowledge Cards to signal parameters."""
        results: List[MatchResult] = []

        cards = self.card_store.search_cards(
            signal_type=signal_type,
            country=country,
            limit=limit,
        )

        for card in cards:
            score = 0.0
            reasons = []

            # Signal type match
            if card.signal_type == signal_type:
                score += 0.7
                reasons.append(f"Signal type: {signal_type}")

            # Country match
            if country and country in card.countries:
                score += 0.3
                reasons.append(f"Country: {country}")

            if score > 0.5:
                results.append(
                    MatchResult(
                        item_type="knowledge_card",
                        item_id=card.card_id,
                        item=card,
                        relevance_score=score,
                        match_reasons=reasons,
                    )
                )

        return results

    def get_context_summary(
        self,
        signal_type: str,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a context summary for a signal type.

        Returns aggregated statistics about relevant content.
        """
        threads = self.thread_store.search_threads(
            signal_type=signal_type.lower() if signal_type else None,
            country=country,
            limit=100,
        )

        cards = self.card_store.search_cards(
            signal_type=signal_type,
            country=country,
            limit=50,
        )

        return {
            "signal_type": signal_type,
            "country": country,
            "thread_count": len(threads),
            "card_count": len(cards),
            "total_upvotes": sum(t.upvotes for t in threads),
            "total_replies": sum(t.reply_count for t in threads),
            "avg_card_win_rate": (
                sum(c.win_rate or 0 for c in cards) / len(cards)
                if cards else 0
            ),
            "top_contributors": self._get_top_contributors(
                threads, cards
            ),
        }

    def _get_top_contributors(
        self,
        threads: List[Thread],
        cards: List[KnowledgeCard],
    ) -> List[Dict[str, Any]]:
        """Get top contributors from threads and cards."""
        contributor_stats: Dict[str, Dict[str, Any]] = {}

        for thread in threads:
            author = thread.author_name
            if author not in contributor_stats:
                contributor_stats[author] = {
                    "name": author,
                    "threads": 0,
                    "upvotes": 0,
                }
            contributor_stats[author]["threads"] += 1
            contributor_stats[author]["upvotes"] += thread.upvotes

        for card in cards:
            for contributor in card.contributors:
                if contributor not in contributor_stats:
                    contributor_stats[contributor] = {
                        "name": contributor,
                        "cards": 0,
                    }
                contributor_stats[contributor]["cards"] += 1

        return sorted(
            contributor_stats.values(),
            key=lambda x: x.get("upvotes", 0) + x.get("cards", 0) * 10,
            reverse=True,
        )[:5]
