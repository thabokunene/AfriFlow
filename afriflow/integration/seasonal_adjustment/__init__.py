"""
@file __init__.py
@description Public API for the seasonal_adjustment package. Re-exports the
    AgriculturalCalendar, SeasonAdjuster, and FalseAlarmFilter together with
    their supporting data-classes so callers can import from a single location.
    Harvest-season cash flow spikes are not anomalies — this package ensures
    downstream detectors know the difference.
@author Thabo Kunene
@created 2026-03-18
"""
# Package-level note:
# We provide agricultural calendar-aware signal adjustment so that
# harvest-season cash flow spikes are not mistaken for anomalies and
# seasonal troughs are not mistaken for churn or data quality failures.
#
# DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
# Group, MTN, or any affiliated entity. It is a demonstration of concept,
# domain knowledge, and data engineering skill by Thabo Kunene.

# Calendar domain: country × sector × month pattern definitions
from .agricultural_calendar import (
    AgriculturalCalendar,   # Main calendar registry
    SeasonalPattern,        # Per country/sector pattern dataclass
    SeasonPhase,            # Enum: PLANTING, GROWING, HARVEST, POST_HARVEST, OFF_SEASON
    CashFlowDirection,      # Enum: STRONGLY_POSITIVE … STRONGLY_NEGATIVE
)

# Adjustment engine: applies calendar multipliers to raw metric values
from .season_adjuster import (
    SeasonAdjuster,         # Core adjustment logic
    AdjustmentResult,       # Dataclass: raw + adjusted value + deviation score
    AdjustmentContext,      # Dataclass: entity/country/sector/date + history
)

# False alarm filter: suppresses signals explained by known calendar effects
from .false_alarm_filter import (
    FalseAlarmFilter,       # Evaluates signals against suppression rules
    FilterDecision,         # Dataclass: suppression verdict + confidence
    SuppressionReason,      # Enum: SEASONAL_CALENDAR, SALARY_CYCLE, etc.
)

# Public API surface — all names a consuming module can safely import
__all__ = [
    "AgriculturalCalendar",
    "SeasonalPattern",
    "SeasonPhase",
    "CashFlowDirection",
    "SeasonAdjuster",
    "AdjustmentResult",
    "AdjustmentContext",
    "FalseAlarmFilter",
    "FilterDecision",
    "SuppressionReason",
]
