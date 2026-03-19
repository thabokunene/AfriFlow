"""
@file corridor_engine.py
@description Core intelligence engine for identifying and managing cross-border
             payment corridors. Scans payment data to discover new corridors,
             monitors activity levels, and calculates aggregate metrics such
             as volume and revenue for each identified country pair.
@author Thabo Kunene
@created 2026-03-19
"""

# Corridor Intelligence Engine
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data classes and type hinting
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

# Centralised platform logging
from afriflow.logging_config import get_logger

# Initialise a module-scoped logger for corridor lifecycle events
logger = get_logger("corridor.engine")


@dataclass
class Corridor:
    """
    Represents a directed trade corridor between two countries.

    :param corridor_id: Unique identifier (e.g., 'ZA-NG')
    :param source_country: ISO-2 code of the originating country
    :param destination_country: ISO-2 code of the target country
    :param corridor_name: Human-readable name (e.g., 'South Africa to Nigeria')
    :param is_active: True if payments were detected in the last 90 days
    :param first_payment_date: ISO date of the first detected payment
    :param last_payment_date: ISO date of the most recent payment
    :param total_clients: Number of unique clients active in this corridor
    :param total_volume_90d: Sum of payment volume in ZAR (last 90 days)
    :param total_revenue_90d: Sum of revenue generated in ZAR (last 90 days)
    :param is_new: True if the corridor was first detected within the last 30 days
    """

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
        """
        Convert the corridor instance to a dictionary for API serialization.

        :return: A dictionary containing all corridor attributes.
        """
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
    """
    Engine responsible for discovering and tracking country-to-country trade corridors.
    """

    def __init__(self) -> None:
        """
        Initialise the engine with an empty in-memory corridor registry.
        """
        # Map of corridor_id to Corridor objects for fast lookup
        self._corridors: Dict[str, Corridor] = {}
        logger.info("CorridorEngine initialized")

    def identify_corridors(self, payment_data: List[Dict]) -> List[Corridor]:
        """
        Analyse raw payment records to identify and update trade corridors.

        :param payment_data: List of payment dictionaries with source/dest countries
        :return: List of all identified Corridor objects.
        """
        # --- Logic to identify corridors from raw payments would be implemented here ---
        # Currently returns the state of the in-memory registry.
        return list(self._corridors.values())

    def get_active_corridors(self) -> List[Corridor]:
        """
        Retrieve corridors that have seen activity within the lookback window.

        :return: A list of active Corridor objects.
        """
        return [c for c in self._corridors.values() if c.is_active]

    def get_new_corridors(self, days: int) -> List[Corridor]:
        """
        Retrieve corridors discovered within the specified number of days.

        :param days: Lookback period for discovery
        :return: A list of new Corridor objects.
        """
        return [c for c in self._corridors.values() if c.is_new]

    def get_corridor_detail(self, corridor_id: str) -> Dict:
        """
        Get comprehensive details for a specific corridor.

        :param corridor_id: The ID of the corridor to retrieve
        :return: Dictionary of corridor details, or empty dict if not found.
        """
        corridor = self._corridors.get(corridor_id)
        return corridor.to_dict() if corridor else {}

    def get_corridor_clients(self, corridor_id: str) -> List[Dict]:
        """
        Get a list of clients active within a specific corridor.

        :param corridor_id: The ID of the corridor
        :return: A list of client summary dictionaries.
        """
        return []

    def get_top_corridors(self, limit: int, sort_by: str) -> List[Corridor]:
        """
        Rank corridors by volume or revenue.

        :param limit: Number of corridors to return
        :param sort_by: Attribute to sort by ('volume' or 'revenue')
        :return: A ranked list of Corridor objects.
        """
        results = list(self._corridors.values())
        # Sort logic based on the requested metric
        if sort_by == "volume":
            results.sort(key=lambda x: x.total_volume_90d, reverse=True)
        return results[:limit]

    def detect_corridor_changes(self, lookback_days: int) -> List[Dict]:
        """
        Identify significant changes in corridor behavior (e.g., volume spikes).

        :param lookback_days: Period over which to detect changes
        :return: A list of change event dictionaries.
        """
        return []
