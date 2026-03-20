"""
@file context_matching_engine.py
@description Lekgotla Context Matching Engine - Signal-anchored thread and card matching
@author Thabo Kunene
@created 2026-03-19

This module provides context-aware matching between incoming signals and
existing Lekgotla discussions (threads) and validated approaches (Knowledge Cards).

When a Relationship Manager receives a signal alert (e.g., EXPANSION signal for
a client), this engine finds relevant threads and cards to provide context and
proven approaches.

Key Classes:
- ContextQuery: Query object with signal and client context
- ContextMatch: Matched item with relevance score
- ContextMatchingEngine: Main matching engine with scoring logic

Features:
- Signal type matching (primary signal anchor)
- Country-based matching (geographic relevance)
- Product-based matching (solution relevance)
- Corridor matching (trade route relevance)
- Client-specific matching (historical context)
- Relevance scoring (0-100 scale)
- Multi-factor ranking

Usage:
    >>> from afriflow.lekgotla.context_matching_engine import (
    ...     ContextMatchingEngine, ContextQuery
    ... )
    >>> engine = ContextMatchingEngine(thread_store, card_store)
    >>> query = ContextQuery(
    ...     signal_type="EXPANSION",
    ...     countries=["GH"],
    ...     products=["WC", "FX"]
    ... )
    >>> matches = engine.find_relevant(query, limit=5)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Standard library imports
from dataclasses import dataclass, field  # For data class decorators and default values
from typing import Dict, List, Optional, Any  # Type hints for dictionaries, lists, optional values
import logging  # For debug and info logging
from datetime import datetime  # For timestamp generation

# Import logging utility for structured logging
from afriflow.logging_config import get_logger

# Import Thread and ThreadStore for thread-based matching
from afriflow.lekgotla.thread_store import Thread, ThreadStore

logger = get_logger("lekgotla.context_matching")  # Get logger instance for this module


@dataclass
class ContextQuery:
    """
    Context query for finding relevant threads and cards.

    This dataclass encapsulates all the context needed to find
    relevant discussions and validated approaches for a given
    business situation.

    Attributes:
        signal_type: Type of signal (e.g., "EXPANSION", "HEDGE_GAP")
        signal_id: Specific signal instance ID (for exact matching)
        countries: List of relevant country codes (e.g., ["GH", "NG"])
        products: List of relevant products (e.g., ["WC", "FX", "INS"])
        client_golden_id: Client's golden ID (for client-specific history)
        corridor: Trade corridor (e.g., "ZA > GH" for South Africa to Ghana)
        sector: Industry sector (e.g., "MINING", "AGRICULTURE", "TELECOM")

    Example:
        >>> query = ContextQuery(
        ...     signal_type="EXPANSION",
        ...     countries=["GH"],
        ...     products=["WC", "FX", "INS"],
        ...     corridor="ZA > GH"
        ... )
    """
    signal_type: Optional[str] = None  # Signal type filter (e.g., "EXPANSION")
    signal_id: Optional[str] = None  # Specific signal ID for exact matching
    countries: List[str] = field(default_factory=list)  # Country codes filter
    products: List[str] = field(default_factory=list)  # Product codes filter
    client_golden_id: Optional[str] = None  # Client-specific history
    corridor: Optional[str] = None  # Trade corridor (e.g., "ZA > GH")
    sector: Optional[str] = None  # Industry sector


@dataclass
class ContextMatch:
    """
    Matched thread or card with relevance score.

    Represents a single matched item (thread or Knowledge Card)
    with a calculated relevance score and reasons for the match.

    Attributes:
        item_type: Type of matched item ("thread" or "card")
        item_id: Unique identifier of the matched item
        relevance_score: Score from 0 to 100 indicating relevance
        match_reasons: List of reasons why this item matched

    Example:
        >>> match = ContextMatch(
        ...     item_type="thread",
        ...     item_id="THR-ABC123",
        ...     relevance_score=85.5,
        ...     match_reasons=["Signal type match", "Country match: GH"]
        ... )
    """
    item_type: str  # "thread" or "card"
    item_id: str  # Unique item identifier
    relevance_score: float  # 0 to 100 relevance score
    match_reasons: List[str]  # Reasons for the match


class ContextMatchingEngine:
    """
    Context-aware matching engine for threads and Knowledge Cards.

    This engine matches incoming signals to existing Lekgotla content
    (threads and Knowledge Cards) to provide RMs with relevant context
    and proven approaches when they receive alerts.

    The matching algorithm uses multiple factors:
    1. Signal type match (40% weight) - Primary anchor
    2. Country match (25% weight) - Geographic relevance
    3. Product match (20% weight) - Solution relevance
    4. Corridor match (15% weight) - Trade route relevance

    Attributes:
        thread_store: ThreadStore instance for thread queries
        card_store: KnowledgeCardStore instance for card queries

    Example:
        >>> engine = ContextMatchingEngine(thread_store, card_store)
        >>> query = ContextQuery(
        ...     signal_type="EXPANSION",
        ...     countries=["GH"],
        ...     products=["WC", "FX"]
        ... )
        >>> matches = engine.find_relevant(query, limit=5)
        >>> for match in matches:
        ...     print(f"{match.item_type} {match.item_id}: {match.relevance_score}")
    """

    # Matching weights for scoring algorithm
    # These determine the importance of each factor in relevance calculation
    WEIGHT_SIGNAL_TYPE = 0.40  # 40% weight for signal type match
    WEIGHT_COUNTRY = 0.25  # 25% weight for country match
    WEIGHT_PRODUCT = 0.20  # 20% weight for product match
    WEIGHT_CORRIDOR = 0.15  # 15% weight for corridor match

    def __init__(
        self,
        thread_store: ThreadStore,
        card_store: Any
    ) -> None:
        """
        Initialize the context matching engine.

        Args:
            thread_store: ThreadStore instance for thread queries
            card_store: KnowledgeCardStore instance for card queries
        """
        self.thread_store = thread_store  # Store thread store reference
        self.card_store = card_store  # Store card store reference

        logger.info("ContextMatchingEngine initialized")  # Log initialization

    def find_relevant(
        self,
        query: ContextQuery,
        limit: int = 10
    ) -> List[ContextMatch]:
        """
        Find relevant threads and cards for a context query.

        This is the main entry point for finding relevant content.
        It searches both threads and Knowledge Cards, scores them
        by relevance, and returns the top matches.

        Args:
            query: ContextQuery with signal and client context
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of ContextMatch objects sorted by relevance score

        Example:
            >>> query = ContextQuery(
            ...     signal_type="EXPANSION",
            ...     countries=["GH"],
            ...     products=["WC", "FX"]
            ... )
            >>> matches = engine.find_relevant(query, limit=5)
        """
        matches: List[ContextMatch] = []  # Initialize empty matches list

        # Find relevant threads from thread store
        # Search by signal type and country for best results
        relevant_threads = self.thread_store.search_threads(
            signal_type=query.signal_type,
            country=query.countries[0] if query.countries else None,
            limit=limit * 2  # Get more threads to filter and score
        )

        # Score each thread and add to matches
        for thread in relevant_threads:
            score, reasons = self._score_thread(thread, query)
            if score > 30:  # Minimum threshold for relevance
                matches.append(ContextMatch(
                    item_type="thread",
                    item_id=thread.thread_id,
                    relevance_score=score,
                    match_reasons=reasons
                ))

        # Find relevant Knowledge Cards from card store
        relevant_cards = self.card_store.search_cards(
            signal_type=query.signal_type,
            country=query.countries[0] if query.countries else None,
            limit=limit
        )

        # Score each card and add to matches
        for card in relevant_cards:
            score, reasons = self._score_card(card, query)
            if score > 30:  # Minimum threshold for relevance
                matches.append(ContextMatch(
                    item_type="card",
                    item_id=card.card_id,
                    relevance_score=score,
                    match_reasons=reasons
                ))

        # Sort matches by relevance score (highest first)
        # This ensures most relevant content appears at the top
        matches.sort(key=lambda m: m.relevance_score, reverse=True)

        # Return top matches up to the limit
        return matches[:limit]

    def _score_thread(
        self,
        thread: Thread,
        query: ContextQuery
    ) -> tuple[float, List[str]]:
        """
        Calculate relevance score for a thread.

        This internal method scores a thread based on how well it
        matches the query context. Uses weighted multi-factor scoring.

        Args:
            thread: Thread object to score
            query: ContextQuery with matching criteria

        Returns:
            Tuple of (score, reasons) where score is 0-100 and
            reasons is a list of match reasons for transparency
        """
        score = 0.0  # Initialize score
        reasons = []  # Track match reasons for transparency

        # Factor 1: Signal type match (40% weight)
        # This is the primary anchor - threads should match signal type
        if query.signal_type and thread.signal_type == query.signal_type:
            score += self.WEIGHT_SIGNAL_TYPE * 100
            reasons.append(f"Signal type match: {query.signal_type}")

        # Factor 2: Country match (25% weight)
        # Geographic relevance is critical for practical applicability
        if query.countries:
            matching_countries = set(query.countries) & set(thread.countries)
            if matching_countries:
                country_score = len(matching_countries) / max(len(query.countries), 1)
                score += self.WEIGHT_COUNTRY * 100 * country_score
                reasons.append(f"Country match: {', '.join(matching_countries)}")

        # Factor 3: Product match (20% weight)
        # Product relevance ensures solutions are applicable
        if query.products and hasattr(thread, 'products'):
            matching_products = set(query.products) & set(thread.products)
            if matching_products:
                product_score = len(matching_products) / max(len(query.products), 1)
                score += self.WEIGHT_PRODUCT * 100 * product_score
                reasons.append(f"Product match: {', '.join(matching_products)}")

        # Factor 4: Corridor match (15% weight)
        # Trade corridor matching for cross-border relevance
        if query.corridor and hasattr(thread, 'corridor'):
            if thread.corridor == query.corridor:
                score += self.WEIGHT_CORRIDOR * 100
                reasons.append(f"Corridor match: {query.corridor}")

        return score, reasons

    def _score_card(
        self,
        card: Any,
        query: ContextQuery
    ) -> tuple[float, List[str]]:
        """
        Calculate relevance score for a Knowledge Card.

        Similar to thread scoring but adapted for Knowledge Card
        attributes. Cards typically have higher signal type relevance.

        Args:
            card: KnowledgeCard object to score
            query: ContextQuery with matching criteria

        Returns:
            Tuple of (score, reasons) where score is 0-100 and
            reasons is a list of match reasons
        """
        score = 0.0
        reasons = []

        # Factor 1: Signal type match (40% weight)
        if query.signal_type and card.signal_type == query.signal_type:
            score += self.WEIGHT_SIGNAL_TYPE * 100
            reasons.append(f"Signal type match: {query.signal_type}")

        # Factor 2: Country match (25% weight)
        if query.countries:
            matching_countries = set(query.countries) & set(card.countries)
            if matching_countries:
                country_score = len(matching_countries) / max(len(query.countries), 1)
                score += self.WEIGHT_COUNTRY * 100 * country_score
                reasons.append(f"Country match: {', '.join(matching_countries)}")

        # Factor 3: Product match (20% weight)
        if query.products:
            matching_products = set(query.products) & set(card.products)
            if matching_products:
                product_score = len(matching_products) / max(len(query.products), 1)
                score += self.WEIGHT_PRODUCT * 100 * product_score
                reasons.append(f"Product match: {', '.join(matching_products)}")

        return score, reasons

    def get_context_summary(
        self,
        signal_type: str,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a context summary for a signal type.

        This method provides aggregate statistics about available
        content for a given signal type, useful for UI display
        and analytics.

        Args:
            signal_type: Signal type to summarize (e.g., "EXPANSION")
            country: Optional country filter

        Returns:
            Dictionary with thread count, card count, and top contributors
        """
        # Get relevant threads for the signal type
        threads = self.thread_store.search_threads(
            signal_type=signal_type,
            country=country,
            limit=100
        )

        # Get relevant cards for the signal type
        cards = self.card_store.search_cards(
            signal_type=signal_type,
            country=country,
            limit=50
        )

        # Calculate aggregate statistics
        return {
            "signal_type": signal_type,
            "country": country,
            "thread_count": len(threads),
            "card_count": len(cards),
            "total_upvotes": sum(getattr(t, 'upvote_count', 0) for t in threads),
            "total_replies": sum(getattr(t, 'reply_count', 0) for t in threads),
            "avg_card_win_rate": (
                sum(getattr(c, 'win_rate', 0) or 0 for c in cards) / len(cards)
                if cards else 0
            ),
        }


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.lekgotla.context_matching_engine import *'

__all__ = [
    # Data classes for queries and matches
    "ContextQuery",
    "ContextMatch",
    # Main matching engine class
    "ContextMatchingEngine",
]
