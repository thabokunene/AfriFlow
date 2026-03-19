"""
@file credit_card_txn_generator.py
@description Synthetic data generator for PBB credit card transactions,
    modeling merchant categories and spending patterns in African retail markets.
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

# Logger for operational tracking of the credit card transaction simulation
logger = get_logger("domains.pbb.simulator.credit_card_txn_generator")


@dataclass
class CreditCardTxn:
    """
    Represents a synthetic credit card transaction with merchant and financial metadata.
    """
    account_id: str
    amount: float
    merchant: str
    currency: str
    # UTC timestamps for consistent event ordering across regions
    timestamp: datetime
    # mcc (Merchant Category Code) used for spending analysis and fraud detection
    mcc: str


class CreditCardTxnGenerator(SimulatorBase):
    """
    Generator for simulating retail credit card transactions.
    
    Design intent:
    - Model diverse merchant categories common in African retail.
    - Produce realistic transaction amounts and currency distributions.
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with supported currencies and MCC codes.
        """
        # Primary African currencies for retail simulation
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        # MCC codes: Groceries (5411), Dining (5812), Fuel (5541), Transport (4111), Dept Stores (5311)
        self._mcc = ["5411", "5812", "5541", "4111", "5311"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters. Currently no specific validation logic is required.
        """
        pass

    def generate_one(self, **kwargs) -> CreditCardTxn:
        """
        Generates a single synthetic credit card transaction record.
        
        :return: A CreditCardTxn dataclass instance.
        """
        return CreditCardTxn(
            account_id=f"ACC-{random.randint(100000, 999999)}",
            # Random amount within typical retail spending ranges
            amount=round(random.uniform(1, 5000), 2),
            # Common African retailers for realistic simulation
            merchant=random.choice(["Shoprite", "PicknPay", "MrPrice", "Takealot"]),
            currency=random.choice(self._curr),
            timestamp=datetime.now(timezone.utc),
            mcc=random.choice(self._mcc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[CreditCardTxn]:
        """
        Creates an iterator that yields a specified number of transaction records.
        """
        return super().stream(count=count, **kwargs)
