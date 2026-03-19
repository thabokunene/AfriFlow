"""
@file propagator.py
@description Currency event propagator for the AfriFlow integration layer,
    classifying FX rate movements into event types and propagating systemic
    impacts across all five domains (CIB, Forex, Insurance, Cell, PBB).
@author Thabo Kunene
@created 2026-03-19
"""

from dataclasses import dataclass, field  # dataclasses for clean value-object definitions
from datetime import datetime             # used for event timestamps and ID generation
from typing import Dict, List, Optional  # type hints for all public signatures
from enum import Enum                    # strongly typed enumerations for event types


# Severity levels ordered from most to least urgent.
# CRITICAL events (e.g. official devaluations) trigger immediate RM alerts.
class EventSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# All known FX event categories in African markets.
# PARALLEL_DIVERGENCE is Africa-specific: it signals that the black-market
# rate has moved far beyond the official rate — a leading indicator of
# an imminent official devaluation.
class EventType(Enum):
    DEVALUATION = "DEVALUATION"
    RAPID_DEPRECIATION = "RAPID_DEPRECIATION"
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    PARALLEL_DIVERGENCE = "PARALLEL_DIVERGENCE"
    CENTRAL_BANK_INTERVENTION = "CENTRAL_BANK_INTERVENTION"
    BAND_WIDENING = "BAND_WIDENING"


@dataclass
class CurrencyEvent:
    """
    Represents a detected currency event.

    :param event_id: Unique event identifier (e.g. FXE-NGN-20260317120000)
    :param currency: ISO 4217 currency code affected (e.g. NGN, ZAR)
    :param event_type: Classification of the event (EventType enum)
    :param severity: Urgency level (EventSeverity enum)
    :param magnitude_pct: Percentage rate move that triggered the event
    :param official_rate_before: Central bank rate before the event
    :param official_rate_after: Central bank rate after the event
    :param parallel_rate: Black-market/parallel market rate if applicable
    :param detection_timestamp: ISO timestamp when the event was detected
    :param source: Detection source (e.g. rate_anomaly_detector)
    :param description: Human-readable summary of the event
    """

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
    """
    Impact assessment for a single domain resulting from a currency event.

    :param domain: Domain name (CIB, FOREX, INSURANCE, CELL, PBB)
    :param client_golden_id: Unified client identifier from entity resolution
    :param client_name: Canonical client name
    :param impact_type: Category of impact (e.g. FACILITY_ADEQUACY, MTM_GAIN)
    :param impact_description: Human-readable explanation of the impact
    :param estimated_financial_impact_zar: Estimated ZAR value of the impact
    :param action_required: Recommended RM follow-up action
    :param urgency: Urgency level string (IMMEDIATE, HIGH, MEDIUM)
    :param affected_instruments: List of specific instruments or IDs affected
    """

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
    """
    Full cascade impact report across all five domains for a currency event.

    :param event: The triggering CurrencyEvent
    :param total_clients_affected: Count of unique clients with any exposure
    :param total_estimated_impact_zar: Sum of all domain impacts in ZAR
    :param cib_impacts: Per-client CIB domain impact records
    :param forex_impacts: Per-client Forex domain impact records
    :param insurance_impacts: Per-client Insurance domain impact records
    :param cell_impacts: Cell/telco JV impact records
    :param pbb_impacts: Per-client PBB payroll impact records
    :param generated_at: ISO timestamp when this report was produced
    """

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

    # Fallback thresholds used for currencies not in CURRENCY_THRESHOLDS.
    # All values represent percentage moves that cross each classification boundary.
    DEFAULT_THRESHOLDS = {
        "DEVALUATION": 10.0,
        "RAPID_DEPRECIATION": 5.0,
        "PARALLEL_DIVERGENCE": 20.0,
    }

    # Per-currency thresholds. Currencies with higher volatility baselines
    # (NGN, GHS, AOA) have lower thresholds — a 4% NGN move is significant
    # whereas a 4% ZAR move is within normal range.
    # XOF has higher thresholds because it is pegged to the euro and moves
    # much less frequently — any break from peg is structurally significant.
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
            # Ghana cedi has historically experienced sharp devaluations
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
            # Angolan kwanza — small moves can signal large structural shifts
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
            # West African CFA franc — euro-pegged, so thresholds are higher
            # because peg breaks are rare but catastrophic
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

        Returns None if the movement is within normal bounds for
        the given currency. The classification cascade is:
          1. Official announcement + large move → DEVALUATION (CRITICAL)
          2. Large move without announcement   → RAPID_DEPRECIATION (HIGH)
          3. Smaller but notable move          → RAPID_DEPRECIATION (MEDIUM)
          4. Parallel market divergence only   → PARALLEL_DIVERGENCE (MEDIUM)

        :param currency: ISO 4217 currency code (e.g. NGN, ZAR)
        :param rate_change_pct: Observed percentage change in the official rate
        :param parallel_divergence_pct: Optional spread between official and
                                        black-market rate as a percentage
        :param is_official_announcement: True when a central bank announcement
                                         is confirmed (lifts severity to CRITICAL)
        :return: CurrencyEvent if thresholds are breached, else None
        """

        # Look up per-currency thresholds, falling back to global defaults
        thresholds = self.CURRENCY_THRESHOLDS.get(
            currency, self.DEFAULT_THRESHOLDS
        )

        event_type = None
        severity = None

        # Step 1: Official devaluation announcement with large move is CRITICAL
        if is_official_announcement and abs(rate_change_pct) >= thresholds["DEVALUATION"]:
            event_type = EventType.DEVALUATION
            severity = EventSeverity.CRITICAL

        # Step 2: Market-driven move of devaluation magnitude (no CB announcement)
        elif abs(rate_change_pct) >= thresholds["DEVALUATION"]:
            event_type = EventType.RAPID_DEPRECIATION
            severity = EventSeverity.HIGH

        # Step 3: Moderate but notable depreciation
        elif abs(rate_change_pct) >= thresholds["RAPID_DEPRECIATION"]:
            event_type = EventType.RAPID_DEPRECIATION
            severity = EventSeverity.MEDIUM

        # Step 4: Parallel market divergence signals potential upcoming devaluation
        elif (
            parallel_divergence_pct is not None
            and parallel_divergence_pct >= thresholds["PARALLEL_DIVERGENCE"]
        ):
            event_type = EventType.PARALLEL_DIVERGENCE
            severity = EventSeverity.MEDIUM

        # No threshold breached — movement is within normal range for this currency
        if event_type is None:
            return None

        return CurrencyEvent(
            event_id=f"FXE-{currency}-{datetime.now():%Y%m%d%H%M%S}",
            currency=currency,
            event_type=event_type,
            severity=severity,
            magnitude_pct=rate_change_pct,
            # Rate values are populated by the calling ingestion layer
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
        golden_record_store,  # provides client master data and country exposure lookup
        cib_store,            # trade finance facility and corridor data
        forex_store,          # open FX positions and hedge inventory
        insurance_store,      # active policies and insured values
        cell_store,           # MTN JV revenue and SIM metrics
        pbb_store,            # employee payroll and PBB account data
    ):
        # Store domain data providers as instance attributes for use in propagate()
        self.golden_record = golden_record_store
        self.cib = cib_store
        self.forex = forex_store
        self.insurance = insurance_store
        self.cell = cell_store
        self.pbb = pbb_store

    def propagate(self, event: CurrencyEvent) -> CascadeReport:
        """
        Run full cascade propagation for a currency event.

        We process each domain independently and then aggregate
        into a unified cascade report. Each domain impact is
        calculated separately so that domain-specific logic
        (e.g. hedge status for forex, employee count threshold for
        PBB) can be applied without coupling the domains together.

        :param event: The detected CurrencyEvent to propagate
        :return: CascadeReport with per-domain impacts and totals
        """

        # Map ISO 4217 currency codes to ISO 3166-1 alpha-2 country codes.
        # This is the primary key for retrieving affected clients from the
        # golden record store.
        currency_country_map = {
            "NGN": "NG", "KES": "KE", "GHS": "GH",
            "TZS": "TZ", "UGX": "UG", "ZMW": "ZM",
            "MZN": "MZ", "XOF": "CI", "CDF": "CD",
            "AOA": "AO", "ZAR": "ZA", "BWP": "BW",
            "NAD": "NA", "MWK": "MW", "RWF": "RW",
        }

        # Resolve the country code; return empty report if currency is unknown
        affected_country = currency_country_map.get(
            event.currency
        )

        if not affected_country:
            # Currency not mapped — we cannot identify affected clients
            return self._empty_report(event)

        # Fetch all clients with any exposure to the affected country
        affected_clients = (
            self.golden_record.get_clients_with_exposure(
                country=affected_country
            )
        )

        # Run each domain calculation independently.
        # Cell is a country-level (not per-client) calculation because
        # MTN JV revenue is reported at group level, not per-client.
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

        # Aggregate all domain impacts into a single list for totalling
        all_impacts = (
            cib_impacts + forex_impacts + insurance_impacts
            + cell_impacts + pbb_impacts
        )
        # Sum ZAR-denominated impact estimates across all domains
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

        :param event: The triggering currency event
        :param clients: List of client dicts from the golden record store
        :param country: ISO 3166-1 alpha-2 country code of the affected currency
        :return: List of DomainImpact records for CIB domain
        """

        impacts = []

        for client in clients:
            # Retrieve this client's CIB exposure in the affected country
            cib_data = self.cib.get_client_exposure(
                client["golden_id"], country
            )

            # Skip clients with no CIB exposure in this country
            if not cib_data:
                continue

            # Estimate the facility shortfall: the local-currency facility value
            # shrinks proportionally to the devaluation magnitude
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
                # CRITICAL events demand same-day RM contact; HIGH is next-business-day
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

        :param event: The triggering currency event
        :param clients: List of client dicts with golden_id and canonical_name
        :return: List of DomainImpact records for the Forex domain
        """

        impacts = []

        for client in clients:
            # Get this client's open FX positions denominated in the affected currency
            forex_data = self.forex.get_client_positions(
                client["golden_id"], event.currency
            )

            # Skip clients with no open positions in this currency
            if not forex_data:
                continue

            # MTM impact = notional value of open forwards × rate change percentage
            mtm_impact = (
                forex_data.get("open_forward_notional", 0)
                * (abs(event.magnitude_pct) / 100)
            )

            # Whether the client has any active hedges for this currency
            has_hedges = forex_data.get("has_hedges", False)

            impact = DomainImpact(
                domain="FOREX",
                client_golden_id=client["golden_id"],
                client_name=client["canonical_name"],
                # Unhedged clients are a higher priority concern than hedged ones
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
                # Unhedged clients require IMMEDIATE RM outreach
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

        :param event: The triggering currency event
        :param clients: List of client dicts with golden_id and canonical_name
        :param country: ISO 3166-1 alpha-2 country code of the affected currency
        :return: List of DomainImpact records for the Insurance domain
        """

        impacts = []

        for client in clients:
            # Retrieve policies held by this client in the affected country
            ins_data = self.insurance.get_client_policies(
                client["golden_id"], country
            )

            # Skip clients with no insurance policies in this country
            if not ins_data:
                continue

            # The coverage gap is the portion of insured local-currency value
            # that is now under-covered because asset values in ZAR terms have
            # declined proportionally with the devaluation
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

        Note: Cell impact is calculated at country level (not per-client)
        because MTN JV revenue is reported as a group-level metric.

        :param event: The triggering currency event
        :param country: ISO 3166-1 alpha-2 country code
        :return: List of DomainImpact records for the Cell domain (0 or 1 items)
        """

        # Retrieve country-level MTN JV metrics
        cell_data = self.cell.get_country_metrics(country)

        # If no MTN operations exist in this country, there is no cell impact
        if not cell_data:
            return []

        # Monthly JV revenue declines proportionally with the currency move.
        # We annualise the impact (× 12) for the estimated_financial_impact_zar field.
        revenue_impact = (
            cell_data.get("monthly_jv_revenue_zar", 0)
            * (abs(event.magnitude_pct) / 100)
        )

        return [
            DomainImpact(
                domain="CELL",
                # Cell impact is group-level, not tied to a specific client golden ID
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
                # Annualised impact for comparability with other domain estimates
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

        :param event: The triggering currency event
        :param clients: List of client dicts with golden_id and canonical_name
        :param country: ISO 3166-1 alpha-2 country code
        :return: List of DomainImpact records for the PBB domain
        """

        impacts = []

        for client in clients:
            # Retrieve payroll data for employees of this client in the affected country
            pbb_data = self.pbb.get_client_payroll(
                client["golden_id"], country
            )

            # Skip clients with no payroll in this country
            if not pbb_data:
                continue

            employee_count = pbb_data.get("employee_count", 0)
            monthly_payroll = pbb_data.get(
                "monthly_payroll_local", 0
            )

            # Purchasing power loss = the local-currency payroll value
            # that is now effectively worth less in real terms
            purchasing_power_loss = (
                monthly_payroll
                * (abs(event.magnitude_pct) / 100)
            )

            # Only report on significant workforces (50+ employees).
            # Smaller workforces generate too little PBB volume to action.
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
