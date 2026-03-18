from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.cell.simulator.tower_outage_simulator")


@dataclass
class TowerOutage:
    tower_id: str
    country: str
    started_at: datetime
    duration_minutes: int
    severity: str


class TowerOutageSimulator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._countries = ["NG", "ZA", "KE", "GH", "TZ"]

    def validate_input(self, **kwargs) -> None:
        pass

    def generate_one(self, **kwargs) -> TowerOutage:
        minutes = random.randint(5, 360)
        severity = "critical" if minutes > 180 else "high" if minutes > 60 else "medium"
        return TowerOutage(
            tower_id=f"TWR-{random.randint(1000, 9999)}",
            country=kwargs.get("country") or random.choice(self._countries),
            started_at=datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 60)),
            duration_minutes=minutes,
            severity=severity,
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[TowerOutage]:
        return super().stream(count=count, **kwargs)
