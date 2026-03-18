"""
@file reinsurance_cession_generator.py
@description Generates synthetic reinsurance cession events for insurance domain simulators
@author Thabo Kunene
@created 2026-03-17
"""
from __future__ import annotations
import random  # stochastic selection of ceded percentage and premium amounts
from dataclasses import dataclass
from datetime import datetime, timezone  # UTC timestamps for audit consistency
from typing import Iterator
from afriflow.logging_config import get_logger  # structured logging for simulator lifecycle
from afriflow.domains.shared.interfaces import SimulatorBase  # base contract for deterministic streaming

logger = get_logger("domains.insurance.simulator.reinsurance_cession_generator")


@dataclass
class ReinsuranceCession:
    policy_id: str
    ceded_pct: float
    reinsurer: str
    premium_usd: float
    timestamp: datetime


class ReinsuranceCessionGenerator(SimulatorBase):
    """
    Simulator for reinsurance cessions commonly used to transfer risk.
    Produces realistic ranges for ceded percentages and premiums.
    """
    def initialize(self, config=None) -> None:
        """
        Prepare static reinsurer list; could be extended to load from config.
        """
        self._reinsurers = ["MunichRe", "SwissRe", "HannoverRe"]

    def validate_input(self, **kwargs) -> None:
        """
        Validate parameters for cession generation.
        Currently no parameters; placeholder for future constraints (e.g., max premium).
        """
        pass

    def generate_one(self, **kwargs) -> ReinsuranceCession:
        """
        Generate a single cession event with randomized attributes in realistic bounds.
        Returns:
            ReinsuranceCession dataclass instance
        """
        return ReinsuranceCession(
            policy_id=f"POL-{random.randint(1000,9999)}",
            ceded_pct=round(random.uniform(0.1, 0.9), 2),
            reinsurer=random.choice(self._reinsurers),
            premium_usd=round(random.uniform(1000, 250000), 2),
            timestamp=datetime.now(timezone.utc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[ReinsuranceCession]:
        """
        Stream multiple cession events using base simulator stream implementation.
        """
        return super().stream(count=count, **kwargs)
