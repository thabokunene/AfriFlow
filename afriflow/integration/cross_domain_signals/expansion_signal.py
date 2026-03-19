"""
@file expansion_signal.py
@description Cross-domain geographic expansion detection engine, identifying
    new market entry by combining corroborating signals from CIB, Cell, Forex,
    Insurance, and PBB domains.
@author Thabo Kunene
@created 2026-03-19
"""

# Allow forward references in type hints (e.g. Optional["ExpansionSignal"])
from __future__ import annotations

# Standard-library imports
from dataclasses import dataclass          # Typed result containers
from typing import Dict, List, Optional, Any  # Type annotations
from collections import defaultdict        # Auto-initialising corridor dicts

# AfriFlow internal imports
from afriflow.config.settings import (
    Settings,            # Top-level configuration object
    ExpansionThresholds, # Domain-specific evidence thresholds
)
from afriflow.config.loader import get_settings          # Global settings loader
from afriflow.exceptions import SignalDetectionError, ConfigurationError  # Custom errors
from afriflow.logging_config import get_logger           # Centralised logger factory

# Module-scoped logger — all log lines from this module share the same name
logger = get_logger("cross_domain_signals.expansion")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExpansionSignal:
    """A detected expansion signal for a client."""

    # The golden-record identifier linking this signal back to the client
    golden_id: str
    # Resolved canonical client name
    client_name: str
    # ISO 3166-1 alpha-2 country code of the expansion destination
    expansion_country: str
    # Confidence score 0–99; signals below 40 are discarded before creation
    confidence_score: float
    # Estimated annual revenue opportunity in South African Rand
    estimated_opportunity_zar: float

    # --- Evidence counts (each contributes to the confidence score) ---
    cib_new_corridor_payments: int   # Number of distinct payment events to this country
    cib_corridor_value: float        # Total ZAR value of those payments
    cell_new_sim_activations: int    # Number of new corporate SIM activations
    forex_new_currency_trades: int   # Number of FX trades for this country's currency
    insurance_new_countries: int     # New insurance policies in this country
    pbb_new_countries: int           # New payroll accounts in this country

    # --- Gap flags (True = already covered; False = revenue opportunity) ---
    forex_hedging_in_place: bool     # Whether FX hedging is already active
    insurance_coverage_in_place: bool  # Whether insurance coverage exists

    # Ordered list of recommended product pitches for the RM
    recommended_products: List[str]
    # Urgency classification: "HIGH" (≥80 confidence) or "MEDIUM" otherwise
    urgency: str

    def to_rm_alert(self) -> Dict:
        """
        Convert to RM alert format suitable for CRM or notification systems.

        :return: Dict with Subject, Body, Priority, OwnerId, Country,
                 Confidence, and OpportunityValue keys
        """
        return {
            "Subject": f"Expansion Alert: {self.client_name} - {self.expansion_country}",
            "Body": (
                f"Client {self.client_name} is expanding into "
                f"{self.expansion_country}. Confidence: {self.confidence_score:.0f}%. "
                f"Estimated opportunity: R{self.estimated_opportunity_zar:,.0f}"
            ),
            # Urgent threshold at 80 to prioritise the highest-confidence alerts
            "Priority": "Urgent" if self.confidence_score >= 80 else "High",
            "OwnerId": self.golden_id,
            "Country": self.expansion_country,
            "Confidence": self.confidence_score,
            "OpportunityValue": self.estimated_opportunity_zar,
        }


# ---------------------------------------------------------------------------
# Detection engine
# ---------------------------------------------------------------------------

class ExpansionDetector:
    """
    Detects geographic expansion by combining cross-domain signals.

    A single domain signal is weak evidence; multiple corroborating signals
    produce high-confidence alerts. The detector uses configurable thresholds
    to determine when evidence is sufficient for signal generation.

    Evidence Sources:
        - CIB: New payment corridors to foreign countries
        - Cell: New SIM activations in new countries
        - Forex: New currency hedging for expansion countries
        - Insurance: New country coverage
        - PBB: New payroll accounts in expansion countries

    Attributes:
        settings: Configuration settings object
        thresholds: Expansion detection thresholds from config
        _cib_payments: Cached CIB payment events by client ID
        _cell_activations: Cached cell activation events by client ID
        _forex_trades: Cached forex trade events by client ID
        _client_metadata: Client metadata cache

    Example:
        >>> detector = ExpansionDetector()
        >>> detector.ingest_cib_payment(payment_data)
        >>> detector.ingest_cell_activation(activation_data)
        >>> signals = detector.detect_expansions(client_metadata)
    """

    # Static mapping used to correlate forex currency codes with country codes
    # when determining whether a forex trade covers an expansion destination
    CURRENCY_COUNTRY_MAP: Dict[str, str] = {
        "ZAR": "ZA", "NGN": "NG", "KES": "KE", "GHS": "GH",
        "TZS": "TZ", "UGX": "UG", "ZMW": "ZM", "MZN": "MZ",
        "CDF": "CD", "XAF": "CM", "XOF": "CI", "MUR": "MU",
    }

    def __init__(
        self,
        settings: Optional[Settings] = None
    ) -> None:
        """
        Initialize the expansion detector with configuration.

        Args:
            settings: Optional Settings object. If not provided,
                     loads from global configuration.

        Raises:
            ConfigurationError: If settings cannot be loaded

        Example:
            >>> detector = ExpansionDetector()
            >>> detector.thresholds.min_cib_payments_for_signal
            3
        """
        try:
            # Use injected settings if provided; otherwise load from config file
            self.settings = settings if settings is not None else get_settings()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            raise ConfigurationError(
                f"Failed to load expansion detector settings: {e}"
            ) from e

        # Pull typed expansion thresholds from the loaded settings
        self.thresholds: ExpansionThresholds = self.settings.expansion_thresholds

        logger.debug(
            "ExpansionDetector initialized with thresholds: "
            f"min_cib_payments={self.thresholds.min_cib_payments_for_signal}, "
            f"min_cib_value={self.thresholds.min_cib_value_for_signal}, "
            f"min_sim_activations={self.thresholds.min_sim_activations_for_signal}"
        )

        # In-memory event stores: keyed by client ID for O(1) lookup
        self._cib_payments: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._cell_activations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._forex_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Client metadata cache populated by the caller before detect_expansions()
        self._client_metadata: Dict[str, Dict[str, Any]] = {}

    def ingest_cib_payment(
        self,
        payment: Dict[str, Any]
    ) -> None:
        """
        Ingest a CIB payment event for expansion detection.

        Args:
            payment: CIB payment event with debtor_client_id and
                    creditor_country fields

        Example:
            >>> detector = ExpansionDetector()
            >>> detector.ingest_cib_payment({
            ...     "debtor_client_id": "CIB-001",
            ...     "creditor_country": "KE",
            ...     "amount": 1000000
            ... })
        """
        # Index by debtor_client_id so corridor lookups are O(1)
        client_id = payment.get("debtor_client_id")
        if client_id:
            self._cib_payments[client_id].append(payment)
            logger.debug(
                f"Ingested CIB payment for client {client_id} "
                f"to {payment.get('creditor_country')}"
            )

    def ingest_cell_activation(
        self,
        activation: Dict[str, Any]
    ) -> None:
        """
        Ingest a cell SIM activation event for expansion detection.

        Args:
            activation: Cell activation event with corporate_client_id
                       and activation_country fields

        Example:
            >>> detector = ExpansionDetector()
            >>> detector.ingest_cell_activation({
            ...     "corporate_client_id": "CIB-001",
            ...     "activation_country": "KE",
            ...     "sim_count": 50
            ... })
        """
        # Index by corporate_client_id to correlate with CIB records
        client_id = activation.get("corporate_client_id")
        if client_id:
            self._cell_activations[client_id].append(activation)
            logger.debug(
                f"Ingested cell activation for client {client_id} "
                f"in {activation.get('activation_country')}"
            )

    def ingest_forex_trade(
        self,
        trade: Dict[str, Any]
    ) -> None:
        """
        Ingest a forex trade event for expansion detection.

        Args:
            trade: Forex trade event with client_id and target_currency
        """
        # Index by client_id to correlate with CIB corridor data
        client_id = trade.get("client_id")
        if client_id:
            self._forex_trades[client_id].append(trade)
            logger.debug(
                f"Ingested forex trade for client {client_id} "
                f"in {trade.get('target_currency')}"
            )

    def detect_expansions(
        self,
        client_metadata: Dict[str, Dict[str, Any]],
        home_country: str = "ZA",
        lookback_days: int = 90,
    ) -> List[ExpansionSignal]:
        """
        Detect expansion signals for all clients with ingested data.

        Args:
            client_metadata: Dictionary mapping client IDs to metadata
            home_country: Home country code to exclude from expansion
                         (default: "ZA" for South Africa)
            lookback_days: Number of days to look back for signals
                          (currently informational only)

        Returns:
            List of ExpansionSignal objects sorted by confidence score
            (highest first)

        Raises:
            SignalDetectionError: If detection fails

        Example:
            >>> detector = ExpansionDetector()
            >>> # Ingest events...
            >>> signals = detector.detect_expansions(client_metadata)
            >>> len(signals)
            1
        """
        try:
            signals: List[ExpansionSignal] = []
            # Only evaluate clients for whom we have CIB payment data
            all_clients = set(self._cib_payments.keys())

            for client_id in all_clients:
                client_info = client_metadata.get(client_id, {})
                # Delegate per-client logic to the private helper
                client_signals = self._detect_client_expansion(
                    client_id, client_info, home_country
                )
                signals.extend(client_signals)

            # Return highest-confidence signals first for briefing prioritisation
            return sorted(
                signals,
                key=lambda s: s.confidence_score,
                reverse=True,
            )
        except Exception as e:
            logger.error(f"Expansion detection failed: {e}")
            raise SignalDetectionError(
                f"Expansion detection failed: {e}"
            ) from e

    def _detect_client_expansion(
        self,
        client_id: str,
        client_info: Dict[str, Any],
        home_country: str,
    ) -> List[ExpansionSignal]:
        """
        Detect expansion signals for a single client.

        Args:
            client_id: Client identifier
            client_info: Client metadata (tier, name, etc.)
            home_country: Home country to exclude

        Returns:
            List of expansion signals for this client
        """
        signals: List[ExpansionSignal] = []

        # Build payment corridors excluding the client's home country
        cib_corridors = self._get_cib_corridors(
            client_id, home_country
        )

        for country, cib_data in cib_corridors.items():
            # Evaluate all evidence for this country
            signal = self._evaluate_expansion_evidence(
                client_id,
                client_info,
                country,
                cib_data,
            )
            # Only include signals that meet the minimum confidence threshold
            if signal and signal.confidence_score >= self.thresholds.min_cib_payments_for_signal:
                signals.append(signal)

        return signals

    def _get_cib_corridors(
        self,
        client_id: str,
        home_country: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get CIB payment corridors for a client excluding home country.

        Args:
            client_id: Client identifier
            home_country: Home country to exclude from results

        Returns:
            Dictionary mapping country codes to payment statistics
            (count and total value)
        """
        # defaultdict auto-initialises missing country entries
        corridors: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"payments": 0, "value": 0.0}
        )

        for payment in self._cib_payments.get(client_id, []):
            creditor_country = payment.get("creditor_country")
            # Skip domestic payments — they are not evidence of expansion
            if creditor_country and creditor_country != home_country:
                corridors[creditor_country]["payments"] += 1
                corridors[creditor_country]["value"] += payment.get(
                    "amount", 0.0
                )

        return dict(corridors)

    def _evaluate_expansion_evidence(
        self,
        client_id: str,
        client_info: Dict,
        country: str,
        cib_data: Dict,
    ) -> Optional[ExpansionSignal]:
        """Evaluate expansion evidence for a country."""
        # Extract raw payment count and corridor value from the CIB aggregate
        cib_payments = cib_data["payments"]
        cib_value = cib_data["value"]

        # Get cell activations for this country
        cell_activations = [
            a for a in self._cell_activations.get(client_id, [])
            if a.get("activation_country") == country
        ]
        # Sum SIM count across all activation events for this country
        sim_count = sum(
            a.get("sim_count", 0) for a in cell_activations
        )

        # Get forex trades for this country's currency
        forex_trades = self._get_forex_trades_for_country(
            client_id, country
        )
        # Any forex trade for this currency = forex domain is engaged
        has_forex = len(forex_trades) > 0
        # is_hedge flag distinguishes hedging trades from speculative trades
        is_hedged = any(
            t.get("is_hedge", False) for t in forex_trades
        )

        # Check insurance (simplified - assume not in place for demo)
        has_insurance = False

        # Calculate the composite confidence score
        confidence = self._calculate_confidence(
            cib_payments=cib_payments,
            cib_value=cib_value,
            sim_activations=sim_count,
            has_forex=has_forex,
            has_insurance=has_insurance,
            has_pbb=False,  # PBB ingestion not yet wired in this version
        )

        # Discard low-confidence signals to reduce RM noise
        if confidence < 40:
            return None

        # Estimate the revenue opportunity in ZAR
        opportunity = self._estimate_opportunity(
            client_info=client_info,
            country=country,
            cib_value=cib_value,
            has_hedge=is_hedged,
            has_insurance=has_insurance,
            employee_count=0,  # Employee count not yet available in this path
        )

        # Build the recommended product list based on detected gaps
        products = []
        if not is_hedged:
            # FX gap: client has no forward cover for this currency
            products.append("FX hedging solution")
            products.append("Forward contract")
        if not has_insurance:
            # Insurance gap: client operates in this country without coverage
            products.append("Trade credit insurance")
            products.append("Asset coverage review")
        # Working capital is universally relevant for expansion markets
        products.append("Working capital facility")

        return ExpansionSignal(
            golden_id=client_id,
            client_name=client_info.get("client_name", "Unknown"),
            expansion_country=country,
            confidence_score=confidence,
            estimated_opportunity_zar=opportunity,
            cib_new_corridor_payments=cib_payments,
            cib_corridor_value=cib_value,
            cell_new_sim_activations=sim_count,
            forex_new_currency_trades=len(forex_trades),
            insurance_new_countries=0,
            pbb_new_countries=0,
            forex_hedging_in_place=is_hedged,
            insurance_coverage_in_place=has_insurance,
            recommended_products=products,
            urgency="HIGH" if confidence >= 80 else "MEDIUM",
        )

    def _get_forex_trades_for_country(
        self,
        client_id: str,
        country: str,
    ) -> List[Dict]:
        """Get forex trades for a country's currency."""
        # Map ISO country codes to their primary trading currencies
        currency_map = {
            "ZA": "ZAR", "NG": "NGN", "KE": "KES",
            "GH": "GHS", "TZ": "TZS", "UG": "UGX",
            "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
        }
        # Derive expected currency from the country code
        target_currency = currency_map.get(country)

        trades = []
        for trade in self._forex_trades.get(client_id, []):
            # Only include trades targeting the expansion country's currency
            if trade.get("target_currency") == target_currency:
                trades.append(trade)
        return trades

    def _calculate_confidence(
        self,
        cib_payments: int,
        cib_value: float,
        sim_activations: int,
        has_forex: bool,
        has_insurance: bool,
        has_pbb: bool,
    ) -> float:
        """
        Calculate confidence score from evidence.

        Score is capped at 99 (never 100) to signal that cross-domain
        evidence is probabilistic, not deterministic.

        :return: Confidence score in [0, 99]
        """
        score = 0.0

        # CIB contribution (max 40 points)
        # Payment count earns 20 points if it clears the minimum threshold
        if cib_payments >= self.thresholds.min_cib_payments_for_signal:
            score += 20
        # Payment value earns up to 20 additional points scaled by ZAR value
        if cib_value >= self.thresholds.min_cib_value_for_signal:
            score += min(20, cib_value / 500_000)

        # Cell contribution (max 25 points)
        # Full 25 points if SIM count clears the threshold
        if sim_activations >= self.thresholds.min_sim_activations_for_signal:
            score += 25
        elif sim_activations > 0:
            # Partial credit for sub-threshold activations (some presence)
            score += min(15, sim_activations / 2)

        # Forex contribution (max 15 points)
        if has_forex:
            score += 15

        # Insurance contribution (max 10 points)
        if has_insurance:
            score += 10

        # PBB contribution (max 10 points)
        if has_pbb:
            score += 10

        # Cap at 99 to preserve the probabilistic interpretation
        return min(99, score)

    def _estimate_opportunity(
        self,
        client_info: Dict,
        country: str,
        cib_value: float,
        has_hedge: bool,
        has_insurance: bool,
        employee_count: int,
    ) -> float:
        """
        Estimate revenue opportunity in ZAR.

        Fee rates are higher for lower tiers because Platinum clients
        have negotiated tighter spreads and require less uplift.

        :return: Estimated annual revenue opportunity in ZAR
        """
        tier = client_info.get("tier", "Bronze")

        # Base transaction fee rate by relationship tier
        fee_rates = {
            "Platinum": 0.005,   # Tightest spreads for top-tier clients
            "Gold": 0.008,
            "Silver": 0.010,
            "Bronze": 0.012,     # Standard rate for newer / smaller clients
        }
        base_rate = fee_rates.get(tier, 0.012)

        opportunity = 0.0

        # CIB corridor fees: earned on payment flow volume
        opportunity += cib_value * base_rate

        # FX spread opportunity: only available if client is not already hedged
        if not has_hedge:
            opportunity += cib_value * 0.003

        # Insurance premium opportunity: only available if client is uninsured
        if not has_insurance:
            opportunity += cib_value * 0.002

        # Payroll opportunity: R2 500 per employee per annum is a rough estimate
        opportunity += employee_count * 2500

        return opportunity
