"""
@file agricultural_calendar.py
@description Encodes country × sector × month agricultural seasonal patterns
    for AfriFlow's seasonal adjustment layer. Provides revenue multipliers,
    season phase labels, and cash flow direction enums per month so that
    downstream detectors can distinguish genuine anomalies from expected
    harvest-season variation. Covers ZA, NG, KE, GH, ZM, TZ, CI, and MZ.
@author Thabo Kunene
@created 2026-03-18
"""
# Context:
# Africa's agricultural seasons are the single biggest driver of informal
# economy cash flow patterns. A MoMo velocity spike in October in Ghana is
# not anomalous — it is cocoa harvest. A payment drop in March in Zambia
# is not churn — it is post-maize planting season credit stress.
#
# Key calendars covered:
#   ZA  – maize (Apr–Jun harvest), wine (Feb–Apr), gold (year-round)
#   NG  – cocoa (Oct–Feb main crop)
#   KE  – tea (two flush seasons), coffee (Oct–Dec harvest)
#   GH  – cocoa (Oct–Jan main crop, May–Jun light crop)
#   ZM  – copper (continuous, price-driven), maize (Apr–Jul harvest)
#   TZ  – coffee (Jul–Oct harvest)
#   CI  – cocoa (Oct–Mar main crop, Apr–Jul mid-crop)
#   ZA  – wine & citrus (Feb–Apr wine, Jul–Sep citrus)
#
# DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
# Group, MTN, or any affiliated entity. It is a demonstration of concept,
# domain knowledge, and data engineering skill by Thabo Kunene.

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple
from enum import Enum

from afriflow.logging_config import get_logger

# Module-level logger for tracing calendar load and lookup activity
logger = get_logger("integration.seasonal_adjustment.agricultural_calendar")


class SeasonPhase(Enum):
    """Phase of an agricultural season.

    Used to label each calendar month with its agronomic meaning
    so that signal detectors can contextualise anomalies correctly.
    """
    PLANTING = "planting"           # Seed/seedling establishment — low activity
    GROWING = "growing"             # Crop development — moderate low activity
    HARVEST = "harvest"             # Crop collection — high cash flow
    POST_HARVEST = "post_harvest"   # Storage, grading, first sales — moderate high
    OFF_SEASON = "off_season"       # Between crop cycles — lowest activity


class CashFlowDirection(Enum):
    """Expected cash flow direction relative to the annual baseline.

    Thresholds are applied in _build_cashflow_from_multiplier:
      >= 1.30 → STRONGLY_POSITIVE
      >= 1.10 → POSITIVE
      >= 0.90 → NEUTRAL
      >= 0.70 → NEGATIVE
       < 0.70 → STRONGLY_NEGATIVE
    """
    STRONGLY_POSITIVE = "strongly_positive"    # >30% above annual baseline
    POSITIVE = "positive"                       # 10–30% above baseline
    NEUTRAL = "neutral"                         # Within ±10% of baseline
    NEGATIVE = "negative"                       # 10–30% below baseline
    STRONGLY_NEGATIVE = "strongly_negative"     # >30% below baseline


@dataclass
class SeasonalPattern:
    """Monthly seasonal pattern for a country × sector combination.

    Stores per-month revenue multipliers, season phases, and cash flow
    direction labels. Peak and trough month lists support quick range
    checks without iterating the full multiplier dict.

    Attributes:
        country: ISO-2 country code (e.g. "GH", "ZA")
        sector: Commodity/sector name (e.g. "cocoa", "maize", "copper")
        month_multipliers: Dict of month (1–12) → revenue multiplier vs annual avg
        phase_by_month: Dict of month → SeasonPhase enum value
        cashflow_by_month: Dict of month → CashFlowDirection (derived from multiplier)
        peak_months: Months where multiplier is highest (typically harvest)
        trough_months: Months where multiplier is lowest (typically off-season)
        notes: Human-readable explanation of the seasonal pattern
    """
    country: str
    sector: str
    month_multipliers: Dict[int, float]         # 1.0 = annual average revenue
    phase_by_month: Dict[int, SeasonPhase]
    cashflow_by_month: Dict[int, CashFlowDirection]
    peak_months: List[int]
    trough_months: List[int]
    notes: str = ""

    def get_multiplier(self, month: int) -> float:
        """Get the revenue multiplier for a given month (1–12).

        Returns 1.0 (no adjustment) if the month is not in the pattern,
        so callers always receive a safe default.
        """
        return self.month_multipliers.get(month, 1.0)

    def get_phase(self, month: int) -> SeasonPhase:
        """Get the agricultural season phase for a given month.

        Defaults to OFF_SEASON when the month is not mapped, which is
        the safest assumption for unrecognised periods.
        """
        return self.phase_by_month.get(month, SeasonPhase.OFF_SEASON)

    def get_cashflow_direction(self, month: int) -> CashFlowDirection:
        """Get the expected cash flow direction for a given month.

        Defaults to NEUTRAL when the month is not mapped.
        """
        return self.cashflow_by_month.get(month, CashFlowDirection.NEUTRAL)

    def is_peak_month(self, month: int) -> bool:
        """Return True if the month is one of the identified peak months."""
        return month in self.peak_months

    def is_trough_month(self, month: int) -> bool:
        """Return True if the month is one of the identified trough months."""
        return month in self.trough_months


def _build_cashflow_from_multiplier(multiplier: float) -> CashFlowDirection:
    """Derive a CashFlowDirection enum from a numeric multiplier.

    Applies fixed threshold bands to classify expected cash flow
    relative to the annual average for this country × sector.

    Args:
        multiplier: Revenue multiplier (1.0 = annual average).

    Returns:
        Corresponding CashFlowDirection enum value.
    """
    if multiplier >= 1.30:
        return CashFlowDirection.STRONGLY_POSITIVE  # Harvest surge
    elif multiplier >= 1.10:
        return CashFlowDirection.POSITIVE           # Moderate above average
    elif multiplier >= 0.90:
        return CashFlowDirection.NEUTRAL            # Within normal range
    elif multiplier >= 0.70:
        return CashFlowDirection.NEGATIVE           # Moderate below average
    else:
        return CashFlowDirection.STRONGLY_NEGATIVE  # Deep off-season trough


# ── Seasonal pattern definitions ─────────────────────────────────────────────
# Multipliers derived from domain knowledge of African agricultural cycles.
# A multiplier of 1.35 means cash flows in that month are expected to be
# 35% above the annual average for this country × sector.
# These inform SeasonalPattern.month_multipliers; cashflow_by_month is derived
# automatically in _build_pattern() using _build_cashflow_from_multiplier().

_PATTERNS_RAW: List[Dict] = [
    # ── Ghana Cocoa ─────────────────────────────────────────────────────────
    # Main crop: Oct–Feb (peak Nov–Jan); light/mid-crop: May–Jul
    # Farmer income reaches KTDA-equivalent peak at licensed buying company payments.
    {
        "country": "GH",
        "sector": "cocoa",
        "month_multipliers": {
            # Jan still in main crop tail; Feb post-harvest winding down
            1: 1.40, 2: 1.10,
            # Mar–Apr: off-season / early planting
            3: 0.80, 4: 0.70,
            # May–Jun: light crop begins
            5: 0.75, 6: 0.90,
            # Jul: light crop post-harvest
            7: 1.00,
            # Aug–Sep: new season planting / growing
            8: 0.85, 9: 0.80,
            # Oct–Dec: main crop harvest surge
            10: 1.20, 11: 1.45, 12: 1.50,
        },
        "phase_by_month": {
            1: SeasonPhase.HARVEST, 2: SeasonPhase.POST_HARVEST,
            3: SeasonPhase.PLANTING, 4: SeasonPhase.PLANTING,
            5: SeasonPhase.GROWING, 6: SeasonPhase.HARVEST,    # light crop
            7: SeasonPhase.POST_HARVEST, 8: SeasonPhase.PLANTING,
            9: SeasonPhase.GROWING, 10: SeasonPhase.GROWING,
            11: SeasonPhase.HARVEST, 12: SeasonPhase.HARVEST,  # main crop
        },
        "peak_months": [11, 12, 1],    # Main crop peak
        "trough_months": [3, 4, 9],    # Deep off-season
        "notes": "Main crop harvested Oct–Feb; light crop May–Jul. "
                 "Farmer income spikes at weighing station payments.",
    },
    # ── Nigeria Cocoa ────────────────────────────────────────────────────────
    {
        "country": "NG",
        "sector": "cocoa",
        "month_multipliers": {
            1: 1.30, 2: 1.15, 3: 0.85, 4: 0.75, 5: 0.70, 6: 0.80,
            7: 0.90, 8: 0.85, 9: 0.90, 10: 1.10, 11: 1.50, 12: 1.45,
        },
        "phase_by_month": {
            1: SeasonPhase.HARVEST, 2: SeasonPhase.POST_HARVEST,
            3: SeasonPhase.OFF_SEASON, 4: SeasonPhase.PLANTING,
            5: SeasonPhase.GROWING, 6: SeasonPhase.GROWING,
            7: SeasonPhase.GROWING, 8: SeasonPhase.GROWING,
            9: SeasonPhase.GROWING, 10: SeasonPhase.HARVEST,
            11: SeasonPhase.HARVEST, 12: SeasonPhase.HARVEST,
        },
        "peak_months": [10, 11, 12],
        "trough_months": [4, 5, 6],
        "notes": "SW Nigeria cocoa belt. Main season Oct–Feb. "
                 "Groundnut peak Aug–Oct in north.",
    },
    # ── South Africa Maize ───────────────────────────────────────────────────
    {
        "country": "ZA",
        "sector": "maize",
        "month_multipliers": {
            1: 0.70, 2: 0.75, 3: 0.80, 4: 1.20, 5: 1.45, 6: 1.40,
            7: 1.15, 8: 0.90, 9: 0.80, 10: 0.75, 11: 0.70, 12: 0.70,
        },
        "phase_by_month": {
            1: SeasonPhase.GROWING, 2: SeasonPhase.GROWING,
            3: SeasonPhase.GROWING, 4: SeasonPhase.HARVEST,
            5: SeasonPhase.HARVEST, 6: SeasonPhase.POST_HARVEST,
            7: SeasonPhase.POST_HARVEST, 8: SeasonPhase.OFF_SEASON,
            9: SeasonPhase.OFF_SEASON, 10: SeasonPhase.PLANTING,
            11: SeasonPhase.PLANTING, 12: SeasonPhase.GROWING,
        },
        "peak_months": [4, 5, 6],
        "trough_months": [11, 12, 1],
        "notes": "Highveld summer grain. Planting Nov–Dec, harvest Apr–Jun. "
                 "Farmer income concentrated in Apr–Jul silo payments.",
    },
    # ── Kenya Tea ────────────────────────────────────────────────────────────
    {
        "country": "KE",
        "sector": "tea",
        "month_multipliers": {
            1: 0.90, 2: 0.85, 3: 0.95, 4: 1.30, 5: 1.40, 6: 1.35,
            7: 1.10, 8: 0.95, 9: 0.85, 10: 1.20, 11: 1.30, 12: 1.10,
        },
        "phase_by_month": {
            1: SeasonPhase.GROWING, 2: SeasonPhase.GROWING,
            3: SeasonPhase.GROWING, 4: SeasonPhase.HARVEST,
            5: SeasonPhase.HARVEST, 6: SeasonPhase.HARVEST,
            7: SeasonPhase.POST_HARVEST, 8: SeasonPhase.GROWING,
            9: SeasonPhase.GROWING, 10: SeasonPhase.HARVEST,
            11: SeasonPhase.HARVEST, 12: SeasonPhase.POST_HARVEST,
        },
        "peak_months": [4, 5, 6, 10, 11],
        "trough_months": [1, 2, 9],
        "notes": "Two flush seasons driven by long rains (Mar–May) and "
                 "short rains (Oct–Dec). KTDA payments are primary income "
                 "for 600k smallholders.",
    },
    # ── Zambia Copper ────────────────────────────────────────────────────────
    {
        "country": "ZM",
        "sector": "copper",
        "month_multipliers": {
            1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.00, 6: 1.00,
            7: 1.00, 8: 1.00, 9: 1.00, 10: 1.00, 11: 1.00, 12: 0.90,
        },
        "phase_by_month": {m: SeasonPhase.GROWING for m in range(1, 13)},
        "peak_months": [3, 4, 5, 6],
        "trough_months": [12],
        "notes": "Copper mining is continuous; seasonality driven by LME "
                 "price cycles and mine maintenance shutdowns (Dec). "
                 "ZMW/USD tracks copper price not season.",
    },
    # ── Côte d'Ivoire Cocoa ──────────────────────────────────────────────────
    {
        "country": "CI",
        "sector": "cocoa",
        "month_multipliers": {
            1: 1.25, 2: 1.30, 3: 0.90, 4: 0.80, 5: 0.90, 6: 1.10,
            7: 1.00, 8: 0.85, 9: 0.80, 10: 1.10, 11: 1.40, 12: 1.45,
        },
        "phase_by_month": {
            1: SeasonPhase.HARVEST, 2: SeasonPhase.HARVEST,
            3: SeasonPhase.POST_HARVEST, 4: SeasonPhase.PLANTING,
            5: SeasonPhase.GROWING, 6: SeasonPhase.HARVEST,
            7: SeasonPhase.POST_HARVEST, 8: SeasonPhase.GROWING,
            9: SeasonPhase.GROWING, 10: SeasonPhase.GROWING,
            11: SeasonPhase.HARVEST, 12: SeasonPhase.HARVEST,
        },
        "peak_months": [11, 12, 1, 2],
        "trough_months": [3, 4, 9],
        "notes": "World's largest cocoa producer. Main crop Oct–Mar, "
                 "mid-crop Apr–Jul. Farmgate payments drive rural MoMo.",
    },
    # ── South Africa Wine / Citrus ───────────────────────────────────────────
    {
        "country": "ZA",
        "sector": "wine_and_fruit",
        "month_multipliers": {
            1: 0.85, 2: 1.10, 3: 1.45, 4: 1.40, 5: 1.20, 6: 0.90,
            7: 1.10, 8: 1.15, 9: 1.05, 10: 0.85, 11: 0.80, 12: 0.80,
        },
        "phase_by_month": {
            1: SeasonPhase.GROWING, 2: SeasonPhase.HARVEST,
            3: SeasonPhase.HARVEST, 4: SeasonPhase.HARVEST,
            5: SeasonPhase.POST_HARVEST, 6: SeasonPhase.OFF_SEASON,
            7: SeasonPhase.HARVEST, 8: SeasonPhase.HARVEST,    # citrus
            9: SeasonPhase.POST_HARVEST, 10: SeasonPhase.PLANTING,
            11: SeasonPhase.GROWING, 12: SeasonPhase.GROWING,
        },
        "peak_months": [2, 3, 4, 7, 8],
        "trough_months": [10, 11, 12],
        "notes": "Western Cape wine harvest Feb–Apr; citrus Jul–Sep. "
                 "Seasonal workers drive spikes in rural PBB and MoMo.",
    },
    # ── Tanzania Coffee ──────────────────────────────────────────────────────
    {
        "country": "TZ",
        "sector": "coffee",
        "month_multipliers": {
            1: 1.20, 2: 0.95, 3: 0.80, 4: 0.75, 5: 0.75, 6: 0.80,
            7: 0.90, 8: 1.05, 9: 1.20, 10: 1.35, 11: 1.30, 12: 1.25,
        },
        "phase_by_month": {
            1: SeasonPhase.POST_HARVEST, 2: SeasonPhase.OFF_SEASON,
            3: SeasonPhase.PLANTING, 4: SeasonPhase.GROWING,
            5: SeasonPhase.GROWING, 6: SeasonPhase.GROWING,
            7: SeasonPhase.GROWING, 8: SeasonPhase.GROWING,
            9: SeasonPhase.HARVEST, 10: SeasonPhase.HARVEST,
            11: SeasonPhase.HARVEST, 12: SeasonPhase.HARVEST,
        },
        "peak_months": [9, 10, 11, 12],
        "trough_months": [3, 4, 5, 6],
        "notes": "Arabica from Kilimanjaro slopes. Main harvest Jul–Jan. "
                 "Tanzania tourism peak Jun–Oct overlaps harvest.",
    },
]


def _build_pattern(raw: Dict) -> SeasonalPattern:
    """Build a SeasonalPattern dataclass from a raw dict definition.

    Derives cashflow_by_month automatically from the multipliers so that
    the raw pattern definitions don't need to duplicate that information.

    Args:
        raw: Dict with keys: country, sector, month_multipliers,
             phase_by_month, peak_months, trough_months, notes.

    Returns:
        Fully constructed SeasonalPattern instance.
    """
    multipliers = raw["month_multipliers"]
    # Derive CashFlowDirection for each month directly from the multiplier value
    cashflow = {m: _build_cashflow_from_multiplier(v) for m, v in multipliers.items()}
    return SeasonalPattern(
        country=raw["country"],
        sector=raw["sector"],
        month_multipliers=multipliers,
        phase_by_month=raw["phase_by_month"],
        cashflow_by_month=cashflow,
        peak_months=raw["peak_months"],
        trough_months=raw["trough_months"],
        notes=raw.get("notes", ""),
    )


class AgriculturalCalendar:
    """We encode country × sector agricultural seasonal patterns.

    These patterns are used to adjust signal thresholds so that
    harvest-season cash flow spikes are not misclassified as
    anomalies, and post-harvest troughs are not misclassified
    as churn or data quality failures.

    On construction, all built-in patterns from _PATTERNS_RAW are
    loaded into a dict keyed by "COUNTRY:sector" for O(1) lookup.

    Attributes:
        patterns: Loaded patterns keyed by "COUNTRY:sector" e.g. "GH:cocoa"
    """

    def __init__(self) -> None:
        """Load all built-in agricultural patterns into the registry."""
        self.patterns: Dict[str, SeasonalPattern] = {}
        for raw in _PATTERNS_RAW:
            pattern = _build_pattern(raw)
            # Key format: UPPERCASE_COUNTRY:lowercase_sector
            key = f"{pattern.country}:{pattern.sector}"
            self.patterns[key] = pattern

        logger.info(
            f"AgriculturalCalendar loaded {len(self.patterns)} patterns "
            f"across {len(self._countries())} countries"
        )

    def _countries(self) -> List[str]:
        """Return the distinct set of country codes represented in the registry."""
        return list({p.country for p in self.patterns.values()})

    def get_pattern(
        self,
        country: str,
        sector: str
    ) -> Optional[SeasonalPattern]:
        """Get seasonal pattern for a country × sector combination.

        Case-normalises the lookup key (country → upper, sector → lower).

        Args:
            country: ISO-2 country code (e.g. "GH", "ZA")
            sector: Sector name (e.g. "cocoa", "maize", "tea")

        Returns:
            SeasonalPattern if registered, else None.
        """
        key = f"{country.upper()}:{sector.lower()}"
        pattern = self.patterns.get(key)
        if pattern is None:
            # Log at DEBUG level — missing patterns are expected for unknown combinations
            logger.debug(f"No pattern for {key}")
        return pattern

    def get_multiplier(
        self,
        country: str,
        sector: str,
        month: int
    ) -> float:
        """Get the revenue multiplier for a country × sector × month combination.

        Returns 1.0 (no adjustment) when no pattern is registered, so the caller
        always receives a safe default and the signal is passed through unchanged.

        Args:
            country: ISO-2 country code
            sector: Sector name
            month: Month number (1–12)

        Returns:
            Revenue multiplier; 1.0 = annual average baseline.
        """
        pattern = self.get_pattern(country, sector)
        if pattern is None:
            return 1.0  # Safe default: no seasonal adjustment
        return pattern.get_multiplier(month)

    def get_phase(
        self,
        country: str,
        sector: str,
        month: int
    ) -> SeasonPhase:
        """Get the agricultural season phase for a country × sector × month.

        Returns OFF_SEASON when no pattern is registered, which is the safest
        default for downstream consumers.
        """
        pattern = self.get_pattern(country, sector)
        if pattern is None:
            return SeasonPhase.OFF_SEASON
        return pattern.get_phase(month)

    def is_expected_spike(
        self,
        country: str,
        sector: str,
        month: int,
        observed_uplift: float
    ) -> bool:
        """Check whether an observed cash flow uplift is explainable by seasonality.

        Compares the observed uplift multiplier to the expected seasonal multiplier.
        If the difference is within ±20%, the signal is classified as seasonal.

        Args:
            country: ISO-2 country code
            sector: Sector name
            month: Month number (1–12)
            observed_uplift: Observed revenue multiplier vs the client's own baseline

        Returns:
            True if the uplift is within ±20% of the expected seasonal multiplier.
        """
        expected = self.get_multiplier(country, sector, month)
        # ±0.20 tolerance window — signals inside this band are seasonal noise
        return abs(observed_uplift - expected) <= 0.20

    def get_sectors(self, country: str) -> List[str]:
        """Get all sector names for which a pattern exists for a given country.

        Filters the pattern registry by country prefix and extracts sector names.
        """
        prefix = f"{country.upper()}:"
        return [
            key.split(":")[1]
            for key in self.patterns
            if key.startswith(prefix)
        ]

    def get_peak_months(self, country: str, sector: str) -> List[int]:
        """Get the list of peak revenue months for a country × sector.

        Returns an empty list when no pattern is registered.
        """
        pattern = self.get_pattern(country, sector)
        return pattern.peak_months if pattern else []

    def get_calendar_summary(
        self,
        country: str
    ) -> Dict[str, Dict[int, float]]:
        """Get a full month-by-month multiplier summary for all sectors in a country.

        Useful for RM briefing generation and BI dashboards.

        Returns:
            Dict of sector → {month: multiplier} for months 1–12.
        """
        sectors = self.get_sectors(country)
        return {
            sector: {
                m: self.get_multiplier(country, sector, m)
                for m in range(1, 13)  # Iterate all 12 calendar months
            }
            for sector in sectors
        }

    def get_country_peak_month(self, country: str) -> Tuple[str, int, float]:
        """Find the single highest-revenue month across all sectors for a country.

        Useful for identifying the most cash-flow-intensive month, e.g.
        Ghana November for cocoa harvest or South Africa May for maize.

        Returns:
            Tuple of (sector, month, multiplier) for the absolute peak.
        """
        best_sector, best_month, best_mult = "", 0, 0.0
        for sector in self.get_sectors(country):
            for month in range(1, 13):
                mult = self.get_multiplier(country, sector, month)
                if mult > best_mult:
                    best_mult = mult
                    best_month = month
                    best_sector = sector
        return best_sector, best_month, best_mult

    def get_statistics(self) -> Dict[str, int]:
        """Return summary statistics about the loaded calendar registry.

        Used for health checks and logging during service initialisation.
        """
        countries = self._countries()
        return {
            "total_patterns": len(self.patterns),
            "countries_covered": len(countries),
            # Sectors per country — useful for coverage gap analysis
            "sectors_per_country": {
                c: len(self.get_sectors(c)) for c in countries
            },
        }


if __name__ == "__main__":
    calendar = AgriculturalCalendar()

    print(f"Loaded {len(calendar.patterns)} patterns")
    print(f"Countries: {calendar._countries()}")

    # Ghana cocoa harvest check
    mult = calendar.get_multiplier("GH", "cocoa", 11)
    phase = calendar.get_phase("GH", "cocoa", 11)
    print(f"\nGH cocoa November: {mult:.2f}x baseline ({phase.value})")

    # Is a 1.4x spike in November expected?
    is_ok = calendar.is_expected_spike("GH", "cocoa", 11, 1.40)
    print(f"1.40x spike expected? {is_ok}")

    # South Africa calendar
    za_cal = calendar.get_calendar_summary("ZA")
    print(f"\nZA sectors: {list(za_cal.keys())}")
    best = calendar.get_country_peak_month("ZA")
    print(f"ZA peak: sector={best[0]}, month={best[1]}, mult={best[2]:.2f}")

    stats = calendar.get_statistics()
    print(f"\nCalendar stats: {stats}")
