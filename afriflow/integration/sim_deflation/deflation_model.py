"""
@file deflation_model.py
@description SIM-to-employee deflation model for African markets. Converts
    raw corporate SIM counts from MTN network feeds into estimated actual
    employee headcounts using country-level multi-SIM penetration rates from
    ITU and GSMA Intelligence reports. Supports per-client calibration using
    PBB payroll data for progressively more accurate estimates.
@author Thabo Kunene
@created 2026-03-18
"""
# Context:
# In African markets, one individual commonly holds 2–4 SIM cards across
# multiple operators. Raw SIM counts therefore systematically overestimate
# workforce size. This model applies country-specific deflation factors to
# produce a calibrated employee headcount estimate.
#
# Disclaimer: This project is not sanctioned by, affiliated with, or endorsed
# by Standard Bank Group, MTN Group, or any affiliated entity. It is a
# demonstration of concept, domain knowledge, and data engineering skill by
# Thabo Kunene.

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CountryDeflationConfig:
    """Per-country SIM deflation configuration.

    Deflation factors are derived from ITU multi-SIM penetration studies
    and GSMA Intelligence reports for Sub-Saharan Africa. The deflation_factor
    is computed as 1 / avg_sims_per_employee so it can be multiplied directly
    against a raw SIM count to produce an employee estimate.

    Urban and rural multipliers allow region-specific adjustments: urban
    workers tend to hold more SIMs (higher multi-SIM rate), rural workers fewer.
    """

    country_code: str               # ISO-2 country code
    country_name: str               # Human-readable country name
    avg_sims_per_employee: float    # Average SIM cards per employed person
    deflation_factor: float         # 1 / avg_sims_per_employee — multiply by raw SIMs
    urban_multiplier: float         # Urban region adjustment (>1 = more SIMs per person)
    rural_multiplier: float         # Rural region adjustment (<1 = fewer SIMs per person)
    confidence_penalty: float       # Reduction from 0.85 baseline for weaker data quality
    source: str                     # Citation for the deflation factor value

    # Class-level cache: populated on first call to _load_configs()
    COUNTRY_CONFIGS: Dict[str, dict] = None

    @classmethod
    def _load_configs(cls) -> Dict[str, dict]:
        """Lazy-load and cache the country configuration lookup table.

        Returns the cached COUNTRY_CONFIGS dict on subsequent calls,
        avoiding redundant re-construction.
        """
        if cls.COUNTRY_CONFIGS is not None:
            return cls.COUNTRY_CONFIGS

        # Country-level multi-SIM data from telecoms regulators (2022–2023)
        cls.COUNTRY_CONFIGS = {
            "ZA": {
                "country_name": "South Africa",
                "avg_sims_per_employee": 1.3,  # Lowest in SSA: mature market, LTE dominant
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.0,     # High-quality ICASA data
                "source": "ICASA Q4 2023 Report",
            },
            "NG": {
                "country_name": "Nigeria",
                "avg_sims_per_employee": 2.8,  # Highest: urban multi-operator usage common
                "urban_multiplier": 1.3,       # Lagos/Abuja: even higher multi-SIM
                "rural_multiplier": 0.7,       # Northern rural: single SIM typical
                "confidence_penalty": 0.0,
                "source": "NCC Subscriber Data 2023",
            },
            "KE": {
                "country_name": "Kenya",
                "avg_sims_per_employee": 2.1,  # Safaricom M-Pesa dominance reduces switching
                "urban_multiplier": 1.2,
                "rural_multiplier": 0.8,
                "confidence_penalty": 0.0,
                "source": "CA Kenya Q3 2023",
            },
            "GH": {
                "country_name": "Ghana",
                "avg_sims_per_employee": 2.3,
                "urban_multiplier": 1.2,
                "rural_multiplier": 0.8,
                "confidence_penalty": 0.0,
                "source": "NCA Ghana 2023",
            },
            "TZ": {
                "country_name": "Tanzania",
                "avg_sims_per_employee": 2.4,
                "urban_multiplier": 1.2,
                "rural_multiplier": 0.8,
                "confidence_penalty": 0.0,
                "source": "TCRA Annual Report 2023",
            },
            "UG": {
                "country_name": "Uganda",
                "avg_sims_per_employee": 2.2,
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.05,    # Slight penalty: UCC data less granular
                "source": "UCC Market Report 2023",
            },
            "MZ": {
                "country_name": "Mozambique",
                "avg_sims_per_employee": 1.8,
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.05,
                "source": "INCM Estimate 2023",
            },
            "CD": {
                "country_name": "Democratic Republic of Congo",
                "avg_sims_per_employee": 1.9,
                "urban_multiplier": 1.3,       # Kinshasa multi-SIM very common
                "rural_multiplier": 0.7,       # Rural DRC: very low penetration
                "confidence_penalty": 0.10,    # Older data, volatile market
                "source": "ARPTC Estimate 2022",
            },
            "CI": {
                "country_name": "Cote d'Ivoire",
                "avg_sims_per_employee": 2.5,
                "urban_multiplier": 1.2,
                "rural_multiplier": 0.8,
                "confidence_penalty": 0.05,
                "source": "ARTCI Report 2023",
            },
            "AO": {
                "country_name": "Angola",
                "avg_sims_per_employee": 1.7,
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.10,    # 2022 data; INACOM reporting gaps
                "source": "INACOM Estimate 2022",
            },
            "ZM": {
                "country_name": "Zambia",
                "avg_sims_per_employee": 2.0,
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.05,
                "source": "ZICTA Report 2023",
            },
        }
        return cls.COUNTRY_CONFIGS

    @classmethod
    def for_country(cls, country_code: str) -> "CountryDeflationConfig":
        """Factory method: build a CountryDeflationConfig for the given country.

        Falls back to a conservative default configuration when the country
        is not registered (avg 2.0 SIMs/employee, confidence penalty 0.15).

        Args:
            country_code: ISO-2 country code.

        Returns:
            Populated CountryDeflationConfig instance.
        """
        configs = cls._load_configs()
        if country_code in configs:
            cfg = configs[country_code]
            return cls(
                country_code=country_code,
                country_name=cfg["country_name"],
                avg_sims_per_employee=cfg["avg_sims_per_employee"],
                # Deflation factor is the reciprocal of the average SIM count
                deflation_factor=1.0 / cfg["avg_sims_per_employee"],
                urban_multiplier=cfg["urban_multiplier"],
                rural_multiplier=cfg["rural_multiplier"],
                confidence_penalty=cfg["confidence_penalty"],
                source=cfg["source"],
            )
        # Unknown country: use a conservative 50% deflation (2 SIMs per person)
        return cls(
            country_code=country_code,
            country_name="Unknown",
            avg_sims_per_employee=2.0,
            deflation_factor=0.50,
            urban_multiplier=1.2,
            rural_multiplier=0.8,
            confidence_penalty=0.15,          # High penalty for unknown markets
            source="Conservative default for unknown market",
        )


@dataclass
class DeflatedWorkforceEstimate:
    """Result of SIM deflation for a single corporate client in a single country.

    Contains both the raw input and the estimated output so that callers
    can audit the deflation and communicate confidence intervals to consumers.
    """

    corporate_client_id: str    # The CIB/MTN corporate client identifier
    country_code: str           # ISO-2 country where the SIMs were observed
    raw_sim_count: int          # Raw SIM cards counted in the MTN corporate feed
    estimated_employees: int    # Deflated employee headcount estimate
    deflation_factor: float     # Factor applied: estimated = raw * deflation_factor
    confidence: float           # Model confidence in [0, 1]
    method: str                 # "calibrated", "country_default", or "zero_input"
    source: str                 # Data source or calibration citation


class SIMDeflationModel:
    """We estimate actual employee headcount from raw corporate SIM counts.

    Uses country-level deflation factors from ITU/GSMA data with optional
    per-client calibration using known PBB payroll data. Calibrated estimates
    progressively replace country defaults as payroll data accumulates.

    The model supports two operational modes:
      1. country_default — published multi-SIM ratios from telecoms regulators
      2. calibrated — client-specific SIM-to-payroll ratio from PBB data
    """

    def __init__(self):
        """Initialise the model with an empty calibration store."""
        # Keyed by "corporate_client_id:country_code"
        self._calibrations: Dict[str, Dict[str, float]] = {}

    def calibrate(
        self,
        corporate_client_id: str,
        country_code: str,
        known_employee_count: int,
        observed_sim_count: int,
    ) -> None:
        """Calibrate the deflation factor for a specific client using PBB payroll data.

        This is the feedback loop that makes the model progressively more accurate.
        When PBB payroll data matches a corporate SIM feed, we derive the actual
        SIM-to-employee ratio for that client and store it as a calibration point.

        Args:
            corporate_client_id: The corporate client identifier.
            country_code: ISO-2 country code where the calibration applies.
            known_employee_count: Verified employee count from PBB payroll.
            observed_sim_count: Concurrent SIM count from the MTN corporate feed.
        """
        # Cannot calibrate if there are no SIMs to divide against
        if observed_sim_count == 0:
            return
        key = f"{corporate_client_id}:{country_code}"
        # Compute the actual SIM-per-employee ratio from real data
        actual_ratio = observed_sim_count / known_employee_count
        self._calibrations[key] = {
            "deflation_factor": 1.0 / actual_ratio,   # Inverse: SIMs → employees
            "actual_ratio": actual_ratio,              # For audit / diagnostics
            "sample_size": known_employee_count,       # Used to weight confidence
        }

    def estimate_workforce(
        self,
        raw_sim_count: int,
        country_code: str,
        corporate_client_id: str,
        region_type: Optional[str] = None,
    ) -> DeflatedWorkforceEstimate:
        """Estimate the number of actual employees from a raw MTN SIM count.

        Applies calibrated factors when available, otherwise falls back to
        the country-level default. Optionally adjusts for urban/rural region type.

        Args:
            raw_sim_count: Raw number of SIM cards from the MTN corporate feed.
            country_code: ISO-2 country code of the observation.
            corporate_client_id: The corporate client identifier.
            region_type: Optional "urban" or "rural" — adjusts the deflation factor.

        Returns:
            DeflatedWorkforceEstimate with headcount, confidence, and method.

        Raises:
            ValueError: If raw_sim_count is negative.
        """
        if raw_sim_count < 0:
            raise ValueError(
                "SIM count cannot be negative"
            )

        # Zero SIM count is a valid clean case — return immediately
        if raw_sim_count == 0:
            return DeflatedWorkforceEstimate(
                corporate_client_id=corporate_client_id,
                country_code=country_code,
                raw_sim_count=0,
                estimated_employees=0,
                deflation_factor=0.0,
                confidence=1.0,     # We are fully confident there are 0 employees
                method="zero_input",
                source="N/A",
            )

        # Build the calibration lookup key
        calibration_key = (
            f"{corporate_client_id}:{country_code}"
        )

        # Prefer client-specific calibrated factor when available
        if calibration_key in self._calibrations:
            cal = self._calibrations[calibration_key]
            estimated = round(
                raw_sim_count * cal["deflation_factor"]
            )
            return DeflatedWorkforceEstimate(
                corporate_client_id=corporate_client_id,
                country_code=country_code,
                raw_sim_count=raw_sim_count,
                estimated_employees=max(1, estimated),  # Never estimate 0 employees
                deflation_factor=cal["deflation_factor"],
                # Confidence improves with sample size; capped at 0.95
                confidence=min(
                    0.95,
                    0.85 + (cal["sample_size"] / 10000),
                ),
                method="calibrated",
                source=(
                    f"PBB payroll calibration "
                    f"(n={cal['sample_size']})"
                ),
            )

        # No calibration available — use country-level defaults
        config = CountryDeflationConfig.for_country(
            country_code
        )
        deflation = config.deflation_factor

        # Apply region-type adjustment when the caller has location context
        if region_type == "urban":
            # Urban workers hold more SIMs → deflate more aggressively
            deflation *= (1.0 / config.urban_multiplier)
        elif region_type == "rural":
            # Rural workers hold fewer SIMs → deflate less aggressively
            deflation *= (1.0 / config.rural_multiplier)

        estimated = round(raw_sim_count * deflation)
        # Confidence starts at 0.85 baseline minus the country penalty
        confidence = 0.85 - config.confidence_penalty

        return DeflatedWorkforceEstimate(
            corporate_client_id=corporate_client_id,
            country_code=country_code,
            raw_sim_count=raw_sim_count,
            estimated_employees=max(1, estimated),  # Floor at 1 — at least one person
            deflation_factor=deflation,
            confidence=confidence,
            method="country_default",
            source=config.source,
        )
