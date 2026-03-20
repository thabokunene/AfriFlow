"""
@file outcome_recorder.py
@description Outcome Recorder - Record RM actions and signal outcomes
@author Thabo Kunene
@created 2026-03-19

This module records the outcomes of signals from detection through RM action
to revenue booking. It tracks whether RMs acted on signals and whether those
actions resulted in won business.

Key Classes:
- OutcomeRecord: Data model for a signal outcome
- OutcomeRecorder: Main engine for outcome recording and retrieval

Features:
- Outcome recording (acted/not acted, won/lost)
- Revenue attribution to signals
- Win rate calculation per signal type
- RM performance tracking
- Time-to-action measurement

Usage:
    >>> from afriflow.outcome_tracking.outcome_recorder import OutcomeRecorder
    >>> recorder = OutcomeRecorder()
    >>> recorder.record_outcome(
    ...     signal_id="SIG-001",
    ...     rm_id="user-123",
    ...     rm_actioned=True,
    ...     revenue_booked=50000.0,
    ...     won=True
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("outcome_tracking.recorder")


@dataclass
class OutcomeRecord:
    """
    Outcome record for a signal.

    Tracks the full lifecycle of a signal from detection
    through RM action to revenue booking.

    Attributes:
        outcome_id: Unique identifier
        signal_id: Original signal identifier
        signal_type: Type of signal (e.g., EXPANSION, HEDGE_GAP)
        rm_id: RM user ID
        rm_actioned: Whether RM took action
        action_date: Date of RM action (if acted)
        revenue_booked: Revenue booked (if won)
        won: Whether opportunity was won
        lost_reason: Reason if lost (optional)
        client_feedback: Client feedback (optional)
        created_at: Record creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> outcome = OutcomeRecord(
        ...     outcome_id="OUT-001",
        ...     signal_id="SIG-001",
        ...     signal_type="EXPANSION",
        ...     rm_id="user-123",
        ...     rm_actioned=True,
        ...     won=True,
        ...     revenue_booked=50000.0
        ... )
    """
    outcome_id: str  # Unique outcome identifier
    signal_id: str  # Original signal ID
    signal_type: str  # Signal type
    rm_id: str  # RM user ID
    rm_actioned: bool = False  # Whether RM acted
    action_date: Optional[str] = None  # Action date
    revenue_booked: float = 0.0  # Revenue booked
    won: bool = False  # Won/lost status
    lost_reason: Optional[str] = None  # Lost reason
    client_feedback: Optional[str] = None  # Client feedback
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "outcome_id": self.outcome_id,
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "rm_id": self.rm_id,
            "rm_actioned": self.rm_actioned,
            "action_date": self.action_date,
            "revenue_booked": self.revenue_booked,
            "won": self.won,
            "lost_reason": self.lost_reason,
            "client_feedback": self.client_feedback,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class OutcomeRecorder:
    """
    Outcome recording and retrieval engine.

    Records signal outcomes and provides analytics on
    signal effectiveness and RM performance.

    Attributes:
        _outcomes: Dictionary mapping outcome_id to OutcomeRecord
        _signal_outcomes: Dictionary mapping signal_id to outcome_id

    Example:
        >>> recorder = OutcomeRecorder()
        >>> recorder.record_outcome(
        ...     signal_id="SIG-001",
        ...     rm_id="user-123",
        ...     rm_actioned=True,
        ...     won=True,
        ...     revenue_booked=50000.0
        ... )
    """

    def __init__(self) -> None:
        """Initialize outcome recorder with empty stores."""
        self._outcomes: Dict[str, OutcomeRecord] = {}
        self._signal_outcomes: Dict[str, str] = {}
        logger.info("OutcomeRecorder initialized")

    def record_outcome(
        self,
        signal_id: str,
        signal_type: str,
        rm_id: str,
        rm_actioned: bool = False,
        revenue_booked: float = 0.0,
        won: bool = False,
        lost_reason: Optional[str] = None,
        client_feedback: Optional[str] = None,
    ) -> OutcomeRecord:
        """
        Record outcome for a signal.

        Args:
            signal_id: Original signal identifier
            signal_type: Type of signal (EXPANSION, HEDGE_GAP, etc.)
            rm_id: RM user ID
            rm_actioned: Whether RM took action
            revenue_booked: Revenue booked (if won)
            won: Whether opportunity was won
            lost_reason: Reason if lost (optional)
            client_feedback: Client feedback (optional)

        Returns:
            Created OutcomeRecord object

        Example:
            >>> outcome = recorder.record_outcome(
            ...     signal_id="SIG-001",
            ...     signal_type="EXPANSION",
            ...     rm_id="user-123",
            ...     rm_actioned=True,
            ...     won=True,
            ...     revenue_booked=50000.0
            ... )
        """
        # Generate unique outcome ID
        outcome_id = f"OUT-{datetime.now().strftime('%Y%m%d')}-{signal_id}"
        now = datetime.now().isoformat()

        # Determine action date if RM acted
        action_date = now if rm_actioned else None

        # Create outcome record
        outcome = OutcomeRecord(
            outcome_id=outcome_id,
            signal_id=signal_id,
            signal_type=signal_type,
            rm_id=rm_id,
            rm_actioned=rm_actioned,
            action_date=action_date,
            revenue_booked=revenue_booked,
            won=won,
            lost_reason=lost_reason,
            client_feedback=client_feedback,
            created_at=now,
            updated_at=now,
        )

        # Store outcome
        self._outcomes[outcome_id] = outcome
        self._signal_outcomes[signal_id] = outcome_id

        logger.info(
            f"Outcome recorded for {signal_id}: "
            f"actioned={rm_actioned}, won={won}, revenue={revenue_booked}"
        )

        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[OutcomeRecord]:
        """Get outcome by ID."""
        return self._outcomes.get(outcome_id)

    def get_outcome_for_signal(
        self,
        signal_id: str
    ) -> Optional[OutcomeRecord]:
        """Get outcome for a specific signal."""
        outcome_id = self._signal_outcomes.get(signal_id)
        if outcome_id:
            return self._outcomes.get(outcome_id)
        return None

    def get_outcomes_by_rm(
        self,
        rm_id: str
    ) -> List[OutcomeRecord]:
        """Get all outcomes for a specific RM."""
        return [
            o for o in self._outcomes.values()
            if o.rm_id == rm_id
        ]

    def get_outcomes_by_signal_type(
        self,
        signal_type: str
    ) -> List[OutcomeRecord]:
        """Get all outcomes for a specific signal type."""
        return [
            o for o in self._outcomes.values()
            if o.signal_type == signal_type
        ]

    def get_win_rate(
        self,
        signal_type: Optional[str] = None,
        rm_id: Optional[str] = None
    ) -> float:
        """
        Calculate win rate for signals.

        Args:
            signal_type: Filter by signal type (optional)
            rm_id: Filter by RM (optional)

        Returns:
            Win rate as percentage (0-100)
        """
        outcomes = list(self._outcomes.values())

        # Apply filters
        if signal_type:
            outcomes = [o for o in outcomes if o.signal_type == signal_type]
        if rm_id:
            outcomes = [o for o in outcomes if o.rm_id == rm_id]

        # Calculate win rate
        if not outcomes:
            return 0.0

        won_count = sum(1 for o in outcomes if o.won)
        return (won_count / len(outcomes)) * 100

    def get_action_rate(
        self,
        signal_type: Optional[str] = None
    ) -> float:
        """
        Calculate RM action rate for signals.

        Args:
            signal_type: Filter by signal type (optional)

        Returns:
            Action rate as percentage (0-100)
        """
        outcomes = list(self._outcomes.values())

        if signal_type:
            outcomes = [o for o in outcomes if o.signal_type == signal_type]

        if not outcomes:
            return 0.0

        actioned_count = sum(1 for o in outcomes if o.rm_actioned)
        return (actioned_count / len(outcomes)) * 100

    def get_revenue_attribution(
        self,
        signal_type: Optional[str] = None
    ) -> float:
        """
        Get total revenue attributed to signals.

        Args:
            signal_type: Filter by signal type (optional)

        Returns:
            Total revenue in ZAR
        """
        outcomes = list(self._outcomes.values())

        if signal_type:
            outcomes = [o for o in outcomes if o.signal_type == signal_type]

        return sum(o.revenue_booked for o in outcomes if o.won)

    def get_statistics(self) -> Dict[str, Any]:
        """Get outcome tracking statistics."""
        outcomes = list(self._outcomes.values())

        if not outcomes:
            return {
                "total_outcomes": 0,
                "action_rate": 0.0,
                "win_rate": 0.0,
                "total_revenue": 0.0,
            }

        total_revenue = sum(o.revenue_booked for o in outcomes if o.won)
        actioned = sum(1 for o in outcomes if o.rm_actioned)
        won = sum(1 for o in outcomes if o.won)

        return {
            "total_outcomes": len(outcomes),
            "action_rate": (actioned / len(outcomes)) * 100,
            "win_rate": (won / len(outcomes)) * 100,
            "total_revenue": total_revenue,
            "avg_revenue_per_win": (
                total_revenue / won if won > 0 else 0.0
            ),
        }


__all__ = [
    "OutcomeRecord",
    "OutcomeRecorder",
]
