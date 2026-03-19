"""
@file shadow_monitor.py
@description Continuous monitoring engine for data shadows. Tracks the state of
             identified gaps over time, detecting when new shadows appear or
             existing ones are resolved. Maintains a history of shadow reports
             per client and triggers state-change events that drive RM alerts
             and relationship health scoring.
@author Thabo Kunene
@created 2026-03-19
"""

# Data Shadow Monitor
#
# We continuously monitor the data shadow for every client
# in the golden record. When new data arrives in any domain
# we re-evaluate the shadow expectations and generate
# alerts for newly detected gaps or newly resolved gaps.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.

# Future import for forward references in type hints
from __future__ import annotations

# Standard library imports for data classes, typing, and dates
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import logging

# Logic engines, exceptions, and logging configuration
from afriflow.data_shadow.expectation_rules import ExpectationRuleEngine
from afriflow.data_shadow.shadow_calculator import ShadowCalculator, DomainShadow
from afriflow.exceptions import DataShadowError
from afriflow.logging_config import get_logger, log_operation

# Initialise a module-scoped logger for shadow monitoring events
logger = get_logger("data_shadow.monitor")


@dataclass
class ShadowStateChange:
    """
    Tracks a transition in a client's data shadow state.

    :param golden_id: Unified client identifier
    :param change_type: Nature of the change (e.g., 'GAP_OPENED', 'GAP_CLOSED')
    :param rule_id: The specific expectation rule involved
    :param country: ISO-2 country code of the gap
    :param currency: Optional 3-letter currency code
    :param previous_state: Snapshot of the shadow before the change
    :param current_state: Snapshot of the shadow after the change
    :param detected_at: ISO timestamp of the detection
    """

    golden_id: str
    change_type: str
    rule_id: str
    country: Optional[str]
    currency: Optional[str]
    previous_state: Optional[Dict]
    current_state: Dict
    detected_at: str


class ShadowMonitor:
    """
    Engine responsible for tracking data shadow evolution and detecting changes.

    Maintains a stateful registry of previous evaluations to identify deltas
    that indicate relationship growth or competitive leakage.
    """

    def __init__(
        self,
        calculator: Optional[ShadowCalculator] = None
    ) -> None:
        """
        Initialise the monitor with a shadow calculator.

        :param calculator: Optional calculator instance; defaults to a new one.
        """
        self.calculator = calculator or ShadowCalculator()
        # In-memory store for the most recent shadow report per client
        self.previous_reports: Dict[str, Dict] = {}
        # Chronological list of all detected state changes
        self.state_changes: List[ShadowStateChange] = []
        logger.info("ShadowMonitor initialized")

    def evaluate_and_track(
        self,
        golden_id: str,
        domain_data: Dict[str, Any]
    ) -> Dict:
        """
        Perform a fresh shadow evaluation and record any state transitions.

        :param golden_id: Unified client identifier
        :param domain_data: Dictionary containing 'actual_presence' and 'metadata'
        :return: A dictionary containing the current shadow report and detected changes.
        :raises DataShadowError: If evaluation fails.
        """
        # Log the start of the tracking operation
        log_operation(
            logger,
            "evaluate_and_track",
            "started",
            golden_id=golden_id,
        )

        try:
            # --- Input Parsing Phase ---
            # Extract the client's verified presence from the incoming data
            actual_presence_raw = domain_data.get("actual_presence", {})
            # Ensure presence countries are stored as sets for efficient lookup
            actual_presence: Dict[str, Set[str]] = {}
            for dom, countries in actual_presence_raw.items():
                if isinstance(countries, (list, set)):
                    actual_presence[dom] = set(countries)
                else:
                    actual_presence[dom] = set()

            # Extract client metadata (metrics, sector, etc.)
            client_metadata = domain_data.get("metadata", {})
            # Fallback logic for flat data structures
            if not client_metadata and not actual_presence:
                 client_metadata = domain_data

            # --- Calculation Phase ---
            # Use the calculator to identify all current shadows
            shadows: List[DomainShadow] = self.calculator.calculate_shadows(
                golden_id=golden_id,
                client_metadata=client_metadata,
                actual_presence=actual_presence
            )

            # Convert DomainShadow objects to dictionary format for the final report
            gaps = []
            total_opportunity = 0.0
            
            for shadow in shadows:
                gap = asdict(shadow)
                # Ensure field names match the expected downstream consumer schema
                gap["rule_id"] = shadow.expectation_rule
                gap["country"] = shadow.country_code
                gap["revenue_opportunity_zar"] = shadow.estimated_revenue_zar
                gaps.append(gap)
                total_opportunity += shadow.estimated_revenue_zar

            # Construct the current state snapshot
            current_report = {
                "golden_id": golden_id,
                "generated_at": datetime.utcnow().isoformat(),
                "total_gaps_detected": len(gaps),
                "total_revenue_opportunity_zar": total_opportunity,
                "gaps": gaps,
                "shadow_health_score": self._calculate_health_score(len(gaps), total_opportunity)
            }

            # --- Change Detection Phase ---
            # Retrieve the last known state for this client
            previous = self.previous_reports.get(golden_id)

            if previous is not None:
                # Compare current vs previous to identify new or resolved gaps
                changes = self._detect_changes(
                    golden_id=golden_id,
                    previous=previous,
                    current=current_report
                )
                self.state_changes.extend(changes)
                # Inject detected changes into the current report
                current_report["state_changes"] = [
                    {
                        "change_type": c.change_type,
                        "rule_id": c.rule_id,
                        "country": c.country,
                        "detected_at": c.detected_at,
                    }
                    for c in changes
                ]
                logger.info(
                    f"Detected {len(changes)} state changes for {golden_id}"
                )
            else:
                # This is the first time we've seen this client
                current_report["state_changes"] = []
                logger.debug(f"First evaluation for {golden_id}")

            # Update the state store with the new report
            self.previous_reports[golden_id] = current_report

            # Log successful completion
            log_operation(
                logger,
                "evaluate_and_track",
                "completed",
                golden_id=golden_id,
                gaps=current_report.get("total_gaps_detected", 0),
            )

            return current_report

        except Exception as e:
            # Handle and log unexpected failures in the monitoring pipeline
            log_operation(
                logger,
                "evaluate_and_track",
                "failed",
                golden_id=golden_id,
                error=str(e),
            )
            raise DataShadowError(
                f"Failed to evaluate shadow for {golden_id}: {e}",
                details={"golden_id": golden_id}
            ) from e

    def _calculate_health_score(self, gap_count: int, opportunity: float) -> float:
        """
        Calculate a numeric relationship health score (0-100).

        :param gap_count: Number of active data shadows.
        :param opportunity: Aggregate ZAR value of identified gaps.
        :return: A float health score; 100 is perfect.
        """
        # Base score starts at 100.
        # Deduct 5 points per gap and 1 point per R1M of missed revenue.
        score = 100.0 - (gap_count * 5.0) - (opportunity / 1_000_000.0)
        # Ensure the score does not fall below zero
        return max(0.0, score)

    def _detect_changes(
        self,
        golden_id: str,
        previous: Dict,
        current: Dict
    ) -> List[ShadowStateChange]:
        """
        Compare previous and current shadow reports
        to detect state changes.
        """
        changes: List[ShadowStateChange] = []
        now = datetime.utcnow().isoformat()

        prev_gap_keys: set = set()
        prev_gap_map: Dict[str, Dict] = {}

        for gap in previous.get("gaps", []):
            key = self._gap_key(gap)
            prev_gap_keys.add(key)
            prev_gap_map[key] = gap

        curr_gap_keys: set = set()
        curr_gap_map: Dict[str, Dict] = {}

        for gap in current.get("gaps", []):
            key = self._gap_key(gap)
            curr_gap_keys.add(key)
            curr_gap_map[key] = gap

        # Newly opened gaps
        for key in curr_gap_keys - prev_gap_keys:
            gap = curr_gap_map[key]
            changes.append(ShadowStateChange(
                golden_id=golden_id,
                change_type="GAP_OPENED",
                rule_id=gap.get("rule_id", ""),
                country=gap.get("country"),
                currency=gap.get("currency"),
                previous_state=None,
                current_state=gap,
                detected_at=now,
            ))
            logger.info(
                f"Gap opened for {golden_id}: "
                f"{gap.get('rule_id')} in {gap.get('country')}"
            )

        # Closed gaps (were present, now resolved)
        for key in prev_gap_keys - curr_gap_keys:
            gap = prev_gap_map[key]
            changes.append(ShadowStateChange(
                golden_id=golden_id,
                change_type="GAP_CLOSED",
                rule_id=gap.get("rule_id", ""),
                country=gap.get("country"),
                currency=gap.get("currency"),
                previous_state=gap,
                current_state={},
                detected_at=now,
            ))
            logger.info(
                f"Gap closed for {golden_id}: "
                f"{gap.get('rule_id')} in {gap.get('country')}"
            )

        return changes

    def _gap_key(self, gap: Dict) -> str:
        """
        Create a unique key for a gap.
        """
        parts = [
            str(gap.get("rule_id", "")),
            str(gap.get("country", "")),
            str(gap.get("currency", "")),
        ]
        return "|".join(parts)

    def get_all_open_gaps(self) -> List[Dict]:
        """
        Return all currently open gaps across all
        monitored clients, sorted by revenue
        opportunity.
        """
        all_gaps: List[Dict] = []

        for golden_id, report in self.previous_reports.items():
            for gap in report.get("gaps", []):
                gap_with_client = dict(gap)
                gap_with_client["golden_id"] = golden_id
                all_gaps.append(gap_with_client)

        all_gaps.sort(
            key=lambda g: g.get("revenue_opportunity_zar", 0),
            reverse=True
        )

        logger.debug(f"Retrieved {len(all_gaps)} open gaps")
        return all_gaps

    def get_portfolio_shadow_health(self) -> Dict:
        """
        Calculate aggregate shadow health metrics
        across the entire client portfolio.
        """
        if not self.previous_reports:
            return {
                "clients_monitored": 0,
                "average_health_score": 0,
                "total_open_gaps": 0,
                "total_revenue_opportunity": 0,
            }

        scores: List[float] = []
        total_gaps = 0
        total_opportunity = 0.0

        for report in self.previous_reports.values():
            scores.append(report.get("shadow_health_score", 0))
            total_gaps += report.get("total_gaps_detected", 0)
            total_opportunity += report.get(
                "total_revenue_opportunity_zar", 0
            )

        avg_score = sum(scores) / len(scores) if scores else 0

        health_metrics = {
            "clients_monitored": len(self.previous_reports),
            "average_health_score": round(avg_score, 1),
            "total_open_gaps": total_gaps,
            "total_revenue_opportunity_zar": total_opportunity,
        }

        logger.debug(
            f"Portfolio health: {len(self.previous_reports)} clients, "
            f"avg score {avg_score:.1f}"
        )

        return health_metrics
