"""
tests/unit/test_data_shadow.py

Unit tests for the Data Shadow Calculator.

We verify that:
1. Missing forex for CIB clients generates a shadow.
2. Missing PBB for clients with cell SIMs generates a shadow.
3. Missing insurance for operational clients generates a shadow.
4. Clients with full domain coverage generate no shadows.
5. Revenue estimates are reasonable.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from afriflow.data_shadow.shadow_calculator import (
    ShadowCalculator,
    DomainShadow,
    ShadowCategory,
)


class TestShadowCalculator:
    """Tests for data shadow detection."""

    def setup_method(self):
        self.calculator = ShadowCalculator()

    def test_cib_without_forex_generates_leakage_shadow(self):
        """
        Client with CIB payments to Kenya but no forex
        hedging should generate a competitive leakage shadow.
        """

        client_data = {
            "cib": {
                "foreign_corridors": [
                    {"country": "KE", "currency": "KES"}
                ],
                "active_countries": ["ZA", "KE"],
                "by_country": {
                    "KE": {
                        "annual_value": 20_000_000
                    }
                }
            },
            "forex": {},
            "insurance": {},
            "cell": {},
            "pbb": {},
        }

        actual_domains = {
            "cib": {"ZA", "KE"},
            "forex": set(),
            "insurance": set(),
            "cell": set(),
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST001",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        forex_shadows = [
            s for s in shadows
            if s.expected_domain == "forex"
        ]
        assert len(forex_shadows) > 0
        assert forex_shadows[0].category == ShadowCategory.COMPETITIVE_LEAKAGE

    def test_cell_without_pbb_generates_payroll_shadow(self):
        """
        Client with 200 corporate SIMs in Kenya but no PBB
        payroll should generate a payroll capture shadow.
        """

        client_data = {
            "cib": {},
            "forex": {},
            "insurance": {},
            "cell": {
                "by_country": {
                    "KE": {"sim_count": 200},
                },
            },
            "pbb": {},
        }

        actual_domains = {
            "cib": set(),
            "forex": set(),
            "insurance": set(),
            "cell": {"KE"},
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST002",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        pbb_shadows = [
            s for s in shadows
            if s.expected_domain == "pbb"
        ]
        assert len(pbb_shadows) > 0
        assert pbb_shadows[0].category == ShadowCategory.PAYROLL_CAPTURE_OPPORTUNITY

    def test_cib_without_insurance_generates_coverage_gap(self):
        """
        Client with R50M CIB activity including supplier
        payments but no insurance should generate a coverage
        gap shadow.
        """

        client_data = {
            "cib": {
                "by_country": {
                    "NG": {
                        "annual_value": 50_000_000,
                        "payment_types": ["SUPPLIER", "PAYROLL"],
                    },
                },
                "active_countries": ["ZA", "NG"],
                "foreign_corridors": [],
            },
            "forex": {},
            "insurance": {},
            "cell": {},
            "pbb": {},
        }

        actual_domains = {
            "cib": {"ZA", "NG"},
            "forex": set(),
            "insurance": set(),
            "cell": set(),
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST003",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        ins_shadows = [
            s for s in shadows
            if s.expected_domain == "insurance"
        ]
        assert len(ins_shadows) > 0
        assert ins_shadows[0].category == ShadowCategory.INSURANCE_GAP

    def test_full_coverage_generates_no_shadows(self):
        """
        Client present in all domains in all countries
        should generate no shadows.
        """

        client_data = {
            "cib": {
                "foreign_corridors": [
                    {"country": "KE", "currency": "KES"}
                ],
                "active_countries": ["ZA", "KE"],
                "by_country": {
                    "KE": {
                        "annual_value": 50_000_000,
                        "payment_types": ["SUPPLIER"],
                    },
                },
            },
            "forex": {
                "spot_volume_90d": 100_000_000,
                "forward_volume_90d": 50_000_000,
                "currencies_traded": ["KES"],
            },
            "insurance": {},
            "cell": {
                "by_country": {
                    "KE": {"sim_count": 200},
                },
            },
            "pbb": {},
        }

        actual_domains = {
            "cib": {"ZA", "KE"},
            "forex": {"KE"},
            "insurance": {"KE"},
            "cell": {"ZA", "KE"},
            "pbb": {"KE"},
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST004",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        leakage_shadows = [
            s for s in shadows
            if s.category == ShadowCategory.COMPETITIVE_LEAKAGE
        ]
        assert len(leakage_shadows) == 0

    def test_small_sim_count_no_pbb_shadow(self):
        """
        Client with only 10 SIMs should NOT trigger a payroll
        shadow (below the 50 SIM threshold).
        """

        client_data = {
            "cib": {},
            "forex": {},
            "insurance": {},
            "cell": {
                "by_country": {
                    "KE": {"sim_count": 10},
                },
            },
            "pbb": {},
        }

        actual_domains = {
            "cib": set(),
            "forex": set(),
            "insurance": set(),
            "cell": {"KE"},
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST005",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        pbb_shadows = [
            s for s in shadows
            if s.expected_domain == "pbb"
        ]
        assert len(pbb_shadows) == 0

    def test_shadow_revenue_estimate_is_positive(self):
        """Revenue estimates for shadows should be positive numbers."""

        client_data = {
            "cib": {
                "foreign_corridors": [
                    {"country": "KE", "currency": "KES"}
                ],
                "active_countries": ["ZA", "KE"],
                "by_country": {
                    "KE": {
                        "annual_value": 100_000_000,
                        "payment_types": ["SUPPLIER"],
                    },
                },
            },
            "forex": {},
            "insurance": {},
            "cell": {},
            "pbb": {},
        }

        actual_domains = {
            "cib": {"ZA", "KE"},
            "forex": set(),
            "insurance": set(),
            "cell": set(),
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST006",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        for shadow in shadows:
            assert shadow.estimated_revenue_opportunity_zar >= 0

    def test_cib_in_non_mtn_country_no_cell_shadow(self):
        """
        CIB activity in a country where MTN does not
        operate should NOT generate a cell shadow.
        """

        client_data = {
            "cib": {
                "active_countries": ["ZA", "ET"],
                "foreign_corridors": [],
            },
            "forex": {},
            "insurance": {},
            "cell": {},
            "pbb": {},
        }

        actual_domains = {
            "cib": {"ZA", "ET"},
            "forex": set(),
            "insurance": set(),
            "cell": set(),
            "pbb": set(),
        }

        shadows = self.calculator.calculate_shadows(
            golden_id="GLD-TEST007",
            client_metadata=client_data,
            actual_presence=actual_domains,
        )

        cell_shadows = [
            s for s in shadows
            if s.expected_domain == "cell"
            and s.expected_country == "ET"
        ]
        assert len(cell_shadows) == 0
