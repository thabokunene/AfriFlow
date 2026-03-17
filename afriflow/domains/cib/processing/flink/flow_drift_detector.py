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

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class FlowDriftAlert:
    """
    Alert for detected flow drift.

    Attributes:
        client_id: Client identifier
        corridor: Payment corridor
        drift_percentage: Percentage change
        direction: Direction of drift (increase/decrease)
        severity: Alert severity
        detected_at: Detection timestamp
    """
    client_id: str
    corridor: str
    drift_percentage: float
    direction: str
    severity: str
    detected_at: datetime


class FlowDriftDetector:
    """
    Detects drift in payment flow patterns.

    We use statistical methods to identify significant
    deviations from historical patterns.

    Attributes:
        threshold_percentage: Drift threshold for alerts
        window_size: Number of periods for comparison
    """

    def __init__(
        self,
        threshold_percentage: float = 20.0,
        window_size: int = 30
    ) -> None:
        """
        Initialize the drift detector.

        Args:
            threshold_percentage: Drift threshold
            window_size: Comparison window size
        """
        self.threshold_percentage = threshold_percentage
        self.window_size = window_size
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
        Add a payment flow observation.

        Args:
            client_id: Client identifier
            corridor: Payment corridor
            value: Payment value
            timestamp: Observation timestamp
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
