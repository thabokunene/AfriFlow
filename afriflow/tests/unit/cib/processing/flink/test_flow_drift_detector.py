from __future__ import annotations

import random
from typing import List

import pytest

from afriflow.domains.cib.processing.flink.flow_drift_detector import (
    FlowDriftDetector,
)
from afriflow.tests.utils.random_data import make_drift_pair


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


def _seeded_series(seed: int, length: int, base: float, noise: float = 0.0) -> List[float]:
    rng = random.Random(seed)
    return [base + rng.uniform(-noise, noise) for _ in range(length)]


def test_seeded_gradual_drift_detected():
    det = FlowDriftDetector(threshold_percentage=10.0, window_size=20)
    prev, curr = make_drift_pair(seed=42, window=20, base=100.0, noise=2.0, drift_type="gradual", drift_magnitude=0.15)
    for v in prev + curr:
        det.add_observation("CLIENT-1", "ZA-NG", v)
    alert = det.detect_drift("CLIENT-1", "ZA-NG")
    assert alert is not None and alert.direction == "increase"


def test_seeded_sudden_spike_detected():
    det = FlowDriftDetector(threshold_percentage=15.0, window_size=10)
    prev, curr = make_drift_pair(seed=99, window=10, base=100.0, noise=1.0, drift_type="spike", drift_magnitude=0.60)
    for v in prev + curr:
        det.add_observation("CLIENT-1", "ZA-NG", v)
    alert = det.detect_drift("CLIENT-1", "ZA-NG")
    assert alert is not None and alert.direction == "increase"


def test_seeded_cyclical_patterns_no_drift():
    det = FlowDriftDetector(threshold_percentage=30.0, window_size=20)
    prev, curr = make_drift_pair(seed=7, window=20, base=100.0, noise=2.0, drift_type="cyclical", drift_magnitude=0.05)
    for v in prev + curr:
        det.add_observation("CLIENT-1", "ZA-NG", v)
    assert det.detect_drift("CLIENT-1", "ZA-NG") is None


def test_seeded_stable_baseline_no_drift():
    det = FlowDriftDetector(threshold_percentage=5.0, window_size=20)
    series = _seeded_series(123, 40, base=100.0, noise=0.5)
    for v in series:
        det.add_observation("CLIENT-1", "ZA-NG", v)
    assert det.detect_drift("CLIENT-1", "ZA-NG") is None


def test_main_block_exec():
    import runpy
    runpy.run_module("afriflow.domains.cib.processing.flink.flow_drift_detector", run_name="__main__")
