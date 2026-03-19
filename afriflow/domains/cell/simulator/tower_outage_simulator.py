"""
@file tower_outage_simulator.py
@description Simulator for generating synthetic cellular tower outage events, used to test network resilience and alerting.
@author Thabo Kunene
@created 2026-03-19
"""

# Enables postponed evaluation of type annotations
from __future__ import annotations
# Random library for stochastic event generation
import random
# Dataclass for structured representation of outage events
from dataclasses import dataclass
# Datetime utilities for timestamping and duration calculations
from datetime import datetime, timedelta, timezone
# Typing hints for defining strong collection contracts
from typing import Iterator
# AfriFlow logging utility for consistent log formatting
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the tower outage simulator namespace
logger = get_logger("domains.cell.simulator.tower_outage_simulator")


@dataclass
class TowerOutage:
    """
    Represents a single cellular tower outage event.
    """
    tower_id: str
    country: str
    started_at: datetime
    duration_minutes: int
    severity: str


class TowerOutageSimulator(SimulatorBase):
    """
    Simulator for generating synthetic tower outage data.
    Useful for testing the alerting pipeline and regional network health monitoring.
    """
    def initialize(self, config=None) -> None:
        """
        Sets up the internal state for the simulator.
        
        :param config: Optional configuration object.
        """
        # Default list of African markets for simulation
        self._countries = ["NG", "ZA", "KE", "GH", "TZ"]

    def validate_input(self, **kwargs) -> None:
        """
        Input validation hook (currently no specific constraints).
        """
        pass

    def generate_one(self, **kwargs) -> TowerOutage:
        """
        Generates a single synthetic tower outage event.
        
        :param kwargs: Optional override for country.
        :return: A TowerOutage instance.
        """
        # Randomize duration and determine severity based on the length of the outage
        minutes = random.randint(5, 360)
        severity = "critical" if minutes > 180 else "high" if minutes > 60 else "medium"
        
        return TowerOutage(
            tower_id=f"TWR-{random.randint(1000, 9999)}",
            country=kwargs.get("country") or random.choice(self._countries),
            # Start time is randomized within the last hour
            started_at=datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 60)),
            duration_minutes=minutes,
            severity=severity,
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[TowerOutage]:
        """
        Yields a stream of generated tower outage events.
        
        :param count: Number of events to generate.
        :param kwargs: Parameters passed to generate_one.
        :return: An iterator of TowerOutage instances.
        """
        return super().stream(count=count, **kwargs)
