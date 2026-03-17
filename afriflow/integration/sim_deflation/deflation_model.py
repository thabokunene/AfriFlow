"""
integration/sim_deflation/deflation_model.py

SIM-to-employee deflation model for African markets.

We adjust raw corporate SIM counts from MTN feeds to
estimate actual employee headcount. Without this
deflation, expansion signals systematically overestimate
workforce size because of multi-SIM culture across
African markets.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class CountryDeflationConfig:
    """Configuration for SIM deflation per country.

    We derive these from ITU multi-SIM penetration
    studies and GSMA Intelligence reports for
    Sub-Saharan Africa.
    """

    country_code: str
    country_name: str
    avg_sims_per_employee: float
    deflation_factor: float
    urban_multiplier: float
    rural_multiplier: float
    confidence_penalty: float
    source: str

    COUNTRY_CONFIGS: Dict[str, dict] = None

    @classmethod
    def _load_configs(cls) -> Dict[str, dict]:
        if cls.COUNTRY_CONFIGS is not None:
            return cls.COUNTRY_CONFIGS

        cls.COUNTRY_CONFIGS = {
            "ZA": {
                "country_name": "South Africa",
                "avg_sims_per_employee": 1.3,
                "urban_multiplier": 1.1,
                "rural_multiplier": 0.9,
                "confidence_penalty": 0.0,
                "source": "ICASA Q4 2023 Report",
            },
            "NG": {
                "country_name": "Nigeria",
                "avg_sims_per_employee": 2.8,
                "urban_multiplier": 1.3,
                "rural_multiplier": 0.7,
                "confidence_penalty": 0.0,
                "source": "NCC Subscriber Data 2023",
            },
            "KE": {
                "country_name": "Kenya",
                "avg_sims_per_employee": 2.1,
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
                "confidence_penalty": 0.05,
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
                "urban_multiplier": 1.3,
                "rural_multiplier": 0.7,
                "confidence_penalty": 0.10,
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
                "confidence_penalty": 0.10,
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
        configs = cls._load_configs()
        if country_code in configs:
            cfg = configs[country_code]
            return cls(
                country_code=country_code,
                country_name=cfg["country_name"],
                avg_sims_per_employee=cfg["avg_sims_per_employee"],
                deflation_factor=1.0 / cfg["avg_sims_per_employee"],
                urban_multiplier=cfg["urban_multiplier"],
                rural_multiplier=cfg["rural_multiplier"],
                confidence_penalty=cfg["confidence_penalty"],
                source=cfg["source"],
            )
        return cls(
            country_code=country_code,
            country_name="Unknown",
            avg_sims_per_employee=2.0,
            deflation_factor=0.50,
            urban_multiplier=1.2,
            rural_multiplier=0.8,
            confidence_penalty=0.15,
            source="Conservative default for unknown market",
        )


@dataclass
class DeflatedWorkforceEstimate:
    """Result of SIM deflation for a single corporate
    client in a single country."""

    corporate_client_id: str
    country_code: str
    raw_sim_count: int
    estimated_employees: int
    deflation_factor: float
    confidence: float
    method: str
    source: str


class SIMDeflationModel:
    """We estimate actual employee headcount from raw
    corporate SIM counts using country-level deflation
    factors with optional per-client calibration from
    PBB payroll data.

    The model supports two modes:
    1. country_default: Uses published multi-SIM ratios
    2. calibrated: Uses historical SIM-to-payroll
       correlation for a specific client
    """

    def __init__(self):
        self._calibrations: Dict[str, Dict[str, float]] = {}

    def calibrate(
        self,
        corporate_client_id: str,
        country_code: str,
        known_employee_count: int,
        observed_sim_count: int,
    ) -> None:
        """We calibrate the deflation factor for a specific
        client using known payroll data from PBB.

        This is the feedback loop that makes the model
        increasingly accurate over time.
        """
        if observed_sim_count == 0:
            return
        key = f"{corporate_client_id}:{country_code}"
        actual_ratio = observed_sim_count / known_employee_count
        self._calibrations[key] = {
            "deflation_factor": 1.0 / actual_ratio,
            "actual_ratio": actual_ratio,
            "sample_size": known_employee_count,
        }

    def estimate_workforce(
        self,
        raw_sim_count: int,
        country_code: str,
        corporate_client_id: str,
        region_type: Optional[str] = None,
    ) -> DeflatedWorkforceEstimate:
        """We estimate the number of actual employees from
        the raw SIM count observed in MTN corporate feeds.
        """
        if raw_sim_count < 0:
            raise ValueError(
                "SIM count cannot be negative"
            )

        if raw_sim_count == 0:
            return DeflatedWorkforceEstimate(
                corporate_client_id=corporate_client_id,
                country_code=country_code,
                raw_sim_count=0,
                estimated_employees=0,
                deflation_factor=0.0,
                confidence=1.0,
                method="zero_input",
                source="N/A",
            )

        calibration_key = (
            f"{corporate_client_id}:{country_code}"
        )

        if calibration_key in self._calibrations:
            cal = self._calibrations[calibration_key]
            estimated = round(
                raw_sim_count * cal["deflation_factor"]
            )
            return DeflatedWorkforceEstimate(
                corporate_client_id=corporate_client_id,
                country_code=country_code,
                raw_sim_count=raw_sim_count,
                estimated_employees=max(1, estimated),
                deflation_factor=cal["deflation_factor"],
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

        config = CountryDeflationConfig.for_country(
            country_code
        )
        deflation = config.deflation_factor

        if region_type == "urban":
            deflation *= (1.0 / config.urban_multiplier)
        elif region_type == "rural":
            deflation *= (1.0 / config.rural_multiplier)

        estimated = round(raw_sim_count * deflation)
        confidence = 0.85 - config.confidence_penalty

        return DeflatedWorkforceEstimate(
            corporate_client_id=corporate_client_id,
            country_code=country_code,
            raw_sim_count=raw_sim_count,
            estimated_employees=max(1, estimated),
            deflation_factor=deflation,
            confidence=confidence,
            method="country_default",
            source=config.source,
        )
