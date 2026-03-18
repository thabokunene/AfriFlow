"""
Comprehensive Unit Tests for Flow Drift Detector

This test suite provides comprehensive coverage for the Flow Drift Detector module,
including edge cases, exception scenarios, and integration points.

Test Categories:
1. Initialization Tests
2. Add Observation Tests
3. Detect Drift Tests
4. Edge Cases
5. Statistics Tests
6. Severity Calculation Tests
7. Multi-Client/Corridor Tests

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone, timedelta
from typing import List

import pytest
import statistics

from afriflow.domains.cib.processing.flink.flow_drift_detector import (
    FlowDriftDetector,
    FlowDriftAlert,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def detector() -> FlowDriftDetector:
    """Create a FlowDriftDetector with default settings."""
    return FlowDriftDetector(threshold_percentage=20.0, window_size=10)


@pytest.fixture
def detector_small_window() -> FlowDriftDetector:
    """Create a FlowDriftDetector with small window for faster tests."""
    return FlowDriftDetector(threshold_percentage=10.0, window_size=5)


def generate_series(base: float, count: int, noise: float = 0.0) -> List[float]:
    """Generate a series of values with optional noise."""
    rng = random.Random(42)
    return [base + rng.uniform(-noise, noise) for _ in range(count)]


def generate_drift_series(
    prev_base: float,
    curr_base: float,
    window: int,
    noise: float = 1.0
) -> List[float]:
    """Generate a series with drift between two periods."""
    rng = random.Random(42)
    prev_period = [prev_base + rng.uniform(-noise, noise) for _ in range(window)]
    curr_period = [curr_base + rng.uniform(-noise, noise) for _ in range(window)]
    return prev_period + curr_period


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Tests for FlowDriftDetector initialization."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        detector = FlowDriftDetector()
        
        assert detector.threshold_percentage == 20.0
        assert detector.window_size == 30
        assert detector.historical_data == {}
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        detector = FlowDriftDetector(
            threshold_percentage=15.0,
            window_size=20
        )
        
        assert detector.threshold_percentage == 15.0
        assert detector.window_size == 20
    
    def test_init_zero_threshold(self):
        """Test initialization with zero threshold."""
        detector = FlowDriftDetector(threshold_percentage=0.0)
        assert detector.threshold_percentage == 0.0
    
    def test_init_large_window(self):
        """Test initialization with large window."""
        detector = FlowDriftDetector(window_size=1000)
        assert detector.window_size == 1000


# ============================================================================
# Add Observation Tests
# ============================================================================

class TestAddObservation:
    """Tests for add_observation method."""
    
    def test_add_single_observation(self, detector):
        """Test adding a single observation."""
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        key = "CLIENT-1:ZA-NG"
        assert key in detector.historical_data
        assert len(detector.historical_data[key]) == 1
        assert detector.historical_data[key][0] == 100.0
    
    def test_add_multiple_observations(self, detector):
        """Test adding multiple observations."""
        for i in range(5):
            detector.add_observation("CLIENT-1", "ZA-NG", float(i * 100))
        
        key = "CLIENT-1:ZA-NG"
        assert len(detector.historical_data[key]) == 5
        assert detector.historical_data[key] == [0.0, 100.0, 200.0, 300.0, 400.0]
    
    def test_add_observation_with_timestamp(self, detector):
        """Test adding observation with explicit timestamp."""
        ts = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0, timestamp=ts)
        
        # Timestamp is logged but not stored in this implementation
        key = "CLIENT-1:ZA-NG"
        assert key in detector.historical_data
    
    def test_add_observation_without_timestamp(self, detector):
        """Test adding observation without timestamp (uses now)."""
        before = datetime.now(timezone.utc)
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        after = datetime.now(timezone.utc)
        
        # Should not raise
        assert "CLIENT-1:ZA-NG" in detector.historical_data
    
    def test_add_observation_data_truncation(self):
        """Test that old data is truncated."""
        detector = FlowDriftDetector(window_size=5)
        
        # Add more than 2 * window_size observations
        for i in range(15):
            detector.add_observation("CLIENT-1", "ZA-NG", float(i))
        
        key = "CLIENT-1:ZA-NG"
        # Should be truncated to window_size * 2
        assert len(detector.historical_data[key]) == 10
    
    def test_add_observation_multiple_clients(self, detector):
        """Test adding observations for multiple clients."""
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        detector.add_observation("CLIENT-2", "ZA-NG", 200.0)
        
        assert "CLIENT-1:ZA-NG" in detector.historical_data
        assert "CLIENT-2:ZA-NG" in detector.historical_data
        assert detector.historical_data["CLIENT-1:ZA-NG"][0] == 100.0
        assert detector.historical_data["CLIENT-2:ZA-NG"][0] == 200.0
    
    def test_add_observation_multiple_corridors(self, detector):
        """Test adding observations for multiple corridors."""
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        detector.add_observation("CLIENT-1", "ZA-KE", 200.0)
        
        assert "CLIENT-1:ZA-NG" in detector.historical_data
        assert "CLIENT-1:ZA-KE" in detector.historical_data


# ============================================================================
# Detect Drift Tests
# ============================================================================

class TestDetectDrift:
    """Tests for detect_drift method."""
    
    def test_no_data_returns_none(self, detector):
        """Test detect_drift with no data returns None."""
        result = detector.detect_drift("UNKNOWN", "ZA-NG")
        assert result is None
    
    def test_insufficient_data_returns_none(self, detector):
        """Test detect_drift with insufficient data returns None."""
        # Add less than window_size observations
        for i in range(5):
            detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        result = detector.detect_drift("CLIENT-1", "ZA-NG")
        assert result is None
    
    def test_detect_increase_drift(self, detector_small_window):
        """Test detection of increase drift."""
        # Create series with 50% increase
        series = generate_drift_series(100.0, 150.0, 5)
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        assert alert is not None
        assert alert.direction == "increase"
        assert alert.drift_percentage > 0
    
    def test_detect_decrease_drift(self, detector_small_window):
        """Test detection of decrease drift."""
        # Create series with 50% decrease
        series = generate_drift_series(100.0, 50.0, 5)
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        assert alert is not None
        assert alert.direction == "decrease"
        assert alert.drift_percentage < 0
    
    def test_no_drift_below_threshold(self, detector):
        """Test no alert when drift is below threshold."""
        # Create series with small change (below 20% threshold)
        series = generate_drift_series(100.0, 110.0, 10, noise=0.5)
        
        for value in series:
            detector.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector.detect_drift("CLIENT-1", "ZA-NG")
        assert alert is None
    
    def test_drift_exactly_at_threshold(self):
        """Test behavior when drift is exactly at threshold."""
        detector = FlowDriftDetector(threshold_percentage=20.0, window_size=5)
        
        # Create series with exactly 20% increase
        prev_period = [100.0] * 5
        curr_period = [120.0] * 5
        
        for value in prev_period + curr_period:
            detector.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector.detect_drift("CLIENT-1", "ZA-NG")
        # Should trigger at exactly threshold
        assert alert is not None
    
    def test_alert_attributes(self, detector_small_window):
        """Test that alert has correct attributes."""
        series = generate_drift_series(100.0, 150.0, 5)
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        assert alert.client_id == "CLIENT-1"
        assert alert.corridor == "ZA-NG"
        assert alert.direction in ["increase", "decrease"]
        assert isinstance(alert.drift_percentage, float)
        assert alert.severity in ["low", "medium", "high", "critical"]
        assert isinstance(alert.detected_at, datetime)
        assert alert.detected_at.tzinfo == timezone.utc


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_zero_previous_average(self, detector_small_window):
        """Test handling of zero previous average."""
        # All zeros in previous period
        series = [0.0] * 5 + [100.0] * 5
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        # Should return None (can't calculate drift from zero)
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        assert alert is None
    
    def test_empty_data_get_statistics(self, detector):
        """Test get_statistics with no data."""
        stats = detector.get_statistics("UNKNOWN", "ZA-NG")
        assert stats == {}
    
    def test_single_observation_statistics(self, detector):
        """Test statistics with single observation."""
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        stats = detector.get_statistics("CLIENT-1", "ZA-NG")
        
        assert stats["count"] == 1
        assert stats["mean"] == 100.0
        assert stats["median"] == 100.0
        assert stats["stdev"] == 0
        assert stats["min"] == 100.0
        assert stats["max"] == 100.0
    
    def test_empty_data_statistics(self, detector):
        """Test statistics with empty data."""
        # Access without adding data
        stats = detector.get_statistics("CLIENT-1", "ZA-NG")
        assert stats == {}
    
    def test_negative_values(self, detector_small_window):
        """Test handling of negative values."""
        series = [-100.0] * 5 + [-50.0] * 5
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        # Should detect drift (50% increase from -100 to -50)
        assert alert is not None
        assert alert.direction == "increase"
    
    def test_very_large_values(self, detector_small_window):
        """Test handling of very large values."""
        series = [1e10] * 5 + [1.5e10] * 5
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        assert alert is not None
    
    def test_mixed_positive_negative(self, detector_small_window):
        """Test handling of mixed positive and negative values."""
        series = [-100.0, 100.0, -100.0, 100.0, -100.0] * 2
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        # Should not raise
        stats = detector_small_window.get_statistics("CLIENT-1", "ZA-NG")
        assert stats["count"] == 10


# ============================================================================
# Severity Calculation Tests
# ============================================================================

class TestSeverityCalculation:
    """Tests for severity calculation."""
    
    def test_severity_critical(self, detector):
        """Test critical severity for >= 50% drift."""
        assert detector._calculate_severity(50.0) == "critical"
        assert detector._calculate_severity(100.0) == "critical"
        assert detector._calculate_severity(55.0) == "critical"
    
    def test_severity_high(self, detector):
        """Test high severity for 30-50% drift."""
        assert detector._calculate_severity(30.0) == "high"
        assert detector._calculate_severity(49.9) == "high"
        assert detector._calculate_severity(35.0) == "high"
    
    def test_severity_medium(self, detector):
        """Test medium severity for 20-30% drift."""
        assert detector._calculate_severity(20.0) == "medium"
        assert detector._calculate_severity(29.9) == "medium"
        assert detector._calculate_severity(25.0) == "medium"
    
    def test_severity_low(self, detector):
        """Test low severity for < 20% drift."""
        assert detector._calculate_severity(10.0) == "low"
        assert detector._calculate_severity(19.9) == "low"
        assert detector._calculate_severity(0.0) == "low"
    
    def test_severity_boundary_values(self, detector):
        """Test severity at boundary values."""
        # Exactly at boundaries
        assert detector._calculate_severity(50.0) == "critical"
        assert detector._calculate_severity(30.0) == "high"
        assert detector._calculate_severity(20.0) == "medium"


# ============================================================================
# Multi-Client/Corridor Tests
# ============================================================================

class TestMultiClientCorridor:
    """Tests for multiple clients and corridors."""
    
    def test_client_isolation(self, detector_small_window):
        """Test that clients are isolated."""
        # Add data for CLIENT-1
        for _ in range(10):
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        # Add different data for CLIENT-2
        for _ in range(10):
            detector_small_window.add_observation("CLIENT-2", "ZA-NG", 200.0)
        
        # CLIENT-1 should have no drift (stable at 100)
        alert1 = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        # CLIENT-2 should have no drift (stable at 200)
        alert2 = detector_small_window.detect_drift("CLIENT-2", "ZA-NG")
        
        assert alert1 is None
        assert alert2 is None
    
    def test_corridor_isolation(self, detector_small_window):
        """Test that corridors are isolated."""
        # Add stable data for ZA-NG
        for _ in range(10):
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        # Add drifting data for ZA-KE
        series = [100.0] * 5 + [200.0] * 5
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-KE", value)
        
        # ZA-NG should have no drift
        alert_ng = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        # ZA-KE should have drift
        alert_ke = detector_small_window.detect_drift("CLIENT-1", "ZA-KE")
        
        assert alert_ng is None
        assert alert_ke is not None
    
    def test_multiple_clients_multiple_corridors(self, detector_small_window):
        """Test complex scenario with multiple clients and corridors."""
        # CLIENT-1: ZA-NG stable, ZA-KE drifting
        for _ in range(10):
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        series = [100.0] * 5 + [200.0] * 5
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-KE", value)
        
        # CLIENT-2: ZA-NG drifting, ZA-KE stable
        series = [100.0] * 5 + [50.0] * 5
        for value in series:
            detector_small_window.add_observation("CLIENT-2", "ZA-NG", value)
        
        for _ in range(10):
            detector_small_window.add_observation("CLIENT-2", "ZA-KE", 100.0)
        
        # Verify isolation
        assert detector_small_window.detect_drift("CLIENT-1", "ZA-NG") is None
        assert detector_small_window.detect_drift("CLIENT-1", "ZA-KE") is not None
        assert detector_small_window.detect_drift("CLIENT-2", "ZA-NG") is not None
        assert detector_small_window.detect_drift("CLIENT-2", "ZA-KE") is None


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for get_statistics method."""
    
    def test_statistics_accuracy(self, detector):
        """Test that statistics are accurate."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for value in values:
            detector.add_observation("CLIENT-1", "ZA-NG", value)
        
        stats = detector.get_statistics("CLIENT-1", "ZA-NG")
        
        assert stats["count"] == 5
        assert stats["mean"] == statistics.mean(values)
        assert stats["median"] == statistics.median(values)
        assert stats["stdev"] == statistics.stdev(values)
        assert stats["min"] == min(values)
        assert stats["max"] == max(values)
    
    def test_statistics_two_values_stdev(self, detector):
        """Test stdev calculation with two values."""
        detector.add_observation("CLIENT-1", "ZA-NG", 10.0)
        detector.add_observation("CLIENT-1", "ZA-NG", 20.0)
        
        stats = detector.get_statistics("CLIENT-1", "ZA-NG")
        
        assert stats["count"] == 2
        assert stats["stdev"] > 0
    
    def test_statistics_single_value_stdev(self, detector):
        """Test stdev is 0 with single value."""
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0)
        
        stats = detector.get_statistics("CLIENT-1", "ZA-NG")
        
        assert stats["count"] == 1
        assert stats["stdev"] == 0


# ============================================================================
# Timezone Tests
# ============================================================================

class TestTimezone:
    """Tests for timezone handling."""
    
    def test_alert_timestamp_timezone(self, detector_small_window):
        """Test that alert timestamp is timezone-aware."""
        series = generate_drift_series(100.0, 150.0, 5)
        
        for value in series:
            detector_small_window.add_observation("CLIENT-1", "ZA-NG", value)
        
        alert = detector_small_window.detect_drift("CLIENT-1", "ZA-NG")
        
        assert alert.detected_at.tzinfo is not None
        assert alert.detected_at.tzinfo == timezone.utc
    
    def test_add_observation_with_different_timezone(self, detector):
        """Test adding observation with explicit timezone."""
        ts = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        
        # Should not raise
        detector.add_observation("CLIENT-1", "ZA-NG", 100.0, timestamp=ts)
        
        assert "CLIENT-1:ZA-NG" in detector.historical_data


# ============================================================================
# Dataclass Tests
# ============================================================================

class TestDataclass:
    """Tests for FlowDriftAlert dataclass."""
    
    def test_alert_creation(self):
        """Test creating FlowDriftAlert."""
        alert = FlowDriftAlert(
            client_id="CLIENT-1",
            corridor="ZA-NG",
            drift_percentage=25.5,
            direction="increase",
            severity="medium",
            detected_at=datetime.now(timezone.utc),
        )
        
        assert alert.client_id == "CLIENT-1"
        assert alert.corridor == "ZA-NG"
        assert alert.drift_percentage == 25.5
        assert alert.direction == "increase"
        assert alert.severity == "medium"
    
    def test_alert_to_string(self):
        """Test alert string representation."""
        alert = FlowDriftAlert(
            client_id="CLIENT-1",
            corridor="ZA-NG",
            drift_percentage=25.5,
            direction="increase",
            severity="medium",
            detected_at=datetime.now(timezone.utc),
        )
        
        # Should have string representation
        assert str(alert) is not None
        assert "CLIENT-1" in str(alert)
