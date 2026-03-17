"""
DATA SHADOW CALCULATOR

We compute the expected data footprint for every client across all five
domains. We compare what we expect to see against what we actually see.
The gaps (shadows) are themselves valuable intelligence.

In developed markets, missing data is noise. In Africa, missing data
is signal.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
from datetime import datetime


class ShadowCategory(Enum):
    COMPETITIVE_LEAKAGE = "COMPETITIVE_LEAKAGE"
    COVERAGE_GAP = "COVERAGE_GAP"
    DATA_FEED_ISSUE = "DATA_FEED_ISSUE"
    DORMANT_RELATIONSHIP = "DORMANT_RELATIONSHIP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class DataShadow:
    """A detected gap between expected and actual data presence."""

    shadow_id: str
    client_golden_id: str
    client_name: str
    expected_domain: str
    expected_country: Optional[str]
    category: ShadowCategory
    source_domain: str
    source_evidence: str
    estimated_revenue_opportunity_zar: float
    confidence: float
    recommended_action: str
    detected_at: str


@dataclass
class ExpectedDomainPresence:
    """What we expect to see for a client in a given domain."""

    domain: str
    country: str
    reason: str
    confidence: float
    source_domain: str
    source_metric: str


class ShadowRule:
    """
    A rule that infers expected domain presence from
    observed data in another domain.
    """

    def __init__(
        self,
        name: str,
        source_domain: str,
        expected_domain: str,
        condition_fn,
        confidence: float,
        shadow_category: ShadowCategory,
        description: str,
    ):
        self.name = name
        self.source_domain = source_domain
        self.expected_domain = expected_domain
        self.condition_fn = condition_fn
        self.confidence = confidence
        self.shadow_category = shadow_category
        self.description = description


class DataShadowCalculator:
    """
    Calculates data shadows for all resolved clients by
    comparing expected domain presence against actual
    domain presence in the golden record.
    """

    MTN_COVERAGE_COUNTRIES = {
        "ZA", "NG", "GH", "UG", "RW", "ZM", "MZ",
        "CI", "CM", "BJ", "CG", "GW", "LR", "SD",
        "SS", "SZ", "BW",
    }

    def __init__(self):
        self.rules: List[ShadowRule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register the default cross domain inference rules."""

        self.rules.append(ShadowRule(
            name="cib_implies_forex",
            source_domain="cib",
            expected_domain="forex",
            condition_fn=self._cib_has_foreign_currency_payments,
            confidence=0.85,
            shadow_category=ShadowCategory.COMPETITIVE_LEAKAGE,
            description=(
                "Client has CIB payments in foreign currencies "
                "but no corresponding forex activity with us. "
                "They are likely hedging with a competitor."
            ),
        ))

        self.rules.append(ShadowRule(
            name="cib_implies_cell",
            source_domain="cib",
            expected_domain="cell",
            condition_fn=self._cib_in_mtn_country,
            confidence=0.70,
            shadow_category=ShadowCategory.COMPETITIVE_LEAKAGE,
            description=(
                "Client has CIB activity in an MTN coverage "
                "country but no cell data. They may use a "
                "competitor telco network."
            ),
        ))

        self.rules.append(ShadowRule(
            name="cell_implies_pbb",
            source_domain="cell",
            expected_domain="pbb",
            condition_fn=self._cell_has_significant_sims,
            confidence=0.75,
            shadow_category=ShadowCategory.COMPETITIVE_LEAKAGE,
            description=(
                "Client has significant corporate SIM presence "
                "but employees are not banking with us. "
                "Payroll capture opportunity."
            ),
        ))

        self.rules.append(ShadowRule(
            name="cib_implies_insurance",
            source_domain="cib",
            expected_domain="insurance",
            condition_fn=self._cib_has_physical_operations,
            confidence=0.65,
            shadow_category=ShadowCategory.COVERAGE_GAP,
            description=(
                "Client has significant CIB activity indicating "
                "physical operations but no insurance coverage "
                "with us."
            ),
        ))

        self.rules.append(ShadowRule(
            name="cib_forex_hedge_gap",
            source_domain="forex",
            expected_domain="forex",
            condition_fn=self._forex_has_hedge_gap,
            confidence=0.80,
            shadow_category=ShadowCategory.COVERAGE_GAP,
            description=(
                "Client trades FX spot regularly but has "
                "insufficient forward or option hedging. "
                "They may be carrying unhedged exposure."
            ),
        ))

    def _cib_has_foreign_currency_payments(
        self, client_data: Dict
    ) -> Optional[List[str]]:
        """Check if client has CIB payments in foreign currencies."""

        cib = client_data.get("cib", {})
        foreign_corridors = cib.get("foreign_corridors", [])

        if len(foreign_corridors) > 0:
            return [c["country"] for c in foreign_corridors]
        return None

    def _cib_in_mtn_country(
        self, client_data: Dict
    ) -> Optional[List[str]]:
        """Check if client has CIB in MTN coverage countries."""

        cib = client_data.get("cib", {})
        active_countries = set(cib.get("active_countries", []))
        mtn_overlap = active_countries & self.MTN_COVERAGE_COUNTRIES

        if len(mtn_overlap) > 0:
            return list(mtn_overlap)
        return None

    def _cell_has_significant_sims(
        self, client_data: Dict
    ) -> Optional[List[str]]:
        """Check if client has 50 or more corporate SIMs."""

        cell = client_data.get("cell", {})
        countries_with_sims = []

        for country, metrics in cell.get("by_country", {}).items():
            if metrics.get("sim_count", 0) >= 50:
                countries_with_sims.append(country)

        return countries_with_sims if countries_with_sims else None

    def _cib_has_physical_operations(
        self, client_data: Dict
    ) -> Optional[List[str]]:
        """Check if CIB activity suggests physical operations."""

        cib = client_data.get("cib", {})
        countries = []

        for country, metrics in cib.get("by_country", {}).items():
            if metrics.get("annual_value", 0) > 10_000_000:
                if "SUPPLIER" in metrics.get("payment_types", []):
                    countries.append(country)

        return countries if countries else None

    def _forex_has_hedge_gap(
        self, client_data: Dict
    ) -> Optional[List[str]]:
        """Check if client has low hedge ratio."""

        forex = client_data.get("forex", {})
        spot_volume = forex.get("spot_volume_90d", 0)
        forward_volume = forex.get("forward_volume_90d", 0)

        if spot_volume > 50_000_000:
            hedge_ratio = (
                forward_volume / spot_volume
                if spot_volume > 0
                else 0
            )
            if hedge_ratio < 0.30:
                currencies = forex.get("currencies_traded", [])
                return currencies if currencies else ["UNKNOWN"]

        return None

    def calculate_shadows(
        self,
        client_golden_id: str,
        client_name: str,
        client_data: Dict,
        actual_domains: Dict[str, Set[str]],
    ) -> List[DataShadow]:
        """
        Calculate all data shadows for a single client.

        We run every rule against the client data, determine
        what we expect to see, and compare against what
        we actually see. Gaps become shadows.

        Parameters:
            client_golden_id: The unified golden ID
            client_name: Canonical client name
            client_data: All available data per domain
            actual_domains: Map of domain to set of countries
                           where we have data
        """

        shadows = []

        for rule in self.rules:
            expected_countries = rule.condition_fn(client_data)

            if expected_countries is None:
                continue

            actual_countries = actual_domains.get(
                rule.expected_domain, set()
            )

            for country in expected_countries:
                if country not in actual_countries:
                    revenue_est = self._estimate_shadow_revenue(
                        rule.expected_domain,
                        client_data,
                        country,
                    )

                    shadow = DataShadow(
                        shadow_id=(
                            f"SHD-{client_golden_id}-"
                            f"{rule.name}-{country}-"
                            f"{datetime.now():%Y%m%d}"
                        ),
                        client_golden_id=client_golden_id,
                        client_name=client_name,
                        expected_domain=rule.expected_domain,
                        expected_country=country,
                        category=rule.shadow_category,
                        source_domain=rule.source_domain,
                        source_evidence=rule.description,
                        estimated_revenue_opportunity_zar=revenue_est,
                        confidence=rule.confidence,
                        recommended_action=self._generate_action(
                            rule, country, client_data
                        ),
                        detected_at=datetime.now().isoformat(),
                    )
                    shadows.append(shadow)

        return shadows

    def _estimate_shadow_revenue(
        self,
        expected_domain: str,
        client_data: Dict,
        country: str,
    ) -> float:
        """
        Estimate the revenue opportunity represented by
        a data shadow.
        """

        cib_value = (
            client_data.get("cib", {})
            .get("by_country", {})
            .get(country, {})
            .get("annual_value", 0)
        )

        estimates = {
            "forex": cib_value * 0.003,
            "insurance": cib_value * 0.002,
            "pbb": (
                client_data.get("cell", {})
                .get("by_country", {})
                .get(country, {})
                .get("sim_count", 0)
                * 2500
            ),
            "cell": cib_value * 0.001,
        }

        return estimates.get(expected_domain, 0.0)

    def _generate_action(
        self,
        rule: ShadowRule,
        country: str,
        client_data: Dict,
    ) -> str:
        """Generate a specific recommended action for the shadow."""

        actions = {
            "cib_implies_forex": (
                f"Contact the client CFO about FX hedging for "
                f"{country} exposure. They are likely using a "
                f"competitor. Offer bundled FX pricing."
            ),
            "cib_implies_cell": (
                f"Engage MTN partnership team to investigate "
                f"why we have no cell data for this client in "
                f"{country}. Client may use Airtel or Vodacom."
            ),
            "cell_implies_pbb": (
                f"Corporate payroll capture opportunity in "
                f"{country}. Contact HR director to propose "
                f"employee banking package."
            ),
            "cib_implies_insurance": (
                f"Insurance coverage gap in {country}. "
                f"Engage Liberty to prepare commercial asset "
                f"and liability insurance proposal."
            ),
            "cib_forex_hedge_gap": (
                f"Client has low hedge ratio. Prepare FX "
                f"hedging strategy presentation for CFO. "
                f"Focus on forward contracts for known "
                f"cash flows."
            ),
        }

        return actions.get(
            rule.name,
            f"Investigate data gap for {rule.expected_domain} "
            f"in {country}."
        )
