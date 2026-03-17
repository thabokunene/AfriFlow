from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.insurance.simulator.reinsurance_cession_generator")


@dataclass
class ReinsuranceCession:
    policy_id: str
    ceded_pct: float
    reinsurer: str
    premium_usd: float
    timestamp: datetime


class ReinsuranceCessionGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._reinsurers = ["MunichRe", "SwissRe", "HannoverRe"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> ReinsuranceCession:
        return ReinsuranceCession(
            policy_id=f"POL-{random.randint(1000,9999)}",
            ceded_pct=round(random.uniform(0.1, 0.9), 2),
            reinsurer=random.choice(self._reinsurers),
            premium_usd=round(random.uniform(1000, 250000), 2),
            timestamp=datetime.now(timezone.utc),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[ReinsuranceCession]:
        return super().stream(count=count, **kwargs)
