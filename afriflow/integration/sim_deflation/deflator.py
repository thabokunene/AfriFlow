"""
@file deflator.py
@description SIM-to-employee deflation engine with sector adjustments and
    confidence intervals. Converts raw corporate SIM counts to employee
    headcount estimates using country-level factors, sector-specific
    multipliers (mining vs agriculture vs retail), and optional PBB payroll
    calibration. Produces point estimates with lower/upper bound ranges.
@author Thabo Kunene
@created 2026-03-18
"""
# Context:
# In Africa, one person commonly holds 2–4 SIM cards across operators.
# Raw SIM counts therefore overestimate workforce size. This engine adds
# sector-level nuance on top of country defaults: agricultural workers
# have higher multi-SIM rates than mining employees on managed rosters.
#
# DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
# by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
# demonstration of concept, domain knowledge, and technical skill built by
# Thabo Kunene for portfolio and learning purposes only.

from dataclasses import dataclass
from typing import Dict, List, Optional
import statistics


@dataclass
class DeflationResult:
    """Result of SIM deflation for a corporate client.

    Stores the full audit trail from raw input through to the estimated
    employee headcount, including the individual factor components and
    the confidence interval bounds.
    """

    raw_sim_count: int              # Input: SIM cards from the MTN corporate feed
    country: str                    # ISO-2 country code
    sector: str                     # Sector code (e.g. "AGR_GRAIN", "MIN_GOLD")
    country_deflation_factor: float # Base factor from COUNTRY_FACTORS (pre-sector adj.)
    sector_adjustment: float        # Sector multiplier applied to the base factor
    effective_deflation_factor: float  # Final factor after sector adj. + calibration
    point_estimate: int             # Central employee headcount estimate
    lower_bound: int                # Lower confidence bound
    upper_bound: int                # Upper confidence bound
    confidence_level: str           # "high", "medium", or "low"
    calibrated: bool                # True if PBB payroll calibration was applied
    calibration_source: str         # "pbb_payroll_calibration" or "country_default"


@dataclass
class CalibrationPoint:
    """A single calibration observation linking SIM count to known employee count."""

    country: str
    sector: str
    sim_count: int                  # Observed raw SIM count at calibration time
    actual_employee_count: int      # Verified employee count from PBB payroll


class SIMDeflationCalibrator:
    """We calibrate deflation factors using PBB payroll data.

    Stores per country/sector calibration points from cases where we have
    both MTN SIM data and verified employee counts from PBB payroll. The
    median SIM-to-employee ratio across all calibration points is used as
    the deflation factor, making it robust to outliers.
    """

    MIN_CALIBRATION_POINTS = 3  # Minimum observations before trusting calibration

    def __init__(self):
        """Initialise with an empty calibration store."""
        # Keyed by "country:sector" — stores a list of CalibrationPoint objects
        self._calibration_data: Dict[str, List[CalibrationPoint]] = {}

    def add_calibration_point(
        self,
        country: str,
        sector: str,
        sim_count: int,
        actual_employee_count: int,
    ) -> None:
        """Record a calibration observation from known payroll data.

        Args:
            country: ISO-2 country code.
            sector: Sector code for this calibration point.
            sim_count: SIM count from MTN corporate feed at calibration time.
            actual_employee_count: Verified employee count from PBB payroll.
        """
        key = f"{country}:{sector}"
        if key not in self._calibration_data:
            self._calibration_data[key] = []

        # Append the new observation to the country/sector bucket
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
        """Get the calibrated deflation factor for a country/sector pair.

        Falls back to country-level calibration when there are insufficient
        sector-level observations. Returns None if there is not enough data
        to produce a reliable calibrated factor.

        Args:
            country: ISO-2 country code.
            sector: Sector code.

        Returns:
            Calibrated deflation factor, or None if insufficient data.
        """
        key = f"{country}:{sector}"
        points = self._calibration_data.get(key, [])

        # Not enough sector-level data — try country-level fallback
        if len(points) < self.MIN_CALIBRATION_POINTS:
            country_key = f"{country}:None"
            country_points = self._calibration_data.get(country_key, [])
            if len(country_points) >= self.MIN_CALIBRATION_POINTS:
                # Compute median SIM/employee ratio across all country points
                factors = [
                    p.sim_count / p.actual_employee_count
                    for p in country_points
                    if p.actual_employee_count > 0  # Guard against division by zero
                ]
                if factors:
                    median_factor = statistics.median(factors)
                    return 1.0 / median_factor  # Convert ratio to deflation factor
            # Insufficient data at both sector and country level
            return None

        # Enough sector-specific data: compute median ratio from these points
        factors = [
            p.sim_count / p.actual_employee_count
            for p in points
            if p.actual_employee_count > 0  # Skip any points with zero employees
        ]

        if not factors:
            return None  # All points had zero employees — unusable

        # Median is more robust than mean for small calibration sets
        median_factor = statistics.median(factors)
        return 1.0 / median_factor  # Deflation factor = inverse of SIM/employee ratio


class SIMDeflator:
    """We deflate raw SIM counts to estimated employee headcounts.

    Applies country-level base factors with sector-specific adjustments and
    confidence interval bounds. Automatically uses calibrated factors from
    SIMDeflationCalibrator when PBB payroll data has been supplied.

    Key design choices:
    - Sector adjustments: Agriculture workers hold more SIMs (higher multi-SIM
      rate) than mining employees on managed corporate rosters.
    - Confidence intervals: Wider for markets with weaker data quality.
    - Effective factor clamped to [0.10, 1.0] to prevent nonsensical extremes.
    """

    # Country-level base deflation factors derived from GSMA/ITU multi-SIM data.
    # factor = 1 / avg_sims_per_person — multiplied against raw SIM count.
    COUNTRY_FACTORS: Dict[str, Dict] = {
        "ZA": {"factor": 0.73, "confidence": "high"},   # 1/1.37 — mature market
        "NG": {"factor": 0.31, "confidence": "medium"},  # 1/3.2 — high multi-SIM
        "KE": {"factor": 0.43, "confidence": "high"},    # 1/2.3 — Safaricom dominance
        "GH": {"factor": 0.46, "confidence": "medium"},  # 1/2.2
        "TZ": {"factor": 0.39, "confidence": "medium"},  # 1/2.6
        "UG": {"factor": 0.41, "confidence": "medium"},  # 1/2.4
        "CD": {"factor": 0.42, "confidence": "low"},     # 1/2.4 — weaker data
        "MZ": {"factor": 0.50, "confidence": "medium"},  # 1/2.0
        "ZM": {"factor": 0.57, "confidence": "medium"},  # 1/1.75
        "AO": {"factor": 0.61, "confidence": "low"},     # 1/1.64 — older data
        "CI": {"factor": 0.44, "confidence": "low"},     # 1/2.27
        "BW": {"factor": 0.68, "confidence": "high"},    # 1/1.47 — small, well-reported
        "NA": {"factor": 0.73, "confidence": "high"},    # 1/1.37 — similar to ZA
    }

    # Sector multipliers applied on top of the country base factor.
    # Sectors with casual/seasonal workers have more multi-SIM behaviour.
    SECTOR_ADJUSTMENTS: Dict[str, float] = {
        "MIN_GOLD": 0.8,          # Formal mine roster → fewer multi-SIM employees
        "MIN_COPPER": 0.8,        # Same: managed payroll environment
        "MIN_OIL": 0.85,          # Formal contract workers
        "RET_FMCG": 1.2,          # Retail: high casual/part-time workforce
        "FIN_BANK": 0.9,          # Bank employees: usually single corporate SIM
        "AGR_GRAIN": 1.5,         # Grain farming: seasonal casual labour, high multi-SIM
        "AGR_CASH": 1.4,          # Cash crops: similar seasonal pattern
        "AGR_SUGAR": 1.3,         # Sugar: partially managed workforce
        "CON_INFRA": 1.3,         # Construction: casual labour high multi-SIM
        "TEL_MOBILE": 0.7,        # Telecom employees: managed SIM allocation
        "MAN_GENERAL": 1.0,       # General manufacturing: neutral baseline
        "SVC_PROFESSIONAL": 0.9,  # Professional services: single SIM typical
    }

    # Confidence interval multipliers applied to the point estimate.
    # These define the lower and upper bounds of the headcount range.
    CONFIDENCE_INTERVALS: Dict[str, tuple] = {
        "high":   (0.85, 1.15),  # ±15% range for well-calibrated markets
        "medium": (0.70, 1.30),  # ±30% range for moderate data quality
        "low":    (0.60, 1.40),  # ±40% range for weak / older data
    }

    DEFAULT_FACTOR = 0.50       # Conservative 50% deflation for unknown markets
    DEFAULT_CONFIDENCE = "low"  # Low confidence for any unknown market

    def __init__(self):
        """Initialise the deflator with a fresh calibration store."""
        # Calibrator holds PBB payroll calibration data; injected into deflate()
        self._calibrator = SIMDeflationCalibrator()

    def deflate(
        self,
        sim_count: int,
        country: str,
        sector: str = "MAN_GENERAL",
        calibration_override: Optional[float] = None,
    ) -> DeflationResult:
        """Deflate a raw SIM count to an estimated employee headcount.

        Resolution order for the deflation factor:
          1. calibration_override — if provided, used directly (highest priority)
          2. SIMDeflationCalibrator — if sufficient PBB data exists for country/sector
          3. COUNTRY_FACTORS × SECTOR_ADJUSTMENTS — default fallback

        The effective factor is clamped to [0.10, 1.0] to prevent edge cases.

        Args:
            sim_count: Raw SIM card count from MTN corporate feed.
            country: ISO-2 country code.
            sector: Sector code (default "MAN_GENERAL").
            calibration_override: Optional explicit deflation factor (e.g. from
                                  a freshly-computed PBB payroll match).

        Returns:
            DeflationResult with point estimate, bounds, and audit fields.
        """
        # Look up the country base factor; use defaults for unknown countries
        country_config = self.COUNTRY_FACTORS.get(
            country,
            {"factor": self.DEFAULT_FACTOR, "confidence": self.DEFAULT_CONFIDENCE},
        )

        base_factor = country_config["factor"]
        confidence = country_config["confidence"]

        # Look up the sector multiplier; neutral 1.0 for unknown sectors
        sector_adj = self.SECTOR_ADJUSTMENTS.get(sector, 1.0)

        # Resolution order: override > calibrator > country default
        if calibration_override is not None:
            # Explicit override always wins — used for high-value client special cases
            effective_factor = calibration_override
            calibrated = True
            calibration_source = "pbb_payroll_calibration"
            confidence = "high"  # Caller asserts this factor is accurate
        else:
            # Check if calibrator has enough data for a derived factor
            calibrated_factor = self._calibrator.get_calibrated_factor(
                country, sector
            )
            if calibrated_factor is not None:
                # PBB-derived factor available — use it
                effective_factor = calibrated_factor
                calibrated = True
                calibration_source = "pbb_payroll_calibration"
                confidence = "high"
            else:
                # Fall back to country × sector combination
                effective_factor = base_factor * sector_adj
                calibrated = False
                calibration_source = "country_default"

        # Clamp to sensible range: at least 10% deflation, at most 100% (1 SIM each)
        effective_factor = max(0.10, min(1.0, effective_factor))

        # Point estimate: apply factor to raw SIM count; floor at 1 employee
        point_estimate = max(1, round(sim_count * effective_factor))

        # Apply confidence-level interval bounds to produce a range
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
