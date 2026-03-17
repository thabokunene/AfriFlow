from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.pbb.simulator.loan_application_generator")


@dataclass
class LoanApplication:
    application_id: str
    customer_id: str
    amount: float
    currency: str
    purpose: str
    timestamp: datetime
    score: float


class LoanApplicationGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        self._purposes = ["working_capital", "equipment", "vehicle", "property"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> LoanApplication:
        return LoanApplication(
            application_id=f"APP-{random.randint(100000, 999999)}",
            customer_id=f"CUST-{random.randint(100000, 999999)}",
            amount=round(random.uniform(1000, 500000), 2),
            currency=random.choice(self._curr),
            purpose=random.choice(self._purposes),
            timestamp=datetime.now(timezone.utc),
            score=round(random.uniform(0.0, 1.0), 3),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[LoanApplication]:
        return super().stream(count=count, **kwargs)
