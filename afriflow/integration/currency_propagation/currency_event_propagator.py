"""
@file currency_event_propagator.py
@description Currency Event Propagation Engine for the AfriFlow integration layer.
             When a major FX event is detected, this module propagates the impact
             across all five domains (CIB, Forex, Insurance, Cell, PBB) and
             assembles a unified PropagationResult for RM briefings and ExCo reports.
             Treats FX events as systemic cross-domain shocks rather than
             isolated treasury risks.
@author Thabo Kunene
@created 2026-03-18

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

from dataclasses import dataclass, field  # structured value objects for events and impacts
from datetime import datetime             # timestamp generation for PropagationResult
from typing import Dict, List, Optional  # type annotations throughout
from enum import Enum                    # strongly typed event classifications


# All recognised major currency event types in African markets.
# CURRENCY_PEG_BREAK is particularly important for CFA franc zone countries
# (Côte d'Ivoire, Senegal, etc.) where a peg break would be a once-in-a-generation event.
class CurrencyEventType(Enum):
    DEVALUATION = "DEVALUATION"
    CAPITAL_CONTROL_CHANGE = "CAPITAL_CONTROL_CHANGE"
    CENTRAL_BANK_RATE_MOVE = "CENTRAL_BANK_RATE_MOVE"
    PARALLEL_MARKET_DIVERGENCE = "PARALLEL_MARKET_DIVERGENCE"
    CURRENCY_PEG_BREAK = "CURRENCY_PEG_BREAK"


@dataclass
class CurrencyEvent:
    """
    A detected major currency event.

    :param event_id: Unique event identifier
    :param currency: ISO 4217 currency code (e.g. NGN, ZAR, KES)
    :param country: ISO 3166-1 alpha-2 country code of the affected market
    :param event_type: Classification from CurrencyEventType enum
    :param magnitude_pct: Percentage rate movement that triggered the event
    :param event_date: ISO date when the event occurred
    :param description: Human-readable description of the event
    """

    event_id: str
    currency: str
    country: str
    event_type: CurrencyEventType
    magnitude_pct: float
    event_date: str
    description: str


@dataclass
class DomainImpact:
    """
    Impact of a currency event on a single domain.

    :param domain: Domain name (CIB, Forex, Insurance, Cell, PBB)
    :param impact_description: Narrative description of the impact
    :param affected_clients: Count of affected clients in this domain
    :param estimated_exposure_zar: Total ZAR-denominated exposure estimate
    :param required_actions: Ordered list of recommended follow-up actions
    :param urgency: Urgency level (IMMEDIATE, HIGH, MEDIUM, LOW)
    """

    domain: str
    impact_description: str
    affected_clients: int
    estimated_exposure_zar: float
    required_actions: List[str]
    urgency: str


@dataclass
class PropagationResult:
    """
    Full propagation result across all domains for a currency event.

    :param event: The triggering CurrencyEvent
    :param cib_impact: CIB domain impact or None if no CIB exposure
    :param forex_impact: Forex domain impact or None if no open positions
    :param insurance_impact: Insurance domain impact or None if no policies
    :param cell_impact: Cell/telco JV impact or None if no JV in affected country
    :param pbb_impact: PBB payroll impact or None if no employees affected
    :param total_affected_clients: Sum of affected clients across all domains
    :param total_exposure_zar: Sum of estimated ZAR exposure across all domains
    :param generated_at: ISO timestamp when this result was assembled
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

    # Minimum percentage move to trigger full propagation.
    # Moves below this threshold are considered within normal
    # volatility range and do not require cross-domain action.
    DEVALUATION_THRESHOLD_PCT = 5.0

    # Minimum central bank rate move in basis points to trigger
    # cross-domain propagation (100 bps = 1 percentage point)
    RATE_MOVE_THRESHOLD_BPS = 100

    # Minimum spread between official and parallel market rate (%)
    # before parallel divergence triggers propagation
    PARALLEL_SPREAD_THRESHOLD_PCT = 10.0

    def propagate(
        self,
        event: CurrencyEvent,
        client_exposures: Dict[str, Dict],
    ) -> PropagationResult:
        """
        Propagate a currency event across all domains for all affected clients.

        We accept a dictionary of client exposures keyed by golden_id,
        where each entry contains the client's exposure in each domain
        to the affected currency.

        :param event: The detected CurrencyEvent to propagate
        :param client_exposures: Dict of golden_id → exposure dict.
               Each exposure dict may contain keys:
               - cib_corridor_value: {country: ZAR value}
               - forex_open_positions: {currency: notional}
               - insurance_coverage: {country: coverage value}
               - cell_revenue_local: {country: revenue}
               - pbb_employee_count: {country: count}
        :return: PropagationResult with per-domain impacts and totals
        """

        # Assess each domain independently — domain logic is fully isolated
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

        # Collect only non-None impacts for aggregation
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

        # Sum affected clients and total ZAR exposure across all domains
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
        We assess CIB impact by checking open trade finance
        facilities and payment corridors denominated in the
        affected currency.

        :param event: The triggering CurrencyEvent
        :param exposures: Per-client exposure dictionary
        :return: DomainImpact or None if no CIB exposure exists
        """

        affected = 0
        total_exposure = 0.0

        # Iterate over all clients and accumulate corridor exposure
        for golden_id, exp in exposures.items():
            # cib_corridor_value is a dict of country → ZAR value
            cib_exposure = exp.get(
                "cib_corridor_value", {}
            ).get(event.country, 0)
            if cib_exposure > 0:
                affected += 1
                # Estimate impact = corridor value × magnitude percentage
                impact = (
                    cib_exposure
                    * event.magnitude_pct
                    / 100
                )
                total_exposure += impact

        # Return None if no clients have CIB exposure in this market
        if affected == 0:
            return None

        # Ordered action list — first action is the most urgent
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
            # Moves above 10% are treated as IMMEDIATE (intraday response required)
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
        We assess forex impact by marking to market open positions
        in the affected currency.

        Note: forex impact is always IMMEDIATE because open positions
        are live and must be repriced as soon as a significant move is
        detected.

        :param event: The triggering CurrencyEvent
        :param exposures: Per-client exposure dictionary
        :return: DomainImpact or None if no open FX positions exist
        """

        affected = 0
        total_exposure = 0.0

        for golden_id, exp in exposures.items():
            # forex_open_positions is a dict of currency → notional ZAR value
            fx_exposure = exp.get(
                "forex_open_positions", {}
            ).get(event.currency, 0)
            if fx_exposure > 0:
                affected += 1
                # Accumulate the raw notional; MTM gains/losses are handled
                # separately by the FX desk at the position level
                total_exposure += fx_exposure

        # No open positions in this currency — no forex impact to report
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
            # Forex positions must be repriced immediately — always IMMEDIATE
            urgency="IMMEDIATE",
        )

    def _assess_insurance_impact(
        self,
        event: CurrencyEvent,
        exposures: Dict[str, Dict],
    ) -> Optional[DomainImpact]:
        """
        We assess insurance impact by checking coverage adequacy
        at post-event valuations.

        When a currency devalues, the local-currency value of insured
        assets in ZAR terms falls. If the insurance policy is denominated
        in local currency, the coverage gap grows proportionally.

        :param event: The triggering CurrencyEvent
        :param exposures: Per-client exposure dictionary
        :return: DomainImpact or None if no insurance policies in affected country
        """

        affected = 0
        total_exposure = 0.0

        for golden_id, exp in exposures.items():
            # insurance_coverage is a dict of country → coverage value in ZAR
            ins_coverage = exp.get(
                "insurance_coverage", {}
            ).get(event.country, 0)
            if ins_coverage > 0:
                affected += 1
                # The coverage gap = coverage value × devaluation magnitude.
                # A 15% devaluation creates a 15% coverage shortfall.
                gap = (
                    ins_coverage
                    * event.magnitude_pct
                    / 100
                )
                total_exposure += gap

        # No insurance exposure in this country — skip
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
                # Flag policies whose coverage has fallen below the 80% threshold
                # as these may trigger automatic under-insurance clauses
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
        We assess cell network impact by estimating the change in
        telco JV revenue contribution in ZAR terms.

        Cell revenue is calculated at country level across all clients,
        then expressed as a single group-level DomainImpact. Individual
        client attribution is not relevant for JV revenue reporting.

        :param event: The triggering CurrencyEvent
        :param exposures: Per-client exposure dictionary
        :return: DomainImpact or None if no cell revenue in affected country
        """

        # Sum cell revenue across all clients for this country.
        # cell_revenue_local is a dict of country → local-currency revenue.
        cell_revenue = sum(
            exp.get("cell_revenue_local", {}).get(
                event.country, 0
            )
            for exp in exposures.values()
        )

        # No MTN operations in this country — no cell impact
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
            # JV revenue is reported as one group-level client entry
            affected_clients=1,
            # ZAR-equivalent revenue reduction from currency move
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
        We assess PBB impact by estimating purchasing power changes
        for employees paid in the affected currency.

        When a currency devalues, employees' salaries buy less in
        both local and hard-currency terms. This predictably drives
        increased demand for salary advances and overdraft facilities.

        :param event: The triggering CurrencyEvent
        :param exposures: Per-client exposure dictionary
        :return: DomainImpact or None if no employees in affected country
        """

        # Count the total number of employees in the affected country
        # across all corporate clients
        affected_employees = 0
        for exp in exposures.values():
            # pbb_employee_count is a dict of country → employee headcount
            employees = exp.get(
                "pbb_employee_count", {}
            ).get(event.country, 0)
            affected_employees += employees

        # No employees in this market — no PBB impact to report
        if affected_employees == 0:
            return None

        return DomainImpact(
            domain="PBB",
            impact_description=(
                f"{affected_employees} employees "
                f"in {event.country} affected by "
                f"purchasing power decline"
            ),
            # affected_clients here represents employee count, not corporate entities
            affected_clients=affected_employees,
            # ZAR financial impact is not directly quantifiable at this stage
            # (depends on advance uptake rate); set to 0 as a placeholder
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
