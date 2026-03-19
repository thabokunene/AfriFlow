"""
@file seasonal_calendar.py
@description Agricultural and commodity seasonal calendar for African markets,
    providing adjustments for cross-domain signals to account for harvest-driven
    cash flow volatility and avoid false attrition alerts.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard-library imports
from dataclasses import dataclass      # Typed return value for seasonal queries
from datetime import date              # Query date for season lookup
from typing import Dict, List, Optional, Tuple  # Type annotations


# ---------------------------------------------------------------------------
# Result dataclass: returned for every get_season() call
# ---------------------------------------------------------------------------

@dataclass
class SeasonalPeriod:
    """A seasonal classification for a specific sector
    in a specific country at a given point in time."""

    # The commodity / sector queried (e.g. "cocoa")
    sector: str
    # ISO 3166-1 alpha-2 country code (e.g. "GH")
    country: str
    # The date that was supplied to the query
    query_date: date
    # Phase label: "PEAK", "OFF_PEAK", "HARVEST", "PLANTING", "NEUTRAL", etc.
    phase: str
    # Multiplier to apply to observed volume: 1.0 = normal, 1.8 = peak, 0.4 = off-peak
    expected_volume_factor: float
    # Human-readable description of the phase for RM-facing output
    description: str


# ---------------------------------------------------------------------------
# Calendar engine
# ---------------------------------------------------------------------------

class SeasonalCalendar:
    """We model the agricultural and commodity cycles
    that drive corporate cash flows across African
    markets.

    Western ML models treat time as weekly or quarterly
    cycles. African corporate cash flows are dominated
    by harvest seasons that do not align with fiscal
    quarters and vary by crop and geography.
    """

    # Seasonal data structure:
    # SEASONS[sector][country] = list of (start_month, end_month, phase, factor, desc)
    # Months are 1-indexed (January = 1).
    # Ranges that wrap around year-end (e.g. 8–2 in tobacco/MZ) are handled
    # by the get_season() method's year-wrap logic.
    SEASONS: Dict[str, Dict[str, List[Tuple]]] = {
        "cocoa": {
            # Ghana cocoa: two crops per year; main crop Oct–Dec is dominant
            "GH": [
                (10, 12, "PEAK", 1.8, "Main crop harvest"),
                (1, 3, "OFF_PEAK", 0.4, "Inter-season"),
                (4, 6, "MID_CROP", 0.9, "Mid crop harvest"),
                (7, 9, "PRE_SEASON", 0.7, "Pre-season prep"),
            ],
            # Côte d'Ivoire cocoa: world's largest producer; patterns similar to GH
            "CI": [
                (10, 12, "PEAK", 1.9, "Main crop harvest"),
                (1, 3, "OFF_PEAK", 0.3, "Inter-season"),
                (4, 7, "MID_CROP", 0.8, "Mid crop harvest"),
                (8, 9, "PRE_SEASON", 0.6, "Pre-season prep"),
            ],
        },
        "maize": {
            # South Africa summer maize: planted Oct–Nov, harvested Apr–Jun
            "ZA": [
                (4, 6, "HARVEST", 1.7, "Main harvest season"),
                (7, 9, "POST_HARVEST", 1.2, "Marketing period"),
                (10, 12, "PLANTING", 0.8, "Planting season"),
                (1, 3, "GROWING", 0.5, "Growing season"),
            ],
            # Zambia maize: similar pattern to ZA but harvest slightly later
            "ZM": [
                (4, 7, "HARVEST", 1.6, "Main harvest season"),
                (8, 10, "POST_HARVEST", 1.1, "Marketing period"),
                (11, 12, "PLANTING", 0.7, "Planting season"),
                (1, 3, "GROWING", 0.4, "Growing season"),
            ],
        },
        "tea": {
            # Kenya tea: bimodal harvest driven by two rainy seasons
            "KE": [
                (1, 3, "PEAK", 1.6, "High rainfall harvest"),
                (4, 6, "MODERATE", 1.1, "Moderate harvest"),
                (7, 9, "PEAK", 1.5, "Second flush harvest"),
                (10, 12, "LOW", 0.6, "Dry season"),
            ],
        },
        "sugar": {
            # Mozambique sugar: long crushing season Jun–Nov
            "MZ": [
                (6, 11, "PEAK", 1.5, "Crushing and harvest"),
                (12, 2, "OFF_PEAK", 0.5, "Inter-crop"),    # Wraps year-end
                (3, 5, "PRE_SEASON", 0.8, "Growth period"),
            ],
            # South Africa sugar: extended season Apr–Dec
            "ZA": [
                (4, 12, "PEAK", 1.3, "Extended crush season"),
                (1, 3, "OFF_PEAK", 0.6, "Inter-crop"),
            ],
        },
        "tobacco": {
            # Zambia tobacco: auction season Apr–Aug drives payment volume
            "ZM": [
                (4, 8, "PEAK", 1.7, "Auction and export"),
                (9, 12, "PLANTING", 0.6, "Planting period"),
                (1, 3, "GROWING", 0.5, "Growing period"),
            ],
            # Mozambique tobacco: harvest and curing Feb–Jul
            "MZ": [
                (3, 7, "PEAK", 1.6, "Harvest and curing"),
                (8, 2, "OFF_PEAK", 0.5, "Off-season"),     # Wraps year-end
            ],
        },
        "mining": {
            # South Africa mining: year-round operations, no seasonal pattern
            "ZA": [
                (1, 12, "NEUTRAL", 1.0, "Year-round ops"),
            ],
            # DRC copper/cobalt: reduced operations in rainy season
            "CD": [
                (5, 10, "PEAK", 1.3, "Dry season operations"),
                (11, 4, "REDUCED", 0.7, "Rainy season reduced ops"),  # Wraps year-end
            ],
        },
    }

    def get_season(
        self,
        sector: str,
        country: str,
        query_date: date,
    ) -> SeasonalPeriod:
        """
        We return the seasonal classification for a
        given sector, country, and date.

        If we do not have seasonal data for the sector
        or country combination, we return a NEUTRAL
        classification with a volume factor of 1.0
        so that no adjustment is applied.

        :param sector: Commodity or industry sector (case-insensitive)
        :param country: ISO 3166-1 alpha-2 country code
        :param query_date: The date to classify
        :return: SeasonalPeriod with phase, factor, and description
        """
        # Normalise sector to lowercase for case-insensitive lookup
        sector_lower = sector.lower()
        if sector_lower not in self.SEASONS:
            # Unknown sector — return neutral to avoid spurious adjustments
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
            # Known sector but unknown country combination — return neutral
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
                # Simple non-wrapping range (e.g. April to June)
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
                # Wrapping range: e.g. Oct(10) to Feb(2) means Oct, Nov, Dec, Jan, Feb
                if month >= start_m or month <= end_m:
                    return SeasonalPeriod(
                        sector=sector,
                        country=country,
                        query_date=query_date,
                        phase=phase,
                        expected_volume_factor=factor,
                        description=desc,
                    )

        # No range matched (gap in the season definitions) — return neutral
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
        """
        We adjust an observed volume by the seasonal
        factor to produce a normalized volume that can
        be compared across time periods.

        If a cocoa exporter's payments drop 60% in March,
        the seasonally adjusted volume might show only
        a 10% drop, which is normal. Without this
        adjustment, the flow drift detector would
        generate a false attrition alert.

        :param raw_volume: The observed payment or activity volume
        :param sector: Commodity or industry sector (case-insensitive)
        :param country: ISO 3166-1 alpha-2 country code
        :param query_date: The date of the observed volume
        :return: Volume normalised by the seasonal factor; equal to raw_volume
                 if the factor is NEUTRAL (1.0) or zero (division guard)
        """
        period = self.get_season(sector, country, query_date)
        # Guard against division by zero for edge-case zero-factor entries
        if period.expected_volume_factor == 0:
            return raw_volume
        # Divide by the expected factor: a peak-season volume is deflated,
        # an off-season volume is inflated, to produce a comparable baseline
        return raw_volume / period.expected_volume_factor
