from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from afriflow.domains.cell.processing.flink.expansion_detector import (
    ExpansionDetector,
)


def test_detects_new_country_above_threshold():
    det = ExpansionDetector(min_sim_threshold=5, time_window_days=30)
    ts_old = datetime.now(timezone.utc) - timedelta(days=60)
    ts_new = datetime.now(timezone.utc) - timedelta(days=5)
    det.add_activation("CLIENT-1", "ZA", 20, timestamp=ts_old)
    det.add_activation("CLIENT-1", "NG", 6, timestamp=ts_new)
    signals = det.detect_expansion("CLIENT-1")
    assert len(signals) == 1
    s = signals[0]
    assert s.client_id == "CLIENT-1"
    assert s.new_country == "NG"
    assert s.sim_count == 6
    assert s.confidence > 0
    assert s.detected_at.tzinfo == timezone.utc


def test_no_signal_below_threshold():
    det = ExpansionDetector(min_sim_threshold=10, time_window_days=30)
    det.add_activation("CLIENT-1", "NG", 9, timestamp=datetime.now(timezone.utc))
    assert det.detect_expansion("CLIENT-1") == []


def test_historical_country_filtered():
    det = ExpansionDetector(min_sim_threshold=1, time_window_days=30)
    ts_old = datetime.now(timezone.utc) - timedelta(days=40)
    ts_new = datetime.now(timezone.utc) - timedelta(days=5)
    det.add_activation("CLIENT-1", "ZA", 5, timestamp=ts_old)
    det.add_activation("CLIENT-1", "ZA", 5, timestamp=ts_new)
    assert det.detect_expansion("CLIENT-1") == []


def test_confidence_adjustment_high_risk():
    det = ExpansionDetector(min_sim_threshold=1, time_window_days=30)
    det.add_activation("CLIENT-1", "CD", 100, timestamp=datetime.now(timezone.utc))
    s = det.detect_expansion("CLIENT-1")[0]
    assert 0 < s.confidence <= 100
    assert s.confidence < 100


def test_get_client_footprint():
    det = ExpansionDetector()
    det.add_activation("CLIENT-1", "ZA", 3)
    det.add_activation("CLIENT-1", "ZA", 2)
    det.add_activation("CLIENT-1", "NG", 4)
    fp = det.get_client_footprint("CLIENT-1")
    assert fp["ZA"] == 5 and fp["NG"] == 4
