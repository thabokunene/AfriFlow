"""
tests/unit/test_sim_deflation.py

Unit tests for the SIM to Employee Deflation Model.

We verify that:
1. Country level deflation factors are applied correctly.
2. Sector adjustments modify the base factor appropriately.
3. Confidence intervals are calculated per country confidence level.
4. Calibration overrides take precedence over defaults.
5. Edge cases (zero SIMs, unknown countries) are handled.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from integration.sim_deflation.deflator import (
    SIMDeflator,
    SIMDeflationCalibrator,
    DeflationResult,
)


class TestSIMDeflator:
    """Tests for the core SIM deflation engine."""

    def setup_method(self):
        self.deflator = SIMDeflator()

    def test_south_africa_deflation(self):
        """South Africa has a factor of 0.73 (1.3 SIMs per person)."""

        result = self.deflator.deflate(
            sim_count=1000, country="ZA"
        )

        assert result.country_deflation_factor == 0.73
        assert result.point_estimate == 730
        assert result.confidence_level == "high"

    def test_nigeria_deflation(self):
        """Nigeria has a factor of 0.31 (2.8 SIMs per person)."""

        result = self.deflator.deflate(
            sim_count=1000, country="NG"
        )

        assert result.country_deflation_factor == 0.31
        assert result.point_estimate == 310
        assert result.confidence_level == "medium"

    def test_nigeria_1000_sims_is_not_1000_employees(self):
        """
        This test encodes the core insight: in Nigeria,
        1000 corporate SIMs does NOT mean 1000 employees.
        It means approximately 310 employees. Reporting
        1000 would destroy RM trust.
        """

        result = self.deflator.deflate(
            sim_count=1000, country="NG"
        )

        assert result.point_estimate < 500, (
            "Nigerian SIM count must be deflated significantly. "
            "Raw SIM count is not employee count."
        )

    def test_sector_adjustment_mining(self):
        """Mining has 0.8x adjustment (company SIMs dominate)."""

        result = self.deflator.deflate(
            sim_count=1000, country="ZA", sector="MIN_GOLD"
        )

        assert result.sector_adjustment == 0.8
        expected = round(1000 * 0.73 * 0.8)
        assert result.point_estimate == expected

    def test_sector_adjustment_retail(self):
        """Retail has 1.2x adjustment (personal SIMs common)."""

        result = self.deflator.deflate(
            sim_count=1000, country="ZA", sector="RET_FMCG"
        )

        assert result.sector_adjustment == 1.2
        expected = round(1000 * 0.73 * 1.2)
        assert result.point_estimate == expected

    def test_unknown_country_uses_default(self):
        """Unknown countries get conservative default factor."""

        result = self.deflator.deflate(
            sim_count=1000, country="XX"
        )

        assert result.country_deflation_factor == 0.50
        assert result.confidence_level == "low"

    def test_unknown_sector_uses_neutral_adjustment(self):
        """Unknown sectors get 1.0x adjustment (no change)."""

        result = self.deflator.deflate(
            sim_count=1000, country="ZA", sector="UNKNOWN_SECTOR"
        )

        assert result.sector_adjustment == 1.0

    def test_confidence_intervals_high(self):
        """High confidence countries have tight intervals (plus minus 15%)."""

        result = self.deflator.deflate(
            sim_count=1000, country="ZA"
        )

        assert result.lower_bound == round(730 * 0.85)
        assert result.upper_bound == round(730 * 1.15)
        assert result.confidence_level == "high"

    def test_confidence_intervals_low(self):
        """Low confidence countries have wide intervals (plus minus 40%)."""

        result = self.deflator.deflate(
            sim_count=1000, country="CD"
        )

        point = result.point_estimate
        assert result.lower_bound == max(1, round(point * 0.60))
        assert result.upper_bound == round(point * 1.40)
        assert result.confidence_level == "low"

    def test_zero_sims_returns_minimum_one(self):
        """Zero SIMs should still return at least 1 (not zero or negative)."""

        result = self.deflator.deflate(
            sim_count=0, country="ZA"
        )

        assert result.point_estimate >= 1
        assert result.lower_bound >= 1

    def test_single_sim_returns_one(self):
        """A single SIM should return 1 employee."""

        result = self.deflator.deflate(
            sim_count=1, country="ZA"
        )

        assert result.point_estimate >= 1

    def test_calibration_override(self):
        """Calibration override should replace default factor."""

        result = self.deflator.deflate(
            sim_count=1000,
            country="NG",
            calibration_override=0.45,
        )

        assert result.effective_deflation_factor == 0.45
        assert result.point_estimate == 450
        assert result.calibrated is True
        assert result.calibration_source == "pbb_payroll_calibration"
        assert result.confidence_level == "high"

    def test_effective_factor_clamped_to_valid_range(self):
        """Effective factor should never exceed 1.0 or go below 0.1."""

        result = self.deflator.deflate(
            sim_count=1000,
            country="BW",
            sector="TEL_MOBILE",
        )

        assert 0.10 <= result.effective_deflation_factor <= 1.0

    def test_result_contains_all_fields(self):
        """Every result should contain all required fields."""

        result = self.deflator.deflate(
            sim_count=500, country="KE", sector="AGR_GRAIN"
        )

        assert isinstance(result, DeflationResult)
        assert result.raw_sim_count == 500
        assert result.country == "KE"
        assert result.sector == "AGR_GRAIN"
        assert result.country_deflation_factor > 0
        assert result.sector_adjustment > 0
        assert result.effective_deflation_factor > 0
        assert result.point_estimate > 0
        assert result.lower_bound > 0
        assert result.upper_bound >= result.point_estimate
        assert result.lower_bound <= result.point_estimate


class TestSIMDeflationCalibrator:
    """Tests for the calibration feedback loop."""

    def setup_method(self):
        self.calibrator = SIMDeflationCalibrator()

    def test_insufficient_data_returns_none(self):
        """We need at least 3 data points for calibration."""

        self.calibrator.add_calibration_point(
            country="NG", sector="MIN_GOLD",
            sim_count=100, actual_employee_count=35,
        )

        result = self.calibrator.get_calibrated_factor("NG", "MIN_GOLD")
        assert result is None

    def test_calibration_with_sufficient_data(self):
        """With 3+ data points, we return a calibrated factor."""

        self.calibrator.add_calibration_point(
            "NG", "MIN_GOLD", sim_count=100, actual_employee_count=35,
        )
        self.calibrator.add_calibration_point(
            "NG", "MIN_GOLD", sim_count=200, actual_employee_count=65,
        )
        self.calibrator.add_calibration_point(
            "NG", "MIN_GOLD", sim_count=500, actual_employee_count=180,
        )

        result = self.calibrator.get_calibrated_factor("NG", "MIN_GOLD")
        assert result is not None
        assert 0.30 <= result <= 0.40

    def test_calibration_uses_median(self):
        """Calibration should use median, not mean, to be outlier resistant."""

        self.calibrator.add_calibration_point(
            "KE", "RET_FMCG", sim_count=100, actual_employee_count=45,
        )
        self.calibrator.add_calibration_point(
            "KE", "RET_FMCG", sim_count=200, actual_employee_count=85,
        )
        self.calibrator.add_calibration_point(
            "KE", "RET_FMCG", sim_count=50, actual_employee_count=5,
        )

        result = self.calibrator.get_calibrated_factor("KE", "RET_FMCG")
        assert result is not None

        factors_sorted = sorted([0.45, 0.425, 0.10])
        expected_median = factors_sorted[1]
        assert abs(result - expected_median) < 0.01

    def test_country_fallback_when_sector_insufficient(self):
        """
        If sector specific data is insufficient,
        fall back to country level calibration.
        """

        self.calibrator.add_calibration_point(
            "NG", "None", sim_count=100, actual_employee_count=30,
        )
        self.calibrator.add_calibration_point(
            "NG", "None", sim_count=200, actual_employee_count=55,
        )
        self.calibrator.add_calibration_point(
            "NG", "None", sim_count=300, actual_employee_count=90,
        )

        result = self.calibrator.get_calibrated_factor("NG", "NEW_SECTOR")
        assert result is not None
