"""
@file __init__.py
@description Initialization for the Forex domain simulator module, providing synthetic FX market data and trade generators.
@author Thabo Kunene
@created 2026-03-19
"""

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

# Core rate feed generator and data structures for price simulation
from afriflow.domains.forex.simulator.rate_feed_generator import (
    RateFeedGenerator,
    RateTick,
)
# Generator for synthetic FX trades between clients and the bank
from afriflow.domains.forex.simulator.fx_trade_generator import (
    FXTradeGenerator,
    FXTrade,
)
# Simulator for various hedging instruments (forwards, options, swaps)
from afriflow.domains.forex.simulator.hedging_simulator import (
    HedgingSimulator,
    HedgeInstrument,
)

# Defines the public interface for the forex simulator package
__all__ = [
    "RateFeedGenerator", # Synthetic price feed engine
    "RateTick", # Individual price point container
    "FXTradeGenerator", # Synthetic trade execution engine
    "FXTrade", # Trade record container
    "HedgingSimulator", # Risk mitigation instrument simulator
    "HedgeInstrument", # Hedging record container
]
