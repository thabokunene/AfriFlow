"""
@file currency_map.py
@description Mapping and utility functions for African and major global currencies to their respective countries.
@author Thabo Kunene
@created 2026-03-19

This module provides currency-country mapping and utility functions for the AfriFlow platform.
It enables cross-domain signal generation where we need to infer geographic exposure
from currency codes, and vice versa.

Key Features:
- Country to currency mapping (ISO 3166-1 alpha-2 to ISO 4217)
- Currency to country reverse lookup
- Major currency identification for trade and hedging
- African currency detection for regional analytics
- Graceful fallbacks for unknown codes to prevent pipeline crashes

Usage:
    >>> from afriflow.reference_data.currency_map import (
    ...     get_currency_for_country,
    ...     get_country_for_currency,
    ...     is_major_currency,
    ...     is_african_currency
    ... )
    >>> get_currency_for_country("ZA")  # Returns "ZAR"
    >>> get_country_for_currency("KES")  # Returns "KE"
    >>> is_major_currency("USD")  # Returns True
    >>> is_african_currency("NGN")  # Returns True

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for dictionary and list structures
# Dict for key-value mappings, List for ordered collections
from typing import Dict, List

# Standard logging for reporting unknown country/currency mappings
# This enables observability when unexpected codes are encountered
import logging

# Initialize module-level logger for currency resolution events
# Logger name follows afriflow namespace convention
logger = logging.getLogger(__name__)


# ============================================
# COUNTRY TO CURRENCY MAPPING
# ============================================

# Primary mapping of ISO 3166-1 alpha-2 country codes to ISO 4217 currency codes.
# This serves as the source of truth for geographic-financial attribution.
# Used by: corridor analysis, signal detection, revenue attribution
COUNTRY_TO_CURRENCY: Dict[str, str] = {
    # Southern African Development Community (SADC)
    "ZA": "ZAR",  # South African Rand (regional reserve currency)
    "ZM": "ZMW",  # Zambian Kwacha
    "ZW": "ZWL",  # Zimbabwean Dollar
    "MZ": "MZN",  # Mozambican Metical
    "AO": "AOA",  # Angolan Kwanza
    "BW": "BWP",  # Botswana Pula
    "NA": "NAD",  # Namibian Dollar (pegged to ZAR)
    "SZ": "SZL",  # Swazi Lilangeni (pegged to ZAR)
    "LS": "LSL",  # Lesotho Loti (pegged to ZAR)
    
    # East African Community (EAC)
    "KE": "KES",  # Kenyan Shilling (regional hub)
    "TZ": "TZS",  # Tanzanian Shilling
    "UG": "UGX",  # Ugandan Shilling
    "RW": "RWF",  # Rwandan Franc
    "BI": "BIF",  # Burundian Franc
    "SS": "SSP",  # South Sudanese Pound
    
    # West African Economic and Monetary Union (WAEMU)
    "CI": "XOF",  # West African CFA Franc (BCEAO)
    "SN": "XOF",  # Senegal (same currency as CI)
    "ML": "XOF",  # Mali (same currency as CI)
    "BF": "XOF",  # Burkina Faso (same currency as CI)
    "NE": "XOF",  # Niger (same currency as CI)
    "TG": "XOF",  # Togo (same currency as CI)
    "BJ": "XOF",  # Benin (same currency as CI)
    "GW": "XOF",  # Guinea-Bissau (same currency as CI)
    
    # Other West African countries
    "NG": "NGN",  # Nigerian Naira (largest African economy)
    "GH": "GHS",  # Ghanaian Cedi
    "SL": "SLL",  # Sierra Leonean Leone
    "LR": "LRD",  # Liberian Dollar
    "GN": "GNF",  # Guinean Franc
    
    # Central Africa
    "CM": "XAF",  # Central African CFA Franc (BEAC)
    "GA": "XAF",  # Gabon (same currency as CM)
    "CG": "XAF",  # Republic of the Congo (same currency as CM)
    "CF": "XAF",  # Central African Republic (same currency as CM)
    "TD": "XAF",  # Chad (same currency as CM)
    "GQ": "XAF",  # Equatorial Guinea (same currency as CM)
    "CD": "CDF",  # Congolese Franc (DRC)
    
    # North Africa
    "EG": "EGP",  # Egyptian Pound
    "MA": "MAD",  # Moroccan Dirham
    "DZ": "DZD",  # Algerian Dinar
    "TN": "TND",  # Tunisian Dinar
    "LY": "LYD",  # Libyan Dinar
    
    # Horn of Africa
    "ET": "ETB",  # Ethiopian Birr
    "SO": "SOS",  # Somali Shilling
    "DJ": "DJF",  # Djiboutian Franc
    "ER": "ERN",  # Eritrean Nakfa
    
    # Indian Ocean Islands
    "MU": "MUR",  # Mauritian Rupee
    "SC": "SCR",  # Seychellois Rupee
    "KM": "KMF",  # Comorian Franc
    "MG": "MGA",  # Malagasy Ariary
    
    # Major global settlement and reserve currencies
    # These are critical for forex hedging and cross-border trade
    "US": "USD",  # US Dollar (global reserve currency)
    "GB": "GBP",  # British Pound (sterling)
    "EU": "EUR",  # Euro (European Union)
    "CN": "CNY",  # Chinese Yuan (growing African trade partner)
    "JP": "JPY",  # Japanese Yen
    "CH": "CHF",  # Swiss Franc
    "AU": "AUD",  # Australian Dollar
    "CA": "CAD",  # Canadian Dollar
    "IN": "INR",  # Indian Rupee (significant African trade)
    "BR": "BRL",  # Brazilian Real (South-South trade)
    "AE": "AED",  # UAE Dirham (Middle East trade hub)
    "SA": "SAR",  # Saudi Riyal (oil trade)
}


# ============================================
# REVERSE MAPPING (CURRENCY TO COUNTRY)
# ============================================

# Automatically generated reverse mapping for looking up countries by currency.
# Note: Some currencies (like XOF, XAF) are used by multiple countries.
# This mapping returns the primary/first country for such currencies.
# For complete multi-country lookup, use get_countries_for_currency()
CURRENCY_TO_COUNTRY: Dict[str, str] = {
    v: k for k, v in COUNTRY_TO_CURRENCY.items()
}


# ============================================
# CURRENCY CLASSIFICATIONS
# ============================================

# High-liquidity currencies frequently used in cross-border trade and hedging.
# These currencies have active forex markets and are commonly hedged by clients.
# Used by: hedge gap detection, corridor analytics, risk scoring
MAJOR_CURRENCIES: List[str] = [
    "USD",  # US Dollar (global reserve)
    "EUR",  # Euro (European trade)
    "GBP",  # British Pound (sterling)
    "ZAR",  # South African Rand (regional reserve)
    "NGN",  # Nigerian Naira (largest African economy)
    "KES",  # Kenyan Shilling (East African hub)
    "EGP",  # Egyptian Pound (North African hub)
    "GHS",  # Ghanaian Cedi (West African hub)
    "CNY",  # Chinese Yuan (major trade partner)
    "AED",  # UAE Dirham (Middle East trade)
]

# Legacy alias for MAJOR_CURRENCIES to maintain backward compatibility with older modules.
# Deprecated: Use MAJOR_CURRENCIES instead (uppercase constant naming convention)
major_currencies: List[str] = MAJOR_CURRENCIES

# African currencies subset (excludes major global currencies)
# Used for regional analytics and African-focused reporting
AFRICAN_CURRENCIES: List[str] = [
    code for code in COUNTRY_TO_CURRENCY.values()
    if code not in {"USD", "EUR", "GBP", "CNY", "JPY", "CHF", "AUD", "CAD"}
]

# Currencies used by multiple countries (currency unions)
# Important for accurate country attribution in analytics
CURRENCY_UNIONS: Dict[str, List[str]] = {
    "XOF": ["CI", "SN", "ML", "BF", "NE", "TG", "BJ", "GW"],  # WAEMU
    "XAF": ["CM", "GA", "CG", "CF", "TD", "GQ"],  # CEMAC
    "ZAR": ["ZA", "NA", "LS", "SZ"],  # Common Monetary Area (pegged)
}


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_currency_for_country(country_code: str) -> str:
    """
    Retrieves the primary currency code associated with a given country.

    This function performs a case-insensitive lookup and provides a safe
    default (USD) for unknown country codes to prevent pipeline crashes.
    The fallback is logged for monitoring data quality issues.

    Args:
        country_code: Two-letter ISO 3166-1 alpha-2 country code
                     Examples: 'ZA' (South Africa), 'NG' (Nigeria), 'KE' (Kenya)

    Returns:
        Three-letter ISO 4217 currency code
        Examples: 'ZAR', 'NGN', 'KES'
        Returns 'USD' as fallback for unknown countries

    Example:
        >>> get_currency_for_country("ZA")
        'ZAR'
        >>> get_currency_for_country("ng")  # Case insensitive
        'NGN'
        >>> get_currency_for_country("XX")  # Unknown country
        'USD'  # With warning logged
    """
    # Normalize input to uppercase for dictionary lookup
    # This handles both "za" and "ZA" correctly
    country_upper = country_code.upper()

    # Fallback to USD if the country is not in our registry
    # This prevents pipeline crashes on bad data while logging the issue
    if country_upper not in COUNTRY_TO_CURRENCY:
        logger.warning(
            f"Unknown country code: {country_code}, "
            f"defaulting to USD"
        )
        return "USD"

    # Return the currency code for the country
    return COUNTRY_TO_CURRENCY[country_upper]


def get_country_for_currency(currency_code: str) -> str:
    """
    Identifies the primary country associated with a specific currency.

    Note: Some currencies (XOF, XAF, ZAR) are used by multiple countries.
    This function returns the primary/first country. For complete list,
    use get_countries_for_currency() instead.

    Args:
        currency_code: Three-letter ISO 4217 currency code
                      Examples: 'KES' (Kenya), 'ZAR' (South Africa)

    Returns:
        Two-letter ISO 3166-1 alpha-2 country code
        Examples: 'KE', 'ZA'
        Returns empty string if currency not found

    Example:
        >>> get_country_for_currency("KES")
        'KE'
        >>> get_country_for_currency("zar")  # Case insensitive
        'ZA'
        >>> get_country_for_currency("XXX")  # Unknown currency
        ''
    """
    # Normalize input to uppercase for consistent lookup
    currency_upper = currency_code.upper()
    
    # Perform reverse lookup using pre-computed dictionary
    # Returns empty string if not found (safe default)
    return CURRENCY_TO_COUNTRY.get(currency_upper, "")


def get_countries_for_currency(currency_code: str) -> List[str]:
    """
    Get all countries that use a specific currency.

    This handles currency unions (XOF, XAF) and pegged currencies (ZAR)
    where multiple countries share the same currency code.

    Args:
        currency_code: Three-letter ISO 4217 currency code

    Returns:
        List of two-letter ISO country codes
        Empty list if currency not found

    Example:
        >>> get_countries_for_currency("XOF")
        ['CI', 'SN', 'ML', 'BF', 'NE', 'TG', 'BJ', 'GW']
        >>> get_countries_for_currency("ZAR")
        ['ZA', 'NA', 'LS', 'SZ']
        >>> get_countries_for_currency("KES")
        ['KE']
    """
    currency_upper = currency_code.upper()
    
    # Check if currency is in a union (multiple countries)
    if currency_upper in CURRENCY_UNIONS:
        return CURRENCY_UNIONS[currency_upper].copy()
    
    # Single country currency
    country = CURRENCY_TO_COUNTRY.get(currency_upper, "")
    return [country] if country else []


def is_major_currency(currency_code: str) -> bool:
    """
    Determines if a currency is classified as a major trading currency.

    Major currencies are those with high liquidity, active forex markets,
    and frequent use in cross-border trade and hedging operations.

    Args:
        currency_code: Three-letter ISO 4217 currency code

    Returns:
        True if the currency is in the MAJOR_CURRENCIES list
        False otherwise

    Example:
        >>> is_major_currency("USD")
        True
        >>> is_major_currency("ZAR")
        True
        >>> is_major_currency("ZMW")
        False
    """
    # Normalize to uppercase and check membership in major currencies list
    return currency_code.upper() in MAJOR_CURRENCIES


def is_african_currency(currency_code: str) -> bool:
    """
    Check if a currency is from an African country.

    This function identifies African currencies by excluding major
    non-African global currencies. Used for regional analytics
    and African-focused reporting.

    Args:
        currency_code: Three-letter ISO 4217 currency code

    Returns:
        True if the currency is primarily used in Africa
        False for major global currencies (USD, EUR, etc.)

    Example:
        >>> is_african_currency("NGN")
        True
        >>> is_african_currency("ZAR")
        True
        >>> is_african_currency("USD")
        False
        >>> is_african_currency("EUR")
        False
    """
    # Normalize to uppercase for comparison
    currency_upper = currency_code.upper()
    
    # Exclude major non-African currencies
    # All other currencies in our registry are African
    non_african = {"USD", "EUR", "GBP", "CNY", "JPY", "CHF", "AUD", "CAD", "INR", "BRL", "AED", "SAR"}
    
    return currency_upper not in non_african


def get_currency_union(currency_code: str) -> Optional[str]:
    """
    Get the currency union name for a multi-country currency.

    Some African currencies are shared across multiple countries
    through monetary unions. This function identifies which union
    a currency belongs to.

    Args:
        currency_code: Three-letter ISO 4217 currency code

    Returns:
        Currency union name or None if not in a union
        Unions: "WAEMU", "CEMAC", "CMA"

    Example:
        >>> get_currency_union("XOF")
        'WAEMU'
        >>> get_currency_union("XAF")
        'CEMAC'
        >>> get_currency_union("ZAR")
        'CMA'
        >>> get_currency_union("KES")
        None  # Single country currency
    """
    currency_upper = currency_code.upper()
    
    # Map currency codes to their union names
    union_names = {
        "XOF": "WAEMU",  # West African Economic and Monetary Union
        "XAF": "CEMAC",  # Central African Economic and Monetary Community
        "ZAR": "CMA",    # Common Monetary Area (Southern Africa)
    }
    
    return union_names.get(currency_upper, None)


def validate_currency_code(currency_code: str) -> bool:
    """
    Validate that a currency code exists in our registry.

    This function performs a case-insensitive check to verify
    that a currency code is recognized by the platform.

    Args:
        currency_code: Three-letter ISO 4217 currency code to validate

    Returns:
        True if the currency code is in our registry
        False otherwise

    Example:
        >>> validate_currency_code("ZAR")
        True
        >>> validate_currency_code("zar")  # Case insensitive
        True
        >>> validate_currency_code("XXX")
        False
    """
    return currency_code.upper() in CURRENCY_TO_COUNTRY


def validate_country_code(country_code: str) -> bool:
    """
    Validate that a country code exists in our registry.

    This function performs a case-insensitive check to verify
    that a country code is recognized by the platform.

    Args:
        country_code: Two-letter ISO 3166-1 alpha-2 country code

    Returns:
        True if the country code is in our registry
        False otherwise

    Example:
        >>> validate_country_code("ZA")
        True
        >>> validate_country_code("za")  # Case insensitive
        True
        >>> validate_country_code("XX")
        False
    """
    return country_code.upper() in COUNTRY_TO_CURRENCY


# Import Optional for function return type hints
from typing import Optional

# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.reference_data.currency_map import *'

__all__ = [
    # Data structures
    "COUNTRY_TO_CURRENCY",
    "CURRENCY_TO_COUNTRY",
    "CURRENCY_UNIONS",
    "MAJOR_CURRENCIES",
    "AFRICAN_CURRENCIES",
    # Utility functions
    "get_currency_for_country",
    "get_country_for_currency",
    "get_countries_for_currency",
    "is_major_currency",
    "is_african_currency",
    "get_currency_union",
    "validate_currency_code",
    "validate_country_code",
]
