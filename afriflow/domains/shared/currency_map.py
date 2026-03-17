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

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Country code to currency mapping (ISO 4217)
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
    # Common cross-border settlement currencies
    "US": "USD",  # US Dollar
    "GB": "GBP",  # British Pound
    "EU": "EUR",  # Euro
    "CN": "CNY",  # Chinese Yuan
}

# Reverse mapping: currency to country
CURRENCY_TO_COUNTRY: Dict[str, str] = {
    v: k for k, v in COUNTRY_TO_CURRENCY.items()
}

# Major currencies for filtering and validation
MAJOR_CURRENCIES: List[str] = [
    "USD", "EUR", "ZAR", "NGN", "KES", "GBP"
]

# Backward compatibility alias (lowercase)
major_currencies: List[str] = MAJOR_CURRENCIES


def get_currency_for_country(country_code: str) -> str:
    """
    Get the currency code for a country.

    Args:
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        ISO 4217 currency code

    Raises:
        ValueError: If country code not found
    """
    country_upper = country_code.upper()

    if country_upper not in COUNTRY_TO_CURRENCY:
        logger.warning(
            f"Unknown country code: {country_code}, "
            f"defaulting to USD"
        )
        return "USD"

    return COUNTRY_TO_CURRENCY[country_upper]


def get_country_for_currency(currency_code: str) -> str:
    """
    Get the primary country for a currency.

    Args:
        currency_code: ISO 4217 currency code

    Returns:
        ISO 3166-1 alpha-2 country code or empty string
    """
    currency_upper = currency_code.upper()
    return CURRENCY_TO_COUNTRY.get(currency_upper, "")


def is_major_currency(currency_code: str) -> bool:
    """
    Check if a currency is a major trading currency.

    Args:
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
