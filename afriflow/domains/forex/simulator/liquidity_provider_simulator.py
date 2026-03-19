"""
@file liquidity_provider_simulator.py
@description Generator for synthetic FX liquidity provider quotes, simulating various LP types and their market-making behavior.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Liquidity Provider Simulator

We generate realistic synthetic liquidity provider quotes
for African FX currency pairs.

Liquidity providers (LPs) are banks and financial institutions
that provide two-way FX prices:

1. Tier 1 LPs: Global banks (JPM, Barclays, Citi) — tightest
   spreads, deepest liquidity, but minimum ticket sizes.
2. Regional LPs: African banks (Standard Bank, FirstRand) —
   better local currency liquidity, understand local flows.
3. Electronic LPs: Algorithmic market makers — continuous
   pricing, but may widen spreads during volatility.

Quote aggregation across multiple LPs gives the best
executable price for client orders.

Disclaimer: This is not a sanctioned Standard Bank
Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# Random library for stochastic price and spread generation
import random
# Standard logging for operational telemetry and audit trails
import logging
# Dataclasses for structured representation of liquidity quotes
from dataclasses import dataclass
# Datetime utilities for timestamping generated quotes
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, List, Optional, Dict

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the liquidity provider simulator namespace
logger = get_logger("domains.forex.simulator.liquidity_provider_simulator")


@dataclass
class LiquidityQuote:
    """
    A single liquidity provider quote record.
    Represents an executable or firm price provided by an LP.

    Attributes:
        quote_id: Unique identifier for the quote.
        provider: Identifier of the liquidity provider (e.g., 'LP-A').
        currency_pair: The currency pair being quoted (e.g., 'USD/ZAR').
        bid: The price at which the LP is willing to buy.
        ask: The price at which the LP is willing to sell.
        bid_size_musd: Liquidity available on the bid side in millions of USD.
        ask_size_musd: Liquidity available on the ask side in millions of USD.
        timestamp: The precise ISO timestamp when the quote was issued.
        depth_musd: Total depth of the order book for this LP in millions of USD.
        is_firm: Boolean flag indicating if the price is guaranteed for execution.
    """

    quote_id: str
    provider: str
    currency_pair: str
    bid: float
    ask: float
    bid_size_musd: float
    ask_size_musd: float
    timestamp: datetime
    depth_musd: float
    is_firm: bool = True


class LiquidityProviderSimulator(SimulatorBase):
    """
    Generator for realistic synthetic LP quotes.
    Useful for testing best execution algorithms and market depth analytics.

    Usage:
        gen = LiquidityProviderSimulator()
        quote = gen.generate_one(currency_pair="USD/ZAR")
    """

    # Profiles defining the behavior of different types of liquidity providers.
    # spread_factor: multipliers for the base spread (lower is tighter).
    # depth_factor: multipliers for the base liquidity depth (higher is deeper).
    PROVIDERS = {
        "LP-A": {"type": "tier_1_global", "spread_factor": 0.8, "depth_factor": 2.0},
        "LP-B": {"type": "tier_1_global", "spread_factor": 0.9, "depth_factor": 1.8},
        "LP-C": {"type": "regional_africa", "spread_factor": 1.2, "depth_factor": 1.0},
        "LP-D": {"type": "regional_africa", "spread_factor": 1.3, "depth_factor": 0.9},
        "LP-E": {"type": "electronic_mm", "spread_factor": 0.7, "depth_factor": 1.5},
    }

    # Base mid prices for major and African currency pairs used as a simulation anchor.
    BASE_PRICES = {
        "USD/ZAR": 18.50, "USD/NGN": 1580.0, "USD/KES": 130.0,
        "USD/GHS": 15.5, "EUR/ZAR": 20.0, "GBP/ZAR": 23.5,
        "EUR/USD": 1.08, "GBP/USD": 1.27,
    }

    def __init__(self, seed: Optional[int] = None, config=None):
        """
        Initializes the liquidity provider simulator.

        :param seed: Optional random seed for deterministic generation.
        :param config: Optional AppConfig override.
        """
        if seed is not None:
            random.seed(seed)
        self._quote_count = 0
        logger.info("LiquidityProviderSimulator initialized")
        super().__init__(config)

    def initialize(self, config=None) -> None:
        """
        Sets up the internal state including active pairs and providers.
        
        :param config: Optional configuration object.
        """
        self._pairs = list(self.BASE_PRICES.keys())
        self._providers = list(self.PROVIDERS.keys())
        logger.info("LiquidityProviderSimulator configuration loaded")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before quote generation.
        
        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the currency pair or provider is unknown.
        """
        # Ensure the currency pair is in our registry.
        pair = kwargs.get("currency_pair")
        if pair is not None and pair not in self._pairs:
            raise ValueError(f"Unknown currency_pair: {pair}")

        # Ensure the provider is in our registry.
        provider = kwargs.get("provider")
        if provider is not None and provider not in self._providers:
            raise ValueError(f"Unknown provider: {provider}")
        Validate input parameters.

        Raises:
            ValueError: If currency_pair or provider is invalid
        """
        pair = kwargs.get("currency_pair")
        if pair is not None and pair not in self._pairs:
            raise ValueError(f"Unsupported currency_pair: {pair}")

        provider = kwargs.get("provider")
        if provider is not None and provider not in self._providers:
            raise ValueError(f"Unknown provider: {provider}")

    def _get_mid_price(self, currency_pair: str) -> float:
        """Get base mid price with small random variation."""
        base = self.BASE_PRICES.get(currency_pair, 1.0)
        # Add random walk component (±0.05%)
        variation = random.uniform(-0.0005, 0.0005)
        return round(base * (1 + variation), 4)

    def _get_spread(
        self,
        currency_pair: str,
        provider: str,
    ) -> float:
        """Calculate bid-ask spread based on pair and provider."""
        base_spreads = {
            "USD/ZAR": 0.0025, "USD/NGN": 0.005, "USD/KES": 0.003,
            "USD/GHS": 0.006, "EUR/ZAR": 0.003, "GBP/ZAR": 0.003,
            "EUR/USD": 0.0001, "GBP/USD": 0.0002,
        }
        base = base_spreads.get(currency_pair, 0.002)

        provider_info = self.PROVIDERS.get(provider, {})
        factor = provider_info.get("spread_factor", 1.0)

        # Add market condition variation
        market_factor = random.uniform(0.8, 1.5)

        return base * factor * market_factor

    def generate_one(self, **kwargs) -> LiquidityQuote:
        """
        Generate a single liquidity quote.

        Args:
            **kwargs: Optional overrides for pair, provider, bid, ask

        Returns:
            LiquidityQuote instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            self._quote_count += 1
            pair = kwargs.get("currency_pair") or random.choice(self._pairs)
            provider = kwargs.get("provider") or random.choice(self._providers)

            mid = self._get_mid_price(pair)
            spread = self._get_spread(pair, provider)

            # Calculate bid/ask from mid and spread
            bid = round(mid - spread / 2, 4)
            ask = round(mid + spread / 2, 4)

            # Override if provided
            if "bid" in kwargs:
                bid = round(kwargs["bid"], 4)
            if "ask" in kwargs:
                ask = round(kwargs["ask"], 4)

            # Ensure bid < ask
            if bid >= ask:
                bid = round(ask - 0.0001, 4)

            # Depth based on provider profile
            provider_info = self.PROVIDERS.get(provider, {})
            depth_factor = provider_info.get("depth_factor", 1.0)
            base_depth = random.uniform(5, 100)
            depth = round(base_depth * depth_factor, 3)

            # Sizes (may differ for bid/ask)
            bid_size = round(depth * random.uniform(0.8, 1.2), 3)
            ask_size = round(depth * random.uniform(0.8, 1.2), 3)

            # Firm quotes more likely from tier 1
            provider_type = provider_info.get("type", "")
            is_firm = random.random() < (0.95 if "tier_1" in provider_type else 0.85)

            quote = LiquidityQuote(
                quote_id=f"QUOTE-{self._quote_count:08d}",
                provider=provider,
                currency_pair=pair,
                bid=bid,
                ask=ask,
                bid_size_musd=bid_size,
                ask_size_musd=ask_size,
                timestamp=datetime.now(timezone.utc),
                depth_musd=depth,
                is_firm=is_firm,
            )

            logger.debug(
                f"Generated LP quote: {provider} {pair} "
                f"{bid:.4f}/{ask:.4f} spread={spread:.6f} "
                f"depth=${depth:,.0f}M firm={is_firm}"
            )

            return quote

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate liquidity quote: {e}")
            raise RuntimeError(f"Quote generation failed: {e}") from e

    def generate_aggregated_quote(
        self,
        currency_pair: str,
    ) -> Dict[str, float]:
        """
        Generate aggregated best bid/ask across all LPs.

        Args:
            currency_pair: Currency pair to aggregate

        Returns:
            Dictionary with best_bid, best_ask, mid, spread
        """
        quotes = [
            self.generate_one(currency_pair=currency_pair, provider=p)
            for p in self._providers
        ]

        best_bid = max(q.bid for q in quotes)
        best_ask = min(q.ask for q in quotes)
        mid = round((best_bid + best_ask) / 2, 4)
        spread = round(best_ask - best_bid, 4)

        return {
            "currency_pair": currency_pair,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread": spread,
            "spread_pct": round(spread / mid * 100, 4) if mid else 0,
            "num_quotes": len(quotes),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def stream(self, count: int = 1, **kwargs) -> Iterator[LiquidityQuote]:
        """
        Stream liquidity quotes.

        Args:
            count: Number of quotes to generate
            **kwargs: Passed to generate_one

        Yields:
            LiquidityQuote instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} liquidity quotes")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} liquidity quotes")
