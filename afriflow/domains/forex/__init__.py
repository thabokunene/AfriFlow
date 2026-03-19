"""
@file __init__.py
@description Root package initialization for the Forex (Foreign Exchange) domain, exposing core simulators and rate management components.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Forex (Foreign Exchange) domain.

We process FX trades, rate ticks, and hedging instruments
for African currency pairs. This domain provides:

1. Rate feed generation for African currencies
2. FX trade simulation and tracking
3. Hedging effectiveness analytics
4. Parallel market monitoring (NGN, AOA, ETB)
5. Volatility spike detection

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Core rate feed generator and data structures for synthetic FX rate ticks
from afriflow.domains.forex.simulator.rate_feed_generator import (
    RateFeedGenerator,
    RateTick,
    RateScenario,
)

# Defines the public interface for the forex domain package
__all__ = [
    "RateFeedGenerator", # Engine for generating synthetic currency price feeds
    "RateTick", # Data structure representing a single price point
    "RateScenario", # Enumeration of market conditions (e.g., bull, bear, stable)
]
