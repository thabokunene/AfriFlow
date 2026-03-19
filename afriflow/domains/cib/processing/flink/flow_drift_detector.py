"""
@file flow_drift_detector.py
@description Flink-based detector for identifying statistical drift in CIB payment flows, providing early warnings for client behavior shifts.
@author Thabo Kunene
@created 2026-03-19
"""

"""
CIB Flow Drift Detector.

We detect significant changes in payment flow patterns
using statistical methods. This enables early warning
of client attrition or expansion.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Type hinting for defining strong collection and functional contracts
from typing import Dict, List, Optional, Any
# Dataclasses for structured representation of drift alerts
from dataclasses import dataclass
# Datetime utilities for timestamping detected anomalies
from datetime import datetime, timezone
# Standard logging for operational observability and alerting context
import logging
# Statistics library for calculating mean and variance of payment flows
import statistics

# Initialize module-level logger for drift detection events
logger = logging.getLogger(__name__)


@dataclass
class FlowDriftAlert:
    """
    Structured alert triggered when significant payment flow drift is detected.

    Attributes:
        client_id: Unique identifier for the corporate client.
        corridor: The payment corridor being monitored (e.g., 'ZA-NG').
        drift_percentage: The calculated percentage change from the baseline.
        direction: Indicates whether the flow has 'increased' or 'decreased'.
        severity: The priority level of the alert ('critical', 'high', 'medium').
        detected_at: The precise timestamp when the drift was identified.
    """
    client_id: str
    corridor: str
    drift_percentage: float
    direction: str
    severity: str
    detected_at: datetime


class FlowDriftDetector:
    """
    Statistical engine for detecting deviations in CIB payment flows.
    
    This detector maintains a rolling window of historical values to calculate
    a baseline and identify outliers that exceed a configurable threshold.

    Attributes:
        threshold_percentage: The minimum drift percentage required to trigger an alert.
        window_size: The number of historical observations to maintain for the baseline.
    """

    def __init__(
        self,
        threshold_percentage: float = 20.0,
        window_size: int = 30
    ) -> None:
        """
        Initializes the drift detector with configurable thresholds and window sizes.

        :param threshold_percentage: Minimum drift for an alert. Defaults to 20.0%.
        :param window_size: Number of historical data points to keep. Defaults to 30.
        """
        self.threshold_percentage = threshold_percentage
        self.window_size = window_size
        # Dictionary mapping a unique key (client_id:corridor) to a list of historical values
        self.historical_data: Dict[str, List[float]] = {}

        logger.info(
            f"FlowDriftDetector initialized: "
            f"threshold={threshold_percentage}%, "
            f"window={window_size} days"
        )

    def add_observation(
        self,
        client_id: str,
        corridor: str,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Records a new payment flow observation for a client and corridor.

        :param client_id: Identifier of the client.
        :param corridor: The payment corridor.
        :param value: The value of the payment flow.
        :param timestamp: The observation timestamp (optional).
        """
        key = f"{client_id}:{corridor}"

        if key not in self.historical_data:
            self.historical_data[key] = []

        self.historical_data[key].append(value)

        # Keep only recent data
        if len(self.historical_data[key]) > self.window_size * 2:
            self.historical_data[key] = (
                self.historical_data[key][-self.window_size * 2:]
            )

        logger.debug(
            f"Added observation for {key}: {value}"
        )

    def detect_drift(
        self,
        client_id: str,
        corridor: str
    ) -> Optional[FlowDriftAlert]:
        """
        Detect drift in payment flows.

        Args:
            client_id: Client identifier
            corridor: Payment corridor

        Returns:
            FlowDriftAlert if drift detected, None otherwise
        """
        key = f"{client_id}:{corridor}"

        if key not in self.historical_data:
            return None

        data = self.historical_data[key]

        if len(data) < self.window_size:
            logger.debug(
                f"Insufficient data for drift detection: {key}"
            )
            return None

        # Split into two periods
        mid_point = len(data) // 2
        previous_period = data[:mid_point]
        current_period = data[mid_point:]

        # Calculate averages
        prev_avg = statistics.mean(previous_period)
        curr_avg = statistics.mean(current_period)

        if prev_avg == 0:
            return None

        # Calculate drift
        drift_pct = ((curr_avg - prev_avg) / prev_avg) * 100

        if abs(drift_pct) >= self.threshold_percentage:
            direction = "increase" if drift_pct > 0 else "decrease"
            severity = self._calculate_severity(abs(drift_pct))

            alert = FlowDriftAlert(
                client_id=client_id,
                corridor=corridor,
                drift_percentage=round(drift_pct, 2),
                direction=direction,
                severity=severity,
                # Use timezone-aware UTC to avoid naive datetime deprecation and ambiguity
                detected_at=datetime.now(timezone.utc),
            )

            logger.warning(
                f"Flow drift detected: {key} "
                f"{direction} {drift_pct:.1f}%"
            )

            return alert

        return None

    def _calculate_severity(self, drift_pct: float) -> str:
        """
        Calculate alert severity based on drift percentage.

        Args:
            drift_pct: Absolute drift percentage

        Returns:
            Severity level
        """
        if drift_pct >= 50:
            return "critical"
        elif drift_pct >= 30:
            return "high"
        elif drift_pct >= 20:
            return "medium"
        else:
            return "low"

    def get_statistics(
        self,
        client_id: str,
        corridor: str
    ) -> Dict[str, Any]:
        """
        Get flow statistics for a corridor.

        Args:
            client_id: Client identifier
            corridor: Payment corridor

        Returns:
            Statistics dictionary
        """
        key = f"{client_id}:{corridor}"

        if key not in self.historical_data:
            return {}

        data = self.historical_data[key]

        if not data:
            return {}

        return {
            "count": len(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0,
            "min": min(data),
            "max": max(data),
        }


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    detector = FlowDriftDetector(threshold_percentage=20.0)

    # Add observations
    import random
    for i in range(60):
        value = 100000 + random.uniform(-10000, 10000)
        detector.add_observation("CLIENT-001", "ZA-NG", value)

    # Detect drift
    alert = detector.detect_drift("CLIENT-001", "ZA-NG")
    if alert:
        print(f"Alert: {alert}")
    else:
        print("No drift detected")
