"""
@file constants.py
@description Centralised configuration and domain mappings for currency event
             detection and propagation. Defines country-to-currency mappings,
             identifies markets with parallel dynamics, and specifies
             commodity correlations used for FX early warning signals.
@author Thabo Kunene
@created 2026-03-19
"""

# Currency Events Constants
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Currency to country mapping for African currencies.
# Maps the 3-letter ISO currency code to the 2-letter ISO country code.
CURRENCY_COUNTRY_MAP = {
    "ZAR": "ZA", "NGN": "NG", "KES": "KE",
    "GHS": "GH", "TZS": "TZ", "UGX": "UG",
    "ZMW": "ZM", "MZN": "MZ", "AOA": "AO",
    "XOF": "CI", "XAF": "CM", "CDF": "CD",
    "RWF": "RW", "ETB": "ET", "MWK": "MW",
    "BWP": "BW", "NAD": "NA", "SZL": "SZ",
    "LSL": "LS", "ZWL": "ZW", "MUR": "MU",
    "SSP": "SS"
}

# Currencies with known parallel market dynamics.
# These currencies often have an official rate and a diverging parallel rate.
PARALLEL_MARKET_CURRENCIES = {
    "NGN", "AOA", "ETB", "ZWL", "SSP", "CDF"
}

# Commodity correlation for early warning signals.
# Maps a currency to its most influential commodity and the correlation coefficient.
COMMODITY_CORRELATIONS = {
    "ZMW": {"commodity": "copper", "correlation": 0.72},
    "NGN": {"commodity": "brent_crude", "correlation": 0.68},
    "GHS": {"commodity": "gold", "correlation": 0.55},
    "TZS": {"commodity": "gold", "correlation": 0.45},
    "MZN": {"commodity": "aluminium", "correlation": 0.40},
}

# --- Domain identifiers: used for cross-domain impact propagation ---
# Formal corporate and investment banking domain
DOMAIN_CIB = "cib"
# Foreign exchange and treasury domain
DOMAIN_FOREX = "forex"
# Commercial and retail insurance domain
DOMAIN_INSURANCE = "insurance"
# Mobile network and mobile money domain
DOMAIN_CELL = "cell"
# Personal and business banking domain
DOMAIN_PBB = "pbb"

# List of all domains supported by the currency event propagator
ALL_DOMAINS = [
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB
]
