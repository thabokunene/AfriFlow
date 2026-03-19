"""
@file currency_map.py
@description Mapping and utility functions for African and major global currencies to their respective countries.
@author Thabo Kunene
@created 2026-03-19
"""

"""
African Currency to Country Mapping.

We maintain this mapping for cross-domain signal
generation where we need to infer geographic exposure
from currency codes.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for dictionary and list structures
from typing import Dict, List
# Standard logging for reporting unknown country/currency mappings
import logging

# Initialize module-level logger for currency resolution events
logger = logging.getLogger(__name__)

# Primary mapping of ISO 3166-1 alpha-2 country codes to ISO 4217 currency codes.
# This serves as the source of truth for geographic-financial attribution.
COUNTRY_TO_CURRENCY: Dict[str, str] = {
    "ZA": "ZAR",  # South African Rand
    "NG": "NGN",  # Nigerian Naira
    "KE": "KES",  # Kenyan Shilling
    "EG": "EGP",  # Egyptian Pound
    "GH": "GHS",  # Ghanaian Cedi
    "RW": "RWF",  # Rwandan Franc
    "MA": "MAD",  # Moroccan Dirham
    "ET": "ETB",  # Ethiopian Birr
    "CI": "XOF",  # West African CFA Franc
    "TZ": "TZS",  # Tanzanian Shilling
    "UG": "UGX",  # Ugandan Shilling
    "ZM": "ZMW",  # Zambian Kwacha
    "ZW": "ZWL",  # Zimbabwean Dollar
    "MZ": "MZN",  # Mozambican Metical
    "AO": "AOA",  # Angolan Kwanza
    # Major global settlement and reserve currencies
    "US": "USD",  # US Dollar
    "GB": "GBP",  # British Pound
    "EU": "EUR",  # Euro
    "CN": "CNY",  # Chinese Yuan
}

# Automatically generated reverse mapping for looking up countries by currency.
CURRENCY_TO_COUNTRY: Dict[str, str] = {
    v: k for k, v in COUNTRY_TO_CURRENCY.items()
}

# High-liquidity currencies frequently used in cross-border trade and hedging.
MAJOR_CURRENCIES: List[str] = [
    "USD", "EUR", "ZAR", "NGN", "KES", "GBP"
]

# Legacy alias for MAJOR_CURRENCIES to maintain backward compatibility with older modules.
major_currencies: List[str] = MAJOR_CURRENCIES


def get_currency_for_country(country_code: str) -> str:
    """
    Retrieves the primary currency code associated with a given country.

    :param country_code: Two-letter ISO country code (e.g., 'ZA').
    :return: Three-letter ISO currency code (e.g., 'ZAR'). Defaults to 'USD' if unknown.
    """
    # Normalize input to uppercase for dictionary lookup
    country_upper = country_code.upper()

    # Fallback to USD if the country is not in our registry to prevent pipeline crashes
    if country_upper not in COUNTRY_TO_CURRENCY:
        logger.warning(
            f"Unknown country code: {country_code}, "
            f"defaulting to USD"
        )
        return "USD"

    return COUNTRY_TO_CURRENCY[country_upper]


def get_country_for_currency(currency_code: str) -> str:
    """
    Identifies the primary country associated with a specific currency.

    :param currency_code: Three-letter ISO currency code (e.g., 'KES').
    :return: Two-letter ISO country code (e.g., 'KE') or an empty string if not found.
    """
    # Normalize input to uppercase
    currency_upper = currency_code.upper()
    # Perform reverse lookup
    return CURRENCY_TO_COUNTRY.get(currency_upper, "")


def is_major_currency(currency_code: str) -> bool:
    """
    Determines if a currency is classified as a major trading currency within the platform.

    :param currency_code: Three-letter ISO currency code.
    :return: True if the currency is in the MAJOR_CURRENCIES list, False otherwise.
    """
        currency_code: ISO 4217 currency code

    Returns:
        True if major currency
    """
    return currency_code.upper() in MAJOR_CURRENCIES


def is_african_currency(currency_code: str) -> bool:
    """
    Check if a currency is from an African country.

    Args:
        currency_code: ISO 4217 currency code

    Returns:
        True if African currency
    """
    currency_upper = currency_code.upper()
    # Exclude major non-African currencies
    non_african = {"USD", "EUR", "GBP", "CNY"}
    return currency_upper not in non_african
