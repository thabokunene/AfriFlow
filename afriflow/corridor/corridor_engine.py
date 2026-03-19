"""
Corridor Engine

Identifies and maps payment corridors between countries
based on cross-border transaction patterns.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.engine")


@dataclass
class Corridor:
    """A payment corridor between two countries."""
    corridor_id: str
    source_country: str
    destination_country: str
    client_id: Optional[str]
    client_name: Optional[str]
    first_detected: datetime
    last_activity: datetime
    total_volume: float = 0.0
    transaction_count: int = 0
    domains_active: List[str] = field(default_factory=list)
    status: str = "active"
    leakage_detected: bool = False
    estimated_leakage: float = 0.0

    @property
    def name(self) -> str:
        """Human-readable corridor name."""
        return f"{self.source_country} > {self.destination_country}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "corridor_id": self.corridor_id,
            "source_country": self.source_country,
            "destination_country": self.destination_country,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "name": self.name,
            "first_detected": self.first_detected.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "total_volume": self.total_volume,
            "transaction_count": self.transaction_count,
            "domains_active": self.domains_active,
            "status": self.status,
            "leakage_detected": self.leakage_detected,
            "estimated_leakage": self.estimated_leakage,
        }


class CorridorEngine:
    """
    Corridor identification and management.

    Identifies corridors from transaction patterns and
    maintains corridor state.
    """

    def __init__(self):
        self._corridors: Dict[str, Corridor] = {}
        self._client_corridors: Dict[str, List[str]] = {}
        self._country_corridors: Dict[str, List[str]] = {}

        logger.info("CorridorEngine initialized")

    def identify_corridor(
        self,
        source_country: str,
        destination_country: str,
        client_id: Optional[str] = None,
        client_name: Optional[str] = None,
        volume: float = 0.0,
        domain: Optional[str] = None,
    ) -> Corridor:
        """
        Identify or update a corridor.

        Args:
            source_country: Source country code
            destination_country: Destination country code
            client_id: Optional client identifier
            client_name: Optional client name
            volume: Transaction volume
            domain: Domain this was detected in

        Returns:
            Corridor object
        """
        corridor_id = self._generate_corridor_id(
            source_country, destination_country, client_id
        )

        now = datetime.now()

        if corridor_id in self._corridors:
            # Update existing corridor
            corridor = self._corridors[corridor_id]
            corridor.total_volume += volume
            corridor.transaction_count += 1
            corridor.last_activity = now

            if domain and domain not in corridor.domains_active:
                corridor.domains_active.append(domain)
        else:
            # Create new corridor
            corridor = Corridor(
                corridor_id=corridor_id,
                source_country=source_country,
                destination_country=destination_country,
                client_id=client_id,
                client_name=client_name,
                first_detected=now,
                last_activity=now,
                total_volume=volume,
                transaction_count=1,
                domains_active=[domain] if domain else [],
            )

            self._corridors[corridor_id] = corridor

            # Update indexes
            if client_id:
                if client_id not in self._client_corridors:
                    self._client_corridors[client_id] = []
                self._client_corridors[client_id].append(corridor_id)

            if source_country not in self._country_corridors:
                self._country_corridors[source_country] = []
            self._country_corridors[source_country].append(corridor_id)

        logger.debug(
            f"Corridor identified/updated: {corridor.name}"
        )

        return corridor

    def get_corridor(self, corridor_id: str) -> Optional[Corridor]:
        """Get corridor by ID."""
        return self._corridors.get(corridor_id)

    def get_corridors_for_client(
        self, client_id: str
    ) -> List[Corridor]:
        """Get all corridors for a client."""
        corridor_ids = self._client_corridors.get(client_id, [])
        return [
            self._corridors[cid]
            for cid in corridor_ids
            if cid in self._corridors
        ]

    def get_corridors_for_country(
        self, country: str
    ) -> List[Corridor]:
        """Get all corridors involving a country."""
        corridor_ids = self._country_corridors.get(country, [])
        return [
            self._corridors[cid]
            for cid in corridor_ids
            if cid in self._corridors
        ]

    def get_all_corridors(self) -> List[Corridor]:
        """Get all corridors."""
        return list(self._corridors.values())

    def mark_leakage(
        self,
        corridor_id: str,
        estimated_leakage: float,
    ) -> None:
        """Mark a corridor as having detected leakage."""
        corridor = self.get_corridor(corridor_id)
        if not corridor:
            raise ValueError(f"Corridor {corridor_id} not found")

        corridor.leakage_detected = True
        corridor.estimated_leakage = estimated_leakage

        logger.warning(
            f"Leakage detected on corridor {corridor.name}: "
            f"{estimated_leakage}"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get corridor statistics."""
        total_volume = sum(
            c.total_volume for c in self._corridors.values()
        )
        total_transactions = sum(
            c.transaction_count for c in self._corridors.values()
        )
        leakage_corridors = sum(
            1 for c in self._corridors.values()
            if c.leakage_detected
        )
        total_leakage = sum(
            c.estimated_leakage for c in self._corridors.values()
            if c.leakage_detected
        )

        return {
            "total_corridors": len(self._corridors),
            "total_volume": total_volume,
            "total_transactions": total_transactions,
            "avg_volume_per_corridor": (
                total_volume / len(self._corridors)
                if self._corridors else 0
            ),
            "leakage_corridors": leakage_corridors,
            "total_leakage": total_leakage,
            "clients_with_corridors": len(self._client_corridors),
            "countries_involved": len(self._country_corridors),
        }

    def _generate_corridor_id(
        self,
        source: str,
        destination: str,
        client_id: Optional[str],
    ) -> str:
        """Generate unique corridor ID."""
        import uuid

        if client_id:
            return f"COR-{client_id}-{source}-{destination}"
        else:
            return f"COR-{source}-{destination}-{uuid.uuid4().hex[:8]}"
