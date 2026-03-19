"""
@file loan_application_generator.py
@description Synthetic data generator for PBB loan applications,
    modeling credit scores and loan purposes for retail and business lending.
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

# Logger for operational tracking of the loan application simulation
logger = get_logger("domains.pbb.simulator.loan_application_generator")


@dataclass
class LoanApplication:
    """
    Represents a synthetic loan application with credit scoring and purpose metadata.
    """
    application_id: str
    customer_id: str
    amount: float
    currency: str
    purpose: str
    # UTC timestamps for consistent event ordering across regions
    timestamp: datetime
    # score represents an internal credit score (0.0 to 1.0)
    score: float


class LoanApplicationGenerator(SimulatorBase):
    """
    Generator for simulating retail and business loan applications.
    
    Design intent:
    - Model diverse loan purposes (e.g., working capital, property).
    - Produce realistic credit scores and application amounts.
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with supported currencies and loan purposes.
        """
        # Primary African currencies for lending simulation
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        # Common loan purposes for both personal and small business banking
        self._purposes = ["working_capital", "equipment", "vehicle", "property"]

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters. Currently no specific validation logic is required.
        """
        pass

    def generate_one(self, **kwargs) -> LoanApplication:
        """
        Generates a single synthetic loan application record.
        
        :return: A LoanApplication dataclass instance.
        """
        return LoanApplication(
            application_id=f"APP-{random.randint(100000, 999999)}",
            customer_id=f"CUST-{random.randint(100000, 999999)}",
            # Random amount within typical retail/SME lending ranges
            amount=round(random.uniform(1000, 500000), 2),
            currency=random.choice(self._curr),
            purpose=random.choice(self._purposes),
            timestamp=datetime.now(timezone.utc),
            # Generate a risk score (higher is generally better/lower risk)
            score=round(random.uniform(0.0, 1.0), 3),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[LoanApplication]:
        """
        Creates an iterator that yields a specified number of application records.
        """
        return super().stream(count=count, **kwargs)
