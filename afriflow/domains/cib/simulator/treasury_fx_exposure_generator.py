"""
@file treasury_fx_exposure_generator.py
@description Generator for synthetic CIB treasury FX exposure records, simulating currency risk and hedging activities for corporate clients.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Treasury FX Exposure Generator

We generate realistic synthetic treasury FX exposure records
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# Random library for stochastic event generation
import random
# Standard logging for operational observability and audit trails
import logging
# Dataclass for structured representation of FX exposure records
from dataclasses import dataclass
# Datetime utilities for timestamping generated exposure records
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, List, Optional

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the treasury FX exposure generator namespace
logger = get_logger("domains.cib.simulator.treasury_fx_exposure_generator")


@dataclass
class FXExposure:
    """
    A single FX exposure record.
    Represents the net currency exposure of a corporate client and their hedging status.

    Attributes:
        client_id: Unique identifier for the corporate client.
        currency_pair: The currency pair representing the exposure (e.g., 'USD/ZAR').
        exposure_usd: The net exposure amount converted to USD.
        timestamp: The precise timestamp of the record generation.
        hedged_pct: The percentage of the exposure that is currently hedged (0.0 to 1.0).
    """

    client_id: str
    currency_pair: str
    exposure_usd: float
    timestamp: datetime
    hedged_pct: float


class TreasuryFXExposureGenerator(SimulatorBase):
    """
    Generator for realistic synthetic treasury FX exposures.
    Useful for testing risk monitoring pipelines and hedging recommendation engines.

    Usage:
        gen = TreasuryFXExposureGenerator()
        exposure = gen.generate_one(currency_pair="USD/ZAR")
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with a predefined list of active currency pairs.
        
        :param config: Optional configuration object.
        """
        # Common currency pairs for African corporate treasury operations.
        self._pairs = ["USD/ZAR", "USD/NGN", "EUR/ZAR", "USD/KES", "GBP/ZAR", "EUR/NGN"]
        logger.info("TreasuryFXExposureGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before record generation.

        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the currency pair is unknown or metrics are invalid.
        """
        # Ensure the currency pair is in our registry and correctly formatted.
        pair = kwargs.get("currency_pair")
        if pair is not None:
            if not isinstance(pair, str) or "/" not in pair:
                raise ValueError(f"Invalid currency_pair format: {pair}")
            if pair not in self._pairs:
                raise ValueError(f"Unknown currency_pair: {pair}")

        # Guard against invalid exposure types.
        exposure = kwargs.get("exposure_usd")
        if exposure is not None and not isinstance(exposure, (int, float)):
            raise ValueError("exposure_usd must be a number")

        # Ensure the hedge percentage is within valid probabilistic bounds.
        hedged = kwargs.get("hedged_pct")
        if hedged is not None and not (0.0 <= hedged <= 1.0):
            raise ValueError("hedged_pct must be between 0.0 and 1.0")

    def generate_one(self, **kwargs) -> FXExposure:
        """
        Generates a single synthetic treasury FX exposure record.

        :param kwargs: Optional overrides for currency_pair, exposure_usd, and hedged_pct.
        :return: An FXExposure instance.
        :raises ValueError: If input validation fails.
        :raises RuntimeError: If generation fails due to unexpected errors.
        """
        try:
            self.validate_input(**kwargs)

            # Use provided values or generate random ones within realistic ranges.
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
