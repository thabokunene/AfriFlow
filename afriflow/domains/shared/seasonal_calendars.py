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

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SeasonalPattern:
    """A seasonal pattern for a commodity in a country."""

    commodity: str
    country_code: str
    peak_months: List[int]  # 1 = January, 12 = December
    trough_months: List[int]
    flow_type: str  # export, import, domestic
    expected_peak_multiplier: float  # vs annual average
    expected_trough_multiplier: float


SEASONAL_PATTERNS = [
    SeasonalPattern(
        commodity="maize",
        country_code="ZA",
        peak_months=[4, 5, 6],
        trough_months=[11, 12, 1],
        flow_type="export",
        expected_peak_multiplier=2.5,
        expected_trough_multiplier=0.3,
    ),
    SeasonalPattern(
        commodity="maize",
        country_code="ZM",
        peak_months=[4, 5, 6],
        trough_months=[11, 12, 1],
        flow_type="export",
        expected_peak_multiplier=2.2,
        expected_trough_multiplier=0.4,
    ),
    SeasonalPattern(
        commodity="cocoa",
        country_code="GH",
        peak_months=[10, 11, 12],
        trough_months=[3, 4, 5],
        flow_type="export",
        expected_peak_multiplier=3.0,
        expected_trough_multiplier=0.2,
    ),
    SeasonalPattern(
        commodity="cocoa",
        country_code="CI",
        peak_months=[10, 11, 12],
        trough_months=[3, 4, 5],
        flow_type="export",
        expected_peak_multiplier=3.2,
        expected_trough_multiplier=0.2,
    ),
    SeasonalPattern(
        commodity="tea",
        country_code="KE",
        peak_months=[1, 2, 3],
        trough_months=[7, 8, 9],
        flow_type="export",
        expected_peak_multiplier=2.0,
        expected_trough_multiplier=0.5,
    ),
    SeasonalPattern(
        commodity="sugar",
        country_code="MZ",
        peak_months=[6, 7, 8, 9, 10, 11],
        trough_months=[1, 2, 3],
        flow_type="export",
        expected_peak_multiplier=1.8,
        expected_trough_multiplier=0.4,
    ),
    SeasonalPattern(
        commodity="tobacco",
        country_code="ZM",
        peak_months=[3, 4, 5, 6],
        trough_months=[9, 10, 11],
        flow_type="export",
        expected_peak_multiplier=2.5,
        expected_trough_multiplier=0.3,
    ),
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
