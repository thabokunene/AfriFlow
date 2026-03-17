"""
Currency Event Propagator

When a major FX event occurs, we propagate the impact
across all affected domains and recalculate cross-domain
signals for every affected client.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import logging
from enum import Enum

from afriflow.currency_events.event_classifier import (
    CurrencyEvent,
    EventTier,
)
from afriflow.currency_events.constants import (
    CURRENCY_COUNTRY_MAP,
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB
)
from afriflow.exceptions import CurrencyPropagationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("currency_events.propagator")


@dataclass
class DomainImpact:
    """
    We represent the impact of a currency event on
    a specific domain for a specific client.
    """

    golden_id: str
    domain: str
    impact_type: str
    description: str
    impact_value_zar: float
    action_required: bool
    recommended_action: str
    urgency: str


@dataclass
class PropagationResult:
    """
    We collect all domain impacts from propagating
    a currency event.
    """

    event: CurrencyEvent
    total_clients_affected: int
    total_exposure_zar: float
    domain_impacts: List[DomainImpact]
    propagation_timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    @property
    def summary(self) -> Dict:
        """We generate a summary for ExCo reporting."""

        domain_counts = {}
        for impact in self.domain_impacts:
            domain_counts[impact.domain] = (
                domain_counts.get(impact.domain, 0) + 1
            )

        return {
            "event_id": self.event.event_id,
            "currency": self.event.currency_code,
            "tier": self.event.event_tier.value,
            "magnitude_pct": self.event.magnitude_pct,
            "clients_affected": (
                self.total_clients_affected
            ),
            "total_exposure_zar": self.total_exposure_zar,
            "impacts_by_domain": domain_counts,
            "actions_required": sum(
                1 for i in self.domain_impacts
                if i.action_required
            ),
            "propagation_timestamp": (
                self.propagation_timestamp
            )
        }


class CurrencyEventPropagator:
    """
    We propagate currency events across all five domains
    for every affected client.
    """

    def __init__(self):
        self.client_exposures: Dict[
            str, Dict[str, Dict]
        ] = {}
        logger.debug("CurrencyEventPropagator initialized")

    def register_client_exposure(
        self,
        golden_id: str,
        currency: str,
        domain: str,
        exposure_details: Dict
    ):
        """
        We register a client's exposure to a currency
        in a specific domain.
        """

        if golden_id not in self.client_exposures:
            self.client_exposures[golden_id] = {}

        key = f"{currency}:{domain}"
        self.client_exposures[golden_id][key] = (
            exposure_details
        )

    def propagate(
        self, event: CurrencyEvent
    ) -> PropagationResult:
        """
        We propagate a currency event across all
        affected domains and clients.
        """

        impacts = []
        affected_clients = set()
        total_exposure = 0.0

        currency = event.currency_code
        country = CURRENCY_COUNTRY_MAP.get(
            currency, "UNKNOWN"
        )

        for golden_id, exposures in (
            self.client_exposures.items()
        ):
            client_impacts = []

            # CIB impact
            cib_key = f"{currency}:{DOMAIN_CIB}"
            if (
                cib_key in exposures
                and DOMAIN_CIB in event.affected_domains
            ):
                cib_exp = exposures[cib_key]
                impact = self._calculate_cib_impact(
                    golden_id, cib_exp, event
                )
                if impact:
                    client_impacts.append(impact)

            # Forex impact
            forex_key = f"{currency}:{DOMAIN_FOREX}"
            if (
                forex_key in exposures
                and DOMAIN_FOREX in event.affected_domains
            ):
                forex_exp = exposures[forex_key]
                impact = self._calculate_forex_impact(
                    golden_id, forex_exp, event
                )
                if impact:
                    client_impacts.append(impact)

            # Insurance impact
            ins_key = f"{currency}:{DOMAIN_INSURANCE}"
            if (
                ins_key in exposures
                and DOMAIN_INSURANCE in event.affected_domains
            ):
                ins_exp = exposures[ins_key]
                impact = self._calculate_insurance_impact(
                    golden_id, ins_exp, event
                )
                if impact:
                    client_impacts.append(impact)

            # Cell/MoMo impact
            cell_key = f"{currency}:{DOMAIN_CELL}"
            if (
                cell_key in exposures
                and DOMAIN_CELL in event.affected_domains
            ):
                cell_exp = exposures[cell_key]
                impact = self._calculate_cell_impact(
                    golden_id, cell_exp, event
                )
                if impact:
                    client_impacts.append(impact)

            # PBB impact
            pbb_key = f"{currency}:{DOMAIN_PBB}"
            if (
                pbb_key in exposures
                and DOMAIN_PBB in event.affected_domains
            ):
                pbb_exp = exposures[pbb_key]
                impact = self._calculate_pbb_impact(
                    golden_id, pbb_exp, event
                )
                if impact:
                    client_impacts.append(impact)

            if client_impacts:
                affected_clients.add(golden_id)
                impacts.extend(client_impacts)
                total_exposure += sum(
                    abs(i.impact_value_zar)
                    for i in client_impacts
                )

        logger.info(
            f"Propagated {event.event_id}: {len(affected_clients)} clients affected, "
            f"R{total_exposure:,.2f} total exposure"
        )

        return PropagationResult(
            event=event,
            total_clients_affected=len(
                affected_clients
            ),
            total_exposure_zar=total_exposure,
            domain_impacts=impacts
        )

    def _calculate_cib_impact(
        self,
        golden_id: str,
        exposure: Dict,
        event: CurrencyEvent
    ) -> Optional[DomainImpact]:
        """
        We calculate the CIB impact of a currency event.
        """

        facility_value = exposure.get(
            "facility_value_local", 0
        )
        utilization = exposure.get("utilization_pct", 0)

        if facility_value <= 0:
            return None

        # After devaluation, the same USD imports cost
        # more in local currency
        new_cost_ratio = 1 + (
            event.magnitude_pct / 100
        )
        effective_utilization = (
            utilization * new_cost_ratio
        )

        if effective_utilization > 90:
            return DomainImpact(
                golden_id=golden_id,
                domain=DOMAIN_CIB,
                impact_type="FACILITY_INADEQUACY",
                description=(
                    f"Trade finance facility utilization "
                    f"rises from {utilization:.0f}% to "
                    f"{effective_utilization:.0f}% after "
                    f"{event.currency_code} "
                    f"{event.magnitude_pct:.1f}% move"
                ),
                impact_value_zar=(
                    facility_value
                    * (effective_utilization - 100)
                    / 100
                ),
                action_required=True,
                recommended_action=(
                    "Review and increase trade finance "
                    "facility limit or restructure to "
                    "USD-denominated facility"
                ),
                urgency=(
                    "IMMEDIATE"
                    if effective_utilization > 100
                    else "HIGH"
                )
            )

        return None

    def _calculate_forex_impact(
        self,
        golden_id: str,
        exposure: Dict,
        event: CurrencyEvent
    ) -> Optional[DomainImpact]:
        """
        We calculate the forex impact by marking
        forward positions to market.
        """

        forward_notional = exposure.get(
            "forward_notional_zar", 0
        )
        booked_rate = exposure.get("booked_rate", 0)

        if forward_notional <= 0 or booked_rate <= 0:
            return None

        mtm_impact = (
            forward_notional
            * event.magnitude_pct
            / 100
        )

        return DomainImpact(
            golden_id=golden_id,
            domain=DOMAIN_FOREX,
            impact_type="MTM_REVALUATION",
            description=(
                f"Forward position MTM impact: "
                f"R{abs(mtm_impact):,.0f} "
                f"{'gain' if mtm_impact > 0 else 'loss'} "
                f"on {event.currency_code} forwards"
            ),
            impact_value_zar=mtm_impact,
            action_required=abs(mtm_impact) > 1_000_000,
            recommended_action=(
                "Review counterparty credit exposure "
                "and margin requirements"
                if abs(mtm_impact) > 1_000_000
                else "Monitor position"
            ),
            urgency=(
                "HIGH"
                if abs(mtm_impact) > 5_000_000
                else "MEDIUM"
            )
        )

    def _calculate_insurance_impact(
        self,
        golden_id: str,
        exposure: Dict,
        event: CurrencyEvent
    ) -> Optional[DomainImpact]:
        """
        We calculate insurance coverage adequacy after
        currency devaluation.
        """

        coverage_value_local = exposure.get(
            "coverage_value_local", 0
        )
        asset_value_usd = exposure.get(
            "asset_value_usd", 0
        )

        if (
            coverage_value_local <= 0
            or asset_value_usd <= 0
        ):
            return None

        # After devaluation, local currency coverage
        # is worth less in USD terms
        coverage_reduction_pct = event.magnitude_pct

        return DomainImpact(
            golden_id=golden_id,
            domain=DOMAIN_INSURANCE,
            impact_type="COVERAGE_INADEQUACY",
            description=(
                f"Insurance coverage value in USD terms "
                f"reduced by {coverage_reduction_pct:.1f}% "
                f"after {event.currency_code} devaluation. "
                f"Assets may be underinsured."
            ),
            impact_value_zar=(
                coverage_value_local
                * coverage_reduction_pct
                / 100
            ),
            action_required=coverage_reduction_pct > 5,
            recommended_action=(
                "Contact insurance broker to review "
                "coverage adequacy and adjust sum "
                "insured to reflect current FX rate"
            ),
            urgency=(
                "HIGH"
                if coverage_reduction_pct > 10
                else "MEDIUM"
            )
        )

    def _calculate_cell_impact(
        self,
        golden_id: str,
        exposure: Dict,
        event: CurrencyEvent
    ) -> Optional[DomainImpact]:
        """
        We recalculate MoMo corridor values after
        currency moves.
        """

        momo_monthly_local = exposure.get(
            "momo_monthly_volume_local", 0
        )

        if momo_monthly_local <= 0:
            return None

        # MoMo values in ZAR terms change with the rate
        zar_impact = (
            momo_monthly_local
            * event.magnitude_pct
            / 100
        )

        return DomainImpact(
            golden_id=golden_id,
            domain=DOMAIN_CELL,
            impact_type="MOMO_VALUE_ADJUSTMENT",
            description=(
                f"MoMo corridor values in ZAR terms "
                f"adjusted by {event.magnitude_pct:.1f}% "
                f"due to {event.currency_code} movement"
            ),
            impact_value_zar=zar_impact,
            action_required=False,
            recommended_action=(
                "Corridor analytics automatically "
                "recalculated. No action required."
            ),
            urgency="LOW"
        )

    def _calculate_pbb_impact(
        self,
        golden_id: str,
        exposure: Dict,
        event: CurrencyEvent
    ) -> Optional[DomainImpact]:
        """
        We estimate PBB impact from employee
        purchasing power changes.
        """

        employee_count = exposure.get(
            "employee_count", 0
        )

        if employee_count <= 0:
            return None

        # Devaluation reduces purchasing power,
        # driving salary advance demand
        if event.magnitude_pct > 10:
            estimated_advance_demand = (
                employee_count * 500
            )

            return DomainImpact(
                golden_id=golden_id,
                domain=DOMAIN_PBB,
                impact_type="SALARY_ADVANCE_DEMAND",
                description=(
                    f"Estimated {employee_count} employees "
                    f"affected by {event.magnitude_pct:.1f}% "
                    f"{event.currency_code} devaluation. "
                    f"Salary advance demand likely to spike."
                ),
                impact_value_zar=estimated_advance_demand,
                action_required=employee_count > 100,
                recommended_action=(
                    "Pre-approve salary advance facility "
                    "for corporate payroll clients in "
                    "affected currency zone"
                ),
                urgency=(
                    "HIGH"
                    if employee_count > 500
                    else "MEDIUM"
                )
            )

        return None
