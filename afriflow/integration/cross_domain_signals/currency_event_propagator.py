"""
integration/cross_domain_signals/currency_event_propagator.py

Currency event propagation engine for African FX markets.

When a major currency event occurs (devaluation, capital
control change, central bank intervention), we immediately
recalculate the impact across all five domains for every
affected client. In Africa, FX volatility is not an
isolated risk. It cascades across CIB, Forex, Insurance,
Cell, and PBB simultaneously.

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


@dataclass
class CurrencyEvent:
    """A significant currency event that requires
    cross-domain impact assessment."""

    currency: str
    event_type: str
    magnitude_pct: float
    previous_rate: float
    current_rate: float
    timestamp: datetime
    capital_control_change: Optional[str] = None
    central_bank_action: Optional[str] = None


@dataclass
class ClientCurrencyExposure:
    """A single client's exposure to a specific currency
    across all five domains."""

    golden_id: str
    currency: str
    cib_exposure: float
    forex_forwards: float
    insurance_asset_value: float
    pbb_payroll_monthly: float
    cell_revenue_monthly: float


@dataclass
class PropagatedImpact:
    """The calculated impact of a currency event on a
    single client across all domains."""

    golden_id: str
    currency: str
    event_type: str

    cib_impact_zar: float
    forex_impact_zar: float
    insurance_impact_zar: float
    pbb_impact_zar: float
    cell_impact_zar: float

    total_impact_zar: float
    unhedged_exposure_zar: float
    hedge_ratio_pct: float

    recommended_actions: List[str]
    urgency: str


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

    VOLATILITY_THRESHOLDS: Dict[str, float] = {
        "ZAR": 3.0,
        "NGN": 8.0,
        "KES": 4.0,
        "GHS": 5.0,
        "TZS": 4.0,
        "UGX": 4.0,
        "ZMW": 5.0,
        "MZN": 6.0,
        "CDF": 10.0,
        "XOF": 2.0,
        "AOA": 8.0,
    }

    DEFAULT_THRESHOLD: float = 5.0

    def __init__(self):
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
        """We register a client's exposure to a specific
        currency across all domains."""
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
        """We evaluate whether a rate change is significant
        enough to warrant cross-domain propagation.

        We use currency-specific volatility thresholds
        because a 5% move in NGN is routine while a 5%
        move in XOF (CFA franc, pegged to EUR) is a
        structural crisis.
        """
        if previous_rate == 0:
            return None

        change_pct = abs(
            (current_rate - previous_rate) / previous_rate
        ) * 100

        threshold = self.VOLATILITY_THRESHOLDS.get(
            currency, self.DEFAULT_THRESHOLD
        )

        if change_pct < threshold and not capital_control_change:
            return None

        if current_rate > previous_rate:
            event_type = "DEVALUATION"
        else:
            event_type = "APPRECIATION"

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
        """We propagate a currency event across all
        affected clients and all five domains.

        For each client with exposure to the affected
        currency, we calculate:
        - CIB: Trade finance facility adequacy change
        - Forex: Forward contract MTM impact
        - Insurance: Asset coverage adequacy change
        - PBB: Employee purchasing power impact
        - Cell: JV revenue impact in ZAR terms
        """
        impacts = []
        exposed_clients = self._exposures.get(
            event.currency, {}
        )

        for golden_id, exposure in exposed_clients.items():
            rate_factor = (
                event.current_rate / event.previous_rate
            )

            cib_impact = exposure.cib_exposure * (
                1 - rate_factor
            )

            if exposure.forex_forwards > 0:
                forex_impact = exposure.forex_forwards * (
                    rate_factor - 1
                )
            else:
                forex_impact = 0

            insurance_impact = (
                exposure.insurance_asset_value
                * (1 - rate_factor)
            )

            pbb_impact = (
                exposure.pbb_payroll_monthly
                * 12
                * (1 - rate_factor)
            )

            cell_impact = (
                exposure.cell_revenue_monthly
                * 12
                * (1 - rate_factor)
            )

            total = (
                cib_impact
                + forex_impact
                + insurance_impact
                + pbb_impact
                + cell_impact
            )

            total_exposure = (
                exposure.cib_exposure
                + exposure.insurance_asset_value
                + exposure.pbb_payroll_monthly * 12
                + exposure.cell_revenue_monthly * 12
            )
            unhedged = max(
                0, total_exposure - exposure.forex_forwards
            )
            hedge_ratio = (
                (exposure.forex_forwards / total_exposure * 100)
                if total_exposure > 0
                else 0
            )

            actions = self._recommend_actions(
                event, exposure, hedge_ratio
            )
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
        """We generate specific recommended actions based
        on the event type and client exposure profile."""
        actions = []

        if hedge_ratio < 30:
            actions.append(
                f"URGENT: Client has only "
                f"{hedge_ratio:.0f}% hedge ratio "
                f"on {event.currency}. Offer forward "
                f"contract or option structure."
            )

        if event.event_type == "DEVALUATION":
            if exposure.cib_exposure > 0:
                actions.append(
                    "Review CIB trade finance facility "
                    "limits. Client may need increased "
                    "facility to cover higher local "
                    "currency costs."
                )
            if exposure.insurance_asset_value > 0:
                actions.append(
                    "Insurance coverage may be inadequate "
                    "after revaluation. Schedule asset "
                    "revaluation and coverage review."
                )
            if exposure.pbb_payroll_monthly > 0:
                actions.append(
                    "Employee purchasing power reduced. "
                    "Expect salary advance requests. "
                    "Prepare payroll support package."
                )

        if event.event_type == "CAPITAL_CONTROL_CHANGE":
            actions.append(
                "Capital controls changed. Review all "
                "repatriation schedules and advise on "
                "compliant payment structuring."
            )

        return actions
