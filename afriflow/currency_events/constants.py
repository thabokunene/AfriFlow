"""
Currency Events Constants

Centralized configuration and domain mappings for 
currency event detection and propagation.
"""

# Currency to country mapping for African currencies
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

# Currencies with known parallel market dynamics
PARALLEL_MARKET_CURRENCIES = {
    "NGN", "AOA", "ETB", "ZWL", "SSP", "CDF"
}

# Commodity correlation for early warning
COMMODITY_CORRELATIONS = {
    "ZMW": {"commodity": "copper", "correlation": 0.72},
    "NGN": {"commodity": "brent_crude", "correlation": 0.68},
    "GHS": {"commodity": "gold", "correlation": 0.55},
    "TZS": {"commodity": "gold", "correlation": 0.45},
    "MZN": {"commodity": "aluminium", "correlation": 0.40},
}

# Domain identifiers
DOMAIN_CIB = "cib"
DOMAIN_FOREX = "forex"
DOMAIN_INSURANCE = "insurance"
DOMAIN_CELL = "cell"
DOMAIN_PBB = "pbb"

ALL_DOMAINS = [
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB
]
