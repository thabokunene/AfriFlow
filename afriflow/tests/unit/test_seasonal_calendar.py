"""
tests/unit/test_seasonal_calendar.py

We test the agricultural and commodity seasonal calendar
that prevents false attrition alerts during expected
low-activity periods.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from datetime import date
from integration.cross_domain_signals.seasonal_calendar import (
    SeasonalCalendar,
    SeasonalPeriod,
)


class TestSeasonalClassification:
    """We test that the calendar correctly identifies
    peak and off-peak periods for key commodity sectors
    across African geographies."""

    @pytest.fixture
    def calendar(self):
        return SeasonalCalendar()

    def test_cocoa_peak_west_africa(self, calendar):
        period = calendar.get_season(
            sector="cocoa",
            country="GH",
            query_date=date(2024, 11, 15),
        )
        assert period.phase == "PEAK"

    def test_cocoa_offseason_west_africa(self, calendar):
        period = calendar.get_season(
            sector="cocoa",
            country="GH",
            query_date=date(2024, 3, 15),
        )
        assert period.phase == "OFF_PEAK"

    def test_maize_harvest_southern_africa(self, calendar):
        period = calendar.get_season(
            sector="maize",
            country="ZA",
            query_date=date(2024, 5, 1),
        )
        assert period.phase in ("HARVEST", "PEAK")

    def test_tea_season_east_africa(self, calendar):
        period = calendar.get_season(
            sector="tea",
            country="KE",
            query_date=date(2024, 2, 1),
        )
        assert period.phase == "PEAK"

    def test_sugar_season_mozambique(self, calendar):
        period = calendar.get_season(
            sector="sugar",
            country="MZ",
            query_date=date(2024, 8, 1),
        )
        assert period.phase == "PEAK"

    def test_unknown_sector_returns_neutral(self, calendar):
        period = calendar.get_season(
            sector="blockchain_consulting",
            country="ZA",
            query_date=date(2024, 6, 1),
        )
        assert period.phase == "NEUTRAL"

    def test_adjustment_factor_reduces_during_offseason(
        self, calendar
    ):
        """During off-season, we expect payment volumes
        to drop. The adjustment factor should account
        for this so we do not trigger false alarms."""
        peak = calendar.get_season(
            sector="cocoa",
            country="GH",
            query_date=date(2024, 11, 1),
        )
        off = calendar.get_season(
            sector="cocoa",
            country="GH",
            query_date=date(2024, 3, 1),
        )
        assert off.expected_volume_factor < peak.expected_volume_factor
