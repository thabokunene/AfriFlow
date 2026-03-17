"""
integration/cross_domain_signals/seasonal_calendar.py

Agricultural and commodity seasonal calendar for
African markets.

We use this to adjust cross-domain signals for
expected seasonal patterns. Without seasonal
adjustment, the flow drift detector generates false
attrition alerts every off-season.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple


@dataclass
class SeasonalPeriod:
    """A seasonal classification for a specific sector
    in a specific country at a given point in time."""

    sector: str
    country: str
    query_date: date
    phase: str
    expected_volume_factor: float
    description: str


class SeasonalCalendar:
    """We model the agricultural and commodity cycles
    that drive corporate cash flows across African
    markets.

    Western ML models treat time as weekly or quarterly
    cycles. African corporate cash flows are dominated
    by harvest seasons that do not align with fiscal
    quarters and vary by crop and geography.
    """

    SEASONS: Dict[str, Dict[str, List[Tuple]]] = {
        "cocoa": {
            "GH": [
                (10, 12, "PEAK", 1.8, "Main crop harvest"),
                (1, 3, "OFF_PEAK", 0.4, "Inter-season"),
                (4, 6, "MID_CROP", 0.9, "Mid crop harvest"),
                (7, 9, "PRE_SEASON", 0.7, "Pre-season prep"),
            ],
            "CI": [
                (10, 12, "PEAK", 1.9, "Main crop harvest"),
                (1, 3, "OFF_PEAK", 0.3, "Inter-season"),
                (4, 7, "MID_CROP", 0.8, "Mid crop harvest"),
                (8, 9, "PRE_SEASON", 0.6, "Pre-season prep"),
            ],
        },
        "maize": {
            "ZA": [
                (4, 6, "HARVEST", 1.7, "Main harvest season"),
                (7, 9, "POST_HARVEST", 1.2, "Marketing period"),
                (10, 12, "PLANTING", 0.8, "Planting season"),
                (1, 3, "GROWING", 0.5, "Growing season"),
            ],
            "ZM": [
                (4, 7, "HARVEST", 1.6, "Main harvest season"),
                (8, 10, "POST_HARVEST", 1.1, "Marketing period"),
                (11, 12, "PLANTING", 0.7, "Planting season"),
                (1, 3, "GROWING", 0.4, "Growing season"),
            ],
        },
        "tea": {
            "KE": [
                (1, 3, "PEAK", 1.6, "High rainfall harvest"),
                (4, 6, "MODERATE", 1.1, "Moderate harvest"),
                (7, 9, "PEAK", 1.5, "Second flush harvest"),
                (10, 12, "LOW", 0.6, "Dry season"),
            ],
        },
        "sugar": {
            "MZ": [
                (6, 11, "PEAK", 1.5, "Crushing and harvest"),
                (12, 2, "OFF_PEAK", 0.5, "Inter-crop"),
                (3, 5, "PRE_SEASON", 0.8, "Growth period"),
            ],
            "ZA": [
                (4, 12, "PEAK", 1.3, "Extended crush season"),
                (1, 3, "OFF_PEAK", 0.6, "Inter-crop"),
            ],
        },
        "tobacco": {
            "ZM": [
                (4, 8, "PEAK", 1.7, "Auction and export"),
                (9, 12, "PLANTING", 0.6, "Planting period"),
                (1, 3, "GROWING", 0.5, "Growing period"),
            ],
            "MZ": [
                (3, 7, "PEAK", 1.6, "Harvest and curing"),
                (8, 2, "OFF_PEAK", 0.5, "Off-season"),
            ],
        },
        "mining": {
            "ZA": [
                (1, 12, "NEUTRAL", 1.0, "Year-round ops"),
            ],
            "CD": [
                (5, 10, "PEAK", 1.3, "Dry season operations"),
                (11, 4, "REDUCED", 0.7, "Rainy season reduced ops"),
            ],
        },
    }

    def get_season(
        self,
        sector: str,
        country: str,
        query_date: date,
    ) -> SeasonalPeriod:
        """We return the seasonal classification for a
        given sector, country, and date.

        If we do not have seasonal data for the sector
        or country combination, we return a NEUTRAL
        classification with a volume factor of 1.0
        so that no adjustment is applied.
        """
        sector_lower = sector.lower()
        if sector_lower not in self.SEASONS:
            return SeasonalPeriod(
                sector=sector,
                country=country,
                query_date=query_date,
                phase="NEUTRAL",
                expected_volume_factor=1.0,
                description=(
                    f"No seasonal model for sector "
                    f"'{sector}'"
                ),
            )

        country_seasons = self.SEASONS[sector_lower].get(
            country
        )
        if country_seasons is None:
            return SeasonalPeriod(
                sector=sector,
                country=country,
                query_date=query_date,
                phase="NEUTRAL",
                expected_volume_factor=1.0,
                description=(
                    f"No seasonal model for {sector} "
                    f"in {country}"
                ),
            )

        month = query_date.month

        for start_m, end_m, phase, factor, desc in country_seasons:
            if start_m <= end_m:
                if start_m <= month <= end_m:
                    return SeasonalPeriod(
                        sector=sector,
                        country=country,
                        query_date=query_date,
                        phase=phase,
                        expected_volume_factor=factor,
                        description=desc,
                    )
            else:
                if month >= start_m or month <= end_m:
                    return SeasonalPeriod(
                        sector=sector,
                        country=country,
                        query_date=query_date,
                        phase=phase,
                        expected_volume_factor=factor,
                        description=desc,
                    )

        return SeasonalPeriod(
            sector=sector,
            country=country,
            query_date=query_date,
            phase="NEUTRAL",
            expected_volume_factor=1.0,
            description="No matching season found",
        )

    def adjust_volume(
        self,
        raw_volume: float,
        sector: str,
        country: str,
        query_date: date,
    ) -> float:
        """We adjust an observed volume by the seasonal
        factor to produce a normalized volume that can
        be compared across time periods.

        If a cocoa exporter's payments drop 60% in March,
        the seasonally adjusted volume might show only
        a 10% drop, which is normal. Without this
        adjustment, the flow drift detector would
        generate a false attrition alert.
        """
        period = self.get_season(sector, country, query_date)
        if period.expected_volume_factor == 0:
            return raw_volume
        return raw_volume / period.expected_volume_factor
