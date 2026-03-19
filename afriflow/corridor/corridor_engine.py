"""
Corridor Intelligence Engine

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.engine")


@dataclass
class Corridor:
    corridor_id: str
    source_country: str
    destination_country: str
    corridor_name: str
    is_active: bool
    first_payment_date: str
    last_payment_date: str
    total_clients: int
    total_volume_90d: float
    total_revenue_90d: float
    is_new: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corridor_id": self.corridor_id,
            "source_country": self.source_country,
            "destination_country": self.destination_country,
            "corridor_name": self.corridor_name,
            "is_active": self.is_active,
            "first_payment_date": self.first_payment_date,
            "last_payment_date": self.last_payment_date,
            "total_clients": self.total_clients,
            "total_volume_90d": self.total_volume_90d,
            "total_revenue_90d": self.total_revenue_90d,
            "is_new": self.is_new,
        }


class CorridorEngine:
    def __init__(self) -> None:
        self._corridors: Dict[str, Corridor] = {}
        logger.info("CorridorEngine initialized")

    def identify_corridors(self, payment_data: List[Dict]) -> List[Corridor]:
        # Logic to identify corridors from raw payments
        return list(self._corridors.values())

    def get_active_corridors(self) -> List[Corridor]:
        return [c for c in self._corridors.values() if c.is_active]

    def get_new_corridors(self, days: int) -> List[Corridor]:
        return [c for c in self._corridors.values() if c.is_new]

    def get_corridor_detail(self, corridor_id: str) -> Dict:
        corridor = self._corridors.get(corridor_id)
        return corridor.to_dict() if corridor else {}

    def get_corridor_clients(self, corridor_id: str) -> List[Dict]:
        return []

    def get_top_corridors(self, limit: int, sort_by: str) -> List[Corridor]:
        results = list(self._corridors.values())
        if sort_by == "volume":
            results.sort(key=lambda x: x.total_volume_90d, reverse=True)
        return results[:limit]

    def detect_corridor_changes(self, lookback_days: int) -> List[Dict]:
        return []
