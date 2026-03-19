"""
@file merchant_pos_generator.py
@description Synthetic data generator for PBB merchant POS transactions,
    modeling urban spending patterns and merchant activity across African cities.
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

# Logger for operational tracking of the merchant POS simulation
logger = get_logger("domains.pbb.simulator.merchant_pos_generator")


@dataclass
class MerchantPOS:
    """
    Represents a synthetic merchant Point of Sale (POS) transaction.
    """
    merchant_id: str
    txn_id: str
    amount: float
    currency: str
    # UTC timestamps for consistent event ordering across regions
    timestamp: datetime
    # city tracks the geographical distribution of spending
    city: str


class MerchantPOSGenerator(SimulatorBase):
    """
    Generator for simulating merchant POS transactions.
    
    Design intent:
    - Model merchant activity across major African urban centers.
    - Produce realistic transaction volumes and city-level spending data.
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with supported currencies and target cities.
        """
        # Primary African currencies for POS simulation
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        # Major African cities to simulate geographical distribution of transactions
        self._cities = ["Johannesburg", "Lagos", "Nairobi", "Accra", "Dar es Salaam"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters. Currently no specific validation logic is required.
        """
        pass

    def generate_one(self, **kwargs) -> MerchantPOS:
        """
        Generates a single synthetic merchant POS transaction record.
        
        :return: A MerchantPOS dataclass instance.
        """
        return MerchantPOS(
            merchant_id=f"MER-{random.randint(1000,9999)}",
            txn_id=f"TXN-{random.randint(100000,999999)}",
            # Random amount within typical POS transaction ranges
            amount=round(random.uniform(1, 10000), 2),
            currency=random.choice(self._curr),
            timestamp=datetime.now(timezone.utc),
            city=random.choice(self._cities),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[MerchantPOS]:
        """
        Creates an iterator that yields a specified number of POS records.
        """
        return super().stream(count=count, **kwargs)
