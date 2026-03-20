"""
@file corridor_engine.py
@description Corridor Intelligence Engine - Cross-border payment corridor identification and management
@author Thabo Kunene
@created 2026-03-19

This module identifies and maps payment corridors between countries based on
cross-border transaction patterns. It tracks corridor activity, client participation,
and revenue generation.

Key Classes:
- Corridor: Data model for a payment corridor between two countries
- CorridorEngine: Main engine for corridor identification and management

Features:
- Automatic corridor identification from payment data
- Corridor activity tracking (volume, clients, revenue)
- New corridor detection (first payment in 90 days)
- Corridor statistics and health monitoring

Usage:
    >>> from afriflow.corridor.corridor_engine import CorridorEngine
    >>> engine = CorridorEngine()
    >>> payments = [
    ...     {"source": "ZA", "destination": "NG", "amount": 1000000, "client_id": "C001"},
    ...     {"source": "ZA", "destination": "NG", "amount": 500000, "client_id": "C002"}
    ... ]
    >>> corridors = engine.identify_corridors(payments)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Standard library imports
from dataclasses import dataclass  # For data class decorator
from typing import Dict, List, Optional, Any  # Type hints for dictionaries, lists, optional values
import logging  # For debug and info logging
from datetime import datetime  # For timestamp generation and date comparisons

# Import logging utility for structured logging
from afriflow.logging_config import get_logger

logger = get_logger("corridor.engine")  # Get logger instance for this module


@dataclass
class Corridor:
    """
    Payment corridor between two countries.

    Represents a cross-border payment route with aggregated
    statistics about client activity, volume, and revenue.

    Attributes:
        corridor_id: Unique identifier (format: "SOURCE-DEST", e.g., "ZA-NG")
        source_country: Source country code (ISO 3166-1 alpha-2)
        destination_country: Destination country code
        corridor_name: Human-readable name (e.g., "South Africa to Nigeria")
        is_active: Whether corridor has recent activity (last 90 days)
        first_payment_date: Date of first payment on this corridor
        last_payment_date: Date of most recent payment
        total_clients: Number of unique clients using this corridor
        total_volume_90d: Total payment volume in last 90 days (ZAR)
        total_revenue_90d: Total revenue generated in last 90 days (ZAR)
        is_new: Whether this is a newly discovered corridor (<90 days old)

    Example:
        >>> corridor = Corridor(
        ...     corridor_id="ZA-NG",
        ...     source_country="ZA",
        ...     destination_country="NG",
        ...     corridor_name="South Africa to Nigeria",
        ...     is_active=True,
        ...     total_clients=15,
        ...     total_volume_90d=50000000.0
        ... )
    """
    corridor_id: str  # Unique corridor identifier (e.g., "ZA-NG")
    source_country: str  # Source country code
    destination_country: str  # Destination country code
    corridor_name: str  # Human-readable corridor name
    is_active: bool  # Active status (recent activity)
    first_payment_date: str  # First payment date (ISO 8601)
    last_payment_date: str  # Last payment date (ISO 8601)
    total_clients: int  # Number of unique clients
    total_volume_90d: float  # Volume in last 90 days (ZAR)
    total_revenue_90d: float  # Revenue in last 90 days (ZAR)
    is_new: bool  # New corridor flag

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert corridor to dictionary for JSON serialization.

        This method enables easy serialization for API responses
        and database storage.

        Returns:
            Dictionary with all corridor fields
        """
        return {
            "corridor_id": self.corridor_id,  # Unique ID
            "source_country": self.source_country,  # Source country
            "destination_country": self.destination_country,  # Destination
            "corridor_name": self.corridor_name,  # Readable name
            "is_active": self.is_active,  # Active status
            "first_payment_date": self.first_payment_date,  # First payment
            "last_payment_date": self.last_payment_date,  # Last payment
            "total_clients": self.total_clients,  # Client count
            "total_volume_90d": self.total_volume_90d,  # 90d volume
            "total_revenue_90d": self.total_revenue_90d,  # 90d revenue
            "is_new": self.is_new,  # New corridor flag
        }


class CorridorEngine:
    """
    Corridor identification and management engine.

    This class processes raw payment data to identify and track
    payment corridors between countries. It aggregates statistics
    and detects new corridors for business development.

    Features:
    - Automatic corridor identification from payments
    - Client and volume tracking per corridor
    - Activity status monitoring (active/inactive)
    - New corridor detection

    Attributes:
        _corridors: Dictionary mapping corridor_id to Corridor objects

    Example:
        >>> engine = CorridorEngine()
        >>> payments = [
        ...     {"source": "ZA", "destination": "NG", "amount": 1000000, "client_id": "C001"},
        ...     {"source": "ZA", "destination": "NG", "amount": 500000, "client_id": "C002"}
        ... ]
        >>> corridors = engine.identify_corridors(payments)
    """

    def __init__(self) -> None:
        """
        Initialize the corridor engine with empty corridor store.

        Creates an empty dictionary for storing identified corridors.
        In production, this would connect to a database for persistence.
        """
        self._corridors: Dict[str, Corridor] = {}  # Corridor storage
        logger.info("CorridorEngine initialized")  # Log initialization

    def identify_corridors(
        self,
        payment_data: List[Dict]
    ) -> List[Corridor]:
        """
        Groups raw payments into corridors and calculates statistics.

        This method processes a list of payment records and aggregates
        them into corridors based on source-destination pairs. It tracks
        client participation, total volume, and date ranges.

        Args:
            payment_data: List of payment dictionaries with format:
                {
                    'source': 'ZA',  # Source country code
                    'destination': 'NG',  # Destination country code
                    'amount': 1000.0,  # Payment amount in ZAR
                    'client_id': 'C001',  # Client identifier
                    'date': '2026-03-19'  # Optional payment date
                }

        Returns:
            List of identified Corridor objects

        Example:
            >>> payments = [
            ...     {"source": "ZA", "destination": "NG", "amount": 1000000, "client_id": "C001"},
            ...     {"source": "ZA", "destination": "NG", "amount": 500000, "client_id": "C002"}
            ... ]
            >>> corridors = engine.identify_corridors(payments)
            >>> print(f"Found {len(corridors)} corridors")
        """
        # Temporary data structure for aggregating payments
        # Key: corridor_id (e.g., "ZA-NG"), Value: aggregated data
        temp_data: Dict[str, Any] = {}

        # Process each payment record
        for p in payment_data:
            # Create corridor ID from source-destination pair
            cid = f"{p['source']}-{p['destination']}"

            # Initialize corridor data if first time seeing this route
            if cid not in temp_data:
                temp_data[cid] = {
                    "source": p["source"],  # Source country
                    "destination": p["destination"],  # Destination country
                    "clients": set(),  # Unique client IDs (set prevents duplicates)
                    "volume": 0.0,  # Cumulative volume
                    "first_date": p.get("date", datetime.now().isoformat()),  # First payment date
                    "last_date": p.get("date", datetime.now().isoformat()),  # Last payment date
                }

            # Add client to set (automatically handles uniqueness)
            temp_data[cid]["clients"].add(p["client_id"])

            # Accumulate payment volume
            temp_data[cid]["volume"] += p["amount"]

            # Update last payment date if this payment is more recent
            current_date = p.get("date", datetime.now().isoformat())
            if current_date > temp_data[cid]["last_date"]:
                temp_data[cid]["last_date"] = current_date

        # Convert aggregated data to Corridor objects
        for cid, data in temp_data.items():
            # Determine if corridor is new (first time seeing it)
            is_new_corridor = cid not in self._corridors

            # Create Corridor object with aggregated statistics
            self._corridors[cid] = Corridor(
                corridor_id=cid,  # Unique identifier
                source_country=data["source"],  # Source country
                destination_country=data["destination"],  # Destination
                corridor_name=f"{data['source']} to {data['destination']}",  # Readable name
                is_active=True,  # Mark as active (just saw payments)
                first_payment_date=(
                    data["first_date"] if is_new_corridor
                    else self._corridors[cid].first_payment_date
                ),  # Preserve original first date
                last_payment_date=data["last_date"],  # Most recent payment
                total_clients=len(data["clients"]),  # Count unique clients
                total_volume_90d=data["volume"],  # Total volume
                total_revenue_90d=data["volume"] * 0.001,  # Estimate: 0.1% revenue
                is_new=is_new_corridor,  # New corridor flag
            )

        logger.info(
            f"Identified {len(temp_data)} corridors from {len(payment_data)} payments"
        )

        # Return list of all identified corridors
        return list(self._corridors.values())

    def get_corridor(self, corridor_id: str) -> Optional[Corridor]:
        """
        Retrieve a specific corridor by ID.

        Args:
            corridor_id: Corridor identifier (e.g., "ZA-NG")

        Returns:
            Corridor object if found, None otherwise

        Example:
            >>> corridor = engine.get_corridor("ZA-NG")
            >>> if corridor:
            ...     print(f"Volume: {corridor.total_volume_90d}")
        """
        return self._corridors.get(corridor_id)

    def get_all_corridors(self) -> List[Corridor]:
        """
        Get all identified corridors.

        Returns:
            List of all Corridor objects
        """
        return list(self._corridors.values())

    def get_active_corridors(self) -> List[Corridor]:
        """
        Get only active corridors (with recent activity).

        Returns:
            List of active Corridor objects
        """
        return [c for c in self._corridors.values() if c.is_active]

    def get_new_corridors(self) -> List[Corridor]:
        """
        Get newly discovered corridors (first payment in 90 days).

        Returns:
            List of new Corridor objects
        """
        return [c for c in self._corridors.values() if c.is_new]

    def get_corridor_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all corridors.

        Returns:
            Dictionary with corridor statistics
        """
        if not self._corridors:
            return {
                "total_corridors": 0,
                "active_corridors": 0,
                "new_corridors": 0,
                "total_volume": 0.0,
                "total_revenue": 0.0,
            }

        # Calculate aggregate metrics
        total_volume = sum(c.total_volume_90d for c in self._corridors.values())
        total_revenue = sum(c.total_revenue_90d for c in self._corridors.values())
        active_count = sum(1 for c in self._corridors.values() if c.is_active)
        new_count = sum(1 for c in self._corridors.values() if c.is_new)

        return {
            "total_corridors": len(self._corridors),
            "active_corridors": active_count,
            "new_corridors": new_count,
            "total_volume": total_volume,
            "total_revenue": total_revenue,
            "avg_volume_per_corridor": total_volume / len(self._corridors),
        }


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.corridor.corridor_engine import *'

__all__ = [
    # Corridor data model
    "Corridor",
    # Main corridor engine class
    "CorridorEngine",
]
