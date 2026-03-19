"""
@file device_upgrade_generator.py
@description Generator for synthetic device upgrade events, simulating technological adoption and income mobility.
@author Thabo Kunene
@created 2026-03-19
"""

# Enables postponed evaluation of type annotations
from __future__ import annotations
# Random library for stochastic event generation
import random
# Dataclass for structured representation of upgrade events
from dataclasses import dataclass
# Datetime utilities for timestamping generated events
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, Optional
# AfriFlow logging utility for consistent log formatting
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the device upgrade generator namespace
logger = get_logger("domains.cell.simulator.device_upgrade_generator")


@dataclass
class DeviceUpgradeEvent:
    """
    Represents a single device upgrade event.
    Tracks the transition from an older device category to a newer one.
    """
    msisdn: str
    old_device_tier: str
    new_device_tier: str
    timestamp: datetime
    country: str


class DeviceUpgradeGenerator(SimulatorBase):
    """
    Simulator for generating synthetic device upgrade data.
    Useful for testing income mobility models and cross-sell triggers.
    """
    def initialize(self, config=None) -> None:
        """
        Sets up the internal state for the generator, including tiers and target countries.
        
        :param config: Optional configuration object.
        """
        # Device categories representing increasing levels of cost and capability
        self._tiers = ["feature", "entry-smart", "mid-smart", "flagship"]
        # Default African markets for simulation
        self._countries = ["NG", "ZA", "KE", "GH", "TZ"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before event generation.
        
        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the MSISDN is provided but is not a numeric string.
        """
        if "msisdn" in kwargs and not str(kwargs["msisdn"]).isdigit():
            raise ValueError("msisdn must be numeric string")

    def _random_msisdn(self) -> str:
        """
        Generates a random South African MSISDN for testing.
        
        :return: A numeric string representing a mobile number.
        """
        return "27" + "".join(str(random.randint(0, 9)) for _ in range(9))

    def generate_one(self, **kwargs) -> DeviceUpgradeEvent:
        """
        Generates a single synthetic device upgrade event.
        
        :param kwargs: Optional overrides for msisdn and country.
        :return: A DeviceUpgradeEvent instance.
        """
        self.validate_input(**kwargs)
        # Select an old tier (excluding flagship as you can't upgrade from it in this simple model)
        old_tier = random.choice(self._tiers[:-1])
        # Move one step up the tier ladder
        new_tier = self._tiers[self._tiers.index(old_tier) + 1] if old_tier != "flagship" else "flagship"
        
        return DeviceUpgradeEvent(
            msisdn=kwargs.get("msisdn") or self._random_msisdn(),
            old_device_tier=old_tier,
            new_device_tier=new_tier,
            timestamp=datetime.now(timezone.utc),
            country=kwargs.get("country") or random.choice(self._countries),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[DeviceUpgradeEvent]:
        """
        Yields a stream of generated device upgrade events.
        
        :param count: Number of events to generate.
        :param kwargs: Parameters passed to generate_one.
        :return: An iterator of DeviceUpgradeEvent instances.
        """
        return super().stream(count=count, **kwargs)
