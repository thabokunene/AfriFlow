"""
Corridor Heatmap Generator

We generate realistic synthetic corridor heatmap data
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

logger = get_logger("domains.cib.simulator.corridor_heatmap_generator")


@dataclass
class CorridorHeat:
    """
    A single corridor heatmap record.

    We publish these to the CIB domain Kafka topic
    (cib.corridor_heatmap) for visualization.
    """

    corridor: str
    volume_usd: float
    transactions: int
    timestamp: datetime


class CorridorHeatmapGenerator(SimulatorBase):
    """
    We generate realistic synthetic corridor heatmap data
    for testing and demo purposes.

    Usage:
        gen = CorridorHeatmapGenerator(seed=42)
        heat = gen.generate_one(corridor="ZA-NG")
    """

    def initialize(self, config=None) -> None:
        """Initialize the generator with corridors."""
        self._corridors: List[str] = [
            "ZA-NG", "NG-GH", "ZA-KE", "KE-TZ", "NG-CI",
            "ZA-GH", "NG-KE", "KE-UG", "TZ-ZM", "GH-CI"
        ]
        logger.info("CorridorHeatmapGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If corridor is invalid
        """
        corridor = kwargs.get("corridor")
        if corridor is not None and corridor not in self._corridors:
            raise ValueError(f"Invalid corridor: {corridor}")

        volume = kwargs.get("volume_usd")
        if volume is not None and volume < 0:
            raise ValueError("volume_usd must be non-negative")

        txns = kwargs.get("transactions")
        if txns is not None and txns < 0:
            raise ValueError("transactions must be non-negative")

    def generate_one(self, **kwargs) -> CorridorHeat:
        """
        Generate a single corridor heatmap record.

        Args:
            **kwargs: Optional overrides for corridor, volume_usd, transactions

        Returns:
            CorridorHeat instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

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
