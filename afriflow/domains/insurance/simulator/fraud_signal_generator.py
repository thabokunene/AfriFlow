from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.insurance.simulator.fraud_signal_generator")


@dataclass
class FraudSignal:
    claim_id: str
    policy_id: str
    score: float
    reason: Optional[str]
    timestamp: datetime


class FraudSignalGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        pass

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> FraudSignal:
        score = round(random.uniform(0.0, 1.0), 3)
        reason = random.choice([None, "duplicate_docs", "late_report", "mismatch_medical"])
        return FraudSignal(
            claim_id=f"CLM-{random.randint(1000,9999)}",
            policy_id=f"POL-{random.randint(1000,9999)}",
            score=score,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[FraudSignal]:
        return super().stream(count=count, **kwargs)
