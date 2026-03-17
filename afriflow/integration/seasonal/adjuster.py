"""
integration/seasonal/adjuster.py

Seasonal Adjustment Engine for African Agricultural Cycles.

Western time-series models treat time as weekly or quarterly
cycles. African corporate cash flows are dominated by harvest
seasons that do not align with fiscal quarters.

We adjust for these patterns to prevent false attrition
alerts during expected low-activity periods.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple
import json
import os


@dataclass
class SeasonalFactor:
    """A seasonal adjustment factor for a specific period."""

    season_name: str
    period_name: str
    start_month: int
    end_month: int
    expected_change_pct: float
    cash_flow_impact: str
    confidence: float


@dataclass
class ClientSeasonalProfile:
    """Composite seasonal profile for a multi-country client."""

    client_id: str
    target_date: date
    active_seasons: List[SeasonalFactor]
    composite_adjustment_pct: float
    is_off_season: bool
    is_peak_season: bool


class SeasonalAdjuster:
    """
    We adjust corporate cash flow signals for expected
    seasonal patterns in African agricultural markets.
    """

    SEASONAL_CALENDARS: Dict[str, Dict] = {
        "ZA": {
            "AGR_GRAIN": {
                "maize": [
                    ("planting", 10, 12, -25, "negative"),
                    ("growing", 1, 3, -40, "neutral"),
                    ("harvest", 4, 6, 60, "positive"),
                    ("marketing", 7, 9, 20, "positive_declining"),
                ],
            },
            "AGR_CASH": {
                "sugar": [
                    ("crushing", 4, 12, 50, "positive"),
                    ("off_season", 1, 3, -30, "negative"),
                ],
            },
            "MIN_GOLD": {
                "mining": [
                    ("year_round", 1, 12, 0, "neutral"),
                ],
            },
        },
        "GH": {
            "AGR_CASH": {
                "cocoa": [
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
                    ("peak", 1, 3, 50, "positive"),
                    ("moderate", 4, 6, 20, "positive_moderate"),
                    ("second_flush", 7, 9, 45, "positive"),
                    ("low", 10, 12, -20, "negative"),
                ],
                "coffee": [
                    ("harvest", 10, 12, 60, "positive"),
                    ("off_season", 1, 9, -30, "negative"),
                ],
            },
        },
        "MZ": {
            "AGR_CASH": {
                "sugar": [
                    ("crushing", 6, 11, 80, "positive"),
                    ("off_season", 12, 5, -50, "negative"),
                ],
            },
        },
        "ZM": {
            "AGR_GRAIN": {
                "maize": [
                    ("harvest", 4, 7, 55, "positive"),
                    ("post_harvest", 8, 10, 25, "positive_moderate"),
                    ("planting", 11, 12, -30, "negative"),
                    ("growing", 1, 3, -45, "neutral"),
                ],
            },
        },
    }

    SECTOR_RELEVANCE: Dict[str, float] = {
        "AGR_GRAIN": 1.0,
        "AGR_CASH": 1.0,
        "AGR_SUGAR": 1.0,
        "MIN_GOLD": 0.3,
        "MIN_COPPER": 0.3,
        "RET_FMCG": 0.5,
        "FIN_BANK": 0.4,
        "TEL_MOBILE": 0.3,
        "MAN_GENERAL": 0.4,
        "CON_INFRA": 0.5,
        "SVC_PROFESSIONAL": 0.4,
    }

    def __init__(self, calendar_dir: Optional[str] = None):
        if calendar_dir and os.path.exists(calendar_dir):
            self._load_calendars(calendar_dir)

    def _load_calendars(self, calendar_dir: str) -> None:
        """Load seasonal calendars from YAML files."""
        pass

    def _month_in_range(self, month: int, start: int, end: int) -> bool:
        """Check if month is in range, handling year wraps."""
        if start <= end:
            return start <= month <= end
        else:
            return month >= start or month <= end

    def get_adjustment_factor(
        self,
        client_id: str,
        sector: str,
        country: str,
        target_date: date,
    ) -> SeasonalFactor:
        """
        Get the seasonal adjustment factor for a client
        at a specific point in time.
        """
        month = target_date.month

        country_calendars = self.SEASONAL_CALENDARS.get(country, {})
        sector_calendars = country_calendars.get(sector, {})

        if not sector_calendars:
            return SeasonalFactor(
                season_name="unknown",
                period_name="neutral",
                start_month=1,
                end_month=12,
                expected_change_pct=0.0,
                cash_flow_impact="neutral",
                confidence=0.0,
            )

        for season_name, periods in sector_calendars.items():
            for period_name, start, end, change, impact in periods:
                if self._month_in_range(month, start, end):
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
        """
        Get a composite seasonal profile for a client
        operating across multiple countries and sectors.
        """
        active_seasons = []
        adjustments = []

        for sector in sectors:
            for country in countries:
                factor = self.get_adjustment_factor(
                    client_id, sector, country, target_date
                )
                if factor.confidence > 0:
                    active_seasons.append(factor)
                    adjustments.append(factor.expected_change_pct)

        if adjustments:
            composite = sum(adjustments) / len(adjustments)
        else:
            composite = 0.0

        is_off_season = composite < -20
        is_peak_season = composite > 40

        return ClientSeasonalProfile(
            client_id=client_id,
            target_date=target_date,
            active_seasons=active_seasons,
            composite_adjustment_pct=composite,
            is_off_season=is_off_season,
            is_peak_season=is_peak_season,
        )
