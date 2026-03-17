"""
Seasonal Adjustment - Season Adjuster

We apply agricultural and economic seasonal adjustments to
raw signal metrics before they reach the anomaly detection
and NBA scoring layers. Without adjustment, every harvest-
season cash flow spike would fire as a false anomaly.

Adjustment methodology:
  1. Look up country × sector × month multiplier from
     AgriculturalCalendar.
  2. Divide observed value by multiplier to get
     seasonally-adjusted value.
  3. Compute a deviation score: how far is the adjusted
     value from the 90-day rolling average?
  4. Return both raw and adjusted values plus context.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import statistics

from afriflow.logging_config import get_logger, log_operation
from .agricultural_calendar import AgriculturalCalendar, SeasonPhase

logger = get_logger("integration.seasonal_adjustment.season_adjuster")


@dataclass
class AdjustmentResult:
    """
    Result of seasonal adjustment for a single metric.

    Attributes:
        entity_id: Client or entity identifier
        country: ISO-2 country code
        sector: Economic sector
        metric_name: Name of the metric being adjusted
        raw_value: Observed raw value
        seasonal_multiplier: Expected multiplier for this month
        adjusted_value: raw_value / seasonal_multiplier
        deviation_score: Z-score vs rolling average (post-adjustment)
        is_anomalous: True if deviation exceeds threshold
        season_phase: Current phase (harvest, planting, etc.)
        adjustment_month: Month used for calendar lookup
        notes: Explanation of the adjustment
    """
    entity_id: str
    country: str
    sector: str
    metric_name: str
    raw_value: float
    seasonal_multiplier: float
    adjusted_value: float
    deviation_score: float
    is_anomalous: bool
    season_phase: SeasonPhase
    adjustment_month: int
    notes: str = ""


@dataclass
class AdjustmentContext:
    """
    Context for performing seasonal adjustments.

    Attributes:
        entity_id: Entity to adjust
        country: ISO-2 country code
        sector: Economic sector
        observation_date: Date of the observation
        historical_values: List of prior monthly adjusted values (for rolling avg)
    """
    entity_id: str
    country: str
    sector: str
    observation_date: datetime
    historical_values: List[float] = field(default_factory=list)


class SeasonAdjuster:
    """
    We apply seasonal adjustments to entity-level metrics.

    By normalising out expected seasonal patterns, we allow
    downstream signal detectors to focus on genuine structural
    changes rather than calendar noise.

    Attributes:
        calendar: AgriculturalCalendar instance
        anomaly_z_threshold: Z-score above which we flag anomalies
    """

    ANOMALY_Z_THRESHOLD = 2.5
    MIN_HISTORY_MONTHS = 3

    def __init__(
        self,
        calendar: Optional[AgriculturalCalendar] = None,
        anomaly_z_threshold: float = 2.5,
    ) -> None:
        """
        Initialize the season adjuster.

        Args:
            calendar: Optional pre-built calendar (creates new if None)
            anomaly_z_threshold: Z-score threshold for anomaly flagging
        """
        self.calendar = calendar or AgriculturalCalendar()
        self.anomaly_z_threshold = anomaly_z_threshold
        logger.info(
            f"SeasonAdjuster initialized, z_threshold={anomaly_z_threshold}"
        )

    def adjust(
        self,
        context: AdjustmentContext,
        raw_value: float,
        metric_name: str = "value",
    ) -> AdjustmentResult:
        """
        Adjust a single metric value for seasonality.

        Args:
            context: Adjustment context (entity, country, sector, date)
            raw_value: Observed raw value
            metric_name: Name of the metric

        Returns:
            AdjustmentResult with raw, adjusted, and deviation values
        """
        month = context.observation_date.month

        multiplier = self.calendar.get_multiplier(
            context.country, context.sector, month
        )
        phase = self.calendar.get_phase(
            context.country, context.sector, month
        )

        adjusted = raw_value / multiplier if multiplier > 0 else raw_value

        deviation_score, is_anomalous = self._compute_deviation(
            adjusted, context.historical_values
        )

        has_pattern = self.calendar.get_pattern(context.country, context.sector) is not None
        if has_pattern:
            notes = (
                f"Season phase: {phase.value}. "
                f"Multiplier: {multiplier:.2f}x. "
                f"Adjusted {raw_value:.1f} → {adjusted:.1f}."
            )
        else:
            notes = (
                f"No seasonal pattern for "
                f"{context.country}/{context.sector}; no adjustment applied."
            )

        return AdjustmentResult(
            entity_id=context.entity_id,
            country=context.country,
            sector=context.sector,
            metric_name=metric_name,
            raw_value=raw_value,
            seasonal_multiplier=multiplier,
            adjusted_value=adjusted,
            deviation_score=deviation_score,
            is_anomalous=is_anomalous,
            season_phase=phase,
            adjustment_month=month,
            notes=notes,
        )

    def adjust_batch(
        self,
        contexts_and_values: List[Tuple],
    ) -> List[AdjustmentResult]:
        """
        Adjust a batch of metrics.

        Args:
            contexts_and_values: List of (AdjustmentContext, raw_value, metric_name)

        Returns:
            List of AdjustmentResult objects
        """
        return [
            self.adjust(ctx, val, name)
            for ctx, val, name in contexts_and_values
        ]

    def _compute_deviation(
        self,
        adjusted_value: float,
        historical_values: List[float],
    ) -> Tuple[float, bool]:
        """Compute Z-score deviation from historical baseline."""
        if len(historical_values) < self.MIN_HISTORY_MONTHS:
            return 0.0, False

        try:
            mean = statistics.mean(historical_values)
            stdev = statistics.stdev(historical_values)
        except statistics.StatisticsError:
            return 0.0, False

        if stdev == 0:
            return 0.0, False

        z_score = (adjusted_value - mean) / stdev
        return round(z_score, 3), abs(z_score) > self.anomaly_z_threshold

    def compute_expected_range(
        self,
        country: str,
        sector: str,
        month: int,
        baseline: float,
        tolerance: float = 0.15,
    ) -> Tuple[float, float, float]:
        """
        Compute expected value range for a country × sector × month.

        Returns:
            Tuple of (lower_bound, expected, upper_bound)
        """
        multiplier = self.calendar.get_multiplier(country, sector, month)
        expected = baseline * multiplier
        return expected * (1 - tolerance), expected, expected * (1 + tolerance)

    def get_adjustment_summary(
        self,
        results: List[AdjustmentResult],
    ) -> Dict[str, Any]:
        """Summarise a batch of adjustment results."""
        if not results:
            return {"total": 0}

        anomalous = [r for r in results if r.is_anomalous]
        z_scores = [abs(r.deviation_score) for r in results]

        return {
            "total": len(results),
            "anomalous": len(anomalous),
            "anomaly_rate": round(len(anomalous) / len(results), 3),
            "adjustments_applied": sum(
                1 for r in results if abs(r.seasonal_multiplier - 1.0) > 0.05
            ),
            "mean_z_score": round(sum(z_scores) / len(z_scores), 3),
            "max_z_score": round(max(z_scores), 3),
            "anomalous_entities": [r.entity_id for r in anomalous],
        }


if __name__ == "__main__":
    adjuster = SeasonAdjuster()

    # Ghana cocoa November — harvest season, 40% spike is normal
    ctx = AdjustmentContext(
        entity_id="FARM-GH-001",
        country="GH",
        sector="cocoa",
        observation_date=datetime(2024, 11, 15),
        historical_values=[85.0, 90.0, 88.0, 82.0, 91.0],
    )
    result = adjuster.adjust(ctx, raw_value=140.0, metric_name="momo_volume")
    print(f"Raw: {result.raw_value:.1f} | Adjusted: {result.adjusted_value:.1f}")
    print(f"Z-score: {result.deviation_score:.2f} | Anomalous: {result.is_anomalous}")
    print(f"Notes: {result.notes}")

    # Same spike in March (off-season) → anomalous
    ctx2 = AdjustmentContext(
        entity_id="FARM-GH-001", country="GH", sector="cocoa",
        observation_date=datetime(2024, 3, 15),
        historical_values=[85.0, 90.0, 88.0, 82.0, 91.0],
    )
    r2 = adjuster.adjust(ctx2, raw_value=140.0, metric_name="momo_volume")
    print(f"\nMarch: adjusted={r2.adjusted_value:.1f}, "
          f"z={r2.deviation_score:.2f}, anomalous={r2.is_anomalous}")

    lo, exp, hi = adjuster.compute_expected_range("ZA", "maize", 5, baseline=100.0)
    print(f"\nZA maize May range: {lo:.0f}–{hi:.0f} (centre {exp:.0f})")
