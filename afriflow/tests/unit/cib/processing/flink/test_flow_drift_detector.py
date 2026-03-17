from __future__ import annotations

import random
from typing import List

import pytest

from afriflow.domains.cib.processing.flink.flow_drift_detector import (
    FlowDriftDetector,
)


def _series(prev: float, curr: float, window: int) -> List[float]:
    return [prev] * window + [curr] * window


def test_insufficient_data_returns_none():
    det = FlowDriftDetector(threshold_percentage=20.0, window_size=10)
    det.add_observation("CLIENT-1", "ZA-NG", 100.0)
    assert det.detect_drift("CLIENT-1", "ZA-NG") is None


def test_detect_drift_increase_and_decrease():
    det = FlowDriftDetector(threshold_percentage=10.0, window_size=5)
    for v in _series(100.0, 130.0, 5):
        det.add_observation("CLIENT-1", "ZA-NG", v)
    alert = det.detect_drift("CLIENT-1", "ZA-NG")
    assert alert is not None and alert.direction == "increase"
    det = FlowDriftDetector(threshold_percentage=10.0, window_size=5)
    for v in _series(100.0, 70.0, 5):
        det.add_observation("CLIENT-1", "ZA-NG", v)
    alert = det.detect_drift("CLIENT-1", "ZA-NG")
    assert alert is not None and alert.direction == "decrease"


def test_get_statistics_and_severity():
    det = FlowDriftDetector(threshold_percentage=20.0, window_size=5)
    vals = [100.0, 120.0, 90.0, 110.0, 95.0, 130.0, 140.0, 150.0, 160.0, 170.0]
    for v in vals:
        det.add_observation("CLIENT-1", "ZA-NG", v)
    stats = det.get_statistics("CLIENT-1", "ZA-NG")
    assert stats["count"] == len(vals)
    assert stats["min"] == min(vals) and stats["max"] == max(vals)
    # severity thresholds
    assert det._calculate_severity(55.0) == "critical"
    assert det._calculate_severity(35.0) == "high"
    assert det._calculate_severity(25.0) == "medium"
    assert det._calculate_severity(10.0) == "low"
