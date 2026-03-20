"""
@file circuit_breaker.py
@description Circuit Breaker - Protect pipelines from bad data
@author Thabo Kunene
@created 2026-03-19

This module implements a circuit breaker pattern to protect data
pipelines from processing bad data when quality drops below thresholds.

Key Classes:
- CircuitState: Enumeration of circuit states
- CircuitBreaker: Main circuit breaker engine

Features:
- Three-state circuit breaker (CLOSED, OPEN, HALF_OPEN)
- Automatic state transitions
- Failure counting and threshold-based tripping
- Recovery testing in HALF_OPEN state
- Per-domain circuit breakers

Usage:
    >>> from afriflow.data_quality.circuit_breaker import CircuitBreaker
    >>> breaker = CircuitBreaker()
    >>> if breaker.allow_processing("cib"):
    ...     process_data()
    >>> breaker.record_failure("cib")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from afriflow.logging_config import get_logger

logger = get_logger("data_quality.circuit_breaker")


class CircuitState(Enum):
    """
    Circuit breaker state enumeration.

    Defines the three states of a circuit breaker:
    - CLOSED: Normal operation, processing allowed
    - OPEN: Failure threshold exceeded, processing blocked
    - HALF_OPEN: Testing recovery, limited processing allowed
    """
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Processing blocked
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for data pipeline protection.

    Implements the circuit breaker pattern to prevent
    processing bad data when quality drops below thresholds.

    Attributes:
        _states: Dictionary mapping domain to circuit state
        _failure_counts: Dictionary mapping domain to failure count
        _last_failure: Dictionary mapping domain to last failure time
        _last_state_change: Dictionary mapping domain to state change time

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5)
        >>> if breaker.allow_processing("cib"):
        ...     process_data()
        >>> breaker.record_failure("cib")
    """

    # Default configuration
    DEFAULT_FAILURE_THRESHOLD = 5  # Failures before opening
    DEFAULT_RECOVERY_TIMEOUT_MINUTES = 30  # Minutes before half-open
    DEFAULT_HALF_OPEN_MAX_CALLS = 3  # Test calls in half-open

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_minutes: int = 30,
        half_open_max_calls: int = 3
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout_minutes: Minutes before testing recovery
            half_open_max_calls: Test calls allowed in half-open state
        """
        self._states: Dict[str, CircuitState] = {}
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._last_failure: Dict[str, datetime] = {}
        self._last_state_change: Dict[str, datetime] = {}

        # Configuration
        self.failure_threshold = failure_threshold
        self.recovery_timeout_minutes = recovery_timeout_minutes
        self.half_open_max_calls = half_open_max_calls

        logger.info(
            f"CircuitBreaker initialized: threshold={failure_threshold}, "
            f"recovery={recovery_timeout_minutes}min"
        )

    def allow_processing(self, domain: str) -> bool:
        """
        Check if processing is allowed for a domain.

        Args:
            domain: Domain name

        Returns:
            True if processing allowed, False if blocked

        Example:
            >>> if breaker.allow_processing("cib"):
            ...     process_data()
        """
        state = self._states.get(domain, CircuitState.CLOSED)

        if state == CircuitState.CLOSED:
            return True  # Normal operation

        elif state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            last_failure = self._last_failure.get(domain)
            if last_failure:
                elapsed = datetime.now() - last_failure
                timeout = timedelta(minutes=self.recovery_timeout_minutes)
                if elapsed >= timeout:
                    # Transition to half-open
                    self._transition_state(domain, CircuitState.HALF_OPEN)
                    self._success_counts[domain] = 0
                    logger.info(
                        f"Circuit for {domain} transitioning to HALF_OPEN"
                    )
                    return True
            return False  # Still in timeout

        elif state == CircuitState.HALF_OPEN:
            # Allow limited calls for testing
            success_count = self._success_counts.get(domain, 0)
            return success_count < self.half_open_max_calls

        return False

    def record_success(self, domain: str) -> None:
        """
        Record a successful processing for a domain.

        Args:
            domain: Domain name

        Example:
            >>> breaker.record_success("cib")
        """
        state = self._states.get(domain, CircuitState.CLOSED)

        if state == CircuitState.HALF_OPEN:
            # Increment success count
            self._success_counts[domain] = self._success_counts.get(domain, 0) + 1

            # Check if we've had enough successes to close
            if self._success_counts[domain] >= self.half_open_max_calls:
                self._transition_state(domain, CircuitState.CLOSED)
                self._failure_counts[domain] = 0
                logger.info(f"Circuit for {domain} CLOSED after successful tests")

        elif state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_counts[domain] = 0

    def record_failure(self, domain: str) -> None:
        """
        Record a processing failure for a domain.

        Args:
            domain: Domain name

        Example:
            >>> breaker.record_failure("cib")
        """
        state = self._states.get(domain, CircuitState.CLOSED)
        now = datetime.now()

        if state == CircuitState.HALF_OPEN:
            # Failed during testing, reopen circuit
            self._transition_state(domain, CircuitState.OPEN)
            self._last_failure[domain] = now
            logger.warning(
                f"Circuit for {domain} re-OPENED after failed test"
            )

        elif state == CircuitState.CLOSED:
            # Increment failure count
            self._failure_counts[domain] = self._failure_counts.get(domain, 0) + 1
            self._last_failure[domain] = now

            # Check if threshold exceeded
            if self._failure_counts[domain] >= self.failure_threshold:
                self._transition_state(domain, CircuitState.OPEN)
                logger.warning(
                    f"Circuit for {domain} OPENED after "
                    f"{self._failure_counts[domain]} failures"
                )

    def _transition_state(
        self,
        domain: str,
        new_state: CircuitState
    ) -> None:
        """
        Transition circuit to a new state.

        Args:
            domain: Domain name
            new_state: New circuit state
        """
        old_state = self._states.get(domain, CircuitState.CLOSED)
        self._states[domain] = new_state
        self._last_state_change[domain] = datetime.now()

        logger.info(
            f"Circuit for {domain}: {old_state.value} -> {new_state.value}"
        )

    def get_state(self, domain: str) -> str:
        """
        Get current circuit state for a domain.

        Args:
            domain: Domain name

        Returns:
            State name (CLOSED, OPEN, HALF_OPEN)
        """
        state = self._states.get(domain, CircuitState.CLOSED)
        return state.value

    def get_all_states(self) -> Dict[str, str]:
        """
        Get circuit states for all domains.

        Returns:
            Dictionary mapping domain to state name
        """
        return {
            domain: state.value
            for domain, state in self._states.items()
        }

    def reset(self, domain: Optional[str] = None) -> None:
        """
        Reset circuit breaker(s).

        Args:
            domain: Optional domain to reset (default: all)

        Example:
            >>> breaker.reset("cib")  # Reset specific domain
            >>> breaker.reset()  # Reset all domains
        """
        if domain:
            self._states[domain] = CircuitState.CLOSED
            self._failure_counts[domain] = 0
            self._success_counts[domain] = 0
            logger.info(f"Circuit for {domain} reset")
        else:
            self._states.clear()
            self._failure_counts.clear()
            self._success_counts.clear()
            logger.info("All circuits reset")

    def get_statistics(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        states = self.get_all_states()
        open_count = sum(1 for s in states.values() if s == "OPEN")
        half_open_count = sum(1 for s in states.values() if s == "HALF_OPEN")

        return {
            "total_domains": len(states),
            "closed_count": sum(1 for s in states.values() if s == "CLOSED"),
            "open_count": open_count,
            "half_open_count": half_open_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_minutes": self.recovery_timeout_minutes,
        }


__all__ = [
    "CircuitState",
    "CircuitBreaker",
]
