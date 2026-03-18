"""
@file outcome_tracker.py
@description Tracks alert outcomes to close the model feedback loop. Records
             whether RM alerts and NBA recommendations led to revenue conversions,
             were rejected, expired, or flagged as false positives. Generates
             aggregate outcome reports and model calibration data that feeds back
             into NBA weight tuning, churn predictor threshold adjustment, and
             alert SLA optimisation.
@author Thabo Kunene
@created 2026-03-18
"""

# Outcome Tracker
#
# Tracks whether RM alerts and NBA recommendations actually
# led to revenue outcomes. This closes the feedback loop:
#
#   Alert generated → RM acknowledges → RM actions → Outcome recorded
#
# Outcome types:
#   CONVERTED     — Alert led to a sale/hedging deal/policy
#   REJECTED      — Client declined the recommendation
#   EXPIRED       — Alert expired before RM acted
#   FALSE_POSITIVE — Alert turned out to be incorrect
#   IN_PROGRESS   — RM is actively working the opportunity
#
# Metrics produced:
#   - Conversion rate per alert type
#   - Average revenue per converted alert
#   - False positive rate per domain combination
#   - RM performance ranking by conversion rate
#   - Model calibration data (NBA score → actual conversion)
#
# This data feeds back into:
#   1. NBA model weight calibration
#   2. Churn predictor threshold tuning
#   3. Alert SLA optimisation (are 48h SLAs right for churn?)
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

from __future__ import annotations  # Enables forward references in annotations

from dataclasses import dataclass, field  # Structured data containers with auto-generated __init__
from datetime import datetime             # Outcome timestamp; period boundary defaults
from typing import Dict, List, Optional, Tuple  # Type annotations for clarity


# ---------------------------------------------------------------------------
# Valid outcome values
# ---------------------------------------------------------------------------

# Allowed values for AlertOutcome.outcome.
# Using a frozenset-like set for fast membership testing in record().
_OUTCOME_VALUES = {"CONVERTED", "REJECTED", "EXPIRED",
                   "FALSE_POSITIVE", "IN_PROGRESS"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AlertOutcome:
    """Outcome record for a single alert.

    :param alert_id: ID of the original alert this outcome refers to
    :param alert_type: Alert type e.g. CHURN_RISK, EXPANSION_OPTY, CLV_UPLIFT
    :param client_golden_id: Unified client ID from entity resolution
    :param rm_id: ID of the RM who received and actioned (or did not action) the alert
    :param outcome: One of CONVERTED / REJECTED / EXPIRED / FALSE_POSITIVE / IN_PROGRESS
    :param actual_revenue_zar: Actual revenue generated (0 if not converted)
    :param predicted_revenue_zar: Revenue the NBA model predicted at alert time
    :param nba_score_at_alert: NBA propensity score when the alert was generated (0–100)
    :param days_to_outcome: Days between alert generation and outcome recording
    :param rm_notes: Free-text notes from the RM explaining the outcome
    :param recorded_at: ISO timestamp when this outcome record was written
    """

    alert_id: str
    alert_type: str
    client_golden_id: str
    rm_id: str
    outcome: str                           # Must be in _OUTCOME_VALUES
    actual_revenue_zar: float              # Actual deal revenue; 0 for non-conversions
    predicted_revenue_zar: float           # Model prediction for comparison
    nba_score_at_alert: Optional[float]    # NBA score at time of alert; None if not applicable
    days_to_outcome: Optional[int]         # Lead time from alert to outcome; None if IN_PROGRESS
    rm_notes: str                          # RM's qualitative explanation of the outcome
    recorded_at: str = field(
        default_factory=lambda: datetime.now().isoformat()  # Auto-stamped when outcome recorded
    )


@dataclass
class ModelCalibrationPoint:
    """A single data point for model calibration analysis.

    Maps a model's predicted score to the actual binary outcome, enabling
    calibration curve analysis (predicted probability vs actual frequency).

    :param model: Model name: 'nba', 'churn', 'clv', or 'anomaly'
    :param predicted_score: The model's score at alert time (0–100)
    :param actual_outcome: True if the alert was CONVERTED; False otherwise
    :param alert_type: The type of alert this calibration point comes from
    :param revenue_zar: Actual revenue generated (for weighted calibration)
    """

    model: str             # "nba", "churn", "clv", or "anomaly"
    predicted_score: float  # Score at time of alert (0–100 scale)
    actual_outcome: bool   # True = converted/churned, False = not
    alert_type: str
    revenue_zar: float     # Revenue for revenue-weighted calibration curves


@dataclass
class OutcomeReport:
    """Aggregate outcome metrics for a time period.

    :param period_start: ISO timestamp of the report period start
    :param period_end: ISO timestamp of the report period end
    :param total_alerts: Total number of outcome records in the period
    :param converted: Number of alerts with CONVERTED outcome
    :param rejected: Number of alerts with REJECTED outcome
    :param expired: Number of alerts with EXPIRED outcome (RM did not act in time)
    :param false_positives: Number of alerts flagged FALSE_POSITIVE
    :param conversion_rate: Fraction of total alerts that converted
    :param false_positive_rate: Fraction of total alerts that were false positives
    :param avg_revenue_converted_zar: Average ZAR revenue per converted alert
    :param total_revenue_zar: Total revenue across all converted alerts
    :param by_alert_type: Per-alert-type breakdown dict
    :param by_rm: Per-RM performance ranking dict, sorted by conversion rate desc
    :param calibration_points: List of ModelCalibrationPoint for each scored alert
    """

    period_start: str
    period_end: str
    total_alerts: int
    converted: int
    rejected: int
    expired: int
    false_positives: int

    conversion_rate: float          # Overall conversion rate (0.0–1.0)
    false_positive_rate: float      # Overall false positive rate (0.0–1.0)
    avg_revenue_converted_zar: float  # Average revenue per successful conversion
    total_revenue_zar: float        # Total revenue generated by converted alerts

    by_alert_type: Dict[str, Dict]   # {alert_type: {conversion_rate, count, revenue}}
    by_rm: Dict[str, Dict]           # {rm_id: {conversion_rate, count}} sorted by rate desc
    calibration_points: List[ModelCalibrationPoint]  # For calibration curve analysis


# ---------------------------------------------------------------------------
# Outcome tracker
# ---------------------------------------------------------------------------

class OutcomeTracker:
    """
    Track and analyse alert outcomes to calibrate models and rank RM performance.

    The OutcomeTracker is the feedback mechanism that makes AfriFlow a learning
    system. Without it, alert models cannot improve over time. Key responsibilities:
      - Validate outcome records before storage
      - Aggregate outcomes into conversion rates, revenue metrics, and RM rankings
      - Build model calibration data that reveals where models are over/underconfident

    Usage::

        tracker = OutcomeTracker()

        # Record an outcome
        tracker.record(AlertOutcome(
            alert_id="ALERT-CHURN-GLD-001",
            alert_type="CHURN_RISK",
            client_golden_id="GLD-001",
            rm_id="RM-00142",
            outcome="CONVERTED",
            actual_revenue_zar=450_000,
            predicted_revenue_zar=520_000,
            nba_score_at_alert=78.5,
            days_to_outcome=12,
            rm_notes="Client agreed to FX pricing review",
        ))

        # Generate report
        report = tracker.generate_report(outcomes)
    """

    def record(self, outcome: AlertOutcome) -> None:
        """
        Validate and store an outcome record.

        Raises ValueError if the outcome value is not in the allowed set.
        In production this method would persist to a data store; here it
        validates the record to confirm the caller used a valid outcome type.

        :param outcome: AlertOutcome to validate
        :raises ValueError: If outcome.outcome is not in _OUTCOME_VALUES
        """
        # Enforce allowed outcome values to maintain data integrity in the tracking store
        if outcome.outcome not in _OUTCOME_VALUES:
            raise ValueError(
                f"Invalid outcome '{outcome.outcome}'. "
                f"Must be one of: {_OUTCOME_VALUES}"
            )

    def generate_report(
        self,
        outcomes: List[AlertOutcome],
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
    ) -> OutcomeReport:
        """
        Generate aggregate outcome metrics from a list of outcome records.

        Computes conversion rate, false positive rate, average revenue, and
        per-type/per-RM breakdowns. Also builds model calibration points for
        all outcomes that had an NBA score at alert time.

        :param outcomes: List of AlertOutcome records for the period
        :param period_start: ISO timestamp for period start; defaults to first record
        :param period_end: ISO timestamp for period end; defaults to now
        :return: OutcomeReport with all metrics computed
        """
        # Default period boundaries: first outcome's timestamp to now
        period_start = period_start or (
            outcomes[0].recorded_at if outcomes else ""
        )
        period_end = period_end or datetime.now().isoformat()

        total = len(outcomes)

        # Partition outcomes by type for metric calculation
        converted = [o for o in outcomes if o.outcome == "CONVERTED"]
        rejected = [o for o in outcomes if o.outcome == "REJECTED"]
        expired = [o for o in outcomes if o.outcome == "EXPIRED"]
        fp = [o for o in outcomes if o.outcome == "FALSE_POSITIVE"]
        # IN_PROGRESS outcomes are counted but not used in conversion/FP rates

        # Core KPIs: avoid division by zero when no outcomes exist
        conversion_rate = len(converted) / total if total > 0 else 0.0
        fp_rate = len(fp) / total if total > 0 else 0.0

        # Revenue metrics: only from CONVERTED outcomes
        total_revenue = sum(o.actual_revenue_zar for o in converted)
        avg_revenue = total_revenue / len(converted) if converted else 0.0

        # Breakdown analysis: per alert type and per RM for performance management
        by_type = self._group_by_type(outcomes)
        by_rm = self._group_by_rm(outcomes)

        # Build calibration points for scored outcomes only
        calibration = self._build_calibration_points(outcomes)

        return OutcomeReport(
            period_start=period_start,
            period_end=period_end,
            total_alerts=total,
            converted=len(converted),
            rejected=len(rejected),
            expired=len(expired),
            false_positives=len(fp),
            conversion_rate=round(conversion_rate, 3),   # Round to 3dp for clean display
            false_positive_rate=round(fp_rate, 3),
            avg_revenue_converted_zar=round(avg_revenue, 0),  # Nearest rand
            total_revenue_zar=round(total_revenue, 0),
            by_alert_type=by_type,
            by_rm=by_rm,
            calibration_points=calibration,
        )

    def _group_by_type(
        self, outcomes: List[AlertOutcome]
    ) -> Dict[str, Dict]:
        """
        Group outcomes by alert type and compute per-type conversion metrics.

        Used to identify which alert types have the highest conversion rates,
        enabling prioritisation of high-value alert categories.

        :param outcomes: All outcome records for the period
        :return: Dict mapping alert_type → {count, conversion_rate, total_revenue_zar,
                 avg_days_to_outcome}
        """
        # Group outcome records by alert type
        types: Dict[str, List[AlertOutcome]] = {}
        for o in outcomes:
            types.setdefault(o.alert_type, []).append(o)

        result = {}
        for alert_type, group in types.items():
            converted = [o for o in group if o.outcome == "CONVERTED"]
            result[alert_type] = {
                "count": len(group),
                # Conversion rate for this alert type — key model quality signal
                "conversion_rate": round(
                    len(converted) / len(group), 3
                ),
                # Total revenue generated by this alert type
                "total_revenue_zar": sum(
                    o.actual_revenue_zar for o in converted
                ),
                # Average lead time from alert to closed deal (None if no conversions)
                "avg_days_to_outcome": (
                    sum(
                        o.days_to_outcome
                        for o in converted
                        if o.days_to_outcome is not None
                    ) / len(converted)
                    if converted else None
                ),
            }

        return result

    def _group_by_rm(
        self, outcomes: List[AlertOutcome]
    ) -> Dict[str, Dict]:
        """
        Group outcomes by RM ID and compute per-RM performance metrics.

        Returns a dict sorted by conversion_rate descending so the highest-
        performing RMs appear first in dashboards and coaching reports.

        :param outcomes: All outcome records for the period
        :return: Dict mapping rm_id → {total_alerts, converted, conversion_rate,
                 total_revenue_zar}, sorted by conversion_rate descending
        """
        # Group outcome records by RM
        rms: Dict[str, List[AlertOutcome]] = {}
        for o in outcomes:
            rms.setdefault(o.rm_id, []).append(o)

        result = {}
        for rm_id, group in rms.items():
            converted = [o for o in group if o.outcome == "CONVERTED"]
            result[rm_id] = {
                "total_alerts": len(group),
                "converted": len(converted),
                # RM-level conversion rate — primary RM performance KPI
                "conversion_rate": round(
                    len(converted) / len(group), 3
                ),
                # Total revenue generated by this RM's conversions
                "total_revenue_zar": sum(
                    o.actual_revenue_zar for o in converted
                ),
            }

        # Sort by conversion rate descending — best RMs appear first in reports
        result = dict(
            sorted(
                result.items(),
                key=lambda kv: kv[1]["conversion_rate"],
                reverse=True,
            )
        )

        return result

    def _build_calibration_points(
        self, outcomes: List[AlertOutcome]
    ) -> List[ModelCalibrationPoint]:
        """
        Build model calibration points from outcomes that have NBA scores.

        Each calibration point pairs a model's predicted score with the
        actual binary outcome (converted = True, otherwise = False).
        Used in compute_model_calibration() to analyse over/underconfidence.

        :param outcomes: All outcome records; only those with nba_score_at_alert
                         are included in calibration
        :return: List of ModelCalibrationPoint objects
        """
        points: List[ModelCalibrationPoint] = []

        for o in outcomes:
            # Skip outcomes without a model score; can't calibrate without prediction
            if o.nba_score_at_alert is None:
                continue

            # Map alert types to the underlying model that generated the score.
            # This enables per-model calibration curves (churn model vs NBA model etc.)
            model_map = {
                "CHURN_RISK":     "churn",    # Churn prediction model
                "EXPANSION_OPTY": "nba",      # Next Best Action model
                "CLV_UPLIFT":     "clv",      # Customer Lifetime Value model
                "CURRENCY_RISK":  "nba",      # NBA-driven currency risk scoring
                "FRAUD_FLAG":     "anomaly",  # Anomaly detection model
            }
            model = model_map.get(o.alert_type, "nba")  # Default to NBA if type not mapped

            # Binary actual outcome: CONVERTED = True, all others = False
            actual = o.outcome == "CONVERTED"

            points.append(ModelCalibrationPoint(
                model=model,
                predicted_score=o.nba_score_at_alert,
                actual_outcome=actual,
                alert_type=o.alert_type,
                revenue_zar=o.actual_revenue_zar,
            ))

        return points

    def compute_model_calibration(
        self,
        calibration_points: List[ModelCalibrationPoint],
        model: str,
        score_buckets: int = 10,
    ) -> Dict[str, Dict]:
        """
        Compute a calibration curve for a model by grouping predicted scores into buckets.

        A well-calibrated model has actual conversion rates matching the predicted scores
        in each bucket. This analysis identifies ranges where the model is:
          - Overconfident: high predicted score but low actual conversion rate
          - Underconfident: low predicted score but high actual conversion rate

        The output drives threshold adjustments in the NBA model and churn predictor.

        :param calibration_points: List of ModelCalibrationPoint objects
        :param model: Model name to analyse (e.g. 'nba', 'churn', 'clv')
        :param score_buckets: Number of equal-width score buckets (default: 10 = deciles)
        :return: Dict of bucket_range → {count, actual_conversion_rate,
                 avg_predicted_score, is_overconfident}
        """
        # Filter calibration points to the specified model only
        model_points = [
            p for p in calibration_points if p.model == model
        ]

        # Divide the 0–100 score range into equal-width buckets
        bucket_size = 100 / score_buckets
        buckets: Dict[str, List[ModelCalibrationPoint]] = {}

        for p in model_points:
            # Assign each point to its bucket based on predicted score
            bucket_idx = int(p.predicted_score / bucket_size)
            bucket_key = (
                f"{bucket_idx * bucket_size:.0f}"
                f"-{(bucket_idx + 1) * bucket_size:.0f}"
            )
            buckets.setdefault(bucket_key, []).append(p)

        result = {}
        for bucket, points in sorted(buckets.items()):
            n = len(points)
            conversions = sum(1 for p in points if p.actual_outcome)
            result[bucket] = {
                "count": n,
                # Actual conversion rate in this score bucket
                "actual_conversion_rate": round(conversions / n, 3),
                # Average predicted score within the bucket
                "avg_predicted_score": round(
                    sum(p.predicted_score for p in points) / n, 1
                ),
                # Overconfidence flag: model scores ≥70 but actual conversion < 50%
                # Indicates the model is assigning high confidence to poor leads
                "is_overconfident": (
                    conversions / n < 0.5
                    and sum(p.predicted_score for p in points) / n >= 70
                ),
            }

        return result
