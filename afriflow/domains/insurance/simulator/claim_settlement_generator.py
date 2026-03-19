"""
@file claim_settlement_generator.py
@description Synthetic data generator for insurance claim settlements, modeling payout channels and turnaround times in African markets.
@author Thabo Kunene
@created 2026-03-19
"""

from __future__ import annotations
# Standard libraries for simulation and data structures
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional
# Standard logging and simulator base for consistency across domains
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

# Logger for operational tracking of the simulation process
logger = get_logger("domains.insurance.simulator.claim_settlement_generator")


@dataclass
class ClaimSettlement:
    """
    Represents a settled insurance claim with financial and temporal metadata.
    """
    claim_id: str
    settled_amount: float
    currency: str
    settled_at: datetime
    # turnaround_days tracks operational efficiency from filing to payout
    turnaround_days: int
    # channel captures the payout method (e.g., Mobile Money/MoMo, EFT)
    channel: str


class ClaimSettlementGenerator(SimulatorBase):
    """
    Generator for simulating claim settlement events.
    
    Design intent:
    - Model diverse payout channels common in African insurance markets.
    - Simulate realistic turnaround times (TAT) for claims processing.
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with supported currencies and payout channels.
        """
        # Primary African currencies for settlement simulation
        self._curr = ["ZAR", "NGN", "KES", "GHS", "USD"]
        # Payout channels: EFT (Standard), MoMo (High growth/Regional), Cheque (Legacy)
        self._channels = ["eft", "momo", "cheque"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters for the generation process.
        Currently no specific validation logic is required for this generator.
        """
        pass

    def generate_one(self, **kwargs) -> ClaimSettlement:
        """
        Generates a single synthetic claim settlement record.
        
        :return: A ClaimSettlement dataclass instance.
        """
        # Simulate realistic turnaround times between 1 and 60 days
        days = random.randint(1, 60)
        return ClaimSettlement(
            claim_id=f"CLM-{random.randint(1000,9999)}",
            # Random amount within typical insurance claim ranges
            settled_amount=round(random.uniform(50, 100000), 2),
            currency=random.choice(self._curr),
            settled_at=datetime.now(timezone.utc),
            turnaround_days=days,
            channel=random.choice(self._channels),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[ClaimSettlement]:
        """
        Creates an iterator that yields a specified number of settlement records.
        """
        return super().stream(count=count, **kwargs)
