"""
@file __init__.py
@description Currency Event Propagation Module. Detects and propagates FX
             events across all five domains, treating currency volatility as a
             cross-cutting concern rather than an isolated forex risk. Provides
             event classification and impact propagation logic.
@author Thabo Kunene
@created 2026-03-19
"""

# ---------------------------------------------------------------------------
# Currency Event Propagation Module
#
# We detect and propagate FX events across all five
# domains, treating currency volatility as a cross
# cutting concern rather than an isolated forex risk.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.
# ---------------------------------------------------------------------------

# --- Internal imports: pull public symbols up for consumer convenience ---
# Classification logic for identifying the type and severity of FX events
from afriflow.currency_events.event_classifier import (
    CurrencyEventClassifier,
    CurrencyEvent,
    EventTier,
    EventSeverity,
    EventType,
)
# Propagation logic for calculating the impact of FX events across domains
from afriflow.currency_events.propagator import (
    CurrencyEventPropagator,
    DomainImpact,
    PropagationResult,
)

# Public API surface — controls what 'from afriflow.currency_events import *' exposes
__all__ = [
    # Classification
    "CurrencyEventClassifier",
    "CurrencyEvent",
    "EventTier",
    "EventSeverity",
    "EventType",
    # Propagation
    "CurrencyEventPropagator",
    "DomainImpact",
    "PropagationResult",
]
