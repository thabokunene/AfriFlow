"""
@file shadow_calculator.py
@description Core calculation logic for data shadow detection. Compares a
             client's actual cross-domain footprint against expected domain
             presence (derived from the ExpectationRuleEngine) to identify
             gaps. Quantifies these gaps as 'DomainShadow' objects, which include
             estimated revenue opportunities and confidence scores.
@author Thabo Kunene
@created 2026-03-19
"""

# Data Shadow Calculator
#
# We compute the expected data footprint for each client
# across all domains and identify shadows (gaps between
# expected and actual presence).
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data classes, typing, and dates
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import logging
from enum import Enum

# Rule engine, exceptions, and logging configuration
from afriflow.data_shadow.expectation_rules import (
    ExpectationRuleEngine,
)
from afriflow.exceptions import DataShadowError
from afriflow.logging_config import get_logger, log_operation

# Initialise a module-scoped logger for shadow calculation events
logger = get_logger("data_shadow.calculator")


@dataclass
class DomainShadow:
    """
    Represents a gap between expected and actual domain presence for a client.

    :param shadow_id: Unique identifier for the shadow instance
    :param golden_id: Unified client identifier
    :param country_code: ISO-2 country where the gap exists
    :param expected_domain: The domain missing from the client relationship
    :param expectation_source: The domain that triggered the expectation
    :param expectation_rule: The specific logic rule that identified the gap
    :param confidence_pct: Probability that the identified gap is a real opportunity
    :param estimated_revenue_zar: Rough estimate of ZAR value for this gap
    :param shadow_type: High-level classification of the shadow
    :param first_detected: ISO date when this shadow was first identified
    :param status: Current state of the shadow (e.g., 'ACTIVE', 'RESOLVED')
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
        """
        Convenience property for the country code.
        """
        return self.country_code

    @property
    def estimated_revenue_opportunity_zar(self) -> float:
        """
        Convenience property for the revenue estimate.
        """
        return self.estimated_revenue_zar

    @property
    def category(self) -> Any:
        """
        Maps the raw shadow type string to a structured ShadowCategory enum.
        """
        try:
            return ShadowCategory[self.shadow_type]
        except (KeyError, ValueError):
            # Fallback to raw string if enum mapping fails
            return self.shadow_type


@dataclass
class ClientFootprint:
    """
    Represents a client's actual data presence across countries and domains.

    :param golden_id: Unified client identifier
    :param domain_country_presence: Mapping of domain -> set of ISO-2 country codes
    """

    golden_id: str
    domain_country_presence: Dict[str, Set[str]]


class ShadowCategory(Enum):
    """
    High-level business categories for identified data shadows.
    """
    # Client using a competitor for a known need
    COMPETITIVE_LEAKAGE = "COMPETITIVE_LEAKAGE"
    # Relationship exists but lacks a specific coverage type
    COVERAGE_GAP = "COVERAGE_GAP"
    # High probability opportunity to capture payroll flows
    PAYROLL_CAPTURE_OPPORTUNITY = "PAYROLL_CAPTURE_OPPORTUNITY"
    # Missing commercial or specialized insurance product
    INSURANCE_GAP = "INSURANCE_GAP"
    # Opportunity for joint SBG/MTN service offering
    TELCOPARTNERSHIP_OPPORTUNITY = "TELCOPARTNERSHIP_OPPORTUNITY"


class ShadowCalculator:
    """
    Orchestrates the detection of data shadows for client relationships.
    """

    def __init__(self, rule_engine: Optional[ExpectationRuleEngine] = None) -> None:
        """
        Initialise the calculator with an expectation rule engine.

        :param rule_engine: Optional engine instance; defaults to a new one.
        """
        self.rule_engine = rule_engine or ExpectationRuleEngine()
        # In-memory store for client presence data
        self.actual_footprints: Dict[str, ClientFootprint] = {}
        logger.debug("ShadowCalculator initialized")

    def register_actual_presence(
        self,
        golden_id: str,
        domain: str,
        country_code: str
    ) -> None:
        """
        Update the internal registry with verified client activity.

        :param golden_id: Unified client identifier
        :param domain: The business domain where activity was seen
        :param country_code: The ISO-2 country code of the activity
        """
        # Ensure the client footprint object exists in the registry
        if golden_id not in self.actual_footprints:
            self.actual_footprints[golden_id] = ClientFootprint(
                golden_id=golden_id,
                domain_country_presence={}
            )

        footprint = self.actual_footprints[golden_id]

        # Initialize the set for the domain if it doesn't exist
        if domain not in footprint.domain_country_presence:
            footprint.domain_country_presence[domain] = set()

        # Add the country to the domain's presence set
        footprint.domain_country_presence[domain].add(country_code)

    def calculate_shadows(
        self,
        golden_id: str,
        client_metadata: Dict,
        actual_presence: Optional[Dict[str, Set[str]]] = None
    ) -> List[DomainShadow]:
        """
        Identify data shadows for a client by comparing rules against reality.

        :param golden_id: Unified client identifier
        :param client_metadata: Domain-specific metrics for the client
        :param actual_presence: Optional override for verified presence
        :return: A list of identified DomainShadow objects, sorted by confidence.
        """
        # --- Footprint resolution logic ---
        # Prefer the explicitly passed actual_presence, otherwise use the internal registry.
        if actual_presence is None:
            footprint = self.actual_footprints.get(golden_id)
            if footprint:
                actual_presence = footprint.domain_country_presence
            else:
                # If no presence data is found, we assume no domains are active
                actual_presence = {}

        # --- Rule evaluation phase ---
        # Use the rule engine to determine what we *expect* to see for this client.
        expectations = self.rule_engine.compute_expectations(
            golden_id=golden_id,
            actual_presence=actual_presence,
            client_metadata=client_metadata
        )

        shadows = []

        # --- Gap detection phase ---
        # Iterate through expectations and check if they are satisfied by actual presence.
        for expectation in expectations:
            domain = expectation["domain"]
            country = expectation["country"]

            # Lookup countries where the client actually has a relationship in this domain
            actual_countries = actual_presence.get(domain, set())

            # If the expected country is missing from actual presence, we have a shadow
            if country not in actual_countries:
                now = datetime.now()
                # Create a structured shadow record with a unique identifier
                shadow = DomainShadow(
                    shadow_id=(
                        f"SHD-{golden_id}-{domain}-{country}-{now:%Y%m%d}"
                    ),
                    golden_id=golden_id,
                    country_code=country,
                    expected_domain=domain,
                    expectation_source=expectation["source_domain"],
                    expectation_rule=expectation["rule_name"],
                    confidence_pct=expectation["confidence"],
                    estimated_revenue_zar=expectation.get("estimated_revenue_zar", 0.0),
                    shadow_type=expectation["shadow_type"],
                    first_detected=now.strftime("%Y-%m-%d")
                )
                shadows.append(shadow)

        # Return shadows sorted by confidence descending (most likely opportunities first)
        return sorted(
            shadows,
            key=lambda x: x.confidence_pct,
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
