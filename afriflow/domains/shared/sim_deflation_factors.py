"""
SIM to Employee Deflation Factors.

In Africa, a single person commonly uses 2 to 4 SIM
cards across multiple networks. We must deflate raw
SIM counts to estimate actual employee headcount.

We maintain these factors per country based on
publicly available multi-SIM usage research.

DISCLAIMER: This project is not a sanctioned project.
It is a demonstration of concept, domain knowledge,
and skill by Thabo Kunene.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Average SIMs per person by country and the
# corresponding deflation factor to convert SIM
# count to estimated unique person count.
#
# deflation_factor = 1 / avg_sims_per_person
#
# Sources: GSMA Intelligence (public reports),
# national telecom regulator publications.

SIM_DEFLATION_FACTORS: Dict[str, Dict[str, Any]] = {
    "ZA": {
        "avg_sims_per_person": 1.3,
        "deflation_factor": 0.77,
        "confidence": "high",
        "source": "ICASA quarterly report (public)",
    },
    "NG": {
        "avg_sims_per_person": 2.8,
        "deflation_factor": 0.36,
        "confidence": "medium",
        "source": "NCC subscriber data (public)",
    },
    "KE": {
        "avg_sims_per_person": 2.1,
        "deflation_factor": 0.48,
        "confidence": "high",
        "source": "CA market report (public)",
    },
    "GH": {
        "avg_sims_per_person": 2.3,
        "deflation_factor": 0.43,
        "confidence": "medium",
        "source": "NCA statistics (public)",
    },
    "TZ": {
        "avg_sims_per_person": 2.4,
        "deflation_factor": 0.42,
        "confidence": "medium",
        "source": "TCRA annual report (public)",
    },
    "UG": {
        "avg_sims_per_person": 2.0,
        "deflation_factor": 0.50,
        "confidence": "medium",
        "source": "UCC market review (public)",
    },
    "ZM": {
        "avg_sims_per_person": 1.8,
        "deflation_factor": 0.56,
        "confidence": "low",
        "source": "ZICTA estimate (public)",
    },
    "MZ": {
        "avg_sims_per_person": 1.7,
        "deflation_factor": 0.59,
        "confidence": "low",
        "source": "INCM estimate (public)",
    },
    "CD": {
        "avg_sims_per_person": 1.9,
        "deflation_factor": 0.53,
        "confidence": "low",
        "source": "ARPTC estimate (public)",
    },
    "AO": {
        "avg_sims_per_person": 1.6,
        "deflation_factor": 0.63,
        "confidence": "low",
        "source": "INACOM estimate (public)",
    },
    "CI": {
        "avg_sims_per_person": 2.2,
        "deflation_factor": 0.45,
        "confidence": "medium",
        "source": "ARTCI report (public)",
    },
}

# Default for countries not listed above.
DEFAULT_DEFLATION: Dict[str, Any] = {
    "avg_sims_per_person": 2.0,
    "deflation_factor": 0.50,
    "confidence": "low",
    "source": "GSMA regional average (public)",
}


def get_deflation_factor(country_code: str) -> float:
    """
    Return the SIM to employee deflation factor for
    a given country. We use this to convert raw SIM
    activation counts into estimated employee headcount.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Deflation factor (0.0 to 1.0)

    Raises:
        ValueError: If country_code is invalid
    """
    if not country_code or not isinstance(country_code, str):
        raise ValueError(
            f"Invalid country_code: {country_code}. "
            f"Expected ISO 3166-1 alpha-2 code."
        )

    country_upper = country_code.upper()
    entry = SIM_DEFLATION_FACTORS.get(
        country_upper, DEFAULT_DEFLATION
    )

    if country_upper not in SIM_DEFLATION_FACTORS:
        logger.warning(
            f"No deflation factor for {country_code}, "
            f"using default: {DEFAULT_DEFLATION['deflation_factor']}"
        )

    return float(entry["deflation_factor"])


def get_deflation_confidence(country_code: str) -> str:
    """
    Return the confidence level of the deflation
    factor for a given country.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Confidence level: "high", "medium", or "low"
    """
    if not country_code:
        return "low"

    country_upper = country_code.upper()
    entry = SIM_DEFLATION_FACTORS.get(
        country_upper, DEFAULT_DEFLATION
    )
    return str(entry["confidence"])


def get_avg_sims_per_person(country_code: str) -> float:
    """
    Return the average SIMs per person for a country.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Average SIMs per person
    """
    if not country_code:
        return DEFAULT_DEFLATION["avg_sims_per_person"]

    country_upper = country_code.upper()
    entry = SIM_DEFLATION_FACTORS.get(
        country_upper, DEFAULT_DEFLATION
    )
    return float(entry["avg_sims_per_person"])


def get_deflation_source(country_code: str) -> str:
    """
    Return the source of the deflation factor.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        Source description
    """
    if not country_code:
        return DEFAULT_DEFLATION["source"]

    country_upper = country_code.upper()
    entry = SIM_DEFLATION_FACTORS.get(
        country_upper, DEFAULT_DEFLATION
    )
    return str(entry["source"])
