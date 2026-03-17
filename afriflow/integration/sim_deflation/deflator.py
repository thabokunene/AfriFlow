"""
integration/sim_deflation/deflator.py

SIM to Employee Deflation Engine.

In Africa, one person commonly uses 2 to 4 SIM cards.
We must deflate raw SIM counts to estimate actual
employee headcount. Without this, expansion signals
systematically overestimate workforce size.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import statistics


@dataclass
class DeflationResult:
    """Result of SIM deflation for a corporate client."""

    raw_sim_count: int
    country: str
    sector: str
    country_deflation_factor: float
    sector_adjustment: float
    effective_deflation_factor: float
    point_estimate: int
    lower_bound: int
    upper_bound: int
    confidence_level: str
    calibrated: bool
    calibration_source: str


@dataclass
class CalibrationPoint:
    """A single calibration data point."""

    country: str
    sector: str
    sim_count: int
    actual_employee_count: int


class SIMDeflationCalibrator:
    """
    We calibrate deflation factors using historical
    PBB payroll data where we know actual employee counts.
    """

    MIN_CALIBRATION_POINTS = 3

    def __init__(self):
        self._calibration_data: Dict[str, List[CalibrationPoint]] = {}

    def add_calibration_point(
        self,
        country: str,
        sector: str,
        sim_count: int,
        actual_employee_count: int,
    ) -> None:
        """Add a calibration point from known payroll data."""
        key = f"{country}:{sector}"
        if key not in self._calibration_data:
            self._calibration_data[key] = []

        self._calibration_data[key].append(
            CalibrationPoint(
                country=country,
                sector=sector,
                sim_count=sim_count,
                actual_employee_count=actual_employee_count,
            )
        )

    def get_calibrated_factor(
        self, country: str, sector: str
    ) -> Optional[float]:
        """
        Get calibrated factor for country/sector combination.
        Returns None if insufficient data.
        """
        key = f"{country}:{sector}"
        points = self._calibration_data.get(key, [])

        if len(points) < self.MIN_CALIBRATION_POINTS:
            country_key = f"{country}:None"
            country_points = self._calibration_data.get(country_key, [])
            if len(country_points) >= self.MIN_CALIBRATION_POINTS:
                factors = [
                    p.sim_count / p.actual_employee_count
                    for p in country_points
                    if p.actual_employee_count > 0
                ]
                if factors:
                    median_factor = statistics.median(factors)
                    return 1.0 / median_factor
            return None

        factors = [
            p.sim_count / p.actual_employee_count
            for p in points
            if p.actual_employee_count > 0
        ]

        if not factors:
            return None

        median_factor = statistics.median(factors)
        return 1.0 / median_factor


class SIMDeflator:
    """
    We deflate raw SIM counts to estimated employee
    headcounts using country-level factors with
    sector adjustments and confidence intervals.
    """

    COUNTRY_FACTORS: Dict[str, Dict] = {
        "ZA": {"factor": 0.73, "confidence": "high"},
        "NG": {"factor": 0.31, "confidence": "medium"},
        "KE": {"factor": 0.43, "confidence": "high"},
        "GH": {"factor": 0.46, "confidence": "medium"},
        "TZ": {"factor": 0.39, "confidence": "medium"},
        "UG": {"factor": 0.41, "confidence": "medium"},
        "CD": {"factor": 0.42, "confidence": "low"},
        "MZ": {"factor": 0.50, "confidence": "medium"},
        "ZM": {"factor": 0.57, "confidence": "medium"},
        "AO": {"factor": 0.61, "confidence": "low"},
        "CI": {"factor": 0.44, "confidence": "low"},
        "BW": {"factor": 0.68, "confidence": "high"},
        "NA": {"factor": 0.73, "confidence": "high"},
    }

    SECTOR_ADJUSTMENTS: Dict[str, float] = {
        "MIN_GOLD": 0.8,
        "MIN_COPPER": 0.8,
        "MIN_OIL": 0.85,
        "RET_FMCG": 1.2,
        "FIN_BANK": 0.9,
        "AGR_GRAIN": 1.5,
        "AGR_CASH": 1.4,
        "AGR_SUGAR": 1.3,
        "CON_INFRA": 1.3,
        "TEL_MOBILE": 0.7,
        "MAN_GENERAL": 1.0,
        "SVC_PROFESSIONAL": 0.9,
    }

    CONFIDENCE_INTERVALS: Dict[str, tuple] = {
        "high": (0.85, 1.15),
        "medium": (0.70, 1.30),
        "low": (0.60, 1.40),
    }

    DEFAULT_FACTOR = 0.50
    DEFAULT_CONFIDENCE = "low"

    def __init__(self):
        self._calibrator = SIMDeflationCalibrator()

    def deflate(
        self,
        sim_count: int,
        country: str,
        sector: str = "MAN_GENERAL",
        calibration_override: Optional[float] = None,
    ) -> DeflationResult:
        """
        Deflate raw SIM count to estimated employee headcount.
        """
        country_config = self.COUNTRY_FACTORS.get(
            country,
            {"factor": self.DEFAULT_FACTOR, "confidence": self.DEFAULT_CONFIDENCE},
        )

        base_factor = country_config["factor"]
        confidence = country_config["confidence"]

        sector_adj = self.SECTOR_ADJUSTMENTS.get(sector, 1.0)

        if calibration_override is not None:
            effective_factor = calibration_override
            calibrated = True
            calibration_source = "pbb_payroll_calibration"
            confidence = "high"
        else:
            calibrated_factor = self._calibrator.get_calibrated_factor(
                country, sector
            )
            if calibrated_factor is not None:
                effective_factor = calibrated_factor
                calibrated = True
                calibration_source = "pbb_payroll_calibration"
                confidence = "high"
            else:
                effective_factor = base_factor * sector_adj
                calibrated = False
                calibration_source = "country_default"

        effective_factor = max(0.10, min(1.0, effective_factor))

        point_estimate = max(1, round(sim_count * effective_factor))

        interval = self.CONFIDENCE_INTERVALS.get(
            confidence, self.CONFIDENCE_INTERVALS["low"]
        )
        lower_bound = max(1, round(point_estimate * interval[0]))
        upper_bound = round(point_estimate * interval[1])

        return DeflationResult(
            raw_sim_count=sim_count,
            country=country,
            sector=sector,
            country_deflation_factor=base_factor,
            sector_adjustment=sector_adj,
            effective_deflation_factor=effective_factor,
            point_estimate=point_estimate,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence,
            calibrated=calibrated,
            calibration_source=calibration_source,
        )
