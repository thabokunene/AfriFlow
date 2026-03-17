"""
Governance - Circuit Breaker

We implement the circuit breaker pattern for domain
data feeds. When a feed becomes unhealthy (stale data,
quality degradation, source failures), we trip the
circuit breaker to prevent corrupt data from polluting
downstream consumers.

The circuit breaker has three states:
1. CLOSED: Normal operation, data flows freely
2. OPEN: Circuit tripped, serve last-known-good data
3. HALF_OPEN: Testing if source has recovered

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import logging
import time

from afriflow.exceptions import DataQualityError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    """
    Configuration for a circuit breaker.

    Attributes:
        failure_threshold: Failures before opening circuit
        success_threshold: Successes before closing circuit
        timeout_seconds: Time before attempting recovery
        half_open_max_calls: Max calls in half-open state
    """
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 300.0
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerState:
    """
    Current state of a circuit breaker.

    Attributes:
        state: Current circuit state
        failure_count: Consecutive failures
        success_count: Consecutive successes
        last_failure_time: Time of last failure
        last_state_change: Time of last state change
        half_open_calls: Calls made in half-open state
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    half_open_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker for domain data feeds.

    We use this pattern to gracefully degrade when
    upstream data sources become unhealthy, serving
    last-known-good data instead of propagating errors.

    Attributes:
        name: Circuit breaker name
        config: Circuit breaker configuration
        state: Current circuit state
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit
            config: Optional configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState()

        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s"
        )

    def call(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            DataQualityError: If circuit is open
        """
        log_operation(
            logger,
            "circuit_breaker_call",
            "started",
            name=self.name,
            state=self.state.state.value,
        )

        if not self._allow_request():
            logger.warning(
                f"Circuit breaker '{self.name}' is OPEN, "
                f"rejecting request"
            )
            raise DataQualityError(
                f"Circuit breaker '{self.name}' is open",
                details={
                    "circuit_name": self.name,
                    "state": self.state.state.value,
                    "last_failure": (
                        self.state.last_failure_time.isoformat()
                        if self.state.last_failure_time
                        else None
                    )
                }
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            log_operation(
                logger,
                "circuit_breaker_call",
                "completed",
                name=self.name,
                state=self.state.state.value,
            )
            return result

        except Exception as e:
            self._on_failure()
            log_operation(
                logger,
                "circuit_breaker_call",
                "failed",
                name=self.name,
                state=self.state.state.value,
                error=str(e),
            )
            raise

    def _allow_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request is allowed
        """
        if self.state.state == CircuitState.CLOSED:
            return True

        if self.state.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.state.last_failure_time:
                elapsed = (
                    datetime.utcnow() - self.state.last_failure_time
                ).total_seconds()

                if elapsed >= self.config.timeout_seconds:
                    logger.info(
                        f"Circuit breaker '{self.name}' timeout elapsed, "
                        f"transitioning to HALF_OPEN"
                    )
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True

            return False

        if self.state.state == CircuitState.HALF_OPEN:
            # Allow limited requests to test recovery
            if self.state.half_open_calls < self.config.half_open_max_calls:
                self.state.half_open_calls += 1
                return True
            return False

        return False

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state.state == CircuitState.HALF_OPEN:
            self.state.success_count += 1

            if self.state.success_count >= self.config.success_threshold:
                logger.info(
                    f"Circuit breaker '{self.name}' recovered, "
                    f"transitioning to CLOSED"
                )
                self._transition_to(CircuitState.CLOSED)
        else:
            self.state.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()

        if self.state.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"Circuit breaker '{self.name}' failed in HALF_OPEN, "
                f"transitioning to OPEN"
            )
            self._transition_to(CircuitState.OPEN)
        elif self.state.failure_count >= self.config.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' failure threshold reached, "
                f"transitioning to OPEN"
            )
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: New circuit state
        """
        old_state = self.state.state
        self.state.state = new_state
        self.state.last_state_change = datetime.utcnow()

        if new_state == CircuitState.CLOSED:
            self.state.failure_count = 0
            self.state.success_count = 0
            self.state.half_open_calls = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.state.success_count = 0
            self.state.half_open_calls = 0

        logger.info(
            f"Circuit breaker '{self.name}': "
            f"{old_state.value} -> {new_state.value}"
        )

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            State dictionary
        """
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "last_failure_time": (
                self.state.last_failure_time.isoformat()
                if self.state.last_failure_time
                else None
            ),
            "last_state_change": self.state.last_state_change.isoformat(),
            "half_open_calls": self.state.half_open_calls,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitBreakerState()
        logger.info(f"Circuit breaker '{self.name}' reset")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Attributes:
        breakers: Dictionary of circuit breakers by name
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self.breakers: Dict[str, CircuitBreaker] = {}
        logger.info("CircuitBreakerRegistry initialized")

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Optional configuration

        Returns:
            Circuit breaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        return self.breakers[name]

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get state of all circuit breakers.

        Returns:
            Dictionary of states by name
        """
        return {
            name: breaker.get_state()
            for name, breaker in self.breakers.items()
        }

    def get_open_circuits(self) -> List[str]:
        """
        Get names of all open circuits.

        Returns:
            List of open circuit names
        """
        return [
            name for name, breaker in self.breakers.items()
            if breaker.state.state == CircuitState.OPEN
        ]

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Get a circuit breaker from the global registry.

    Args:
        name: Circuit breaker name
        config: Optional configuration

    Returns:
        Circuit breaker instance
    """
    return _registry.get_or_create(name, config)


def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """
    Get state of all circuit breakers.

    Returns:
        Dictionary of states
    """
    return _registry.get_all_states()


if __name__ == "__main__":
    # Demo usage
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=10,
    )

    breaker = CircuitBreaker("test_feed", config)

    def test_function():
        return "success"

    # Normal operation
    for i in range(3):
        result = breaker.call(test_function)
        print(f"Call {i+1}: {result}")
        print(f"State: {breaker.get_state()['state']}")
