from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.pbb.simulator.merchant_pos_generator")


@dataclass
class MerchantPOS:
    merchant_id: str
    txn_id: str
    amount: float
    currency: str
    timestamp: datetime
    city: str


class MerchantPOSGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        self._cities = ["Johannesburg", "Lagos", "Nairobi", "Accra", "Dar es Salaam"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> MerchantPOS:
        return MerchantPOS(
            merchant_id=f"MER-{random.randint(1000,9999)}",
            txn_id=f"TXN-{random.randint(100000,999999)}",
            amount=round(random.uniform(1, 10000), 2),
            currency=random.choice(self._curr),
            timestamp=datetime.now(timezone.utc),
            city=random.choice(self._cities),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[MerchantPOS]:
        return super().stream(count=count, **kwargs)
