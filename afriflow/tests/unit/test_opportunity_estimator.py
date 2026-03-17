"""
tests/unit/test_opportunity_estimator.py

We test the revenue opportunity estimation logic that
translates cross-domain signals into ZAR values for
RM prioritisation.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.cross_domain_signals.expansion_signal import (
    ExpansionDetector,
)


class TestOpportunityEstimation:
    """We verify that opportunity estimates scale
    correctly with client tier, corridor value, and
    product gaps."""

    @pytest.fixture
    def detector(self):
        return ExpansionDetector()

    def test_platinum_lower_fee_rate(self, detector):
        plat = detector._estimate_opportunity(
            client_info={"tier": "Platinum"},
            country="KE",
            cib_value=10_000_000,
            has_hedge=True,
            has_insurance=True,
            employee_count=0,
        )
        bronze = detector._estimate_opportunity(
            client_info={"tier": "Bronze"},
            country="KE",
            cib_value=10_000_000,
            has_hedge=True,
            has_insurance=True,
            employee_count=0,
        )
        assert plat < bronze

    def test_unhedged_adds_fx_opportunity(self, detector):
        hedged = detector._estimate_opportunity(
            client_info={"tier": "Gold"},
            country="NG",
            cib_value=50_000_000,
            has_hedge=True,
            has_insurance=True,
            employee_count=0,
        )
        unhedged = detector._estimate_opportunity(
            client_info={"tier": "Gold"},
            country="NG",
            cib_value=50_000_000,
            has_hedge=False,
            has_insurance=True,
            employee_count=0,
        )
        assert unhedged > hedged

    def test_employees_add_payroll_opportunity(self, detector):
        no_emp = detector._estimate_opportunity(
            client_info={"tier": "Silver"},
            country="GH",
            cib_value=5_000_000,
            has_hedge=True,
            has_insurance=True,
            employee_count=0,
        )
        with_emp = detector._estimate_opportunity(
            client_info={"tier": "Silver"},
            country="GH",
            cib_value=5_000_000,
            has_hedge=True,
            has_insurance=True,
            employee_count=500,
        )
        assert with_emp > no_emp
        assert with_emp - no_emp == pytest.approx(
            500 * 2500, abs=1
        )

    def test_zero_cib_value_still_returns_positive_if_employees(
        self, detector
    ):
        result = detector._estimate_opportunity(
            client_info={"tier": "Bronze"},
            country="TZ",
            cib_value=0,
            has_hedge=True,
            has_insurance=True,
            employee_count=100,
        )
        assert result > 0
