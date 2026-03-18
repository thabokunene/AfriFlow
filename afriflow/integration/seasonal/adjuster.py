"""
@file adjuster.py
@description Seasonal Adjustment Engine for African agricultural cycles.
    Adjusts corporate cash flow signals for country-sector harvest and
    planting seasons to prevent false attrition alerts during expected
    low-activity periods. Builds composite seasonal profiles for
    multi-country clients operating across several sectors.
@author Thabo Kunene
@created 2026-03-18
"""
# Original module description preserved below:
# integration/seasonal/adjuster.py
#
# Western time-series models treat time as weekly or quarterly cycles.
# African corporate cash flows are dominated by harvest seasons that do
# not align with fiscal quarters. We adjust for these patterns to prevent
# false attrition alerts during expected low-activity periods.
#
# DISCLAIMER: This project is not sanctioned by, affiliated with, or
# endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
# It is a demonstration of concept, domain knowledge, and technical skill
# built by Thabo Kunene for portfolio and learning purposes only.

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple
import json
import os


@dataclass
class SeasonalFactor:
    """A seasonal adjustment factor for a specific period.

    Encodes expected cash flow change percentage and impact
    direction for a named agricultural or commodity season.
    """

    season_name: str       # e.g. "cocoa", "maize"
    period_name: str       # e.g. "harvest", "planting", "off_season"
    start_month: int       # Calendar month when this phase begins (1–12)
    end_month: int         # Calendar month when this phase ends (1–12)
    expected_change_pct: float  # Expected % change vs baseline (negative = below)
    cash_flow_impact: str  # Qualitative label: "positive", "negative", "neutral"
    confidence: float      # Confidence in this factor (0–1), driven by sector relevance


@dataclass
class ClientSeasonalProfile:
    """Composite seasonal profile for a multi-country client.

    Aggregates all active seasonal factors across every country
    and sector a client operates in, and derives a single
    composite adjustment percentage and season status flags.
    """

    client_id: str
    target_date: date
    active_seasons: List[SeasonalFactor]    # All matched seasonal factors
    composite_adjustment_pct: float         # Mean expected change across active seasons
    is_off_season: bool                     # True when composite < -20%
    is_peak_season: bool                    # True when composite > 40%


class SeasonalAdjuster:
    """
    We adjust corporate cash flow signals for expected
    seasonal patterns in African agricultural markets.

    The adjuster holds a lookup table of country × sector seasonal
    calendars and resolves each calendar period to an expected cash
    flow change percentage. Clients operating in multiple countries
    and sectors receive a composite profile.
    """

    # Nested structure: country → sector_code → crop → list of period tuples
    # Each period tuple: (period_name, start_month, end_month, change_pct, impact_label)
    SEASONAL_CALENDARS: Dict[str, Dict] = {
        "ZA": {
            "AGR_GRAIN": {
                "maize": [
                    # Highveld maize: planting Oct–Dec, growing Jan–Mar,
                    # harvest Apr–Jun, marketing (silo sales) Jul–Sep
                    ("planting", 10, 12, -25, "negative"),
                    ("growing", 1, 3, -40, "neutral"),
                    ("harvest", 4, 6, 60, "positive"),
                    ("marketing", 7, 9, 20, "positive_declining"),
                ],
            },
            "AGR_CASH": {
                "sugar": [
                    # KwaZulu-Natal sugar cane: crushing Apr–Dec, off-season Jan–Mar
                    ("crushing", 4, 12, 50, "positive"),
                    ("off_season", 1, 3, -30, "negative"),
                ],
            },
            "MIN_GOLD": {
                "mining": [
                    # Deep-level gold mining is continuous year-round
                    ("year_round", 1, 12, 0, "neutral"),
                ],
            },
        },
        "GH": {
            "AGR_CASH": {
                "cocoa": [
                    # Ghana cocoa: main crop Oct–Dec, off-season Jan–Mar,
                    # light mid-crop Apr–Jun, pre-season building Jul–Sep
                    ("main_crop", 10, 12, 80, "positive"),
                    ("off_season", 1, 3, -50, "negative"),
                    ("mid_crop", 4, 6, 30, "positive_moderate"),
                    ("pre_season", 7, 9, -10, "neutral"),
                ],
            },
        },
        "KE": {
            "AGR_CASH": {
                "tea": [
                    # Kenya tea: two flush seasons driven by long rains (Jan–Mar)
                    # and short rains (Jul–Sep)
                    ("peak", 1, 3, 50, "positive"),
                    ("moderate", 4, 6, 20, "positive_moderate"),
                    ("second_flush", 7, 9, 45, "positive"),
                    ("low", 10, 12, -20, "negative"),
                ],
                "coffee": [
                    # Kenya coffee: main harvest Oct–Dec, off-season Jan–Sep
                    ("harvest", 10, 12, 60, "positive"),
                    ("off_season", 1, 9, -30, "negative"),
                ],
            },
        },
        "MZ": {
            "AGR_CASH": {
                "sugar": [
                    # Mozambique sugar: crushing Jun–Nov, off-season Dec–May
                    # Note: range wraps year boundary (12 to 5)
                    ("crushing", 6, 11, 80, "positive"),
                    ("off_season", 12, 5, -50, "negative"),
                ],
            },
        },
        "ZM": {
            "AGR_GRAIN": {
                "maize": [
                    # Zambia maize: harvest Apr–Jul, post-harvest Aug–Oct,
                    # planting Nov–Dec, growing Jan–Mar
                    ("harvest", 4, 7, 55, "positive"),
                    ("post_harvest", 8, 10, 25, "positive_moderate"),
                    ("planting", 11, 12, -30, "negative"),
                    ("growing", 1, 3, -45, "neutral"),
                ],
            },
        },
    }

    # How much a sector's agricultural cycle dominates its cash flows.
    # 1.0 = fully season-driven; 0.3 = mostly non-seasonal.
    SECTOR_RELEVANCE: Dict[str, float] = {
        "AGR_GRAIN": 1.0,       # Grain farming: entirely season-driven
        "AGR_CASH": 1.0,        # Cash crops (cocoa, tea, coffee): entirely seasonal
        "AGR_SUGAR": 1.0,       # Sugar cane: crushing season dominant
        "MIN_GOLD": 0.3,        # Gold mining: price-driven, low seasonality
        "MIN_COPPER": 0.3,      # Copper mining: price-driven, low seasonality
        "RET_FMCG": 0.5,        # Retail FMCG: festive seasonality moderate
        "FIN_BANK": 0.4,        # Banking: end-of-quarter driven
        "TEL_MOBILE": 0.3,      # Telecom: low agricultural seasonality
        "MAN_GENERAL": 0.4,     # Manufacturing: moderate seasonal demand
        "CON_INFRA": 0.5,       # Construction: wet/dry season dependent
        "SVC_PROFESSIONAL": 0.4, # Professional services: fiscal year driven
    }

    def __init__(self, calendar_dir: Optional[str] = None):
        """Initialise the adjuster, optionally loading external YAML calendars.

        Args:
            calendar_dir: Path to a directory containing YAML calendar overrides.
                          If None or the path does not exist, built-in calendars
                          defined in SEASONAL_CALENDARS are used.
        """
        # Only attempt to load external calendars if the path is valid
        if calendar_dir and os.path.exists(calendar_dir):
            self._load_calendars(calendar_dir)

    def _load_calendars(self, calendar_dir: str) -> None:
        """Load seasonal calendars from YAML files.

        Placeholder: external YAML override loading is not yet implemented.
        Currently the built-in SEASONAL_CALENDARS constant is the sole source.
        """
        pass

    def _month_in_range(self, month: int, start: int, end: int) -> bool:
        """Check if a calendar month falls within a named period.

        Handles year-boundary wraps (e.g. Dec–Feb crushing seasons)
        by testing both the normal case and the wrapped case.

        Args:
            month: The month to test (1–12).
            start: First month of the period (1–12).
            end: Last month of the period (1–12).

        Returns:
            True if the month is within [start, end], accounting for wrap.
        """
        if start <= end:
            # Normal range: no year wrap (e.g. Apr–Jun)
            return start <= month <= end
        else:
            # Year-wrapped range (e.g. Dec–Mar): month is either at the end
            # of one year or at the start of the next
            return month >= start or month <= end

    def get_adjustment_factor(
        self,
        client_id: str,
        sector: str,
        country: str,
        target_date: date,
    ) -> SeasonalFactor:
        """Get the seasonal adjustment factor for a client at a specific point in time.

        Looks up the SEASONAL_CALENDARS for the given country × sector,
        finds the active period for the target month, and returns a
        SeasonalFactor with the expected cash flow change.

        Args:
            client_id: Client identifier (reserved for future per-client overrides).
            sector: Sector code e.g. "AGR_GRAIN", "AGR_CASH".
            country: ISO-2 country code e.g. "ZA", "GH".
            target_date: The date for which adjustment is required.

        Returns:
            SeasonalFactor with confidence=0.0 if no matching pattern found.
        """
        # Extract the month number from the target date
        month = target_date.month

        # Navigate the nested calendar structure: country → sector → crops
        country_calendars = self.SEASONAL_CALENDARS.get(country, {})
        sector_calendars = country_calendars.get(sector, {})

        # No calendar defined for this country/sector: return a neutral factor
        if not sector_calendars:
            return SeasonalFactor(
                season_name="unknown",
                period_name="neutral",
                start_month=1,
                end_month=12,
                expected_change_pct=0.0,
                cash_flow_impact="neutral",
                confidence=0.0,  # Zero confidence signals no data for this combination
            )

        # Iterate crops within this sector and find the active period
        for season_name, periods in sector_calendars.items():
            for period_name, start, end, change, impact in periods:
                if self._month_in_range(month, start, end):
                    # Use the sector relevance weight as the confidence level
                    relevance = self.SECTOR_RELEVANCE.get(sector, 0.5)
                    return SeasonalFactor(
                        season_name=season_name,
                        period_name=period_name,
                        start_month=start,
                        end_month=end,
                        expected_change_pct=change,
                        cash_flow_impact=impact,
                        confidence=relevance,
                    )

        # All periods were checked but none matched this month: return neutral
        return SeasonalFactor(
            season_name="unknown",
            period_name="neutral",
            start_month=1,
            end_month=12,
            expected_change_pct=0.0,
            cash_flow_impact="neutral",
            confidence=0.0,
        )

    def get_client_profile(
        self,
        client_id: str,
        sectors: List[str],
        countries: List[str],
        target_date: date,
    ) -> ClientSeasonalProfile:
        """Get a composite seasonal profile for a multi-country, multi-sector client.

        Iterates over every (sector, country) pair the client operates in,
        collects all matched seasonal factors, and computes a single composite
        adjustment percentage as the unweighted mean of the active adjustments.

        Args:
            client_id: Client identifier.
            sectors: List of sector codes the client operates in.
            countries: List of ISO-2 country codes the client is present in.
            target_date: Date for which the profile is computed.

        Returns:
            ClientSeasonalProfile with composite adjustment and season flags.
        """
        active_seasons = []  # Accumulate all matched seasonal factors
        adjustments = []     # Collect numeric change percentages for averaging

        # Cross-product of sectors × countries
        for sector in sectors:
            for country in countries:
                factor = self.get_adjustment_factor(
                    client_id, sector, country, target_date
                )
                # Only include factors where a real pattern was found (confidence > 0)
                if factor.confidence > 0:
                    active_seasons.append(factor)
                    adjustments.append(factor.expected_change_pct)

        # Compute the simple mean of all active adjustment percentages
        if adjustments:
            composite = sum(adjustments) / len(adjustments)
        else:
            # No matched patterns: assume no seasonal effect
            composite = 0.0

        # Classify the overall composite direction as off-season or peak-season
        is_off_season = composite < -20   # Deep trough: suppress attrition alerts
        is_peak_season = composite > 40   # Harvest spike: suppress false anomalies

        return ClientSeasonalProfile(
            client_id=client_id,
            target_date=target_date,
            active_seasons=active_seasons,
            composite_adjustment_pct=composite,
            is_off_season=is_off_season,
            is_peak_season=is_peak_season,
        )
