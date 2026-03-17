"""
Treasury FX Exposure Generator

We generate realistic synthetic treasury FX exposure records
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

from __future__ import annotations
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.cib.simulator.treasury_fx_exposure_generator")


@dataclass
class FXExposure:
    """
    A single FX exposure record.

    We publish these to the CIB domain Kafka topic
    (cib.treasury.fx_exposures) for risk monitoring.
    """

    client_id: str
    currency_pair: str
    exposure_usd: float
    timestamp: datetime
    hedged_pct: float


class TreasuryFXExposureGenerator(SimulatorBase):
    """
    We generate realistic synthetic treasury FX exposures
    for testing and demo purposes.

    Usage:
        gen = TreasuryFXExposureGenerator(seed=42)
        exposure = gen.generate_one(currency_pair="USD/ZAR")
    """

    def initialize(self, config=None) -> None:
        """Initialize the generator with currency pairs."""
        self._pairs = ["USD/ZAR", "USD/NGN", "EUR/ZAR", "USD/KES", "GBP/ZAR", "EUR/NGN"]
        logger.info("TreasuryFXExposureGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If currency_pair is invalid or exposure is malformed
        """
        pair = kwargs.get("currency_pair")
        if pair is not None:
            if not isinstance(pair, str) or "/" not in pair:
                raise ValueError(f"Invalid currency_pair format: {pair}")
            if pair not in self._pairs:
                raise ValueError(f"Unknown currency_pair: {pair}")

        exposure = kwargs.get("exposure_usd")
        if exposure is not None and not isinstance(exposure, (int, float)):
            raise ValueError("exposure_usd must be a number")

        hedged = kwargs.get("hedged_pct")
        if hedged is not None and not (0.0 <= hedged <= 1.0):
            raise ValueError("hedged_pct must be between 0.0 and 1.0")

    def generate_one(self, **kwargs) -> FXExposure:
        """
        Generate a single FX exposure record.

        Args:
            **kwargs: Optional overrides for currency_pair, exposure_usd, hedged_pct

        Returns:
            FXExposure instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            pair = kwargs.get("currency_pair") or random.choice(self._pairs)
            exposure = kwargs.get("exposure_usd") or round(
                random.uniform(-5_000_000, 5_000_000), 2
            )
            hedged = kwargs.get("hedged_pct") or round(random.uniform(0.0, 1.0), 2)

            fx_exposure = FXExposure(
                client_id=f"CLIENT-{random.randint(100, 999)}",
                currency_pair=pair,
                exposure_usd=exposure,
                timestamp=datetime.now(timezone.utc),
                hedged_pct=hedged,
            )

            logger.debug(
                f"Generated FX exposure: {fx_exposure.client_id} "
                f"{pair} ${exposure:,.2f} (hedged: {hedged:.0%})"
            )

            return fx_exposure

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate FX exposure: {e}")
            raise RuntimeError(f"FX exposure generation failed: {e}") from e

    def stream(self, count: int = 1, **kwargs) -> Iterator[FXExposure]:
        """
        Stream FX exposure records.

        Args:
            count: Number of records to generate
            **kwargs: Passed to generate_one

        Yields:
            FXExposure instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} FX exposure records")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} FX exposure records")
