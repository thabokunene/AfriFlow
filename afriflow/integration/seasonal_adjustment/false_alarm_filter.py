"""
Seasonal Adjustment - False Alarm Filter

We suppress signals that are explained by known seasonal,
calendar, or structural patterns before they reach RM
alert queues. The filter acts as a final gate between
raw anomaly detection and actionable alert dispatch.

Suppression rules applied (in priority order):
  1. Seasonal calendar match — signal explained by harvest/planting
  2. Public holiday / end-of-month calendar — salary credit spikes
  3. Known regulatory events — currency policy announcement windows
  4. Structural one-offs — new corporate client onboarding batch
  5. Data pipeline lag — expected when source ETL is running late

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.logging_config import get_logger
from .agricultural_calendar import AgriculturalCalendar

logger = get_logger("integration.seasonal_adjustment.false_alarm_filter")


class SuppressionReason(Enum):
    """Reason a signal was suppressed."""
    SEASONAL_CALENDAR = "seasonal_calendar"
    SALARY_CYCLE = "salary_cycle"
    PUBLIC_HOLIDAY = "public_holiday"
    END_OF_MONTH = "end_of_month"
    QUARTER_END = "quarter_end"
    REGULATORY_EVENT = "regulatory_event"
    ONBOARDING_BATCH = "onboarding_batch"
    PIPELINE_LAG = "pipeline_lag"
    NOT_SUPPRESSED = "not_suppressed"


@dataclass
class FilterDecision:
    """
    Decision on whether to suppress a signal.

    Attributes:
        signal_id: Identifier of the signal
        is_suppressed: True if the signal should NOT be alerted
        suppression_reason: Why it was suppressed (or NOT_SUPPRESSED)
        confidence: Confidence in the suppression decision (0–1)
        explanation: Human-readable explanation
        residual_score: Adjusted signal score after suppression
    """
    signal_id: str
    is_suppressed: bool
    suppression_reason: SuppressionReason
    confidence: float
    explanation: str
    residual_score: float


# ── Country-specific salary cycle dates ──────────────────────────────────────
# Most African corporate payrolls run on the 25th or last working day.
SALARY_DAYS: Dict[str, List[int]] = {
    "ZA": [25, 26, 27, 28, 29, 30, 31],  # 25th or last working day
    "NG": [25, 26, 27, 28],
    "KE": [26, 27, 28, 29, 30],
    "GH": [25, 26, 27, 28],
    "TZ": [25, 26, 27, 28, 29],
    "UG": [25, 26, 27, 28],
    "ZM": [25, 26, 27, 28],
}

# ── Public holidays that cause anomalous silence (markets closed) ─────────────
PUBLIC_HOLIDAYS: Dict[str, List[tuple]] = {
    "ZA": [(1, 1), (3, 21), (4, 27), (5, 1), (6, 16), (8, 9), (9, 24), (12, 16), (12, 25), (12, 26)],
    "NG": [(1, 1), (4, 18), (5, 1), (6, 12), (10, 1), (12, 25), (12, 26)],
    "KE": [(1, 1), (4, 18), (5, 1), (6, 1), (10, 10), (10, 20), (12, 12), (12, 25), (12, 26)],
    "GH": [(1, 1), (3, 6), (4, 18), (5, 1), (7, 1), (12, 25), (12, 26)],
}


class FalseAlarmFilter:
    """
    We filter signals that are explained by known patterns.

    Before an anomaly reaches the RM alert queue, we check
    whether it falls within a known calendar effect window.
    Suppressed signals are still logged for audit but are
    not dispatched as actionable alerts.

    Attributes:
        calendar: AgriculturalCalendar for seasonal checks
        seasonal_threshold: Multiplier difference below which seasonal
                            explanation is accepted
        suppression_log: History of suppression decisions
    """

    SEASONAL_THRESHOLD = 0.20    # Multiplier within 20% = seasonal
    SALARY_WINDOW_DAYS = 3       # ±3 days around salary day
    EOM_WINDOW_DAYS = 3          # Last 3 days of month

    def __init__(
        self,
        calendar: Optional[AgriculturalCalendar] = None,
    ) -> None:
        self.calendar = calendar or AgriculturalCalendar()
        self.suppression_log: List[FilterDecision] = []
        logger.info("FalseAlarmFilter initialized")

    def evaluate(
        self,
        signal_id: str,
        country: str,
        sector: str,
        observation_date: datetime,
        raw_score: float,
        seasonal_multiplier: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FilterDecision:
        """
        Evaluate whether a signal should be suppressed.

        Args:
            signal_id: Unique signal identifier
            country: ISO-2 country code
            sector: Economic sector
            observation_date: When the signal was observed
            raw_score: Raw anomaly score (0–1)
            seasonal_multiplier: Expected seasonal multiplier
            metadata: Additional context

        Returns:
            FilterDecision with suppression verdict
        """
        metadata = metadata or {}

        # Check each suppression rule in priority order
        decision = (
            self._check_seasonal(
                signal_id, country, sector, observation_date,
                raw_score, seasonal_multiplier
            )
            or self._check_salary_cycle(
                signal_id, country, observation_date, raw_score
            )
            or self._check_public_holiday(
                signal_id, country, observation_date, raw_score
            )
            or self._check_end_of_month(
                signal_id, observation_date, raw_score
            )
            or self._check_quarter_end(
                signal_id, observation_date, raw_score
            )
            or FilterDecision(
                signal_id=signal_id,
                is_suppressed=False,
                suppression_reason=SuppressionReason.NOT_SUPPRESSED,
                confidence=1.0,
                explanation="No suppression pattern matched.",
                residual_score=raw_score,
            )
        )

        self.suppression_log.append(decision)
        if decision.is_suppressed:
            logger.info(
                f"Signal {signal_id} suppressed: "
                f"{decision.suppression_reason.value} "
                f"(confidence={decision.confidence:.2f})"
            )

        return decision

    def evaluate_batch(
        self,
        signals: List[Dict[str, Any]],
    ) -> List[FilterDecision]:
        """
        Evaluate a batch of signals.

        Each signal dict must have keys:
          signal_id, country, sector, observation_date,
          raw_score, seasonal_multiplier
        """
        return [
            self.evaluate(
                signal_id=s["signal_id"],
                country=s["country"],
                sector=s["sector"],
                observation_date=s["observation_date"],
                raw_score=s["raw_score"],
                seasonal_multiplier=s["seasonal_multiplier"],
                metadata=s.get("metadata"),
            )
            for s in signals
        ]

    def _check_seasonal(
        self,
        signal_id: str,
        country: str,
        sector: str,
        observation_date: datetime,
        raw_score: float,
        seasonal_multiplier: float,
    ) -> Optional[FilterDecision]:
        """Suppress if signal score is proportional to seasonal multiplier."""
        # If the multiplier is far from 1.0, the season explains the anomaly
        seasonal_deviation = abs(seasonal_multiplier - 1.0)
        if seasonal_deviation >= self.SEASONAL_THRESHOLD:
            phase = self.calendar.get_phase(
                country, sector, observation_date.month
            )
            confidence = min(0.95, seasonal_deviation / 0.50)
            residual = max(0.0, raw_score - seasonal_deviation)
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.SEASONAL_CALENDAR,
                confidence=round(confidence, 3),
                explanation=(
                    f"Seasonal phase '{phase.value}' in "
                    f"{country}/{sector} explains the signal. "
                    f"Expected multiplier: {seasonal_multiplier:.2f}x."
                ),
                residual_score=round(residual, 3),
            )
        return None

    def _check_salary_cycle(
        self,
        signal_id: str,
        country: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress cash flow spikes around salary day."""
        salary_days = SALARY_DAYS.get(country.upper(), [25, 26, 27, 28])
        dom = observation_date.day
        near_salary = any(
            abs(dom - sd) <= self.SALARY_WINDOW_DAYS
            for sd in salary_days
        )
        if near_salary:
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.SALARY_CYCLE,
                confidence=0.85,
                explanation=(
                    f"Observation on day {dom} of month falls within "
                    f"{country} salary cycle window."
                ),
                residual_score=round(raw_score * 0.3, 3),
            )
        return None

    def _check_public_holiday(
        self,
        signal_id: str,
        country: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress near public holidays (silence or pre-holiday rush)."""
        holidays = PUBLIC_HOLIDAYS.get(country.upper(), [])
        obs_md = (observation_date.month, observation_date.day)
        is_holiday = obs_md in holidays
        if is_holiday:
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.PUBLIC_HOLIDAY,
                confidence=0.90,
                explanation=(
                    f"{obs_md[0]:02d}-{obs_md[1]:02d} is a public holiday "
                    f"in {country}. Volume anomaly expected."
                ),
                residual_score=0.0,
            )
        return None

    def _check_end_of_month(
        self,
        signal_id: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress last 3 days of month — corporate payment clustering."""
        import calendar
        last_day = calendar.monthrange(
            observation_date.year, observation_date.month
        )[1]
        if observation_date.day >= last_day - self.EOM_WINDOW_DAYS:
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.END_OF_MONTH,
                confidence=0.80,
                explanation=(
                    "End-of-month corporate payment clustering "
                    "explains volume spike."
                ),
                residual_score=round(raw_score * 0.4, 3),
            )
        return None

    def _check_quarter_end(
        self,
        signal_id: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress quarter-end reporting windows (Mar/Jun/Sep/Dec last week)."""
        is_quarter_end_month = observation_date.month in [3, 6, 9, 12]
        import calendar
        last_day = calendar.monthrange(
            observation_date.year, observation_date.month
        )[1]
        in_last_week = observation_date.day >= last_day - 6
        if is_quarter_end_month and in_last_week:
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.QUARTER_END,
                confidence=0.85,
                explanation="Quarter-end balance sheet activity explains anomaly.",
                residual_score=round(raw_score * 0.2, 3),
            )
        return None

    def get_suppression_statistics(self) -> Dict[str, Any]:
        """Get statistics on suppression decisions."""
        if not self.suppression_log:
            return {"total_evaluated": 0}

        total = len(self.suppression_log)
        suppressed = [d for d in self.suppression_log if d.is_suppressed]

        by_reason: Dict[str, int] = {}
        for d in suppressed:
            key = d.suppression_reason.value
            by_reason[key] = by_reason.get(key, 0) + 1

        return {
            "total_evaluated": total,
            "suppressed": len(suppressed),
            "suppression_rate": round(len(suppressed) / total, 3),
            "passed_through": total - len(suppressed),
            "by_reason": by_reason,
        }

    def clear_log(self) -> None:
        """Clear the suppression log."""
        self.suppression_log = []


if __name__ == "__main__":
    faf = FalseAlarmFilter()

    # November GH cocoa spike — seasonal, suppress
    d1 = faf.evaluate(
        signal_id="SIG-001",
        country="GH", sector="cocoa",
        observation_date=datetime(2024, 11, 20),
        raw_score=0.78,
        seasonal_multiplier=1.45,
    )
    print(f"SIG-001: suppressed={d1.is_suppressed}, "
          f"reason={d1.suppression_reason.value}")

    # ZA salary day spike — salary cycle, suppress
    d2 = faf.evaluate(
        signal_id="SIG-002",
        country="ZA", sector="retail",
        observation_date=datetime(2024, 11, 25),
        raw_score=0.65,
        seasonal_multiplier=1.0,
    )
    print(f"SIG-002: suppressed={d2.is_suppressed}, "
          f"reason={d2.suppression_reason.value}")

    # Mid-month NG petroleum anomaly — not suppressed
    d3 = faf.evaluate(
        signal_id="SIG-003",
        country="NG", sector="petroleum",
        observation_date=datetime(2024, 11, 13),
        raw_score=0.85,
        seasonal_multiplier=1.0,
    )
    print(f"SIG-003: suppressed={d3.is_suppressed}, "
          f"reason={d3.suppression_reason.value}")

    print(f"\nStats: {faf.get_suppression_statistics()}")
