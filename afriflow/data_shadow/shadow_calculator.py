"""
Data Shadow Calculator

We compute the expected data footprint for each client
across all domains and identify shadows (gaps between
expected and actual presence).

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging
from enum import Enum

from afriflow.data_shadow.expectation_rules import (
    ExpectationRuleEngine,
)
from afriflow.exceptions import DataShadowError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("data_shadow.calculator")


@dataclass
class DomainShadow:
    """
    We represent a gap between expected and actual
    domain presence for a client in a country.
    """

    shadow_id: str
    golden_id: str
    country_code: str
    expected_domain: str
    expectation_source: str
    expectation_rule: str
    confidence_pct: float
    estimated_revenue_zar: float
    shadow_type: str
    first_detected: str
    status: str = "ACTIVE"

    @property
    def expected_country(self) -> str:
        return self.country_code

    @property
    def estimated_revenue_opportunity_zar(self) -> float:
        return self.estimated_revenue_zar

    @property
    def category(self):
        try:
            return ShadowCategory[self.shadow_type]
        except Exception:
            return self.shadow_type

@dataclass
class ClientFootprint:
    """
    We represent a client's actual data presence
    across domains and countries.
    """

    golden_id: str
    domain_country_presence: Dict[str, Set[str]]
    # domain -> set of country codes


class ShadowCategory(Enum):
    COMPETITIVE_LEAKAGE = "COMPETITIVE_LEAKAGE"
    COVERAGE_GAP = "COVERAGE_GAP"
    PAYROLL_CAPTURE_OPPORTUNITY = "PAYROLL_CAPTURE_OPPORTUNITY"
    INSURANCE_GAP = "INSURANCE_GAP"
    TELCOPARTNERSHIP_OPPORTUNITY = "TELCOPARTNERSHIP_OPPORTUNITY"


class ShadowCalculator:
    """
    We calculate data shadows by comparing expected
    domain presence (derived from cross-domain
    inference rules) against actual domain presence.

    The shadows tell us where revenue is leaking to
    competitors or where risk is unmonitored.
    """

    def __init__(self):
        self.rule_engine = ExpectationRuleEngine()
        self.actual_footprints: Dict[
            str, ClientFootprint
        ] = {}

    def register_actual_presence(
        self,
        golden_id: str,
        domain: str,
        country_code: str
    ):
        """
        We register that a client has actual presence
        in a domain in a country.
        """

        if golden_id not in self.actual_footprints:
            self.actual_footprints[golden_id] = (
                ClientFootprint(
                    golden_id=golden_id,
                    domain_country_presence={}
                )
            )

        footprint = self.actual_footprints[golden_id]

        if domain not in footprint.domain_country_presence:
            footprint.domain_country_presence[domain] = (
                set()
            )

        footprint.domain_country_presence[domain].add(
            country_code
        )

    def calculate_shadows(
        self,
        golden_id: str,
        client_metadata: Dict,
        actual_presence: Optional[Dict[str, Set[str]]] = None
    ) -> List[DomainShadow]:
        """
        We calculate all shadows for a client by
        applying expectation rules against actual
        presence.
        """
        
        # Prefer passed actual_presence, fallback to registered footprint
        if actual_presence is None:
            footprint = self.actual_footprints.get(golden_id)
            if footprint:
                actual_presence = footprint.domain_country_presence
            else:
                actual_presence = {}

        # Get all expected presences from rules
        expectations = (
            self.rule_engine.compute_expectations(
                golden_id=golden_id,
                actual_presence=actual_presence,
                client_metadata=client_metadata
            )
        )

        shadows = []

        for expectation in expectations:
            domain = expectation["domain"]
            country = expectation["country"]

            # Check if actual presence exists
            actual_countries = actual_presence.get(domain, set())

            if country not in actual_countries:
                shadow = DomainShadow(
                    shadow_id=(
                        f"SHD-{golden_id}-{domain}"
                        f"-{country}"
                        f"-{datetime.now():%Y%m%d}"
                    ),
                    golden_id=golden_id,
                    country_code=country,
                    expected_domain=domain,
                    expectation_source=(
                        expectation["source_domain"]
                    ),
                    expectation_rule=(
                        expectation["rule_name"]
                    ),
                    confidence_pct=(
                        expectation["confidence"]
                    ),
                    estimated_revenue_zar=(
                        expectation.get("estimated_revenue_zar", 0.0)
                    ),
                    shadow_type=(
                        expectation["shadow_type"]
                    ),
                    first_detected=(
                        datetime.now().strftime(
                            "%Y-%m-%d"
                        )
                    )
                )
                shadows.append(shadow)

        return sorted(
            shadows,
            key=lambda s: s.estimated_revenue_zar,
            reverse=True
        )

    def get_shadow_summary(
        self, golden_id: str
    ) -> Dict:
        """
        We generate a summary of all shadows for a
        client, suitable for the RM briefing.
        """

        shadows = self.calculate_shadows(
            golden_id,
            client_metadata={}
        )

        if not shadows:
            return {
                "golden_id": golden_id,
                "total_shadows": 0,
                "total_estimated_leakage_zar": 0,
                "shadows_by_domain": {},
                "shadows_by_country": {}
            }

        by_domain = {}
        by_country = {}

        for shadow in shadows:
            domain = shadow.expected_domain
            country = shadow.country_code

            if domain not in by_domain:
                by_domain[domain] = {
                    "count": 0,
                    "estimated_revenue_zar": 0
                }
            by_domain[domain]["count"] += 1
            by_domain[domain][
                "estimated_revenue_zar"
            ] += shadow.estimated_revenue_zar

            if country not in by_country:
                by_country[country] = {
                    "count": 0,
                    "estimated_revenue_zar": 0
                }
            by_country[country]["count"] += 1
            by_country[country][
                "estimated_revenue_zar"
            ] += shadow.estimated_revenue_zar

        return {
            "golden_id": golden_id,
            "total_shadows": len(shadows),
            "total_estimated_leakage_zar": sum(
                s.estimated_revenue_zar for s in shadows
            ),
            "shadows_by_domain": by_domain,
            "shadows_by_country": by_country
        }
