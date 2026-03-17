"""
Seasonal Calendar Loader

Loads and serves seasonal adjustment factors for African
agricultural, commodity, and cultural cycles.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import json
import os
from typing import Dict, Optional
import logging

from afriflow.exceptions import SeasonalCalendarError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("seasonal.calendar_loader")


class SeasonalCalendarLoader:
    """
    We load seasonal factors from the African calendar
    JSON and serve them to signal detection components.

    We support lookup by country, industry, and month.
    When no specific factor exists, we return 1.0
    (no adjustment).
    """

    DEFAULT_FACTOR = 1.0
    CALENDAR_PATH = os.path.join(
        os.path.dirname(__file__),
        "african_calendar.json"
    )

    def __init__(
        self, calendar_path: Optional[str] = None
    ):
        self.calendar_path = (
            calendar_path or self.CALENDAR_PATH
        )
        self.factors: Dict = {}
        self.religious: Dict = {}
        self._load()

    def _load(self):
        """Load the calendar from JSON."""

        with open(self.calendar_path, "r") as f:
            data = json.load(f)

        self.factors = data.get("seasonal_factors", {})
        self.religious = data.get(
            "religious_calendar", {}
        )

    def get_factor(
        self,
        country_code: str,
        industry: str,
        month: int
    ) -> float:
        """
        We retrieve the seasonal factor for a given
        country, industry, and month.

        Args:
            country_code: ISO 3166-1 alpha-2 code
            industry: Industry segment key
            month: Month number (1 to 12)

        Returns:
            Seasonal factor. Values > 1.0 indicate peak
            season. Values < 1.0 indicate off season.
        """

        if month < 1 or month > 12:
            raise ValueError(
                f"Month must be between 1 and 12, "
                f"got {month}"
            )

        country_factors = self.factors.get(
            country_code, {}
        )
        industry_factors = country_factors.get(
            industry, {}
        )
        factor = industry_factors.get(
            str(month), self.DEFAULT_FACTOR
        )

        return float(factor)

    def get_ramadan_adjustment(
        self,
        country_code: str,
        is_ramadan_period: bool,
        is_eid_week: bool
    ) -> float:
        """
        We retrieve the Ramadan adjustment factor for
        countries with significant Muslim populations.
        """

        affected = self.religious.get(
            "ramadan_affected_countries", []
        )

        if country_code not in affected:
            return self.DEFAULT_FACTOR

        adjustments = self.religious.get(
            "ramadan_adjustment", {}
        )

        if is_eid_week:
            return adjustments.get(
                "consumer_spending_eid_week",
                self.DEFAULT_FACTOR
            )
        elif is_ramadan_period:
            return adjustments.get(
                "consumer_spending_during",
                self.DEFAULT_FACTOR
            )

        return self.DEFAULT_FACTOR

    def get_christmas_corridor_adjustment(
        self,
        corridor: str,
        month: int
    ) -> float:
        """
        We retrieve the Christmas remittance corridor
        adjustment for Southern African labor corridors.
        """

        christmas = self.religious.get(
            "christmas_remittance", {}
        )
        affected_corridors = christmas.get(
            "affected_corridors", []
        )

        if corridor not in affected_corridors:
            return self.DEFAULT_FACTOR

        if month == 12:
            return christmas.get(
                "corridor_volume_multiplier_december",
                self.DEFAULT_FACTOR
            )
        elif month == 11:
            return christmas.get(
                "corridor_volume_multiplier_november",
                self.DEFAULT_FACTOR
            )

        return self.DEFAULT_FACTOR

    def list_available_calendars(self) -> Dict:
        """
        We list all available country and industry
        combinations in the calendar.
        """

        available = {}
        for country, industries in self.factors.items():
            available[country] = list(industries.keys())
        return available
