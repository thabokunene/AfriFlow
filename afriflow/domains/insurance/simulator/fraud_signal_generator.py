"""
@file fraud_signal_generator.py
@description Synthetic data generator for insurance fraud signals, providing risk scores and reasoning for suspicious claims.
@author Thabo Kunene
@created 2026-03-19
"""

from __future__ import annotations
# Standard libraries for simulation and data structures
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional
# Standard logging and simulator base for consistency across domains
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

# Logger for operational tracking of the fraud signal simulation
logger = get_logger("domains.insurance.simulator.fraud_signal_generator")


@dataclass
class FraudSignal:
    """
    Represents a fraud risk signal generated for a specific claim.
    """
    claim_id: str
    policy_id: str
    # score ranges from 0.0 (low risk) to 1.0 (high risk)
    score: float
    # reason provides a high-level explanation for the score (e.g., duplicate docs)
    reason: Optional[str]
    timestamp: datetime


class FraudSignalGenerator(SimulatorBase):
    """
    Generator for simulating insurance fraud signals.
    
    Design intent:
    - Provide realistic risk scores for claims analysis.
    - Model common fraud indicators (e.g., late reporting, mismatched documents).
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator. Currently no state initialization is required.
        """
        pass

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters.
        """
        pass

    def generate_one(self, **kwargs) -> FraudSignal:
        """
        Generates a single synthetic fraud signal.
        
        :return: A FraudSignal dataclass instance.
        """
        # Generate a risk score between 0 and 1
        score = round(random.uniform(0.0, 1.0), 3)
        # Randomly select a fraud indicator reason
        reason = random.choice([None, "duplicate_docs", "late_report", "mismatch_medical"])
        return FraudSignal(
            claim_id=f"CLM-{random.randint(1000,9999)}",
            policy_id=f"POL-{random.randint(1000,9999)}",
            score=score,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[FraudSignal]:
        """
        Creates an iterator that yields a specified number of fraud signals.
        """
        return super().stream(count=count, **kwargs)
