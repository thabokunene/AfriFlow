"""
@file signal_lifecycle.py
@description Signal Lifecycle Tracking - Signal state transition management
@author Thabo Kunene
@created 2026-03-19

This module tracks the lifecycle state of signals from detection through
RM action to final outcome. It enables monitoring of signal progress and
identifies bottlenecks in the signal-to-revenue pipeline.

Key Classes:
- SignalState: Enumeration of signal states
- SignalLifecycle: State machine for signal lifecycle management

Features:
- State transition tracking
- Time-in-state measurement
- Bottleneck identification
- Lifecycle analytics

Usage:
    >>> from afriflow.outcome_tracking.signal_lifecycle import SignalLifecycle
    >>> lifecycle = SignalLifecycle()
    >>> lifecycle.transition("SIG-001", "ACTIONED")
    >>> lifecycle.get_current_state("SIG-001")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("outcome_tracking.lifecycle")


class SignalState(Enum):
    """
    Signal lifecycle state enumeration.

    Defines the possible states a signal progresses through:
    - DETECTED: Signal detected by platform
    - DELIVERED: Signal delivered to RM
    - ACTIONED: RM took action on signal
    - WON: Opportunity won (revenue booked)
    - LOST: Opportunity lost
    - EXPIRED: Signal expired without action
    """
    DETECTED = "DETECTED"  # Initial state
    DELIVERED = "DELIVERED"  # Delivered to RM
    ACTIONED = "ACTIONED"  # RM took action
    WON = "WON"  # Won (revenue booked)
    LOST = "LOST"  # Lost
    EXPIRED = "EXPIRED"  # Expired without action


class SignalLifecycle:
    """
    Signal lifecycle state machine.

    Tracks state transitions for signals and measures
    time spent in each state for bottleneck analysis.

    Attributes:
        _states: Dictionary mapping signal_id to current state
        _transitions: Dictionary mapping signal_id to transition history
        _state_entered_at: Dictionary mapping signal_id to state entry time

    Example:
        >>> lifecycle = SignalLifecycle()
        >>> lifecycle.transition("SIG-001", "DETECTED")
        >>> lifecycle.transition("SIG-001", "DELIVERED")
        >>> lifecycle.transition("SIG-001", "ACTIONED")
        >>> state = lifecycle.get_current_state("SIG-001")
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        SignalState.DETECTED: [SignalState.DELIVERED, SignalState.EXPIRED],
        SignalState.DELIVERED: [SignalState.ACTIONED, SignalState.EXPIRED],
        SignalState.ACTIONED: [SignalState.WON, SignalState.LOST],
        SignalState.WON: [],  # Terminal state
        SignalState.LOST: [],  # Terminal state
        SignalState.EXPIRED: [],  # Terminal state
    }

    def __init__(self) -> None:
        """Initialize lifecycle tracker with empty state stores."""
        self._states: Dict[str, SignalState] = {}
        self._transitions: Dict[str, List[Dict[str, Any]]] = {}
        self._state_entered_at: Dict[str, str] = {}
        logger.info("SignalLifecycle initialized")

    def transition(
        self,
        signal_id: str,
        new_state: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition a signal to a new state.

        Args:
            signal_id: Signal identifier
            new_state: New state name (DETECTED, DELIVERED, etc.)
            metadata: Optional metadata for the transition

        Returns:
            True if transition successful, False if invalid

        Example:
            >>> lifecycle.transition("SIG-001", "ACTIONED")
        """
        # Convert string to enum
        try:
            new_state_enum = SignalState[new_state]
        except KeyError:
            logger.error(f"Invalid state: {new_state}")
            return False

        # Get current state
        current_state = self._states.get(signal_id)

        # Validate transition
        if current_state:
            valid_next = self.VALID_TRANSITIONS.get(current_state, [])
            if new_state_enum not in valid_next:
                logger.warning(
                    f"Invalid transition: {current_state.value} -> {new_state}"
                )
                return False

        # Record transition
        now = datetime.now().isoformat()
        transition_record = {
            "from_state": current_state.value if current_state else None,
            "to_state": new_state,
            "timestamp": now,
            "metadata": metadata or {},
        }

        # Update state
        self._states[signal_id] = new_state_enum
        self._state_entered_at[signal_id] = now

        # Record transition history
        if signal_id not in self._transitions:
            self._transitions[signal_id] = []
        self._transitions[signal_id].append(transition_record)

        logger.info(
            f"Signal {signal_id} transitioned: "
            f"{current_state.value if current_state else 'NEW'} -> {new_state}"
        )

        return True

    def get_current_state(self, signal_id: str) -> Optional[str]:
        """
        Get current state of a signal.

        Args:
            signal_id: Signal identifier

        Returns:
            Current state name or None if not found
        """
        state = self._states.get(signal_id)
        return state.value if state else None

    def get_transition_history(
        self,
        signal_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get full transition history for a signal.

        Args:
            signal_id: Signal identifier

        Returns:
            List of transition records
        """
        return self._transitions.get(signal_id, [])

    def get_time_in_state(
        self,
        signal_id: str
    ) -> Optional[float]:
        """
        Get time spent in current state (in hours).

        Args:
            signal_id: Signal identifier

        Returns:
            Hours in current state or None if not found
        """
        entered_at = self._state_entered_at.get(signal_id)
        if not entered_at:
            return None

        entered = datetime.fromisoformat(entered_at)
        now = datetime.now()
        delta = now - entered
        return delta.total_seconds() / 3600

    def get_signals_in_state(
        self,
        state: str
    ) -> List[str]:
        """
        Get all signals in a specific state.

        Args:
            state: State name to filter by

        Returns:
            List of signal IDs in that state
        """
        try:
            target_state = SignalState[state]
        except KeyError:
            return []

        return [
            sid for sid, state in self._states.items()
            if state == target_state
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get lifecycle statistics."""
        state_counts = {}
        for state in self._states.values():
            state_name = state.value
            state_counts[state_name] = state_counts.get(state_name, 0) + 1

        return {
            "total_signals": len(self._states),
            "state_distribution": state_counts,
            "detected": state_counts.get("DETECTED", 0),
            "delivered": state_counts.get("DELIVERED", 0),
            "actioned": state_counts.get("ACTIONED", 0),
            "won": state_counts.get("WON", 0),
            "lost": state_counts.get("LOST", 0),
            "expired": state_counts.get("EXPIRED", 0),
        }


__all__ = [
    "SignalState",
    "SignalLifecycle",
]
