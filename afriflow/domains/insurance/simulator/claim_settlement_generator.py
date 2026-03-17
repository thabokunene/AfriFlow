from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.insurance.simulator.claim_settlement_generator")


@dataclass
class ClaimSettlement:
    claim_id: str
    settled_amount: float
    currency: str
    settled_at: datetime
    turnaround_days: int
    channel: str


class ClaimSettlementGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._curr = ["ZAR", "NGN", "KES", "GHS", "USD"]
        self._channels = ["eft", "momo", "cheque"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> ClaimSettlement:
        days = random.randint(1, 60)
        return ClaimSettlement(
            claim_id=f"CLM-{random.randint(1000,9999)}",
            settled_amount=round(random.uniform(50, 100000), 2),
            currency=random.choice(self._curr),
            settled_at=datetime.now(timezone.utc),
            turnaround_days=days,
            channel=random.choice(self._channels),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[ClaimSettlement]:
        return super().stream(count=count, **kwargs)
