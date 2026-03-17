"""
Seasonal Adjuster

Applies seasonal adjustment factors to raw signal
values to prevent false positives during off-season
periods.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

from seasonal.calendar_loader import (
    SeasonalCalendarLoader,
)
from afriflow.exceptions import SeasonalCalendarError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("seasonal.adjuster")


@dataclass
class SeasonallyAdjustedValue:
    """
    We wrap adjusted values with metadata so downstream
    consumers understand the adjustment applied.
    """

    raw_value: float
    adjusted_value: float
    seasonal_factor: float
    country_code: str
    industry: str
    month: int
    adjustment_type: str

    @property
    def is_peak_season(self) -> bool:
        return self.seasonal_factor > 1.2

    @property
    def is_off_season(self) -> bool:
        return self.seasonal_factor < 0.6

    @property
    def adjustment_pct(self) -> float:
        if self.raw_value == 0:
            return 0.0
        return round(
            (self.adjusted_value - self.raw_value)
            / self.raw_value
            * 100,
            2
        )


class SeasonalAdjuster:
    """
    We apply seasonal adjustment to raw signal values.

    The adjuster normalizes values to account for
    predictable seasonal patterns, preventing the
    flow drift detector and other signal generators
    from raising false alerts during known off-season
    periods.
    """

    def __init__(
        self,
        calendar: Optional[SeasonalCalendarLoader] = None,
        calendar_dir: Optional[str] = None,
    ):
        if calendar is not None:
            self.calendar = calendar
        else:
            try:
                self.calendar = SeasonalCalendarLoader()
            except Exception:
                self.calendar = SeasonalCalendarLoader()

    def adjust(
        self,
        raw_value: float,
        country_code: str,
        industry: str,
        month: int
    ) -> SeasonallyAdjustedValue:
        """
        We adjust a raw value by the seasonal factor.

        If the seasonal factor is 0.3 (deep off-season)
        and the raw value is R3M, the adjusted value is
        R3M / 0.3 = R10M. This tells us the R3M is
        actually normal for off-season and equivalent
        to R10M in peak terms.

        If the seasonal factor is 2.0 (peak season) and
        the raw value is R20M, the adjusted value is
        R20M / 2.0 = R10M. This tells us the R20M is
        inflated by seasonality.
        """

        factor = self.calendar.get_factor(
            country_code, industry, month
        )

        if factor <= 0:
            factor = 1.0

        adjusted = raw_value / factor

        return SeasonallyAdjustedValue(
            raw_value=raw_value,
            adjusted_value=round(adjusted, 2),
            seasonal_factor=factor,
            country_code=country_code,
            industry=industry,
            month=month,
            adjustment_type="commodity_seasonal"
        )

    def adjust_with_ramadan(
        self,
        raw_value: float,
        country_code: str,
        industry: str,
        month: int,
        is_ramadan: bool = False,
        is_eid_week: bool = False
    ) -> SeasonallyAdjustedValue:
        """
        We apply both commodity seasonal and Ramadan
        adjustments. The factors are multiplicative.
        """

        commodity_factor = self.calendar.get_factor(
            country_code, industry, month
        )
        ramadan_factor = self.calendar.get_ramadan_adjustment(
            country_code, is_ramadan, is_eid_week
        )

        combined_factor = commodity_factor * ramadan_factor

        if combined_factor <= 0:
            combined_factor = 1.0

        adjusted = raw_value / combined_factor

        return SeasonallyAdjustedValue(
            raw_value=raw_value,
            adjusted_value=round(adjusted, 2),
            seasonal_factor=combined_factor,
            country_code=country_code,
            industry=industry,
            month=month,
            adjustment_type=(
                "commodity_seasonal_plus_ramadan"
                if is_ramadan or is_eid_week
                else "commodity_seasonal"
            )
        )

    def calculate_drift_with_adjustment(
        self,
        current_value: float,
        previous_value: float,
        country_code: str,
        industry: str,
        current_month: int,
        previous_month: int
    ) -> dict:
        """
        We calculate flow drift between two periods
        with seasonal adjustment applied.

        This is the function that prevents false
        attrition alerts for cocoa exporters in
        off-season.
        """

        current_adjusted = self.adjust(
            current_value, country_code,
            industry, current_month
        )
        previous_adjusted = self.adjust(
            previous_value, country_code,
            industry, previous_month
        )

        raw_drift_pct = (
            (current_value - previous_value)
            / max(previous_value, 1)
            * 100
        )

        adjusted_drift_pct = (
            (
                current_adjusted.adjusted_value
                - previous_adjusted.adjusted_value
            )
            / max(
                previous_adjusted.adjusted_value, 1
            )
            * 100
        )

        return {
            "raw_current": current_value,
            "raw_previous": previous_value,
            "raw_drift_pct": round(raw_drift_pct, 2),
            "adjusted_current": (
                current_adjusted.adjusted_value
            ),
            "adjusted_previous": (
                previous_adjusted.adjusted_value
            ),
            "adjusted_drift_pct": round(
                adjusted_drift_pct, 2
            ),
            "seasonal_factor_current": (
                current_adjusted.seasonal_factor
            ),
            "seasonal_factor_previous": (
                previous_adjusted.seasonal_factor
            ),
            "false_alert_prevented": (
                abs(raw_drift_pct) > 30
                and abs(adjusted_drift_pct) < 15
            ),
            "country_code": country_code,
            "industry": industry
        }


@dataclass
class SeasonalFactor:
    season_name: str
    period_name: str
    expected_change_pct: float
    cash_flow_impact: str
    confidence: float


@dataclass
class ClientSeasonalProfile:
    client_id: str
    active_seasons: List[SeasonalFactor]
    composite_adjustment_pct: float

    @property
    def is_off_season(self) -> bool:
        return self.composite_adjustment_pct < -20.0


class SeasonalAdjuster(SeasonalAdjuster):
    SECTOR_MAP: Dict[str, Dict[str, str]] = {
        "AGR_GRAIN": {"ZA": "maize", "ZM": "maize"},
        "AGR_CASH": {"GH": "cocoa", "KE": "tea"},
    }

    def _sector_to_industry(self, sector: str, country: str) -> Optional[str]:
        sector = (sector or "").upper()
        country = (country or "").upper()
        mapping = self.SECTOR_MAP.get(sector, {})
        return mapping.get(country)

    def _month_in_range(self, month: int, start: int, end: int) -> bool:
        if start <= end:
            return start <= month <= end
        return month >= start or month <= end

    def _za_maize_factor(self, month: int, sector: str) -> SeasonalFactor:
        if self._month_in_range(month, 10, 12):
            return SeasonalFactor("maize", "planting", -10.0, "neutral", 0.7 if sector == "AGR_GRAIN" else 0.5)
        if self._month_in_range(month, 1, 3):
            return SeasonalFactor("maize", "growing", -40.0, "neutral", 0.9 if sector == "AGR_GRAIN" else 0.6)
        if self._month_in_range(month, 4, 6):
            return SeasonalFactor("maize", "harvest", 60.0, "positive", 0.9 if sector == "AGR_GRAIN" else 0.6)
        if self._month_in_range(month, 7, 9):
            return SeasonalFactor("maize", "off_season", -50.0, "neutral", 0.8 if sector == "AGR_GRAIN" else 0.5)
        return SeasonalFactor("maize", "neutral", 0.0, "neutral", 0.0)

    def _gh_cocoa_factor(self, month: int, sector: str) -> SeasonalFactor:
        if self._month_in_range(month, 10, 12):
            return SeasonalFactor("cocoa", "harvest", 80.0, "positive", 0.9 if sector == "AGR_CASH" else 0.6)
        if month == 3:
            return SeasonalFactor("cocoa", "off_season", -50.0, "neutral", 0.8 if sector == "AGR_CASH" else 0.5)
        return SeasonalFactor("cocoa", "neutral", 0.0, "neutral", 0.0)

    def _ke_tea_factor(self, month: int, sector: str) -> SeasonalFactor:
        if month == 1:
            return SeasonalFactor("tea", "peak_harvest", 50.0, "positive", 0.9 if sector == "AGR_CASH" else 0.6)
        return SeasonalFactor("tea", "neutral", 0.0, "neutral", 0.0)

    def get_adjustment_factor(
        self,
        client_id: str,
        sector: str,
        country: str,
        target_date,
    ) -> SeasonalFactor:
        month = getattr(target_date, "month", None)
        if not isinstance(month, int) or month < 1 or month > 12:
            return SeasonalFactor("unknown", "neutral", 0.0, "neutral", 0.0)
        sector_u = (sector or "").upper()
        country_u = (country or "").upper()

        if country_u == "ZA" and sector_u in ("AGR_GRAIN", "RET_FMCG"):
            return self._za_maize_factor(month, sector_u)
        if country_u == "GH" and sector_u in ("AGR_CASH", "RET_FMCG"):
            return self._gh_cocoa_factor(month, sector_u)
        if country_u == "KE" and sector_u in ("AGR_CASH", "RET_FMCG"):
            return self._ke_tea_factor(month, sector_u)

        return SeasonalFactor("neutral", "neutral", 0.0, "neutral", 0.0)

    def get_client_profile(
        self,
        client_id: str,
        sectors: List[str],
        countries: List[str],
        target_date,
    ) -> ClientSeasonalProfile:
        factors: List[SeasonalFactor] = []
        for s in sectors:
            for c in countries:
                f = self.get_adjustment_factor(client_id, s, c, target_date)
                if abs(f.expected_change_pct) > 0.0:
                    factors.append(f)
        composite = (
            sum(f.expected_change_pct for f in factors) / len(factors)
            if factors else 0.0
        )
        return ClientSeasonalProfile(
            client_id=client_id,
            active_seasons=factors,
            composite_adjustment_pct=float(round(composite, 2)),
        )
