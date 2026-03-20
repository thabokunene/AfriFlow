"""
@file feedback_loop.py
@description Feedback Loop - Update models based on outcomes
@author Thabo Kunene
@created 2026-03-19

This module provides feedback from outcomes back to Knowledge Cards and
ML models to improve signal detection and recommendations over time.

Key Classes:
- FeedbackLoop: Main engine for outcome-based model updates

Features:
- Knowledge Card win rate updates
- Signal confidence adjustment
- Model retraining triggers
- Performance feedback to RMs

Usage:
    >>> from afriflow.outcome_tracking.feedback_loop import FeedbackLoop
    >>> loop = FeedbackLoop(card_store, ml_models)
    >>> loop.process_outcome("SIG-001", won=True, revenue=50000.0)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("outcome_tracking.feedback")


class FeedbackLoop:
    """
    Outcome-based feedback engine.

    Processes outcomes to update Knowledge Cards, adjust
    signal confidence, and trigger model retraining.

    Attributes:
        card_store: KnowledgeCardStore instance (optional)
        ml_models: ML model interface (optional)
        _feedback_log: List of processed feedback records

    Example:
        >>> loop = FeedbackLoop(card_store, ml_models)
        >>> loop.process_outcome(
        ...     signal_id="SIG-001",
        ...     signal_type="EXPANSION",
        ...     won=True,
        ...     revenue=50000.0,
        ...     card_id="KC-001"
        ... )
    """

    def __init__(
        self,
        card_store: Optional[Any] = None,
        ml_models: Optional[Any] = None
    ) -> None:
        """
        Initialize feedback loop.

        Args:
            card_store: KnowledgeCardStore instance (optional)
            ml_models: ML model interface (optional)
        """
        self.card_store = card_store
        self.ml_models = ml_models
        self._feedback_log: List[Dict[str, Any]] = []
        logger.info("FeedbackLoop initialized")

    def process_outcome(
        self,
        signal_id: str,
        signal_type: str,
        won: bool,
        revenue: float = 0.0,
        card_id: Optional[str] = None,
        rm_id: Optional[str] = None
    ) -> None:
        """
        Process an outcome and update models.

        Args:
            signal_id: Signal identifier
            signal_type: Signal type
            won: Whether opportunity was won
            revenue: Revenue booked
            card_id: Associated Knowledge Card ID (optional)
            rm_id: RM user ID (optional)

        Example:
            >>> loop.process_outcome(
            ...     signal_id="SIG-001",
            ...     signal_type="EXPANSION",
            ...     won=True,
            ...     revenue=50000.0,
            ...     card_id="KC-001"
            ... )
        """
        now = datetime.now().isoformat()

        # Log feedback
        feedback_record = {
            "signal_id": signal_id,
            "signal_type": signal_type,
            "won": won,
            "revenue": revenue,
            "card_id": card_id,
            "rm_id": rm_id,
            "processed_at": now,
        }
        self._feedback_log.append(feedback_record)

        # Update Knowledge Card if associated
        if card_id and self.card_store:
            self._update_card(card_id, won, revenue)

        # Update ML models
        if self.ml_models:
            self._update_ml_models(signal_type, won, revenue)

        logger.info(
            f"Feedback processed: {signal_id} - won={won}, revenue={revenue}"
        )

    def _update_card(
        self,
        card_id: str,
        won: bool,
        revenue: float
    ) -> None:
        """
        Update Knowledge Card based on outcome.

        Args:
            card_id: Knowledge Card ID
            won: Whether opportunity was won
            revenue: Revenue booked
        """
        if not self.card_store:
            return

        # Record usage
        self.card_store.record_usage(
            card_id=card_id,
            user_id="system",
            revenue=revenue,
            won=won
        )

        logger.debug(f"Updated card {card_id}: won={won}, revenue={revenue}")

    def _update_ml_models(
        self,
        signal_type: str,
        won: bool,
        revenue: float
    ) -> None:
        """
        Update ML models based on outcome.

        Args:
            signal_type: Signal type
            won: Whether opportunity was won
            revenue: Revenue booked
        """
        if not self.ml_models:
            return

        # Record label for model training
        label = 1 if won else 0
        self.ml_models.record_label(
            signal_type=signal_type,
            label=label,
            value=revenue
        )

        logger.debug(
            f"Updated ML models: {signal_type} - label={label}"
        )

    def get_feedback_log(
        self,
        signal_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get feedback log with optional filtering.

        Args:
            signal_type: Filter by signal type (optional)
            limit: Maximum records to return

        Returns:
            List of feedback records
        """
        log = self._feedback_log

        if signal_type:
            log = [r for r in log if r.get("signal_type") == signal_type]

        return log[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get feedback loop statistics."""
        if not self._feedback_log:
            return {
                "total_feedback": 0,
                "win_rate": 0.0,
                "total_revenue": 0.0,
            }

        total = len(self._feedback_log)
        won = sum(1 for r in self._feedback_log if r.get("won"))
        revenue = sum(r.get("revenue", 0.0) for r in self._feedback_log)

        return {
            "total_feedback": total,
            "win_rate": (won / total) * 100 if total > 0 else 0.0,
            "total_revenue": revenue,
            "avg_revenue_per_win": (
                revenue / won if won > 0 else 0.0
            ),
        }


__all__ = [
    "FeedbackLoop",
]
