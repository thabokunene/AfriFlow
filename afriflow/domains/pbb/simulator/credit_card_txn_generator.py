from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.pbb.simulator.credit_card_txn_generator")


@dataclass
class CreditCardTxn:
    account_id: str
    amount: float
    merchant: str
    currency: str
    timestamp: datetime
    mcc: str


class CreditCardTxnGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._curr = ["ZAR", "NGN", "KES", "USD"]
        self._mcc = ["5411", "5812", "5541", "4111", "5311"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> CreditCardTxn:
        return CreditCardTxn(
            account_id=f"ACC-{random.randint(100000, 999999)}",
            amount=round(random.uniform(1, 5000), 2),
            merchant=random.choice(["Shoprite", "PicknPay", "MrPrice", "Takealot"]),
            currency=random.choice(self._curr),
            timestamp=datetime.now(timezone.utc),
            mcc=random.choice(self._mcc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[CreditCardTxn]:
        return super().stream(count=count, **kwargs)
