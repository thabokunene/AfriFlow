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
from datetime import datetime

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
        """
        Groups raw payments into corridors and calculates stats.
        Expected payment format: { 'source': 'ZA', 'destination': 'NG', 'amount': 1000.0, 'client_id': '...' }
        """
        temp_data: Dict[str, Any] = {}
        for p in payment_data:
            cid = f"{p['source']}-{p['destination']}"
            if cid not in temp_data:
                temp_data[cid] = {
                    "source": p["source"],
                    "destination": p["destination"],
                    "clients": set(),
                    "volume": 0.0,
                    "first_date": p.get("date", datetime.now().isoformat()),
                    "last_date": p.get("date", datetime.now().isoformat()),
                }
            temp_data[cid]["clients"].add(p["client_id"])
            temp_data[cid]["volume"] += p["amount"]

        for cid, data in temp_data.items():
            self._corridors[cid] = Corridor(
                corridor_id=cid,
                source_country=data["source"],
                destination_country=data["destination"],
                corridor_name=f"{data['source']} to {data['destination']}",
                is_active=True,
                first_payment_date=data["first_date"],
                last_payment_date=data["last_date"],
                total_clients=len(data["clients"]),
                total_volume_90d=data["volume"],
                total_revenue_90d=data["volume"] * 0.01,  # Est 1% margin
                is_new=False,
            )
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
        # Implementation to detect significant shifts in corridor volume
        return []
