"""
Seasonal Adjustment package for AfriFlow.

We provide agricultural calendar-aware signal adjustment
so that harvest-season cash flow spikes are not mistaken
for anomalies, and seasonal troughs are not mistaken for
churn or data quality failures.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .agricultural_calendar import (
    AgriculturalCalendar,
    SeasonalPattern,
    SeasonPhase,
    CashFlowDirection,
)
from .season_adjuster import (
    SeasonAdjuster,
    AdjustmentResult,
    AdjustmentContext,
)
from .false_alarm_filter import (
    FalseAlarmFilter,
    FilterDecision,
    SuppressionReason,
)

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
