"""
@file false_alarm_filter.py
@description Final suppression gate between raw anomaly detection and RM
    alert dispatch. Evaluates signals against five ordered suppression rules:
    seasonal calendar match, salary cycle, public holiday, end-of-month
    payment clustering, and quarter-end balance sheet activity. Suppressed
    signals are logged for audit but not forwarded as actionable alerts.
@author Thabo Kunene
@created 2026-03-18
"""
# Suppression rules applied in priority order:
#   1. Seasonal calendar match — harvest / planting explains the signal
#   2. Salary cycle — cash flow spike near country payroll day
#   3. Public holiday — anomalous silence or pre-holiday rush
#   4. End-of-month — corporate payment clustering last 3 days
#   5. Quarter-end — balance sheet activity in Mar/Jun/Sep/Dec last week
#
# DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
# Group, MTN, or any affiliated entity. It is a demonstration of concept,
# domain knowledge, and data engineering skill by Thabo Kunene.

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.logging_config import get_logger
from .agricultural_calendar import AgriculturalCalendar

# Module-level logger for suppression audit trails
logger = get_logger("integration.seasonal_adjustment.false_alarm_filter")


class SuppressionReason(Enum):
    """Reason a signal was suppressed.

    Each value maps to one of the ordered suppression rules. Signals that
    pass all rules receive NOT_SUPPRESSED and proceed to the RM alert queue.
    """
    SEASONAL_CALENDAR = "seasonal_calendar"   # Rule 1: agricultural harvest/planting
    SALARY_CYCLE = "salary_cycle"             # Rule 2: payroll credit spike
    PUBLIC_HOLIDAY = "public_holiday"         # Rule 3: market closed anomaly
    END_OF_MONTH = "end_of_month"             # Rule 4: corporate payment clustering
    QUARTER_END = "quarter_end"               # Rule 5: balance sheet activity
    REGULATORY_EVENT = "regulatory_event"     # Reserved: currency policy windows
    ONBOARDING_BATCH = "onboarding_batch"     # Reserved: new client batch effect
    PIPELINE_LAG = "pipeline_lag"             # Reserved: source ETL running late
    NOT_SUPPRESSED = "not_suppressed"         # No rule matched — signal is genuine


@dataclass
class FilterDecision:
    """Decision on whether to suppress a signal.

    Attributes:
        signal_id: Identifier of the signal being evaluated
        is_suppressed: True when the signal should NOT be dispatched as an alert
        suppression_reason: The matched suppression rule (or NOT_SUPPRESSED)
        confidence: Confidence in the suppression decision (0–1)
        explanation: Human-readable explanation for the audit log
        residual_score: Signal score after removing the explained component
    """
    signal_id: str
    is_suppressed: bool
    suppression_reason: SuppressionReason
    confidence: float
    explanation: str
    residual_score: float           # Score remaining after suppression adjustment


# ── Country-specific salary cycle dates ──────────────────────────────────────
# Most African corporate payrolls run on the 25th or the last working day.
# We maintain a window of candidate days because the exact day shifts with
# weekends and public holidays.
SALARY_DAYS: Dict[str, List[int]] = {
    "ZA": [25, 26, 27, 28, 29, 30, 31],  # 25th or last working day of month
    "NG": [25, 26, 27, 28],              # Nigerian payroll window
    "KE": [26, 27, 28, 29, 30],          # Kenyan payroll window
    "GH": [25, 26, 27, 28],              # Ghanaian payroll window
    "TZ": [25, 26, 27, 28, 29],          # Tanzanian payroll window
    "UG": [25, 26, 27, 28],              # Ugandan payroll window
    "ZM": [25, 26, 27, 28],              # Zambian payroll window
}

# ── Public holidays that cause anomalous silence (markets closed) ─────────────
# Stored as (month, day) tuples. These are the fixed-date public holidays;
# movable feasts (Easter) are simplified to a representative date.
PUBLIC_HOLIDAYS: Dict[str, List[tuple]] = {
    "ZA": [
        (1, 1),   # New Year
        (3, 21),  # Human Rights Day
        (4, 27),  # Freedom Day
        (5, 1),   # Workers Day
        (6, 16),  # Youth Day
        (8, 9),   # National Women's Day
        (9, 24),  # Heritage Day
        (12, 16), # Day of Reconciliation
        (12, 25), # Christmas
        (12, 26), # Day of Goodwill
    ],
    "NG": [
        (1, 1),   # New Year
        (4, 18),  # Good Friday (approximate)
        (5, 1),   # Workers Day
        (6, 12),  # Democracy Day
        (10, 1),  # Independence Day
        (12, 25), # Christmas
        (12, 26), # Boxing Day
    ],
    "KE": [
        (1, 1),   # New Year
        (4, 18),  # Good Friday (approximate)
        (5, 1),   # Labour Day
        (6, 1),   # Madaraka Day
        (10, 10), # Moi Day
        (10, 20), # Mashujaa Day
        (12, 12), # Jamhuri Day
        (12, 25), # Christmas
        (12, 26), # Boxing Day
    ],
    "GH": [
        (1, 1),   # New Year
        (3, 6),   # Independence Day
        (4, 18),  # Good Friday (approximate)
        (5, 1),   # Workers Day
        (7, 1),   # Republic Day
        (12, 25), # Christmas
        (12, 26), # Boxing Day
    ],
}


class FalseAlarmFilter:
    """We filter signals that are explained by known calendar patterns.

    Before an anomaly reaches the RM alert queue, we check whether it
    falls within a known calendar effect window. Each signal is evaluated
    against five suppression rules in priority order; the first matching
    rule wins. Suppressed signals are still appended to suppression_log
    for audit but are NOT dispatched as actionable alerts.

    Attributes:
        calendar: AgriculturalCalendar used for seasonal phase lookups
        suppression_log: Complete history of all FilterDecision outcomes
    """

    SEASONAL_THRESHOLD = 0.20    # Multiplier deviation >= 20% triggers seasonal suppression
    SALARY_WINDOW_DAYS = 3       # ±3 calendar days around each salary day candidate
    EOM_WINDOW_DAYS = 3          # Suppress if within last 3 days of month

    def __init__(
        self,
        calendar: Optional[AgriculturalCalendar] = None,
    ) -> None:
        """Initialise the filter.

        Args:
            calendar: Optional pre-built AgriculturalCalendar. A new instance
                      is created if not supplied.
        """
        # Use provided calendar or build a fresh one with all built-in patterns
        self.calendar = calendar or AgriculturalCalendar()
        # Accumulates every decision for downstream audit and statistics
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
        """Evaluate whether a signal should be suppressed.

        Applies each suppression rule in priority order using short-circuit
        OR evaluation. The first rule that returns a non-None decision wins.
        If no rule matches, a NOT_SUPPRESSED decision is returned.

        Args:
            signal_id: Unique signal identifier for audit logging
            country: ISO-2 country code
            sector: Economic sector (e.g. "cocoa", "AGR_GRAIN")
            observation_date: Timestamp when the signal was observed
            raw_score: Raw anomaly score in [0, 1]
            seasonal_multiplier: Expected seasonal revenue multiplier for this month
            metadata: Optional additional context (reserved for future use)

        Returns:
            FilterDecision with suppression verdict, reason, and residual score.
        """
        metadata = metadata or {}

        # Apply suppression rules in declared priority order.
        # Python's short-circuit `or` means we stop at the first non-None result.
        decision = (
            # Rule 1: Seasonal calendar — harvest or off-season explains the signal
            self._check_seasonal(
                signal_id, country, sector, observation_date,
                raw_score, seasonal_multiplier
            )
            # Rule 2: Salary cycle — payroll credit spike near month-end
            or self._check_salary_cycle(
                signal_id, country, observation_date, raw_score
            )
            # Rule 3: Public holiday — market closed or pre-holiday rush
            or self._check_public_holiday(
                signal_id, country, observation_date, raw_score
            )
            # Rule 4: End of month — corporate payment clustering
            or self._check_end_of_month(
                signal_id, observation_date, raw_score
            )
            # Rule 5: Quarter end — balance sheet reporting activity
            or self._check_quarter_end(
                signal_id, observation_date, raw_score
            )
            # Default: no rule matched — signal should proceed to alert queue
            or FilterDecision(
                signal_id=signal_id,
                is_suppressed=False,
                suppression_reason=SuppressionReason.NOT_SUPPRESSED,
                confidence=1.0,
                explanation="No suppression pattern matched.",
                residual_score=raw_score,
            )
        )

        # Always append to log for audit, regardless of outcome
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
        """Evaluate a batch of signals in sequence.

        Delegates to evaluate() for each signal dict. Each dict must contain
        the keys: signal_id, country, sector, observation_date, raw_score,
        seasonal_multiplier. The optional 'metadata' key is forwarded if present.

        Args:
            signals: List of signal dicts to evaluate.

        Returns:
            List of FilterDecision objects in the same order as input.
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
        """Suppress if the signal is proportional to the seasonal multiplier.

        A multiplier deviation >= SEASONAL_THRESHOLD (20%) means the calendar
        itself explains the observed anomaly — no need to alert the RM.
        Confidence scales linearly up to 0.95 as the deviation grows.
        """
        # How far is the multiplier from the neutral 1.0 baseline?
        seasonal_deviation = abs(seasonal_multiplier - 1.0)
        if seasonal_deviation >= self.SEASONAL_THRESHOLD:
            # Look up the agronomic phase for contextual explanation
            phase = self.calendar.get_phase(
                country, sector, observation_date.month
            )
            # Confidence scales: 20% deviation → 0.40, 50% deviation → 0.95 cap
            confidence = min(0.95, seasonal_deviation / 0.50)
            # Residual score: what remains after removing the seasonal component
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
        return None  # Rule did not match; try the next rule

    def _check_salary_cycle(
        self,
        signal_id: str,
        country: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress cash flow spikes that fall within the country salary window.

        Uses a ±SALARY_WINDOW_DAYS tolerance around each candidate salary day
        to accommodate weekends and public holiday shifts.
        """
        # Default to a conservative [25–28] window for unknown countries
        salary_days = SALARY_DAYS.get(country.upper(), [25, 26, 27, 28])
        dom = observation_date.day  # Day of month for the observation
        # Check if the observation day is within the tolerance of any salary day
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
                # Salary spikes account for ~70% of the raw score; 30% residual
                residual_score=round(raw_score * 0.3, 3),
            )
        return None  # Not near a salary day; continue to next rule

    def _check_public_holiday(
        self,
        signal_id: str,
        country: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress anomalies on known public holidays.

        Market closures cause anomalous silence; pre-holiday rushes cause
        spikes. Both are expected patterns that should not reach RM queues.
        """
        holidays = PUBLIC_HOLIDAYS.get(country.upper(), [])
        # Convert to (month, day) tuple for membership test
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
                residual_score=0.0,  # Holiday explains the entire score
            )
        return None  # Not a holiday; continue to next rule

    def _check_end_of_month(
        self,
        signal_id: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress signals in the last EOM_WINDOW_DAYS days of any month.

        African corporate clients cluster large payment runs on the last
        working days of the month to meet supplier terms. This is normal.
        """
        import calendar  # Import here to avoid module-level circular dependency
        # Get the total number of days in the observation's month
        last_day = calendar.monthrange(
            observation_date.year, observation_date.month
        )[1]
        # Check if we are within the last EOM_WINDOW_DAYS days
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
                # EOM clustering accounts for ~60% of the score; 40% residual
                residual_score=round(raw_score * 0.4, 3),
            )
        return None  # Not end of month; continue to next rule

    def _check_quarter_end(
        self,
        signal_id: str,
        observation_date: datetime,
        raw_score: float,
    ) -> Optional[FilterDecision]:
        """Suppress signals in the last week of a quarter-end month.

        Quarter-end months are March, June, September, December. Clients
        engage in balance sheet window-dressing and large settlement runs
        during the last 7 days. These are expected and should not trigger alerts.
        """
        # Quarter-end months: Mar, Jun, Sep, Dec
        is_quarter_end_month = observation_date.month in [3, 6, 9, 12]
        import calendar  # Local import to keep module dependencies clear
        last_day = calendar.monthrange(
            observation_date.year, observation_date.month
        )[1]
        # Last 7 calendar days of the month
        in_last_week = observation_date.day >= last_day - 6
        if is_quarter_end_month and in_last_week:
            return FilterDecision(
                signal_id=signal_id,
                is_suppressed=True,
                suppression_reason=SuppressionReason.QUARTER_END,
                confidence=0.85,
                explanation="Quarter-end balance sheet activity explains anomaly.",
                # Quarter-end effect explains ~80% of score; 20% residual
                residual_score=round(raw_score * 0.2, 3),
            )
        return None  # Rule did not match; fall through to NOT_SUPPRESSED default

    def get_suppression_statistics(self) -> Dict[str, Any]:
        """Return aggregated statistics on all suppression decisions so far.

        Used by monitoring dashboards and CI quality gates to track false
        alarm rates and identify which suppression rules fire most often.
        """
        if not self.suppression_log:
            return {"total_evaluated": 0}

        total = len(self.suppression_log)
        suppressed = [d for d in self.suppression_log if d.is_suppressed]

        # Count suppressed signals grouped by their suppression reason
        by_reason: Dict[str, int] = {}
        for d in suppressed:
            key = d.suppression_reason.value
            by_reason[key] = by_reason.get(key, 0) + 1

        return {
            "total_evaluated": total,
            "suppressed": len(suppressed),
            # Rate of suppression: fraction of signals that did NOT reach RM queue
            "suppression_rate": round(len(suppressed) / total, 3),
            "passed_through": total - len(suppressed),
            "by_reason": by_reason,
        }

    def clear_log(self) -> None:
        """Clear the suppression log.

        Called between test runs or when memory usage needs to be controlled
        in long-running streaming processes.
        """
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
