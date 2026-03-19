"""
@file african_countries.py
@description Central registry of African countries, their regions, capitals, and core banking markets.
@author Thabo Kunene
@created 2026-03-19
"""

# Dictionary mapping ISO country codes to metadata including name, region, and capital.
# This serves as a source of truth for country-level data enrichment and reporting.
AFRICAN_COUNTRIES = {
    "ZA": {"name": "South Africa", "region": "Southern Africa", "capital": "Pretoria"},
    "NG": {"name": "Nigeria", "region": "West Africa", "capital": "Abuja"},
    "KE": {"name": "Kenya", "region": "East Africa", "capital": "Nairobi"},
    "EG": {"name": "Egypt", "region": "North Africa", "capital": "Cairo"},
    "GH": {"name": "Ghana", "region": "West Africa", "capital": "Accra"},
    "RW": {"name": "Rwanda", "region": "East Africa", "capital": "Kigali"},
    "MA": {"name": "Morocco", "region": "North Africa", "capital": "Rabat"},
    "ET": {"name": "Ethiopia", "region": "East Africa", "capital": "Addis Ababa"},
    "CI": {"name": "Ivory Coast", "region": "West Africa", "capital": "Yamoussoukro"},
    "TZ": {"name": "Tanzania", "region": "East Africa", "capital": "Dodoma"},
    "UG": {"name": "Uganda", "region": "East Africa", "capital": "Kampala"},
    "ZM": {"name": "Zambia", "region": "Southern Africa", "capital": "Lusaka"},
    "ZW": {"name": "Zimbabwe", "region": "Southern Africa", "capital": "Harare"},
    "MZ": {"name": "Mozambique", "region": "Southern Africa", "capital": "Maputo"},
    "AO": {"name": "Angola", "region": "Central Africa", "capital": "Luanda"},
}

# List of primary markets where the bank maintains significant physical and digital presence.
# These markets typically receive prioritized analytics and infrastructure resources.
CORE_MARKETS = ["ZA", "NG", "KE", "GH"]
