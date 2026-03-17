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

from afriflow.domains.forex.simulator.rate_feed_generator import (
    RateFeedGenerator,
    RateTick,
    RateScenario,
)

__all__ = [
    "RateFeedGenerator",
    "RateTick",
    "RateScenario",
]
