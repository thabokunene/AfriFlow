"""
@file currency_event_propagator.py
@description Currency event propagation engine for African FX markets,
    calculating cross-domain impacts (CIB, Forex, Insurance, Cell, PBB)
    after major currency devaluations or capital control changes.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard-library imports
from dataclasses import dataclass, field   # Typed data containers
from datetime import datetime              # Timestamp on currency events
from typing import Dict, List, Optional    # Type annotations
from collections import defaultdict        # Auto-initialising exposure registry


# ---------------------------------------------------------------------------
# Domain event: describes the FX rate movement that triggered propagation
# ---------------------------------------------------------------------------

@dataclass
class CurrencyEvent:
    """A significant currency event that requires
    cross-domain impact assessment."""

    # ISO 4217 currency code of the affected currency (e.g. "NGN")
    currency: str
    # Classification: "DEVALUATION", "APPRECIATION", or "CAPITAL_CONTROL_CHANGE"
    event_type: str
    # Absolute percentage change that triggered the event
    magnitude_pct: float
    # Rate before the event (expressed as units of currency per USD or ZAR)
    previous_rate: float
    # Rate after the event
    current_rate: float
    # Wall-clock timestamp of when the rate change was observed
    timestamp: datetime
    # Free-text description of the capital control change (if applicable)
    capital_control_change: Optional[str] = None
    # Free-text description of the central bank action (if applicable)
    central_bank_action: Optional[str] = None


# ---------------------------------------------------------------------------
# Exposure record: a client's exposure to a specific currency per domain
# ---------------------------------------------------------------------------

@dataclass
class ClientCurrencyExposure:
    """A single client's exposure to a specific currency
    across all five domains."""

    # Unique client identifier from the golden record
    golden_id: str
    # ISO 4217 currency code
    currency: str
    # CIB trade finance facility value denominated in this currency
    cib_exposure: float
    # Total notional value of FX forward contracts for this currency
    forex_forwards: float
    # Insured asset value denominated in this currency
    insurance_asset_value: float
    # Monthly payroll in this currency (annualised inside propagate())
    pbb_payroll_monthly: float
    # Monthly Cell/telco JV revenue in this currency (annualised inside propagate())
    cell_revenue_monthly: float


# ---------------------------------------------------------------------------
# Impact record: computed cross-domain impact for one client after one event
# ---------------------------------------------------------------------------

@dataclass
class PropagatedImpact:
    """The calculated impact of a currency event on a
    single client across all domains."""

    # Unique client identifier from the golden record
    golden_id: str
    # ISO 4217 currency code of the event
    currency: str
    # Event type from the originating CurrencyEvent
    event_type: str

    # Domain-level impacts in ZAR (positive = loss, negative = gain)
    cib_impact_zar: float
    forex_impact_zar: float
    insurance_impact_zar: float
    pbb_impact_zar: float
    cell_impact_zar: float

    # Aggregate impact across all five domains
    total_impact_zar: float
    # Portion of total exposure that is not covered by forward contracts
    unhedged_exposure_zar: float
    # Percentage of total exposure covered by forward contracts
    hedge_ratio_pct: float

    # Ordered list of recommended actions for the RM to discuss with the client
    recommended_actions: List[str]
    # Urgency classification driven by the magnitude of the rate move
    urgency: str


# ---------------------------------------------------------------------------
# Propagation engine
# ---------------------------------------------------------------------------

class CurrencyEventPropagator:
    """We detect significant FX events and propagate
    their impact across all client exposures in all
    five domains.

    This engine fills the critical gap that Western FX
    architectures miss: in African markets, a naira
    devaluation does not just affect the FX desk. It
    simultaneously impacts CIB facility adequacy,
    insurance coverage, payroll purchasing power, and
    telco JV revenue.
    """

    # Per-currency volatility thresholds (%) above which an event is raised.
    # Thresholds are higher for historically volatile currencies (NGN, AOA, CDF)
    # and lower for more stable ones (XOF, pegged to EUR).
    VOLATILITY_THRESHOLDS: Dict[str, float] = {
        "ZAR": 3.0,   # South African rand — moderate volatility
        "NGN": 8.0,   # Nigerian naira — high structural volatility
        "KES": 4.0,   # Kenyan shilling
        "GHS": 5.0,   # Ghanaian cedi
        "TZS": 4.0,   # Tanzanian shilling
        "UGX": 4.0,   # Ugandan shilling
        "ZMW": 5.0,   # Zambian kwacha
        "MZN": 6.0,   # Mozambican metical
        "CDF": 10.0,  # Congolese franc — very high volatility
        "XOF": 2.0,   # CFA franc (West Africa) — pegged to EUR, very stable
        "AOA": 8.0,   # Angolan kwanza
    }

    # Fallback threshold for currencies not in the map above
    DEFAULT_THRESHOLD: float = 5.0

    def __init__(self):
        """
        Initialise the propagator with an empty exposure registry.

        The registry is keyed by currency code then by client golden_id,
        allowing O(1) lookup of all clients exposed to a given currency.
        """
        # Nested defaultdict: _exposures[currency][golden_id] = ClientCurrencyExposure
        self._exposures: Dict[
            str, Dict[str, ClientCurrencyExposure]
        ] = defaultdict(dict)

    def register_client_exposure(
        self,
        golden_id: str,
        currency: str,
        cib_exposure: float = 0,
        forex_forwards: float = 0,
        insurance_asset_value: float = 0,
        pbb_payroll_monthly: float = 0,
        cell_revenue_monthly: float = 0,
    ) -> None:
        """
        We register a client's exposure to a specific
        currency across all domains.

        :param golden_id: Client identifier from the golden record
        :param currency: ISO 4217 currency code
        :param cib_exposure: CIB trade finance facility value in this currency
        :param forex_forwards: Notional value of forward contracts
        :param insurance_asset_value: Insured asset value in this currency
        :param pbb_payroll_monthly: Monthly payroll in this currency
        :param cell_revenue_monthly: Monthly Cell/telco revenue in this currency
        """
        # Overwrite any prior registration for this (currency, client) pair
        self._exposures[currency][golden_id] = (
            ClientCurrencyExposure(
                golden_id=golden_id,
                currency=currency,
                cib_exposure=cib_exposure,
                forex_forwards=forex_forwards,
                insurance_asset_value=insurance_asset_value,
                pbb_payroll_monthly=pbb_payroll_monthly,
                cell_revenue_monthly=cell_revenue_monthly,
            )
        )

    def evaluate_rate_change(
        self,
        currency: str,
        previous_rate: float,
        current_rate: float,
        timestamp: datetime,
        capital_control_change: Optional[str] = None,
    ) -> Optional[CurrencyEvent]:
        """
        We evaluate whether a rate change is significant
        enough to warrant cross-domain propagation.

        We use currency-specific volatility thresholds
        because a 5% move in NGN is routine while a 5%
        move in XOF (CFA franc, pegged to EUR) is a
        structural crisis.

        :param currency: ISO 4217 currency code
        :param previous_rate: Rate before the observed change
        :param current_rate: Rate after the observed change
        :param timestamp: When the change was observed
        :param capital_control_change: Description of any capital control change
        :return: CurrencyEvent if the move exceeds the threshold, else None
        """
        # Guard against division by zero for new or placeholder rates
        if previous_rate == 0:
            return None

        # Calculate the unsigned percentage change
        change_pct = abs(
            (current_rate - previous_rate) / previous_rate
        ) * 100

        # Use the currency-specific threshold, or the default for unknown currencies
        threshold = self.VOLATILITY_THRESHOLDS.get(
            currency, self.DEFAULT_THRESHOLD
        )

        # Suppress routine moves unless a capital-control change was also flagged
        if change_pct < threshold and not capital_control_change:
            return None

        # Classify direction: a higher rate means the local currency weakened
        if current_rate > previous_rate:
            event_type = "DEVALUATION"
        else:
            event_type = "APPRECIATION"

        # Capital control changes override the directional classification
        if capital_control_change:
            event_type = "CAPITAL_CONTROL_CHANGE"

        return CurrencyEvent(
            currency=currency,
            event_type=event_type,
            magnitude_pct=change_pct,
            previous_rate=previous_rate,
            current_rate=current_rate,
            timestamp=timestamp,
            capital_control_change=capital_control_change,
        )

    def propagate(
        self, event: CurrencyEvent
    ) -> List[PropagatedImpact]:
        """
        We propagate a currency event across all
        affected clients and all five domains.

        For each client with exposure to the affected
        currency, we calculate:
        - CIB: Trade finance facility adequacy change
        - Forex: Forward contract MTM impact
        - Insurance: Asset coverage adequacy change
        - PBB: Employee purchasing power impact
        - Cell: JV revenue impact in ZAR terms

        :param event: The CurrencyEvent to propagate
        :return: List of PropagatedImpact objects sorted by absolute total
                 impact (largest exposure first)
        """
        impacts = []
        # Retrieve all clients registered for this currency
        exposed_clients = self._exposures.get(
            event.currency, {}
        )

        for golden_id, exposure in exposed_clients.items():
            # rate_factor > 1 means devaluation; < 1 means appreciation
            rate_factor = (
                event.current_rate / event.previous_rate
            )

            # CIB: devaluation increases the local-currency cost of the facility
            cib_impact = exposure.cib_exposure * (
                1 - rate_factor
            )

            # Forex: forward contracts gain value during devaluation (positive MTM)
            if exposure.forex_forwards > 0:
                forex_impact = exposure.forex_forwards * (
                    rate_factor - 1
                )
            else:
                # No forwards means no hedge gain — full exposure to spot move
                forex_impact = 0

            # Insurance: insured asset value in ZAR terms changes with rate
            insurance_impact = (
                exposure.insurance_asset_value
                * (1 - rate_factor)
            )

            # PBB: annualised payroll purchasing power impact
            pbb_impact = (
                exposure.pbb_payroll_monthly
                * 12
                * (1 - rate_factor)
            )

            # Cell: annualised JV revenue impact in ZAR terms
            cell_impact = (
                exposure.cell_revenue_monthly
                * 12
                * (1 - rate_factor)
            )

            # Aggregate across all five domains
            total = (
                cib_impact
                + forex_impact
                + insurance_impact
                + pbb_impact
                + cell_impact
            )

            # Total exposure excludes forward contracts (they are the hedge)
            total_exposure = (
                exposure.cib_exposure
                + exposure.insurance_asset_value
                + exposure.pbb_payroll_monthly * 12
                + exposure.cell_revenue_monthly * 12
            )
            # Unhedged exposure = total exposure minus forward contract cover
            unhedged = max(
                0, total_exposure - exposure.forex_forwards
            )
            # Hedge ratio as a percentage of total exposure
            hedge_ratio = (
                (exposure.forex_forwards / total_exposure * 100)
                if total_exposure > 0
                else 0  # Avoid division by zero for clients with zero exposure
            )

            # Generate contextual actions based on event type and exposure profile
            actions = self._recommend_actions(
                event, exposure, hedge_ratio
            )
            # Urgency driven by magnitude: >15% moves are emergencies
            urgency = (
                "IMMEDIATE"
                if event.magnitude_pct > 15
                else "HIGH"
                if event.magnitude_pct > 8
                else "MEDIUM"
            )

            impacts.append(
                PropagatedImpact(
                    golden_id=golden_id,
                    currency=event.currency,
                    event_type=event.event_type,
                    cib_impact_zar=round(cib_impact, 2),
                    forex_impact_zar=round(forex_impact, 2),
                    insurance_impact_zar=round(
                        insurance_impact, 2
                    ),
                    pbb_impact_zar=round(pbb_impact, 2),
                    cell_impact_zar=round(cell_impact, 2),
                    total_impact_zar=round(total, 2),
                    unhedged_exposure_zar=round(unhedged, 2),
                    hedge_ratio_pct=round(hedge_ratio, 1),
                    recommended_actions=actions,
                    urgency=urgency,
                )
            )

        # Surface the clients with the largest absolute exposure first
        return sorted(
            impacts,
            key=lambda i: abs(i.total_impact_zar),
            reverse=True,
        )

    def _recommend_actions(
        self,
        event: CurrencyEvent,
        exposure: ClientCurrencyExposure,
        hedge_ratio: float,
    ) -> List[str]:
        """
        We generate specific recommended actions based
        on the event type and client exposure profile.

        :param event: The currency event that triggered propagation
        :param exposure: The client's registered exposure profile
        :param hedge_ratio: Percentage of exposure already hedged
        :return: Ordered list of recommended action strings for the RM
        """
        actions = []

        # Under-hedged clients are the most urgent — offer to cover the gap
        if hedge_ratio < 30:
            actions.append(
                f"URGENT: Client has only "
                f"{hedge_ratio:.0f}% hedge ratio "
                f"on {event.currency}. Offer forward "
                f"contract or option structure."
            )

        if event.event_type == "DEVALUATION":
            # Devaluation increases local-currency cost of trade finance
            if exposure.cib_exposure > 0:
                actions.append(
                    "Review CIB trade finance facility "
                    "limits. Client may need increased "
                    "facility to cover higher local "
                    "currency costs."
                )
            # Devaluation reduces ZAR value of insured assets — review sums insured
            if exposure.insurance_asset_value > 0:
                actions.append(
                    "Insurance coverage may be inadequate "
                    "after revaluation. Schedule asset "
                    "revaluation and coverage review."
                )
            # Employees' salaries buy less — anticipate advance and loan requests
            if exposure.pbb_payroll_monthly > 0:
                actions.append(
                    "Employee purchasing power reduced. "
                    "Expect salary advance requests. "
                    "Prepare payroll support package."
                )

        if event.event_type == "CAPITAL_CONTROL_CHANGE":
            # Capital controls directly affect repatriation of profits
            actions.append(
                "Capital controls changed. Review all "
                "repatriation schedules and advise on "
                "compliant payment structuring."
            )

        return actions
