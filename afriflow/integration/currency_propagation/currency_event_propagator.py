"""
Currency Event Propagation Engine.

When a major FX event occurs (devaluation, capital
control change, central bank intervention), we
propagate the impact across all five domains
simultaneously.

We treat FX volatility not as a single domain risk
but as a cross cutting concern that modifies every
other domain's calculations.

Disclaimer: This is not a sanctioned project. We
built it as a demonstration of concept, domain
knowledge, and skill.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class CurrencyEventType(Enum):
    DEVALUATION = "DEVALUATION"
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    CENTRAL_BANK_RATE_MOVE = "CENTRAL_BANK_RATE_MOVE"
    PARALLEL_MARKET_DIVERGENCE = "PARALLEL_MARKET_DIVERGENCE"
    CURRENCY_PEG_BREAK = "CURRENCY_PEG_BREAK"


@dataclass
class CurrencyEvent:
    """A detected major currency event."""

    event_id: str
    currency: str
    country: str
    event_type: CurrencyEventType
    magnitude_pct: float
    event_date: str
    description: str


@dataclass
class DomainImpact:
    """Impact of a currency event on a single domain."""

    domain: str
    impact_description: str
    affected_clients: int
    estimated_exposure_zar: float
    required_actions: List[str]
    urgency: str


@dataclass
class PropagationResult:
    """
    Full propagation result across all domains for a
    currency event.
    """

    event: CurrencyEvent
    cib_impact: Optional[DomainImpact]
    forex_impact: Optional[DomainImpact]
    insurance_impact: Optional[DomainImpact]
    cell_impact: Optional[DomainImpact]
    pbb_impact: Optional[DomainImpact]
    total_affected_clients: int
    total_exposure_zar: float
    generated_at: str


class CurrencyEventPropagator:
    """
    We propagate currency events across all five
    domains. When a major FX move occurs, we
    recalculate every affected signal across CIB,
    Forex, Insurance, Cell, and PBB simultaneously.

    This engine exists because African FX events are
    not isolated risks. A 20% naira devaluation hits
    every division of the bank at once, and we must
    present that unified impact view to relationship
    managers and ExCo.
    """

    # We define thresholds that qualify as "major"
    # events requiring propagation.
    DEVALUATION_THRESHOLD_PCT = 5.0
    RATE_MOVE_THRESHOLD_BPS = 100
    PARALLEL_SPREAD_THRESHOLD_PCT = 10.0

    def propagate(
        self,
        event: CurrencyEvent,
        client_exposures: Dict[str, Dict],
    ) -> PropagationResult:
        """
        Propagate a currency event across all domains
        for all affected clients.

        We accept a dictionary of client exposures
        keyed by golden_id, where each entry contains
        the client's exposure in each domain to the
        affected currency.
        """

        cib_impact = self._assess_cib_impact(
            event, client_exposures
        )
        forex_impact = self._assess_forex_impact(
            event, client_exposures
        )
        insurance_impact = self._assess_insurance_impact(
            event, client_exposures
        )
        cell_impact = self._assess_cell_impact(
            event, client_exposures
        )
        pbb_impact = self._assess_pbb_impact(
            event, client_exposures
        )

        impacts = [
            i for i in [
                cib_impact,
                forex_impact,
                insurance_impact,
                cell_impact,
                pbb_impact,
            ]
            if i is not None
        ]

        total_clients = sum(
            i.affected_clients for i in impacts
        )
        total_exposure = sum(
            i.estimated_exposure_zar for i in impacts
        )

        return PropagationResult(
            event=event,
            cib_impact=cib_impact,
            forex_impact=forex_impact,
            insurance_impact=insurance_impact,
            cell_impact=cell_impact,
            pbb_impact=pbb_impact,
            total_affected_clients=total_clients,
            total_exposure_zar=total_exposure,
            generated_at=datetime.now().isoformat(),
        )

    def _assess_cib_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess CIB impact by checking open trade
        finance facilities and payment corridors
        denominated in the affected currency.
        """

        affected = 0
        total_exposure = 0.0

        for golden_id, exp in exposures.items():
            cib_exposure = exp.get(
                "cib_corridor_value", {}
            ).get(event.country, 0)
            if cib_exposure > 0:
                affected += 1
                impact = (
                    cib_exposure
                    * event.magnitude_pct
                    / 100
                )
                total_exposure += impact

        if affected == 0:
            return None

        actions = [
            (
                "Review all open trade finance "
                "facilities in "
                f"{event.currency}"
            ),
            (
                "Recalculate facility adequacy at "
                "post event rates"
            ),
            (
                "Contact clients with facilities "
                "exceeding 80% utilisation"
            ),
        ]

        return DomainImpact(
            domain="CIB",
            impact_description=(
                f"{event.currency} "
                f"{event.event_type.value} "
                f"affects {affected} clients with "
                f"open corridors to {event.country}"
            ),
            affected_clients=affected,
            estimated_exposure_zar=total_exposure,
            required_actions=actions,
            urgency=(
                "IMMEDIATE"
                if event.magnitude_pct > 10
                else "HIGH"
            ),
        )

    def _assess_forex_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess forex impact by marking to market
        open positions in the affected currency.
        """

        affected = 0
        total_exposure = 0.0

        for golden_id, exp in exposures.items():
            fx_exposure = exp.get(
                "forex_open_positions", {}
            ).get(event.currency, 0)
            if fx_exposure > 0:
                affected += 1
                total_exposure += fx_exposure

        if affected == 0:
            return None

        actions = [
            (
                "Mark to market all open "
                f"{event.currency} positions"
            ),
            (
                "Identify clients with expiring "
                "hedges needing rollover"
            ),
            (
                "Flag unhedged clients for "
                "advisory outreach"
            ),
        ]

        return DomainImpact(
            domain="Forex",
            impact_description=(
                f"{event.currency} move affects "
                f"{affected} clients with open "
                f"FX positions"
            ),
            affected_clients=affected,
            estimated_exposure_zar=total_exposure,
            required_actions=actions,
            urgency="IMMEDIATE",
        )

    def _assess_insurance_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess insurance impact by checking
        coverage adequacy at post event valuations.
        """

        affected = 0
        total_exposure = 0.0

        for golden_id, exp in exposures.items():
            ins_coverage = exp.get(
                "insurance_coverage", {}
            ).get(event.country, 0)
            if ins_coverage > 0:
                affected += 1
                gap = (
                    ins_coverage
                    * event.magnitude_pct
                    / 100
                )
                total_exposure += gap

        if affected == 0:
            return None

        return DomainImpact(
            domain="Insurance",
            impact_description=(
                f"Coverage adequacy review needed "
                f"for {affected} clients with "
                f"assets in {event.country}"
            ),
            affected_clients=affected,
            estimated_exposure_zar=total_exposure,
            required_actions=[
                (
                    "Revalue insured assets at "
                    "post event rates"
                ),
                (
                    "Flag policies with coverage "
                    "now below 80% of asset value"
                ),
            ],
            urgency="HIGH",
        )

    def _assess_cell_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess cell network impact by estimating
        the change in telco JV revenue contribution
        in ZAR terms.
        """

        cell_revenue = sum(
            exp.get("cell_revenue_local", {}).get(
                event.country, 0
            )
            for exp in exposures.values()
        )

        if cell_revenue == 0:
            return None

        return DomainImpact(
            domain="Cell",
            impact_description=(
                f"Telco JV revenue from "
                f"{event.country} affected by "
                f"{event.magnitude_pct:.1f}% "
                f"currency move"
            ),
            affected_clients=1,
            estimated_exposure_zar=(
                cell_revenue
                * event.magnitude_pct
                / 100
            ),
            required_actions=[
                "Recalculate JV revenue contribution",
                "Review MoMo transaction economics",
            ],
            urgency="MEDIUM",
        )

    def _assess_pbb_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess PBB impact by estimating purchasing
        power changes for employees paid in the
        affected currency.
        """

        affected_employees = 0
        for exp in exposures.values():
            employees = exp.get(
                "pbb_employee_count", {}
            ).get(event.country, 0)
            affected_employees += employees

        if affected_employees == 0:
            return None

        return DomainImpact(
            domain="PBB",
            impact_description=(
                f"{affected_employees} employees "
                f"in {event.country} affected by "
                f"purchasing power decline"
            ),
            affected_clients=affected_employees,
            estimated_exposure_zar=0,
            required_actions=[
                "Predict salary advance demand spike",
                (
                    "Pre approve overdraft limits for "
                    "affected accounts"
                ),
            ],
            urgency="MEDIUM",
        )
