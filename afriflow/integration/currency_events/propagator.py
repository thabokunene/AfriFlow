"""
CURRENCY EVENT PROPAGATOR

When a major FX event occurs (devaluation, rapid depreciation, capital
control change), we propagate the impact across all five domains
immediately.

This module is the architectural element that demonstrates understanding
of African FX dynamics that no Western or East Asian banking platform
includes. In developed markets, FX is a standalone risk. In Africa,
a currency event is a systemic shock.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only. All data
is simulated.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class EventSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventType(Enum):
    DEVALUATION = "DEVALUATION"
    RAPID_DEPRECIATION = "RAPID_DEPRECIATION"
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    PARALLEL_DIVERGENCE = "PARALLEL_DIVERGENCE"
    CENTRAL_BANK_INTERVENTION = "CENTRAL_BANK_INTERVENTION"
    BAND_WIDENING = "BAND_WIDENING"


@dataclass
class CurrencyEvent:
    """Represents a detected currency event."""

    event_id: str
    currency: str
    event_type: EventType
    severity: EventSeverity
    magnitude_pct: float
    official_rate_before: float
    official_rate_after: float
    parallel_rate: Optional[float]
    detection_timestamp: str
    source: str
    description: str


@dataclass
class DomainImpact:
    """Impact assessment for a single domain."""

    domain: str
    client_golden_id: str
    client_name: str
    impact_type: str
    impact_description: str
    estimated_financial_impact_zar: float
    action_required: str
    urgency: str
    affected_instruments: List[str] = field(
        default_factory=list
    )


@dataclass
class CascadeReport:
    """Full cascade impact report across all domains."""

    event: CurrencyEvent
    total_clients_affected: int
    total_estimated_impact_zar: float
    cib_impacts: List[DomainImpact]
    forex_impacts: List[DomainImpact]
    insurance_impacts: List[DomainImpact]
    cell_impacts: List[DomainImpact]
    pbb_impacts: List[DomainImpact]
    generated_at: str


class CurrencyEventClassifier:
    """
    Classifies FX rate movements into event categories
    based on configurable thresholds per currency.

    We maintain different thresholds for different currencies
    because a 5% move in ZAR/USD is unusual but manageable,
    while a 5% move in NGN/USD might signal a structural
    devaluation.
    """

    DEFAULT_THRESHOLDS = {
        "DEVALUATION": 10.0,
        "RAPID_DEPRECIATION": 5.0,
        "PARALLEL_DIVERGENCE": 20.0,
    }

    CURRENCY_THRESHOLDS = {
        "NGN": {
            "DEVALUATION": 8.0,
            "RAPID_DEPRECIATION": 4.0,
            "PARALLEL_DIVERGENCE": 15.0,
        },
        "ZAR": {
            "DEVALUATION": 12.0,
            "RAPID_DEPRECIATION": 6.0,
            "PARALLEL_DIVERGENCE": 25.0,
        },
        "KES": {
            "DEVALUATION": 10.0,
            "RAPID_DEPRECIATION": 5.0,
            "PARALLEL_DIVERGENCE": 20.0,
        },
        "GHS": {
            "DEVALUATION": 8.0,
            "RAPID_DEPRECIATION": 4.0,
            "PARALLEL_DIVERGENCE": 15.0,
        },
        "ZMW": {
            "DEVALUATION": 10.0,
            "RAPID_DEPRECIATION": 5.0,
            "PARALLEL_DIVERGENCE": 20.0,
        },
        "AOA": {
            "DEVALUATION": 8.0,
            "RAPID_DEPRECIATION": 3.0,
            "PARALLEL_DIVERGENCE": 10.0,
        },
        "MZN": {
            "DEVALUATION": 10.0,
            "RAPID_DEPRECIATION": 5.0,
            "PARALLEL_DIVERGENCE": 20.0,
        },
        "XOF": {
            "DEVALUATION": 15.0,
            "RAPID_DEPRECIATION": 8.0,
            "PARALLEL_DIVERGENCE": 25.0,
        },
    }

    def classify(
        self,
        currency: str,
        rate_change_pct: float,
        parallel_divergence_pct: Optional[float] = None,
        is_official_announcement: bool = False,
    ) -> Optional[CurrencyEvent]:
        """
        Classify a rate movement into an event type.

        Returns None if the movement is within normal
        bounds for the given currency.
        """

        thresholds = self.CURRENCY_THRESHOLDS.get(
            currency, self.DEFAULT_THRESHOLDS
        )

        event_type = None
        severity = None

        if is_official_announcement and abs(rate_change_pct) >= thresholds["DEVALUATION"]:
            event_type = EventType.DEVALUATION
            severity = EventSeverity.CRITICAL

        elif abs(rate_change_pct) >= thresholds["DEVALUATION"]:
            event_type = EventType.RAPID_DEPRECIATION
            severity = EventSeverity.HIGH

        elif abs(rate_change_pct) >= thresholds["RAPID_DEPRECIATION"]:
            event_type = EventType.RAPID_DEPRECIATION
            severity = EventSeverity.MEDIUM

        elif (
            parallel_divergence_pct is not None
            and parallel_divergence_pct >= thresholds["PARALLEL_DIVERGENCE"]
        ):
            event_type = EventType.PARALLEL_DIVERGENCE
            severity = EventSeverity.MEDIUM

        if event_type is None:
            return None

        return CurrencyEvent(
            event_id=f"FXE-{currency}-{datetime.now():%Y%m%d%H%M%S}",
            currency=currency,
            event_type=event_type,
            severity=severity,
            magnitude_pct=rate_change_pct,
            official_rate_before=0.0,
            official_rate_after=0.0,
            parallel_rate=None,
            detection_timestamp=datetime.now().isoformat(),
            source="rate_anomaly_detector",
            description=(
                f"{currency} {event_type.value}: "
                f"{rate_change_pct:.1f}% movement detected"
            ),
        )


class CurrencyEventPropagator:
    """
    Propagates a currency event across all five domains,
    calculating impact for every affected client.

    When the Nigerian naira devalues 20%, we do not just
    update the forex book. We recalculate:
    - Every CIB facility denominated in or exposed to NGN
    - Every forex forward and swap position
    - Every insurance policy covering Nigerian assets
    - MTN Nigeria JV revenue impact
    - Every employee paid in NGN
    """

    def __init__(
        self,
        golden_record_store,
        cib_store,
        forex_store,
        insurance_store,
        cell_store,
        pbb_store,
    ):
        self.golden_record = golden_record_store
        self.cib = cib_store
        self.forex = forex_store
        self.insurance = insurance_store
        self.cell = cell_store
        self.pbb = pbb_store

    def propagate(self, event: CurrencyEvent) -> CascadeReport:
        """
        Run full cascade propagation for a currency event.

        We process each domain independently and then
        aggregate into a unified cascade report.
        """

        currency_country_map = {
            "NGN": "NG", "KES": "KE", "GHS": "GH",
            "TZS": "TZ", "UGX": "UG", "ZMW": "ZM",
            "MZN": "MZ", "XOF": "CI", "CDF": "CD",
            "AOA": "AO", "ZAR": "ZA", "BWP": "BW",
            "NAD": "NA", "MWK": "MW", "RWF": "RW",
        }

        affected_country = currency_country_map.get(
            event.currency
        )

        if not affected_country:
            return self._empty_report(event)

        affected_clients = (
            self.golden_record.get_clients_with_exposure(
                country=affected_country
            )
        )

        cib_impacts = self._calculate_cib_impact(
            event, affected_clients, affected_country
        )
        forex_impacts = self._calculate_forex_impact(
            event, affected_clients
        )
        insurance_impacts = self._calculate_insurance_impact(
            event, affected_clients, affected_country
        )
        cell_impacts = self._calculate_cell_impact(
            event, affected_country
        )
        pbb_impacts = self._calculate_pbb_impact(
            event, affected_clients, affected_country
        )

        all_impacts = (
            cib_impacts + forex_impacts + insurance_impacts
            + cell_impacts + pbb_impacts
        )
        total_impact = sum(
            i.estimated_financial_impact_zar for i in all_impacts
        )

        return CascadeReport(
            event=event,
            total_clients_affected=len(affected_clients),
            total_estimated_impact_zar=total_impact,
            cib_impacts=cib_impacts,
            forex_impacts=forex_impacts,
            insurance_impacts=insurance_impacts,
            cell_impacts=cell_impacts,
            pbb_impacts=pbb_impacts,
            generated_at=datetime.now().isoformat(),
        )

    def _calculate_cib_impact(
        self,
        event: CurrencyEvent,
        clients: List[Dict],
        country: str,
    ) -> List[DomainImpact]:
        """
        Calculate CIB impact for each affected client.

        Primary concerns:
        - Trade finance facility adequacy after devaluation
        - Import cost inflation for clients buying into
          the affected market
        - Working capital pressure
        """

        impacts = []

        for client in clients:
            cib_data = self.cib.get_client_exposure(
                client["golden_id"], country
            )

            if not cib_data:
                continue

            facility_shortfall = (
                cib_data.get("facility_value_local", 0)
                * (abs(event.magnitude_pct) / 100)
            )

            impact = DomainImpact(
                domain="CIB",
                client_golden_id=client["golden_id"],
                client_name=client["canonical_name"],
                impact_type="FACILITY_ADEQUACY",
                impact_description=(
                    f"{event.currency} {event.event_type.value} "
                    f"of {event.magnitude_pct:.1f}% reduces effective "
                    f"facility value by R{facility_shortfall:,.0f}. "
                    f"Client may need facility amendment."
                ),
                estimated_financial_impact_zar=facility_shortfall,
                action_required=(
                    "Review facility adequacy. Contact client "
                    "to discuss amended facility terms."
                ),
                urgency=(
                    "IMMEDIATE"
                    if event.severity == EventSeverity.CRITICAL
                    else "HIGH"
                ),
                affected_instruments=cib_data.get(
                    "active_facilities", []
                ),
            )
            impacts.append(impact)

        return impacts

    def _calculate_forex_impact(
        self,
        event: CurrencyEvent,
        clients: List[Dict],
    ) -> List[DomainImpact]:
        """
        Calculate forex impact for each affected client.

        Primary concerns:
        - Open forward positions mark to market
        - Maturing positions with delivery risk
        - Unhedged clients who now face larger exposure
        """

        impacts = []

        for client in clients:
            forex_data = self.forex.get_client_positions(
                client["golden_id"], event.currency
            )

            if not forex_data:
                continue

            mtm_impact = (
                forex_data.get("open_forward_notional", 0)
                * (abs(event.magnitude_pct) / 100)
            )

            has_hedges = forex_data.get("has_hedges", False)

            impact = DomainImpact(
                domain="FOREX",
                client_golden_id=client["golden_id"],
                client_name=client["canonical_name"],
                impact_type=(
                    "MTM_GAIN" if mtm_impact > 0
                    else "UNHEDGED_EXPOSURE"
                ),
                impact_description=(
                    f"Open {event.currency} positions affected. "
                    f"Estimated MTM impact: R{mtm_impact:,.0f}. "
                    f"Hedging status: "
                    f"{'hedged' if has_hedges else 'UNHEDGED'}."
                ),
                estimated_financial_impact_zar=abs(mtm_impact),
                action_required=(
                    "Review open positions. Contact client "
                    "regarding hedge adjustments."
                    if has_hedges
                    else "Client is UNHEDGED. Urgent outreach "
                    "to discuss protection strategies."
                ),
                urgency=(
                    "IMMEDIATE" if not has_hedges
                    else "HIGH"
                ),
                affected_instruments=forex_data.get(
                    "open_trades", []
                ),
            )
            impacts.append(impact)

        return impacts

    def _calculate_insurance_impact(
        self,
        event: CurrencyEvent,
        clients: List[Dict],
        country: str,
    ) -> List[DomainImpact]:
        """
        Calculate insurance impact for each affected client.

        Primary concerns:
        - Asset revaluation and coverage adequacy
        - Group life benefit real value erosion
        """

        impacts = []

        for client in clients:
            ins_data = self.insurance.get_client_policies(
                client["golden_id"], country
            )

            if not ins_data:
                continue

            coverage_gap = (
                ins_data.get("insured_value_local", 0)
                * (abs(event.magnitude_pct) / 100)
            )

            impact = DomainImpact(
                domain="INSURANCE",
                client_golden_id=client["golden_id"],
                client_name=client["canonical_name"],
                impact_type="COVERAGE_INADEQUACY",
                impact_description=(
                    f"Asset values in {event.currency} need "
                    f"revaluation. Estimated coverage gap: "
                    f"R{coverage_gap:,.0f}."
                ),
                estimated_financial_impact_zar=coverage_gap,
                action_required=(
                    "Revalue insured assets. Contact client "
                    "regarding coverage top up."
                ),
                urgency="HIGH",
                affected_instruments=ins_data.get(
                    "policy_ids", []
                ),
            )
            impacts.append(impact)

        return impacts

    def _calculate_cell_impact(
        self,
        event: CurrencyEvent,
        country: str,
    ) -> List[DomainImpact]:
        """
        Calculate cell network (MTN partnership) impact.

        Primary concerns:
        - JV revenue impact in ZAR terms
        - MoMo volume changes during currency instability
        """

        cell_data = self.cell.get_country_metrics(country)

        if not cell_data:
            return []

        revenue_impact = (
            cell_data.get("monthly_jv_revenue_zar", 0)
            * (abs(event.magnitude_pct) / 100)
        )

        return [
            DomainImpact(
                domain="CELL",
                client_golden_id="GROUP_LEVEL",
                client_name="MTN Partnership",
                impact_type="JV_REVENUE_IMPACT",
                impact_description=(
                    f"MTN {country} JV revenue in ZAR terms "
                    f"reduced by approximately "
                    f"R{revenue_impact:,.0f} per month. "
                    f"MoMo volumes may spike as users prefer "
                    f"mobile money during currency instability."
                ),
                estimated_financial_impact_zar=revenue_impact * 12,
                action_required=(
                    "Monitor MoMo volumes for surge. "
                    "Review JV revenue forecasts."
                ),
                urgency="MEDIUM",
            )
        ]

    def _calculate_pbb_impact(
        self,
        event: CurrencyEvent,
        clients: List[Dict],
        country: str,
    ) -> List[DomainImpact]:
        """
        Calculate PBB (Personal and Business Banking) impact.

        Primary concerns:
        - Employee purchasing power erosion
        - Salary advance demand spike
        - Payroll value changes in ZAR terms
        """

        impacts = []

        for client in clients:
            pbb_data = self.pbb.get_client_payroll(
                client["golden_id"], country
            )

            if not pbb_data:
                continue

            employee_count = pbb_data.get("employee_count", 0)
            monthly_payroll = pbb_data.get(
                "monthly_payroll_local", 0
            )

            purchasing_power_loss = (
                monthly_payroll
                * (abs(event.magnitude_pct) / 100)
            )

            if employee_count < 50:
                continue

            impact = DomainImpact(
                domain="PBB",
                client_golden_id=client["golden_id"],
                client_name=client["canonical_name"],
                impact_type="PURCHASING_POWER_EROSION",
                impact_description=(
                    f"{employee_count} employees in {country} "
                    f"face {abs(event.magnitude_pct):.1f}% "
                    f"purchasing power reduction. "
                    f"Expect salary advance demand spike."
                ),
                estimated_financial_impact_zar=purchasing_power_loss,
                action_required=(
                    "Prepare for salary advance requests. "
                    "Consider proactive employee financial "
                    "wellness outreach."
                ),
                urgency="MEDIUM",
            )
            impacts.append(impact)

        return impacts

    def _empty_report(self, event: CurrencyEvent) -> CascadeReport:
        """Return an empty report when no country mapping exists."""

        return CascadeReport(
            event=event,
            total_clients_affected=0,
            total_estimated_impact_zar=0.0,
            cib_impacts=[],
            forex_impacts=[],
            insurance_impacts=[],
            cell_impacts=[],
            pbb_impacts=[],
            generated_at=datetime.now().isoformat(),
        )
