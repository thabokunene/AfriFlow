"""
@file reinsurance_cession_generator.py
@description Synthetic data generator for insurance reinsurance cessions, modeling risk transfer to global reinsurers.
@author Thabo Kunene
@created 2026-03-19
"""

from __future__ import annotations
# Standard libraries for simulation and data structures
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
# Standard logging and simulator base for consistency across domains
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

# Logger for operational tracking of the reinsurance simulation
logger = get_logger("domains.insurance.simulator.reinsurance_cession_generator")


@dataclass
class ReinsuranceCession:
    """
    Represents a reinsurance cession event where risk is transferred to a third party.
    """
    policy_id: str
    # ceded_pct represents the portion of risk transferred (0.1 to 0.9)
    ceded_pct: float
    reinsurer: str
    # premium_usd is the amount paid to the reinsurer for the risk transfer
    premium_usd: float
    # UTC timestamps for audit consistency and cross-region event ordering
    timestamp: datetime


class ReinsuranceCessionGenerator(SimulatorBase):
    """
    Generator for simulating reinsurance cession events.
    
    Design intent:
    - Model risk distribution across global reinsurance partners.
    - Produce realistic financial metrics for ceded premiums and percentages.
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with a list of major global reinsurers.
        """
        # Primary global partners for reinsurance risk transfer
        self._reinsurers = ["MunichRe", "SwissRe", "HannoverRe"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters. Currently no specific validation logic is required.
        """
        pass

    def generate_one(self, **kwargs) -> ReinsuranceCession:
        """
        Generates a single synthetic reinsurance cession record.
        
        :return: A ReinsuranceCession dataclass instance.
        """
        return ReinsuranceCession(
            policy_id=f"POL-{random.randint(1000,9999)}",
            # Stochastic selection of ceded percentage to simulate varying risk appetites
            ceded_pct=round(random.uniform(0.1, 0.9), 2),
            reinsurer=random.choice(self._reinsurers),
            # Realistic premium range for reinsurance contracts
            premium_usd=round(random.uniform(1000, 250000), 2),
            timestamp=datetime.now(timezone.utc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[ReinsuranceCession]:
        """
        Creates an iterator that yields a specified number of cession records.
        """
        return super().stream(count=count, **kwargs)
