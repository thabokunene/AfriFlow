"""
@file corridor_heatmap_generator.py
@description Generator for synthetic CIB corridor heatmap data, identifying high-volume trade corridors across Africa.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Corridor Heatmap Generator

We generate realistic synthetic corridor heatmap data
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
# Dataclass for structured representation of corridor heatmap records
from dataclasses import dataclass
# Datetime utilities for timestamping generated heatmap records
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, List, Optional

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the corridor heatmap generator namespace
logger = get_logger("domains.cib.simulator.corridor_heatmap_generator")


@dataclass
class CorridorHeat:
    """
    A single corridor heatmap record.
    Represents aggregated transaction volume and count for a specific trade corridor.

    Attributes:
        corridor: The payment corridor (e.g., 'ZA-NG').
        volume_usd: Total transaction volume in USD.
        transactions: Total number of transactions in the period.
        timestamp: The precise timestamp of the record generation.
    """

    corridor: str
    volume_usd: float
    transactions: int
    timestamp: datetime


class CorridorHeatmapGenerator(SimulatorBase):
    """
    Generator for realistic synthetic corridor heatmap data.
    Useful for visualizing trade flows and testing regional analytics.

    Usage:
        gen = CorridorHeatmapGenerator()
        heat = gen.generate_one(corridor="ZA-NG")
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with a predefined list of active trade corridors.
        
        :param config: Optional configuration object.
        """
        # Predefined list of active trade corridors in the African market.
        self._corridors: List[str] = [
            "ZA-NG", "NG-GH", "ZA-KE", "KE-TZ", "NG-CI",
            "ZA-GH", "NG-KE", "KE-UG", "TZ-ZM", "GH-CI"
        ]
        logger.info("CorridorHeatmapGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before record generation.

        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the corridor is unknown or metrics are negative.
        """
        # Ensure the corridor is within our registry.
        corridor = kwargs.get("corridor")
        if corridor is not None and corridor not in self._corridors:
            raise ValueError(f"Invalid corridor: {corridor}")

        # Guard against invalid financial volumes.
        volume = kwargs.get("volume_usd")
        if volume is not None and volume < 0:
            raise ValueError("volume_usd must be non-negative")

        # Guard against invalid transaction counts.
        txns = kwargs.get("transactions")
        if txns is not None and txns < 0:
            raise ValueError("transactions must be non-negative")

    def generate_one(self, **kwargs) -> CorridorHeat:
        """
        Generates a single synthetic corridor heatmap record.

        :param kwargs: Optional overrides for corridor, volume_usd, and transactions.
        :return: A CorridorHeat instance.
        :raises ValueError: If input validation fails.
        :raises RuntimeError: If generation fails due to unexpected errors.
        """
        try:
            self.validate_input(**kwargs)

            # Use provided values or generate random ones within realistic ranges.
            corridor = kwargs.get("corridor") or random.choice(self._corridors)
            txns = kwargs.get("transactions") or random.randint(10, 500)
            vol = kwargs.get("volume_usd") or round(random.uniform(10000, 5000000), 2)

            heat = CorridorHeat(
                corridor=corridor,
                volume_usd=vol,
                transactions=txns,
                timestamp=datetime.now(timezone.utc),
            )

            logger.debug(
                f"Generated corridor heat: {corridor} "
                f"${vol:,.2f} ({txns} txns)"
            )

            return heat

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate corridor heat: {e}")
            raise RuntimeError(f"Heatmap generation failed: {e}") from e

    def stream(self, count: int = 1, **kwargs) -> Iterator[CorridorHeat]:
        """
        Stream corridor heatmap records.

        Args:
            count: Number of records to generate
            **kwargs: Passed to generate_one

        Yields:
            CorridorHeat instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} corridor heatmap records")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} corridor heatmap records")
