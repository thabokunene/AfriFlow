"""
integration/cross_domain_signals/expansion_signal.py

Cross-domain expansion detection engine.

We detect when a corporate client is expanding into
new geographic markets by combining signals from:
- CIB: New payment corridors
- Cell: New SIM activations in new countries
- Forex: New currency hedging
- Insurance: New country coverage
- PBB: New payroll accounts

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging

from afriflow.config import get_settings
from afriflow.exceptions import SignalDetectionError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("cross_domain_signals.expansion")


@dataclass
class ExpansionSignal:
    """A detected expansion signal for a client."""

    golden_id: str
    client_name: str
    expansion_country: str
    confidence_score: float
    estimated_opportunity_zar: float

    # Evidence counts
    cib_new_corridor_payments: int
    cib_corridor_value: float
    cell_new_sim_activations: int
    forex_new_currency_trades: int
    insurance_new_countries: int
    pbb_new_countries: int

    # Gap flags
    forex_hedging_in_place: bool
    insurance_coverage_in_place: bool

    # Recommendations
    recommended_products: List[str]
    urgency: str

    def to_rm_alert(self) -> Dict:
        """Convert to RM alert format."""
        return {
            "Subject": f"Expansion Alert: {self.client_name} - {self.expansion_country}",
            "Body": (
                f"Client {self.client_name} is expanding into "
                f"{self.expansion_country}. Confidence: {self.confidence_score:.0f}%. "
                f"Estimated opportunity: R{self.estimated_opportunity_zar:,.0f}"
            ),
            "Priority": "Urgent" if self.confidence_score >= 80 else "High",
            "OwnerId": self.golden_id,
            "Country": self.expansion_country,
            "Confidence": self.confidence_score,
            "OpportunityValue": self.estimated_opportunity_zar,
        }


class ExpansionDetector:
    """We detect geographic expansion by combining
    cross-domain signals. A single domain signal is
    weak evidence; multiple corroborating signals
    produce high-confidence alerts.

    Example: CIB payments to Kenya + 50 SIM activations
    in Nairobi = credible expansion signal.
    """

    def __init__(self, settings=None):
        """
        Initialize the expansion detector with configuration.

        Args:
            settings: Optional Settings object. If not provided,
                     loads from global configuration.
        """
        self.settings = settings or get_settings()
        self.thresholds = self.settings.expansion_thresholds
        
        logger.debug(
            "ExpansionDetector initialized with thresholds: "
            f"min_cib_payments={self.thresholds.min_cib_payments_for_signal}, "
            f"min_cib_value={self.thresholds.min_cib_value_for_signal}, "
            f"min_sim_activations={self.thresholds.min_sim_activations_for_signal}"
        )
        
        self._cib_payments: Dict[str, List[Dict]] = defaultdict(list)
        self._cell_activations: Dict[str, List[Dict]] = defaultdict(list)
        self._forex_trades: Dict[str, List[Dict]] = defaultdict(list)
        self._client_metadata: Dict[str, Dict] = {}

    def ingest_cib_payment(self, payment: Dict) -> None:
        """Ingest a CIB payment event."""
        client_id = payment.get("debtor_client_id")
        if client_id:
            self._cib_payments[client_id].append(payment)

    def ingest_cell_activation(self, activation: Dict) -> None:
        """Ingest a cell SIM activation event."""
        client_id = activation.get("corporate_client_id")
        if client_id:
            self._cell_activations[client_id].append(activation)

    def ingest_forex_trade(self, trade: Dict) -> None:
        """Ingest a forex trade event."""
        client_id = trade.get("client_id")
        if client_id:
            self._forex_trades[client_id].append(trade)

    def detect_expansions(
        self,
        client_metadata: Dict[str, Dict],
        home_country: str = "ZA",
        lookback_days: int = 90,
    ) -> List[ExpansionSignal]:
        """Detect expansion signals for all clients."""
        signals = []
        all_clients = set(self._cib_payments.keys())

        for client_id in all_clients:
            client_info = client_metadata.get(client_id, {})
            client_signals = self._detect_client_expansion(
                client_id, client_info, home_country
            )
            signals.extend(client_signals)

        return sorted(
            signals,
            key=lambda s: s.confidence_score,
            reverse=True,
        )

    def _detect_client_expansion(
        self,
        client_id: str,
        client_info: Dict,
        home_country: str,
    ) -> List[ExpansionSignal]:
        """Detect expansion for a single client."""
        signals = []

        # Get CIB corridors (excluding home country)
        cib_corridors = self._get_cib_corridors(
            client_id, home_country
        )

        for country, cib_data in cib_corridors.items():
            signal = self._evaluate_expansion_evidence(
                client_id,
                client_info,
                country,
                cib_data,
            )
            if signal and signal.confidence_score >= 40:
                signals.append(signal)

        return signals

    def _get_cib_corridors(
        self,
        client_id: str,
        home_country: str,
    ) -> Dict[str, Dict]:
        """Get CIB payment corridors excluding home country."""
        corridors: Dict[str, Dict] = defaultdict(
            lambda: {"payments": 0, "value": 0.0}
        )

        for payment in self._cib_payments.get(client_id, []):
            creditor_country = payment.get("creditor_country")
            if creditor_country and creditor_country != home_country:
                corridors[creditor_country]["payments"] += 1
                corridors[creditor_country]["value"] += payment.get(
                    "amount", 0
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
        cib_payments = cib_data["payments"]
        cib_value = cib_data["value"]

        # Get cell activations for this country
        cell_activations = [
            a for a in self._cell_activations.get(client_id, [])
            if a.get("activation_country") == country
        ]
        sim_count = sum(
            a.get("sim_count", 0) for a in cell_activations
        )

        # Get forex trades for this country's currency
        forex_trades = self._get_forex_trades_for_country(
            client_id, country
        )
        has_forex = len(forex_trades) > 0
        is_hedged = any(
            t.get("is_hedge", False) for t in forex_trades
        )

        # Check insurance (simplified - assume not in place for demo)
        has_insurance = False

        # Calculate confidence
        confidence = self._calculate_confidence(
            cib_payments=cib_payments,
            cib_value=cib_value,
            sim_activations=sim_count,
            has_forex=has_forex,
            has_insurance=has_insurance,
            has_pbb=False,
        )

        if confidence < 40:
            return None

        # Estimate opportunity
        opportunity = self._estimate_opportunity(
            client_info=client_info,
            country=country,
            cib_value=cib_value,
            has_hedge=is_hedged,
            has_insurance=has_insurance,
            employee_count=0,
        )

        # Generate product recommendations
        products = []
        if not is_hedged:
            products.append("FX hedging solution")
            products.append("Forward contract")
        if not has_insurance:
            products.append("Trade credit insurance")
            products.append("Asset coverage review")
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
        currency_map = {
            "ZA": "ZAR", "NG": "NGN", "KE": "KES",
            "GH": "GHS", "TZ": "TZS", "UG": "UGX",
            "ZM": "ZMW", "MZ": "MZN", "CD": "CDF",
        }
        target_currency = currency_map.get(country)

        trades = []
        for trade in self._forex_trades.get(client_id, []):
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
        """Calculate confidence score from evidence."""
        score = 0.0

        # CIB contribution (max 40 points)
        if cib_payments >= self.thresholds.min_cib_payments_for_signal:
            score += 20
        if cib_value >= self.thresholds.min_cib_value_for_signal:
            score += min(20, cib_value / 500_000)

        # Cell contribution (max 25 points)
        if sim_activations >= self.thresholds.min_sim_activations_for_signal:
            score += 25
        elif sim_activations > 0:
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
        """Estimate revenue opportunity in ZAR."""
        tier = client_info.get("tier", "Bronze")

        # Base fee rate by tier
        fee_rates = {
            "Platinum": 0.005,
            "Gold": 0.008,
            "Silver": 0.010,
            "Bronze": 0.012,
        }
        base_rate = fee_rates.get(tier, 0.012)

        opportunity = 0.0

        # CIB corridor fees
        opportunity += cib_value * base_rate

        # FX opportunity if unhedged
        if not has_hedge:
            opportunity += cib_value * 0.003

        # Insurance opportunity
        if not has_insurance:
            opportunity += cib_value * 0.002

        # Payroll opportunity
        opportunity += employee_count * 2500

        return opportunity
