"""
Volatility Spike Generator

We generate realistic synthetic FX volatility spike events
for African currency pairs.

Volatility spikes in African FX markets are triggered by:

1. Macro data releases: CPI, GDP, trade balance surprises
   can cause 2-5x normal volatility for several hours.
2. Policy changes: Central bank rate decisions, FX regime
   changes (e.g., NGN float in 2023) cause regime shifts.
3. Liquidity crunches: Month-end, quarter-end, or during
   global risk-off events (COVID March 2020).
4. Commodity shocks: Oil price crashes hit NGN, copper
   hits ZMW, gold affects GHS and ZAR.
5. Political events: Elections, leadership changes,
   geopolitical tensions.

Volatility is measured as annualized standard deviation
of returns. Normal ZAR vol is 10-15%; spikes can reach
40-60%.

Disclaimer: This is not a sanctioned Standard Bank
Group project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

from __future__ import annotations
import math
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, List, Optional

from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase
from afriflow.exceptions import ConfigurationError

logger = get_logger("domains.forex.simulator.volatility_spike_generator")


# Base volatility levels (annualized %) by pair
BASE_VOLATILITY = {
    "USD/ZAR": 12.0, "USD/NGN": 25.0, "USD/KES": 8.0,
    "USD/GHS": 22.0, "USD/TZS": 6.0, "USD/UGX": 7.5,
    "USD/ZMW": 18.0, "EUR/ZAR": 10.0, "GBP/ZAR": 14.0,
    "EUR/USD": 8.0, "GBP/USD": 10.0,
}

# Volatility spike multipliers by trigger type
SPIKE_MULTIPLIERS = {
    "macro_data": (2.0, 4.0),      # 2-4x normal vol
    "policy_change": (3.0, 6.0),   # 3-6x for regime changes
    "liquidity_crunch": (1.5, 3.0), # 1.5-3x during funding stress
    "commodity_shock": (2.0, 5.0),  # 2-5x for commodity-linked
    "political_event": (2.5, 5.5),  # 2.5-5.5x for elections etc.
}

# Typical spike durations (minutes) by severity
DURATION_RANGES = {
    "minor": (10, 60),      # Brief spike
    "moderate": (60, 240),  # 1-4 hours
    "severe": (240, 1440),  # 4-24 hours
    "extreme": (1440, 4320), # 1-3 days
}


@dataclass
class VolatilitySpike:
    """
    A volatility spike event record.

    We publish these to the forex domain Kafka topic
    (forex.volatility_spikes) for risk monitoring and
    trading strategy adjustment.

    The spike includes both the base (normal) volatility
    and the elevated (spike) volatility for comparison.
    """

    spike_id: str
    currency_pair: str
    timestamp: datetime
    base_vol: float
    spike_vol: float
    spike_multiplier: float
    duration_minutes: int
    severity: str
    trigger_type: Optional[str]
    trigger_description: Optional[str]
    end_timestamp: Optional[datetime] = None


class VolatilitySpikeGenerator(SimulatorBase):
    """
    We generate realistic synthetic volatility spikes
    for testing and demo purposes.

    Usage:
        gen = VolatilitySpikeGenerator(seed=42)
        spike = gen.generate_one(currency_pair="USD/ZAR")
    """

    def __init__(self, seed: Optional[int] = None, config=None):
        if seed is not None:
            random.seed(seed)
        logger.info("VolatilitySpikeGenerator initialized")
        super().__init__(config)

    def initialize(self, config=None) -> None:
        """Initialize the generator with default pairs."""
        self._pairs = list(BASE_VOLATILITY.keys())
        self._trigger_types = list(SPIKE_MULTIPLIERS.keys())
        logger.info("VolatilitySpikeGenerator configuration loaded")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If currency_pair is invalid or parameters malformed
        """
        pair = kwargs.get("currency_pair")
        if pair is not None and pair not in self._pairs:
            raise ValueError(f"Unsupported currency_pair: {pair}")

        base_vol = kwargs.get("base_vol")
        if base_vol is not None and base_vol <= 0:
            raise ValueError("base_vol must be positive")

        duration = kwargs.get("duration_minutes")
        if duration is not None and duration <= 0:
            raise ValueError("duration_minutes must be positive")

    def _determine_severity(self, multiplier: float) -> str:
        """Determine spike severity based on multiplier."""
        if multiplier >= 5.0:
            return "extreme"
        elif multiplier >= 3.5:
            return "severe"
        elif multiplier >= 2.0:
            return "moderate"
        else:
            return "minor"

    def _get_trigger_description(
        self,
        trigger_type: str,
        currency_pair: str,
    ) -> str:
        """Generate realistic trigger description."""
        descriptions = {
            "macro_data": [
                "CPI print beats expectations",
                "GDP contraction exceeds forecasts",
                "Trade balance deficit widens",
                "Employment data surprise",
            ],
            "policy_change": [
                "Central bank emergency rate hike",
                "FX regime change announced",
                "Capital controls introduced",
                "Reserve requirement change",
            ],
            "liquidity_crunch": [
                "Month-end funding squeeze",
                "Quarter-end repatriation flow",
                "Global risk-off sentiment",
                "Interbank market stress",
            ],
            "commodity_shock": [
                "Oil price sharp decline",
                "Copper futures gap lower",
                "Gold price volatility",
                "Commodity index selloff",
            ],
            "political_event": [
                "Election result uncertainty",
                "Cabinet reshuffle surprise",
                "Geopolitical tension escalation",
                "Policy announcement surprise",
            ],
        }
        options = descriptions.get(trigger_type, ["Market event"])
        return random.choice(options)

    def generate_one(self, **kwargs) -> VolatilitySpike:
        """
        Generate a single volatility spike event.

        Args:
            **kwargs: Optional overrides for spike parameters

        Returns:
            VolatilitySpike instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            spike_id = f"VSPIKE-{random.randint(100000, 999999)}"
            pair = kwargs.get("currency_pair") or random.choice(self._pairs)

            # Base volatility for this pair
            base_vol = kwargs.get("base_vol") or BASE_VOLATILITY.get(pair, 12.0)

            # Trigger type and multiplier
            trigger_type = kwargs.get("trigger_type") or random.choice(self._trigger_types)
            mult_range = SPIKE_MULTIPLIERS.get(trigger_type, (2.0, 4.0))
            multiplier = random.uniform(*mult_range)

            # Spike volatility
            spike_vol = round(base_vol * multiplier, 3)
            base_vol = round(base_vol, 3)

            # Severity and duration
            severity = self._determine_severity(multiplier)
            duration_range = DURATION_RANGES.get(severity, (60, 240))
            duration = kwargs.get("duration_minutes") or random.randint(*duration_range)

            # Timestamps
            start_time = datetime.now(timezone.utc) - timedelta(
                minutes=random.randint(0, 1440)
            )
            end_time = start_time + timedelta(minutes=duration)

            # Trigger description
            description = self._get_trigger_description(trigger_type, pair)

            spike = VolatilitySpike(
                spike_id=spike_id,
                currency_pair=pair,
                timestamp=start_time,
                base_vol=base_vol,
                spike_vol=spike_vol,
                spike_multiplier=round(multiplier, 2),
                duration_minutes=duration,
                severity=severity,
                trigger_type=trigger_type,
                trigger_description=description,
                end_timestamp=end_time,
            )

            logger.info(
                f"Generated volatility spike: {spike_id} "
                f"{pair} {base_vol:.1f}% → {spike_vol:.1f}% "
                f"({multiplier:.1f}x) {severity} - {description}"
            )

            return spike

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate volatility spike: {e}")
            raise RuntimeError(f"Spike generation failed: {e}") from e

    def generate_spike_sequence(
        self,
        currency_pair: str,
        num_spikes: int = 5,
    ) -> List[VolatilitySpike]:
        """
        Generate a sequence of related volatility spikes.

        Simulates a volatility regime with multiple spikes
        over a period (e.g., a crisis week).

        Args:
            currency_pair: Currency pair for the sequence
            num_spikes: Number of spikes to generate

        Returns:
            List of VolatilitySpike instances
        """
        if num_spikes <= 0:
            logger.warning(f"Invalid num_spikes: {num_spikes}")
            return []

        spikes = []
        base_time = datetime.now(timezone.utc) - timedelta(days=num_spikes)

        for i in range(num_spikes):
            spike = self.generate_one(
                currency_pair=currency_pair,
            )
            spike.timestamp = base_time + timedelta(hours=i * 6)
            spike.end_timestamp = spike.timestamp + timedelta(
                minutes=spike.duration_minutes
            )
            spikes.append(spike)

        logger.info(f"Generated sequence of {len(spikes)} volatility spikes for {currency_pair}")
        return spikes

    def stream(self, count: int = 1, **kwargs) -> Iterator[VolatilitySpike]:
        """
        Stream volatility spike events.

        Args:
            count: Number of spikes to generate
            **kwargs: Passed to generate_one

        Yields:
            VolatilitySpike instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} volatility spikes")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} volatility spikes")
