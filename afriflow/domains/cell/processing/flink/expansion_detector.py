"""
@file expansion_detector.py
@description Detects geographic client expansion by analyzing SIM activations across different African markets.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Cell Expansion Detector.

We detect geographic expansion by analyzing SIM
activation patterns across countries. This enables
early identification of client growth opportunities.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for nested data structures and optional parameters
from typing import Dict, List, Optional, Any
# Dataclasses for structured signal output
from dataclasses import dataclass
# Datetime utilities for window-based analysis and timestamp generation
from datetime import datetime, timedelta, timezone
# Standard logging for operational observability and alerting
import logging
# Specialized dictionary for automatic initialization of missing keys
from collections import defaultdict

# BaseProcessor defines the minimal processing interface used across domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config loads environment-aware settings to enforce RBAC and limits
from afriflow.domains.shared.config import get_config

# Module-level logger for structured operational events and incident context
logger = logging.getLogger(__name__)


@dataclass
class ExpansionSignal:
    """
    Structured signal indicating a potential client expansion into a new territory.

    Attributes:
        client_id: Unique identifier for the client entity.
        new_country: ISO code of the newly entered country.
        sim_count: Number of new SIM activations detected.
        confidence: Normalized score (0-100) representing signal strength.
        detected_at: Precise timestamp when the expansion was identified.
    """
    client_id: str
    new_country: str
    sim_count: int
    confidence: float
    detected_at: datetime


class ExpansionDetector:
    """
    Detects geographic expansion from SIM activation trends.
    
    This detector monitors when corporate clients activate a significant number
    of SIM cards in countries where they previously had no footprint.

    Attributes:
        min_sim_threshold: Minimum number of SIMs required to trigger a signal.
        time_window_days: The rolling window period for aggregating activations.
    """

    def __init__(
        self,
        min_sim_threshold: int = 10,
        time_window_days: int = 30
    ) -> None:
        """
        Initializes the expansion detector with configurable thresholds.

        :param min_sim_threshold: Minimum SIM count for a valid signal.
        :param time_window_days: Analysis window in days.
        """
        self.min_sim_threshold = min_sim_threshold
        self.time_window_days = time_window_days

        # Internal state to track activations per client
        self.activations: Dict[str, List[Dict[str, Any]]] = (
            defaultdict(list)
        )

        logger.info(
            f"ExpansionDetector initialized: "
            f"min_sims={min_sim_threshold}, "
            f"window={time_window_days} days"
        )

    def add_activation(
        self,
        client_id: str,
        country: str,
        sim_count: int,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Records a new SIM activation event for a client.

        :param client_id: Identifier of the client.
        :param country: ISO code of the activation country.
        :param sim_count: Number of SIMs activated.
        :param timestamp: Event timestamp (defaults to current UTC time).
        """

        Args:
            client_id: Client identifier
            country: Country of activation
            sim_count: Number of SIMs activated
            timestamp: Activation timestamp
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        self.activations[client_id].append({
            "country": country,
            "sim_count": sim_count,
            "timestamp": timestamp,
        })

        logger.debug(
            f"Added activation: {client_id} - "
            f"{country} ({sim_count} SIMs)"
        )

    def detect_expansion(
        self,
        client_id: str
    ) -> List[ExpansionSignal]:
        """
        Detect expansion for a client.

        Args:
            client_id: Client identifier

        Returns:
            List of ExpansionSignal objects
        """
        if client_id not in self.activations:
            return []

        signals = []
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.time_window_days
        )

        # Group activations by country
        country_sims: Dict[str, int] = defaultdict(int)

        for activation in self.activations[client_id]:
            if activation["timestamp"] >= cutoff:
                country_sims[activation["country"]] += (
                    activation["sim_count"]
                )

        # Identify new countries
        historical_countries = self._get_historical_countries(
            client_id, cutoff
        )

        for country, sim_count in country_sims.items():
            if country not in historical_countries:
                if sim_count >= self.min_sim_threshold:
                    confidence = self._calculate_confidence(
                        sim_count, country
                    )

                    signal = ExpansionSignal(
                        client_id=client_id,
                        new_country=country,
                        sim_count=sim_count,
                        confidence=confidence,
                        detected_at=datetime.now(timezone.utc),
                    )

                    signals.append(signal)

                    logger.info(
                        f"Expansion detected: {client_id} -> "
                        f"{country} ({sim_count} SIMs, "
                        f"{confidence:.0f}% confidence)"
                    )

        return signals

    def _get_historical_countries(
        self,
        client_id: str,
        cutoff: datetime
    ) -> set:
        """
        Get countries with historical presence.

        Args:
            client_id: Client identifier
            cutoff: Cutoff timestamp

        Returns:
            Set of country codes
        """
        countries = set()

        for activation in self.activations[client_id]:
            if activation["timestamp"] < cutoff:
                countries.add(activation["country"])

        return countries

    def _calculate_confidence(
        self,
        sim_count: int,
        country: str
    ) -> float:
        """
        Calculate expansion signal confidence.

        Args:
            sim_count: Number of SIMs
            country: Country code

        Returns:
            Confidence percentage (0-100)
        """
        # Base confidence from SIM count
        base_confidence = min(100, (sim_count / 100) * 100)

        # Adjust for country risk
        high_risk_countries = {"CD", "SS", "SO"}
        if country in high_risk_countries:
            base_confidence *= 0.8

        return min(100, base_confidence)

    def get_client_footprint(
        self,
        client_id: str
    ) -> Dict[str, int]:
        """
        Get client's country footprint.

        Args:
            client_id: Client identifier

        Returns:
            Dictionary of country to SIM count
        """
        footprint: Dict[str, int] = defaultdict(int)

        for activation in self.activations[client_id]:
            footprint[activation["country"]] += (
                activation["sim_count"]
            )

        return dict(footprint)


class Processor(BaseProcessor):
    """
    Minimal processor wrapper enforcing environment-aware RBAC, input size limits,
    and structured error logging. Used for synchronous processing paths.
    """
    def configure(self, config=None) -> None:
        """
        Configure RBAC and size limits based on environment.
        Notes:
        - In staging/prod, restrict to system/service to prevent analyst misuse.
        - Max record size guards against runaway payloads or log flooding.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, required fields, and RBAC authorization.
        Raises:
        - TypeError when payload is not dict-like
        - PermissionError for unauthorized roles
        - ValueError for missing source or oversized payload
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
        role = record.get("access_role")
        src = record.get("source")
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Synchronous processing wrapper with error logging and re-raise behavior.
        Returns a shallow copy with a 'processed' marker on success.
        Edge cases:
        - Any validation failure is logged with structured context and re-raised.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise

if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    detector = ExpansionDetector(min_sim_threshold=10)

    # Add activations
    detector.add_activation("CLIENT-001", "ZA", 50)
    detector.add_activation("CLIENT-001", "NG", 100)
    detector.add_activation("CLIENT-001", "KE", 25)

    # Detect expansion
    signals = detector.detect_expansion("CLIENT-001")
    for signal in signals:
        print(
            f"Expansion: {signal.client_id} -> "
            f"{signal.new_country} "
            f"({signal.sim_count} SIMs, "
            f"{signal.confidence:.0f}%)"
        )
