"""
Currency Event Propagation Module

We detect and propagate FX events across all five
domains, treating currency volatility as a cross
cutting concern rather than an isolated forex risk.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from afriflow.currency_events.event_classifier import (
    CurrencyEventClassifier,
    CurrencyEvent,
    EventTier,
    EventSeverity,
    EventType,
)
from afriflow.currency_events.propagator import (
    CurrencyEventPropagator,
    DomainImpact,
    PropagationResult,
)

__all__ = [
    "CurrencyEventClassifier",
    "CurrencyEvent",
    "EventTier",
    "EventSeverity",
    "EventType",
    "CurrencyEventPropagator",
    "DomainImpact",
    "PropagationResult",
]
