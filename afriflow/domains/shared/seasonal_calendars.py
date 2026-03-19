"""
@file seasonal_calendars.py
@description Registry of agricultural and commodity seasonal patterns across African markets to adjust anomaly detection.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Agricultural and Commodity Seasonal Calendars.

We maintain seasonal calendars for major African
commodities. We use these to adjust signal detection
thresholds and prevent false alerts during known
seasonal patterns.

Disclaimer: This is not a sanctioned project. We
built it as a demonstration of concept, domain
knowledge, and skill.
"""

# Dataclasses for defining structured seasonal pattern metadata
from dataclasses import dataclass
# Type hinting for collections and optional values
from typing import List, Optional


@dataclass
class SeasonalPattern:
    """
    Represents a specific seasonal pattern for a commodity within a country.
    Used to normalize data and adjust expectations for trade flows.

    Attributes:
        commodity: Name of the agricultural or resource commodity (e.g., 'maize').
        country_code: ISO country code where the pattern applies.
        peak_months: List of months (1-12) with highest expected activity.
        trough_months: List of months (1-12) with lowest expected activity.
        flow_type: The nature of the movement ('export', 'import', 'domestic').
        expected_peak_multiplier: Scale factor for activity during peak months.
        expected_trough_multiplier: Scale factor for activity during trough months.
    """

    commodity: str
    country_code: str
    peak_months: List[int]  # 1 = January, 12 = December
    trough_months: List[int]
    flow_type: str  # export, import, domestic
    expected_peak_multiplier: float  # vs annual average
    expected_trough_multiplier: float


# Global registry of seasonal patterns for major African commodities.
# This list informs the corridor and data shadow logic of expected cyclicality.
SEASONAL_PATTERNS = [
    # South African Maize: Harvest peaks in Q2
    SeasonalPattern(
        commodity="maize",
        country_code="ZA",
        peak_months=[4, 5, 6],
        trough_months=[11, 12, 1],
        flow_type="export",
        expected_peak_multiplier=2.5,
        expected_trough_multiplier=0.3,
    ),
    # Zambian Maize: Similar harvest cycle to South Africa
    SeasonalPattern(
        commodity="maize",
        country_code="ZM",
        peak_months=[4, 5, 6],
        trough_months=[11, 12, 1],
        flow_type="export",
        expected_peak_multiplier=2.2,
        expected_trough_multiplier=0.4,
    ),
    # Ghanaian Cocoa: Main crop harvest in Q4
    SeasonalPattern(
        commodity="cocoa",
        country_code="GH",
        peak_months=[10, 11, 12],
        trough_months=[3, 4, 5],
        flow_type="export",
        expected_peak_multiplier=3.0,
        expected_trough_multiplier=0.2,
    ),
    # Ivorian Cocoa: World's largest producer, follows similar Q4 peak
    SeasonalPattern(
        commodity="cocoa",
        country_code="CI",
        peak_months=[10, 11, 12],
        trough_months=[3, 4, 5],
        flow_type="export",
        expected_peak_multiplier=3.2,
        expected_trough_multiplier=0.2,
    ),
    # Kenyan Tea: High production in Q1 following rains
    SeasonalPattern(
        commodity="tea",
        country_code="KE",
        peak_months=[1, 2, 3],
        trough_months=[7, 8, 9],
        flow_type="export",
        expected_peak_multiplier=2.0,
        expected_trough_multiplier=0.5,
    ),
    # Mozambican Sugar: Extended harvest season through second half of year
    SeasonalPattern(
        commodity="sugar",
        country_code="MZ",
        peak_months=[6, 7, 8, 9, 10, 11],
        trough_months=[1, 2, 3],
        flow_type="export",
        expected_peak_multiplier=1.8,
        expected_trough_multiplier=0.4,
    ),
    # Zambian Tobacco: Curing and auction season in Q2
    SeasonalPattern(
        commodity="tobacco",
        country_code="ZM",
        peak_months=[3, 4, 5, 6],
        trough_months=[9, 10, 11],
        flow_type="export",
        expected_peak_multiplier=2.5,
        expected_trough_multiplier=0.3,
    ),
    # Kenyan Coffee: Main harvest period peaking late in the year
    SeasonalPattern(
        commodity="coffee",
        country_code="KE",
        peak_months=[10, 11, 12, 1],
        trough_months=[5, 6, 7],
        flow_type="export",
        expected_peak_multiplier=2.3,
        expected_trough_multiplier=0.4,
    ),
    SeasonalPattern(
        commodity="coffee",
        country_code="UG",
        peak_months=[10, 11, 12, 1],
        trough_months=[5, 6, 7],
        flow_type="export",
        expected_peak_multiplier=2.1,
        expected_trough_multiplier=0.4,
    ),
]


def get_seasonal_patterns(
    country_code: str,
    commodity: Optional[str] = None,
) -> List[SeasonalPattern]:
    """
    Return all seasonal patterns for a country,
    optionally filtered by commodity.
    """
    patterns = [
        p
        for p in SEASONAL_PATTERNS
        if p.country_code == country_code
    ]
    if commodity:
        patterns = [
            p for p in patterns
            if p.commodity == commodity
        ]
    return patterns


def is_peak_season(
    country_code: str,
    commodity: str,
    month: int,
) -> bool:
    """
    Check whether a given month is peak season for
    a commodity in a country. We use this to suppress
    false attrition alerts during expected seasonal
    surges.
    """
    patterns = get_seasonal_patterns(
        country_code, commodity
    )
    for pattern in patterns:
        if month in pattern.peak_months:
            return True
    return False


def is_trough_season(
    country_code: str,
    commodity: str,
    month: int,
) -> bool:
    """
    Check whether a given month is trough season for
    a commodity in a country. We use this to suppress
    false attrition alerts during expected seasonal
    declines.
    """
    patterns = get_seasonal_patterns(
        country_code, commodity
    )
    for pattern in patterns:
        if month in pattern.trough_months:
            return True
    return False
