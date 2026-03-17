"""
Outcome Tracker

Tracks whether RM alerts and NBA recommendations actually
led to revenue outcomes. This closes the feedback loop:

  Alert generated → RM acknowledges → RM actions → Outcome recorded

Outcome types:
  CONVERTED     — Alert led to a sale/hedging deal/policy
  REJECTED      — Client declined the recommendation
  EXPIRED       — Alert expired before RM acted
  FALSE_POSITIVE — Alert turned out to be incorrect
  IN_PROGRESS   — RM is actively working the opportunity

Metrics produced:
  - Conversion rate per alert type
  - Average revenue per converted alert
  - False positive rate per domain combination
  - RM performance ranking by conversion rate
  - Model calibration data (NBA score → actual conversion)

This data feeds back into:
  1. NBA model weight calibration
  2. Churn predictor threshold tuning
  3. Alert SLA optimisation (are 48h SLAs right for churn?)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


_OUTCOME_VALUES = {"CONVERTED", "REJECTED", "EXPIRED",
                   "FALSE_POSITIVE", "IN_PROGRESS"}


@dataclass
class AlertOutcome:
    """Outcome record for a single alert."""

    alert_id: str
    alert_type: str
    client_golden_id: str
    rm_id: str
    outcome: str
    actual_revenue_zar: float
    predicted_revenue_zar: float
    nba_score_at_alert: Optional[float]
    days_to_outcome: Optional[int]
    rm_notes: str
    recorded_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class ModelCalibrationPoint:
    """A single data point for model calibration."""

    model: str           # "nba", "churn", "clv"
    predicted_score: float
    actual_outcome: bool   # True = converted/churned, False = not
    alert_type: str
    revenue_zar: float


@dataclass
class OutcomeReport:
    """Aggregate outcome metrics for a time period."""

    period_start: str
    period_end: str
    total_alerts: int
    converted: int
    rejected: int
    expired: int
    false_positives: int

    conversion_rate: float
    false_positive_rate: float
    avg_revenue_converted_zar: float
    total_revenue_zar: float

    by_alert_type: Dict[str, Dict]   # {alert_type: {conversion_rate, count, revenue}}
    by_rm: Dict[str, Dict]           # {rm_id: {conversion_rate, count}}
    calibration_points: List[ModelCalibrationPoint]


class OutcomeTracker:
    """
    Track and analyse alert outcomes to calibrate models.

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
        """Validate and store an outcome record."""
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
        """Generate aggregate outcome metrics from a list of outcomes."""

        period_start = period_start or (
            outcomes[0].recorded_at if outcomes else ""
        )
        period_end = period_end or datetime.now().isoformat()

        total = len(outcomes)
        converted = [o for o in outcomes if o.outcome == "CONVERTED"]
        rejected = [o for o in outcomes if o.outcome == "REJECTED"]
        expired = [o for o in outcomes if o.outcome == "EXPIRED"]
        fp = [o for o in outcomes if o.outcome == "FALSE_POSITIVE"]

        conversion_rate = len(converted) / total if total > 0 else 0.0
        fp_rate = len(fp) / total if total > 0 else 0.0

        total_revenue = sum(o.actual_revenue_zar for o in converted)
        avg_revenue = total_revenue / len(converted) if converted else 0.0

        by_type = self._group_by_type(outcomes)
        by_rm = self._group_by_rm(outcomes)
        calibration = self._build_calibration_points(outcomes)

        return OutcomeReport(
            period_start=period_start,
            period_end=period_end,
            total_alerts=total,
            converted=len(converted),
            rejected=len(rejected),
            expired=len(expired),
            false_positives=len(fp),
            conversion_rate=round(conversion_rate, 3),
            false_positive_rate=round(fp_rate, 3),
            avg_revenue_converted_zar=round(avg_revenue, 0),
            total_revenue_zar=round(total_revenue, 0),
            by_alert_type=by_type,
            by_rm=by_rm,
            calibration_points=calibration,
        )

    def _group_by_type(
        self, outcomes: List[AlertOutcome]
    ) -> Dict[str, Dict]:
        types: Dict[str, List[AlertOutcome]] = {}
        for o in outcomes:
            types.setdefault(o.alert_type, []).append(o)

        result = {}
        for alert_type, group in types.items():
            converted = [o for o in group if o.outcome == "CONVERTED"]
            result[alert_type] = {
                "count": len(group),
                "conversion_rate": round(
                    len(converted) / len(group), 3
                ),
                "total_revenue_zar": sum(
                    o.actual_revenue_zar for o in converted
                ),
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
        rms: Dict[str, List[AlertOutcome]] = {}
        for o in outcomes:
            rms.setdefault(o.rm_id, []).append(o)

        result = {}
        for rm_id, group in rms.items():
            converted = [o for o in group if o.outcome == "CONVERTED"]
            result[rm_id] = {
                "total_alerts": len(group),
                "converted": len(converted),
                "conversion_rate": round(
                    len(converted) / len(group), 3
                ),
                "total_revenue_zar": sum(
                    o.actual_revenue_zar for o in converted
                ),
            }

        # Sort by conversion rate descending
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
        points: List[ModelCalibrationPoint] = []

        for o in outcomes:
            if o.nba_score_at_alert is None:
                continue

            # Map alert types to model names
            model_map = {
                "CHURN_RISK": "churn",
                "EXPANSION_OPTY": "nba",
                "CLV_UPLIFT": "clv",
                "CURRENCY_RISK": "nba",
                "FRAUD_FLAG": "anomaly",
            }
            model = model_map.get(o.alert_type, "nba")
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
        Compute calibration curve for a model.

        Returns a dict of score buckets with predicted vs actual
        conversion rates. Used to identify score ranges where the
        model is overconfident or underconfident.
        """
        model_points = [
            p for p in calibration_points if p.model == model
        ]

        bucket_size = 100 / score_buckets
        buckets: Dict[str, List[ModelCalibrationPoint]] = {}

        for p in model_points:
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
                "actual_conversion_rate": round(conversions / n, 3),
                "avg_predicted_score": round(
                    sum(p.predicted_score for p in points) / n, 1
                ),
                "is_overconfident": (
                    conversions / n < 0.5
                    and sum(p.predicted_score for p in points) / n >= 70
                ),
            }

        return result
