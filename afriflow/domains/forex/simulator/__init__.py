"""
Forex simulator module.

We generate synthetic FX data including:
- Rate ticks for African currency pairs
- FX trades and hedging instruments
- Order book snapshots
- Liquidity provider quotes
- Volatility spike events

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group or any affiliated entity.
"""

from afriflow.domains.forex.simulator.rate_feed_generator import (
    RateFeedGenerator,
    RateTick,
)
from afriflow.domains.forex.simulator.fx_trade_generator import (
    FXTradeGenerator,
    FXTrade,
)
from afriflow.domains.forex.simulator.hedging_simulator import (
    HedgingSimulator,
    HedgeInstrument,
)

__all__ = [
    "RateFeedGenerator",
    "RateTick",
    "FXTradeGenerator",
    "FXTrade",
    "HedgingSimulator",
    "HedgeInstrument",
]
