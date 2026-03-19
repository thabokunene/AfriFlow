"""
@file order_book_simulator.py
@description Generator for synthetic FX order book levels, simulating market depth and liquidity pressure for African currency pairs.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Order Book Simulator

We generate realistic synthetic order book levels for
African FX currency pairs.

Order book data provides market depth intelligence:
1. Bid-ask spread width indicates liquidity conditions
2. Order size distribution shows institutional vs retail flow
3. Imbalance between bid/ask depth signals directional pressure
4. Quote updates frequency measures market activity

Disclaimer: This is not a sanctioned Standard Bank
Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# Random library for stochastic price and size variability in order book levels
import random
# Standard logging for operational telemetry and audit trails
import logging
# Dataclasses for structured representation of order book level records
from dataclasses import dataclass
# Datetime utilities for timestamping generated levels
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, List, Literal, Optional, Dict

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the order book simulator namespace
logger = get_logger("domains.forex.simulator.order_book_simulator")


@dataclass
class OrderBookLevel:
    """
    A single order book level record.
    Represents an available price and volume on either the bid or ask side.

    Attributes:
        currency_pair: The currency pair for this level (e.g., 'USD/ZAR').
        side: Indicates if the level is on the 'bid' or 'ask' side.
        price: The exchange rate for this specific level.
        size_musd: Available volume at this price in millions of USD.
        timestamp: The precise ISO timestamp of the level generation.
        sequence_num: Monotonically increasing sequence number per currency pair.
    """

    currency_pair: str
    side: Literal["bid", "ask"]
    price: float
    size_musd: float
    timestamp: datetime
    sequence_num: int


class OrderBookSimulator(SimulatorBase):
    """
    Generator for realistic synthetic order book data.
    Useful for testing microstructure analytics and trade execution strategies.

    Usage:
        gen = OrderBookSimulator()
        level = gen.generate_one(currency_pair="USD/ZAR")
    """

    # Indicative base mid prices for major and African currency pairs.
    BASE_PRICES = {
        "USD/ZAR": 18.50, "USD/NGN": 1580.0, "USD/KES": 130.0,
        "USD/GHS": 15.5, "EUR/ZAR": 20.0, "GBP/ZAR": 23.5,
        "ZAR/NGN": 85.4, "EUR/USD": 1.08, "GBP/USD": 1.27,
    }

    # Typical bid-ask spreads in pips per currency pair based on market liquidity.
    # African pairs typically have wider spreads than G10 currencies.
    SPREAD_PIPS = {
        "USD/ZAR": 50, "USD/NGN": 200, "USD/KES": 100,
        "USD/GHS": 300, "EUR/ZAR": 60, "GBP/ZAR": 70,
        "ZAR/NGN": 500, "EUR/USD": 1, "GBP/USD": 2,
    }

    def __init__(self, seed: Optional[int] = None, config=None):
        """
        Initializes the order book simulator.

        :param seed: Optional random seed for deterministic generation.
        :param config: Optional AppConfig override.
        """
        if seed is not None:
            random.seed(seed)
        # Internal state to track the next sequence number per currency pair.
        self._sequence: Dict[str, int] = {}
        logger.info("OrderBookSimulator initialized")
        super().__init__(config)

    def initialize(self, config=None) -> None:
        """
        Sets up the internal state including active currency pairs.
        
        :param config: Optional configuration object.
        """
        self._pairs = list(self.BASE_PRICES.keys())
        logger.info("OrderBookSimulator configuration loaded")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before level generation.
        
        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the currency pair, side, or size is invalid.
        """
        # Ensure the currency pair is in our registry.
        pair = kwargs.get("currency_pair")
        if pair is not None and pair not in self._pairs:
            raise ValueError(f"Unsupported currency_pair: {pair}")

        # Ensure the side is either 'bid' or 'ask'.
        side = kwargs.get("side")
        if side is not None and side not in ("bid", "ask"):
            raise ValueError("side must be 'bid' or 'ask'")

        # Guard against non-positive order sizes.
        size = kwargs.get("size_musd")
        if size is not None and size <= 0:
            raise ValueError("size_musd must be positive")

    def _get_mid_price(self, currency_pair: str) -> float:
        """Get base mid price with small random variation."""
        base = self.BASE_PRICES.get(currency_pair, 1.0)
        # Add small random walk component (±0.1%)
        variation = random.uniform(-0.001, 0.001)
        return round(base * (1 + variation), 4)

    def _get_spread(self, currency_pair: str) -> float:
        """Get spread in price units."""
        mid = self.BASE_PRICES.get(currency_pair, 1.0)
        pips = self.SPREAD_PIPS.get(currency_pair, 10)

        # Convert pips to price units (pip = 0.0001 for most pairs)
        if currency_pair in ("USD/NGN", "USD/KES", "USD/GHS", "ZAR/NGN"):
            pip_value = 0.01  # Larger pip value for high-number currencies
        else:
            pip_value = 0.0001

        return pips * pip_value

    def generate_one(self, **kwargs) -> OrderBookLevel:
        """
        Generate a single order book level.

        Args:
            **kwargs: Optional overrides for pair, side, price, size

        Returns:
            OrderBookLevel instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            pair = kwargs.get("currency_pair") or random.choice(self._pairs)
            side = kwargs.get("side") or random.choice(["bid", "ask"])
            mid = self._get_mid_price(pair)
            spread = self._get_spread(pair)

            # Calculate price based on side
            if side == "bid":
                price = round(mid - spread / 2, 4)
            else:
                price = round(mid + spread / 2, 4)

            # Override price if provided
            if "price" in kwargs:
                price = round(kwargs["price"], 4)

            # Order size (USD millions) - varies by pair liquidity
            liquidity_factor = {
                "USD/ZAR": 1.0, "EUR/USD": 5.0, "GBP/USD": 3.0,
                "USD/NGN": 0.3, "USD/KES": 0.2, "USD/GHS": 0.1,
            }
            factor = liquidity_factor.get(pair, 0.5)
            size = kwargs.get("size_musd") or round(
                random.uniform(1, 500) * factor, 3
            )

            # Sequence number for ordering
            if pair not in self._sequence:
                self._sequence[pair] = 0
            self._sequence[pair] += 1

            level = OrderBookLevel(
                currency_pair=pair,
                side=side,
                price=price,
                size_musd=size,
                timestamp=datetime.now(timezone.utc),
                sequence_num=self._sequence[pair],
            )

            logger.debug(
                f"Generated order book: {pair} {side} "
                f"{price:.4f} ${size:,.3f}M (seq {level.sequence_num})"
            )

            return level

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate order book level: {e}")
            raise RuntimeError(f"Order book generation failed: {e}") from e

    def generate_snapshot(
        self,
        currency_pair: str,
        levels: int = 5,
    ) -> List[OrderBookLevel]:
        """
        Generate a full order book snapshot with multiple levels.

        Args:
            currency_pair: Currency pair to snapshot
            levels: Number of bid/ask levels

        Returns:
            List of OrderBookLevel instances (bids first, then asks)
        """
        if levels <= 0:
            logger.warning(f"Invalid levels: {levels}")
            return []

        mid = self._get_mid_price(currency_pair)
        spread = self._get_spread(currency_pair)
        snapshot = []

        # Generate bid levels (decreasing prices)
        for i in range(levels):
            price = round(mid - spread / 2 - (i * spread * 0.3), 4)
            size = round(random.uniform(1, 100) * (1 - i * 0.15), 3)
            snapshot.append(OrderBookLevel(
                currency_pair=currency_pair,
                side="bid",
                price=price,
                size_musd=max(0.1, size),
                timestamp=datetime.now(timezone.utc),
                sequence_num=self._sequence.get(currency_pair, 0) + i + 1,
            ))

        # Generate ask levels (increasing prices)
        for i in range(levels):
            price = round(mid + spread / 2 + (i * spread * 0.3), 4)
            size = round(random.uniform(1, 100) * (1 - i * 0.15), 3)
            snapshot.append(OrderBookLevel(
                currency_pair=currency_pair,
                side="ask",
                price=price,
                size_musd=max(0.1, size),
                timestamp=datetime.now(timezone.utc),
                sequence_num=self._sequence.get(currency_pair, 0) + levels + i + 1,
            ))

        logger.info(f"Generated order book snapshot: {currency_pair} ({levels} levels)")
        return snapshot

    def stream(self, count: int = 1, **kwargs) -> Iterator[OrderBookLevel]:
        """
        Stream order book levels.

        Args:
            count: Number of levels to generate
            **kwargs: Passed to generate_one

        Yields:
            OrderBookLevel instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} order book levels")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} order book levels")
