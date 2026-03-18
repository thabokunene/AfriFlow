"""
@file season_adjuster.py
@description Applies agricultural and economic seasonal adjustments to raw
    signal metrics before they reach the anomaly detection and NBA scoring
    layers. Divides observed values by the AgriculturalCalendar multiplier
    to normalise out expected seasonal variation, then computes a Z-score
    deviation against a rolling historical baseline to identify genuine
    structural changes.
@author Thabo Kunene
@created 2026-03-18
"""
# Adjustment methodology:
#   1. Look up country × sector × month multiplier from AgriculturalCalendar.
#   2. Divide observed value by multiplier → seasonally-adjusted value.
#   3. Compute Z-score deviation vs the supplied rolling historical values.
#   4. Return raw, adjusted, deviation score, and anomaly flag together.
#
# DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
# Group, MTN, or any affiliated entity. It is a demonstration of concept,
# domain knowledge, and data engineering skill by Thabo Kunene.

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import statistics

from afriflow.logging_config import get_logger, log_operation
from .agricultural_calendar import AgriculturalCalendar, SeasonPhase

# Module-level logger for adjustment operation tracing
logger = get_logger("integration.seasonal_adjustment.season_adjuster")


@dataclass
class AdjustmentResult:
    """Result of seasonal adjustment for a single metric observation.

    Stores both the raw value and the seasonally-adjusted value so that
    downstream consumers can compare them, plus the Z-score deviation
    and anomaly flag computed against the entity's rolling history.

    Attributes:
        entity_id: Client or entity identifier
        country: ISO-2 country code
        sector: Economic sector name
        metric_name: Name of the metric being adjusted (e.g. "momo_volume")
        raw_value: Observed raw value before any adjustment
        seasonal_multiplier: Calendar-derived multiplier for this month
        adjusted_value: raw_value / seasonal_multiplier (normalised)
        deviation_score: Z-score of adjusted_value vs historical rolling average
        is_anomalous: True when |deviation_score| > ANOMALY_Z_THRESHOLD
        season_phase: Agronomic phase for this month (HARVEST, PLANTING, etc.)
        adjustment_month: Month number (1–12) used for the calendar lookup
        notes: Human-readable explanation of the adjustment performed
    """
    entity_id: str
    country: str
    sector: str
    metric_name: str
    raw_value: float
    seasonal_multiplier: float      # 1.0 = no seasonal effect for this month
    adjusted_value: float           # Normalised: raw_value / multiplier
    deviation_score: float          # Z-score vs rolling historical baseline
    is_anomalous: bool              # True if Z-score exceeds the configured threshold
    season_phase: SeasonPhase       # Agronomic label for context
    adjustment_month: int           # Month number used for multiplier lookup
    notes: str = ""                 # Explanation string for audit/logging


@dataclass
class AdjustmentContext:
    """Context bundle for performing a seasonal adjustment.

    Separates the immutable context (who, where, when) from the metric
    value so that batch processing can reuse context objects.

    Attributes:
        entity_id: Entity whose metric is being adjusted
        country: ISO-2 country code of the observation
        sector: Economic sector for calendar lookup
        observation_date: Datetime of the observed metric value
        historical_values: Prior seasonally-adjusted monthly values (for Z-score)
    """
    entity_id: str
    country: str
    sector: str
    observation_date: datetime
    # At least MIN_HISTORY_MONTHS values required to compute a meaningful Z-score
    historical_values: List[float] = field(default_factory=list)


class SeasonAdjuster:
    """We apply seasonal adjustments to entity-level metrics.

    By normalising out expected seasonal patterns, we allow downstream
    signal detectors to focus on genuine structural changes in client
    behaviour rather than calendar noise.

    Attributes:
        calendar: AgriculturalCalendar instance for multiplier and phase lookups
        anomaly_z_threshold: Z-score above which a deviation is flagged anomalous
    """

    ANOMALY_Z_THRESHOLD = 2.5   # ~99th percentile of a standard normal distribution
    MIN_HISTORY_MONTHS = 3      # Minimum history required to compute a Z-score

    def __init__(
        self,
        calendar: Optional[AgriculturalCalendar] = None,
        anomaly_z_threshold: float = 2.5,
    ) -> None:
        """Initialise the SeasonAdjuster.

        Args:
            calendar: Optional pre-built AgriculturalCalendar. A new instance
                      is created if not supplied.
            anomaly_z_threshold: Z-score threshold for flagging anomalies.
                                 Default 2.5 gives ~99% sensitivity.
        """
        # Use the provided calendar or instantiate a fresh one
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
        """Adjust a single metric value for seasonality and compute deviation.

        Steps:
          1. Extract month from context.observation_date.
          2. Look up seasonal multiplier and phase from the calendar.
          3. Divide raw_value by multiplier → adjusted_value.
          4. Compute Z-score of adjusted_value vs context.historical_values.
          5. Build and return AdjustmentResult.

        Args:
            context: Adjustment context with entity, country, sector, date, history.
            raw_value: Observed raw metric value.
            metric_name: Descriptive name for the metric (for notes and logging).

        Returns:
            AdjustmentResult containing raw, adjusted, Z-score, and anomaly flag.
        """
        # Step 1: Extract the observation month for the calendar lookup
        month = context.observation_date.month

        # Step 2: Fetch the seasonal multiplier and agronomic phase
        multiplier = self.calendar.get_multiplier(
            context.country, context.sector, month
        )
        phase = self.calendar.get_phase(
            context.country, context.sector, month
        )

        # Step 3: Normalise the raw value by dividing out the seasonal multiplier.
        # Guard against division-by-zero (multiplier should always be > 0 but be safe).
        adjusted = raw_value / multiplier if multiplier > 0 else raw_value

        # Step 4: Z-score computation against the rolling history
        deviation_score, is_anomalous = self._compute_deviation(
            adjusted, context.historical_values
        )

        # Build a human-readable explanation for the audit log
        has_pattern = self.calendar.get_pattern(context.country, context.sector) is not None
        if has_pattern:
            # A known pattern was applied — document the adjustment
            notes = (
                f"Season phase: {phase.value}. "
                f"Multiplier: {multiplier:.2f}x. "
                f"Adjusted {raw_value:.1f} → {adjusted:.1f}."
            )
        else:
            # No pattern registered for this country/sector — pass-through
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
        """Adjust a batch of metrics in sequence.

        Args:
            contexts_and_values: List of (AdjustmentContext, raw_value, metric_name)
                                 tuples. metric_name is a descriptive string.

        Returns:
            List of AdjustmentResult objects in the same order as input.
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
        """Compute the Z-score of an adjusted value against a historical baseline.

        Requires at least MIN_HISTORY_MONTHS data points; returns (0.0, False)
        when history is insufficient to avoid false positives on sparse data.

        Args:
            adjusted_value: The seasonally-normalised current observation.
            historical_values: Prior seasonally-adjusted monthly values.

        Returns:
            Tuple of (z_score, is_anomalous). is_anomalous is True when
            |z_score| > self.anomaly_z_threshold.
        """
        # Require a minimum history before making anomaly determinations
        if len(historical_values) < self.MIN_HISTORY_MONTHS:
            return 0.0, False  # Not enough history — withhold judgement

        try:
            mean = statistics.mean(historical_values)
            stdev = statistics.stdev(historical_values)   # Sample std deviation
        except statistics.StatisticsError:
            return 0.0, False  # Edge case: identical values or single element

        if stdev == 0:
            return 0.0, False  # Perfectly stable baseline — no deviation possible

        # Standard Z-score formula: (observation - mean) / std deviation
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
        """Compute the expected value range for a country × sector × month.

        Uses the calendar multiplier to scale the baseline, then applies a
        ±tolerance band. Useful for generating RM briefing context and
        anomaly threshold annotations.

        Args:
            country: ISO-2 country code.
            sector: Sector name.
            month: Month number (1–12).
            baseline: The entity's own annual average for this metric.
            tolerance: Fractional tolerance band (default 15%).

        Returns:
            Tuple of (lower_bound, expected_centre, upper_bound).
        """
        multiplier = self.calendar.get_multiplier(country, sector, month)
        expected = baseline * multiplier           # Season-adjusted expected value
        # Apply symmetric tolerance band around the expected centre
        return expected * (1 - tolerance), expected, expected * (1 + tolerance)

    def get_adjustment_summary(
        self,
        results: List[AdjustmentResult],
    ) -> Dict[str, Any]:
        """Summarise a batch of adjustment results for monitoring and reporting.

        Args:
            results: List of AdjustmentResult objects from adjust_batch().

        Returns:
            Dict with counts, rates, and lists of anomalous entity IDs.
        """
        if not results:
            return {"total": 0}

        # Separate anomalous from normal results
        anomalous = [r for r in results if r.is_anomalous]
        # Use absolute Z-scores for the mean and max statistics
        z_scores = [abs(r.deviation_score) for r in results]

        return {
            "total": len(results),
            "anomalous": len(anomalous),
            # Fraction of adjusted metrics that exceeded the Z-score threshold
            "anomaly_rate": round(len(anomalous) / len(results), 3),
            # Count of metrics where a non-trivial seasonal adjustment was applied
            "adjustments_applied": sum(
                1 for r in results if abs(r.seasonal_multiplier - 1.0) > 0.05
            ),
            "mean_z_score": round(sum(z_scores) / len(z_scores), 3),
            "max_z_score": round(max(z_scores), 3),
            # Entity IDs for follow-up investigation
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
