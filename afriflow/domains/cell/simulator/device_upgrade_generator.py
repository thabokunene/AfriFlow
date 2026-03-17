from __future__ import annotations
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional
from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.cell.simulator.device_upgrade_generator")


@dataclass
class DeviceUpgradeEvent:
    msisdn: str
    old_device_tier: str
    new_device_tier: str
    timestamp: datetime
    country: str


class DeviceUpgradeGenerator(SimulatorBase):
    def initialize(self, config=None) -> None:
        self._tiers = ["feature", "entry-smart", "mid-smart", "flagship"]
        self._countries = ["NG", "ZA", "KE", "GH", "TZ"]

    def validate_input(self, **kwargs) -> None:
        if "msisdn" in kwargs and not str(kwargs["msisdn"]).isdigit():
            raise ValueError("msisdn must be numeric string")

    def _random_msisdn(self) -> str:
        return "27" + "".join(str(random.randint(0, 9)) for _ in range(9))

    def generate_one(self, **kwargs) -> DeviceUpgradeEvent:
        self.validate_input(**kwargs)
        old_tier = random.choice(self._tiers[:-1])
        new_tier = self._tiers[self._tiers.index(old_tier) + 1] if old_tier != "flagship" else "flagship"
        return DeviceUpgradeEvent(
            msisdn=kwargs.get("msisdn") or self._random_msisdn(),
            old_device_tier=old_tier,
            new_device_tier=new_tier,
            timestamp=datetime.now(timezone.utc),
            country=kwargs.get("country") or random.choice(self._countries),
        )

    def stream(self, count: int = 1, **kwargs) -> Iterator[DeviceUpgradeEvent]:
        return super().stream(count=count, **kwargs)
