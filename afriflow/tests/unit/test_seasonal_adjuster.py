"""
tests/unit/test_seasonal_adjuster.py

Unit tests for the Seasonal Adjustment Engine.

We verify that:
1. Agricultural seasons are correctly identified by month.
2. Sector relevance scoring works across crop types.
3. Month wrapping (October to February) is handled.
4. Unknown countries and sectors return neutral adjustments.
5. Client seasonal profiles aggregate correctly.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from datetime import date
from seasonal.seasonal_adjuster import (
    SeasonalAdjuster,
    SeasonalFactor,
    ClientSeasonalProfile,
)


class TestSeasonalAdjuster:
    """Tests for the seasonal adjustment engine."""

    def setup_method(self):
        self.adjuster = SeasonalAdjuster(
            calendar_dir="nonexistent_dir"
        )

    def test_south_africa_maize_harvest_april(self):
        """April is maize harvest in Southern Africa. CIB up 60%."""

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-001",
            sector="AGR_GRAIN",
            country="ZA",
            target_date=date(2024, 4, 15),
        )

        assert factor.season_name == "maize"
        assert factor.period_name == "harvest"
        assert factor.expected_change_pct == 60
        assert factor.cash_flow_impact == "positive"

    def test_south_africa_maize_growing_february(self):
        """
        February is the growing season. CIB down 40%.
        This is NOT attrition. Our drift detector must
        subtract this expected decline before alerting.
        """

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-001",
            sector="AGR_GRAIN",
            country="ZA",
            target_date=date(2024, 2, 15),
        )

        assert factor.expected_change_pct == -40
        assert factor.cash_flow_impact == "neutral"

    def test_ghana_cocoa_main_crop_november(self):
        """November is cocoa main crop harvest. CIB up 80%."""

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-002",
            sector="AGR_CASH",
            country="GH",
            target_date=date(2024, 11, 1),
        )

        assert factor.season_name == "cocoa"
        assert factor.expected_change_pct == 80

    def test_ghana_cocoa_off_season_march(self):
        """
        March is cocoa off season. CIB down 50%.
        A Ghanaian cocoa exporter showing 50% payment
        decline in March is perfectly normal.
        """

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-002",
            sector="AGR_CASH",
            country="GH",
            target_date=date(2024, 3, 15),
        )

        assert factor.expected_change_pct == -50

    def test_kenya_tea_peak_january(self):
        """January is tea peak harvest in East Africa."""

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-003",
            sector="AGR_CASH",
            country="KE",
            target_date=date(2024, 1, 20),
        )

        assert factor.season_name == "tea"
        assert factor.expected_change_pct == 50

    def test_unknown_country_returns_neutral(self):
        """Unknown countries should get zero adjustment."""

        factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-004",
            sector="AGR_GRAIN",
            country="XX",
            target_date=date(2024, 4, 15),
        )

        assert factor.expected_change_pct == 0.0
        assert factor.confidence == 0.0

    def test_non_agricultural_sector_gets_reduced_relevance(self):
        """
        A retail client in South Africa during maize harvest
        should still get some seasonal adjustment, but with
        lower confidence than a grain farmer.
        """

        agr_factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-005",
            sector="AGR_GRAIN",
            country="ZA",
            target_date=date(2024, 4, 15),
        )

        ret_factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-006",
            sector="RET_FMCG",
            country="ZA",
            target_date=date(2024, 4, 15),
        )

        assert agr_factor.confidence > ret_factor.confidence

    def test_month_wrap_planting_season(self):
        """
        Planting season spans October to December.
        Both October and December should match.
        """

        oct_factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-007",
            sector="AGR_GRAIN",
            country="ZA",
            target_date=date(2024, 10, 1),
        )

        dec_factor = self.adjuster.get_adjustment_factor(
            client_id="TEST-007",
            sector="AGR_GRAIN",
            country="ZA",
            target_date=date(2024, 12, 31),
        )

        assert oct_factor.period_name == "planting"
        assert dec_factor.period_name == "planting"

    def test_client_profile_aggregation(self):
        """
        A client operating across multiple countries and
        sectors should get a composite seasonal profile.
        """

        profile = self.adjuster.get_client_profile(
            client_id="TEST-008",
            sectors=["AGR_GRAIN", "RET_FMCG"],
            countries=["ZA", "GH"],
            target_date=date(2024, 4, 15),
        )

        assert isinstance(profile, ClientSeasonalProfile)
        assert len(profile.active_seasons) > 0
        assert isinstance(profile.composite_adjustment_pct, float)

    def test_off_season_detection(self):
        """
        Client should be flagged as off season when
        composite adjustment is below negative 20%.
        """

        profile = self.adjuster.get_client_profile(
            client_id="TEST-009",
            sectors=["AGR_GRAIN"],
            countries=["ZA"],
            target_date=date(2024, 2, 15),
        )

        assert profile.is_off_season is True


class TestMonthInRange:
    """Tests for the month range helper that handles year wraps."""

    def setup_method(self):
        self.adjuster = SeasonalAdjuster(
            calendar_dir="nonexistent_dir"
        )

    def test_simple_range(self):
        """April to June should include April, May, June."""

        assert self.adjuster._month_in_range(4, 4, 6) is True
        assert self.adjuster._month_in_range(5, 4, 6) is True
        assert self.adjuster._month_in_range(6, 4, 6) is True
        assert self.adjuster._month_in_range(3, 4, 6) is False
        assert self.adjuster._month_in_range(7, 4, 6) is False

    def test_wrap_around_range(self):
        """October to February should include Oct, Nov, Dec, Jan, Feb."""

        assert self.adjuster._month_in_range(10, 10, 2) is True
        assert self.adjuster._month_in_range(11, 10, 2) is True
        assert self.adjuster._month_in_range(12, 10, 2) is True
        assert self.adjuster._month_in_range(1, 10, 2) is True
        assert self.adjuster._month_in_range(2, 10, 2) is True
        assert self.adjuster._month_in_range(3, 10, 2) is False
        assert self.adjuster._month_in_range(9, 10, 2) is False
