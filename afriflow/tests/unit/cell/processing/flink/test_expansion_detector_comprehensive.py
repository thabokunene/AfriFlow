"""
Comprehensive Unit Tests for Expansion Detector

This test suite provides comprehensive coverage for the Expansion Detector module,
including edge cases, exception scenarios, and integration points.

Test Categories:
1. Initialization Tests
2. Add Activation Tests
3. Detect Expansion Tests
4. Edge Cases
5. Confidence Calculation Tests
6. Client Footprint Tests
7. Processor Class Tests (RBAC)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from afriflow.domains.cell.processing.flink.expansion_detector import (
    ExpansionDetector,
    ExpansionSignal,
    Processor,
)
from afriflow.domains.shared.config import AppConfig


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def detector() -> ExpansionDetector:
    """Create an ExpansionDetector with default settings."""
    return ExpansionDetector(min_sim_threshold=10, time_window_days=30)


@pytest.fixture
def detector_low_threshold() -> ExpansionDetector:
    """Create an ExpansionDetector with low threshold for testing."""
    return ExpansionDetector(min_sim_threshold=1, time_window_days=30)


@pytest.fixture
def sample_timestamps():
    """Provide sample timestamps for testing."""
    now = datetime.now(timezone.utc)
    return {
        "now": now,
        "5_days_ago": now - timedelta(days=5),
        "15_days_ago": now - timedelta(days=15),
        "35_days_ago": now - timedelta(days=35),
        "60_days_ago": now - timedelta(days=60),
        "90_days_ago": now - timedelta(days=90),
    }


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Tests for ExpansionDetector initialization."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        detector = ExpansionDetector()
        
        assert detector.min_sim_threshold == 10
        assert detector.time_window_days == 30
        assert len(detector.activations) == 0
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        detector = ExpansionDetector(
            min_sim_threshold=5,
            time_window_days=60
        )
        
        assert detector.min_sim_threshold == 5
        assert detector.time_window_days == 60
    
    def test_init_zero_threshold(self):
        """Test initialization with zero threshold."""
        detector = ExpansionDetector(min_sim_threshold=0)
        assert detector.min_sim_threshold == 0


# ============================================================================
# Add Activation Tests
# ============================================================================

class TestAddActivation:
    """Tests for add_activation method."""
    
    def test_add_single_activation(self, detector):
        """Test adding a single activation."""
        detector.add_activation("CLIENT-1", "NG", 50)
        
        assert "CLIENT-1" in detector.activations
        assert len(detector.activations["CLIENT-1"]) == 1
        assert detector.activations["CLIENT-1"][0]["country"] == "NG"
        assert detector.activations["CLIENT-1"][0]["sim_count"] == 50
    
    def test_add_activation_with_timestamp(self, detector, sample_timestamps):
        """Test adding activation with explicit timestamp."""
        detector.add_activation(
            "CLIENT-1",
            "NG",
            50,
            timestamp=sample_timestamps["15_days_ago"]
        )
        
        activation = detector.activations["CLIENT-1"][0]
        assert activation["timestamp"] == sample_timestamps["15_days_ago"]
    
    def test_add_activation_without_timestamp(self, detector):
        """Test adding activation without timestamp (uses now)."""
        before = datetime.now(timezone.utc)
        detector.add_activation("CLIENT-1", "NG", 50)
        after = datetime.now(timezone.utc)
        
        activation = detector.activations["CLIENT-1"][0]
        assert before <= activation["timestamp"] <= after
    
    def test_add_multiple_activations_same_client(self, detector):
        """Test adding multiple activations for same client."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-1", "KE", 30)
        detector.add_activation("CLIENT-1", "GH", 20)
        
        assert len(detector.activations["CLIENT-1"]) == 3
    
    def test_add_multiple_activations_same_country(self, detector):
        """Test adding multiple activations for same country."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-1", "NG", 30)
        
        activations = detector.activations["CLIENT-1"]
        assert len(activations) == 2
        assert activations[0]["country"] == "NG"
        assert activations[1]["country"] == "NG"
    
    def test_add_activations_multiple_clients(self, detector):
        """Test adding activations for multiple clients."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-2", "KE", 30)
        detector.add_activation("CLIENT-3", "GH", 20)
        
        assert "CLIENT-1" in detector.activations
        assert "CLIENT-2" in detector.activations
        assert "CLIENT-3" in detector.activations


# ============================================================================
# Detect Expansion Tests
# ============================================================================

class TestDetectExpansion:
    """Tests for detect_expansion method."""
    
    def test_no_activations_returns_empty(self, detector):
        """Test detect_expansion with no activations."""
        signals = detector.detect_expansion("UNKNOWN")
        assert signals == []
    
    def test_no_new_countries_returns_empty(self, detector, sample_timestamps):
        """Test detect_expansion when no new countries."""
        # Add historical presence
        detector.add_activation(
            "CLIENT-1", "NG", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        # Add recent activation in same country
        detector.add_activation(
            "CLIENT-1", "NG", 30,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        assert signals == []
    
    def test_new_country_above_threshold(self, detector, sample_timestamps):
        """Test detection of new country above threshold."""
        # Historical presence
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        # New country above threshold
        detector.add_activation(
            "CLIENT-1", "NG", 15,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        
        assert len(signals) == 1
        assert signals[0].new_country == "NG"
        assert signals[0].sim_count == 15
    
    def test_new_country_below_threshold(self, detector, sample_timestamps):
        """Test no detection when below threshold."""
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        detector.add_activation(
            "CLIENT-1", "NG", 5,  # Below threshold of 10
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        assert signals == []
    
    def test_multiple_new_countries(self, detector_low_threshold, sample_timestamps):
        """Test detection of multiple new countries."""
        # Historical presence
        detector_low_threshold.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        # Multiple new countries
        detector_low_threshold.add_activation(
            "CLIENT-1", "NG", 5,
            timestamp=sample_timestamps["5_days_ago"]
        )
        detector_low_threshold.add_activation(
            "CLIENT-1", "KE", 3,
            timestamp=sample_timestamps["3_days_ago"]
        )
        
        signals = detector_low_threshold.detect_expansion("CLIENT-1")
        
        assert len(signals) == 2
        countries = {s.new_country for s in signals}
        assert countries == {"NG", "KE"}
    
    def test_activations_outside_window_ignored(self, detector, sample_timestamps):
        """Test that activations outside time window are ignored."""
        # Old activation outside 30-day window
        detector.add_activation(
            "CLIENT-1", "NG", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        assert signals == []


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_exactly_at_threshold(self, detector, sample_timestamps):
        """Test behavior when exactly at threshold."""
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        # Exactly at threshold (10)
        detector.add_activation(
            "CLIENT-1", "NG", 10,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        
        # Should detect (>= threshold)
        assert len(signals) == 1
    
    def test_zero_sim_count(self, detector, sample_timestamps):
        """Test handling of zero SIM count."""
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        detector.add_activation(
            "CLIENT-1", "NG", 0,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        # Zero is below threshold
        assert signals == []
    
    def test_very_large_sim_count(self, detector, sample_timestamps):
        """Test handling of very large SIM count."""
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        detector.add_activation(
            "CLIENT-1", "NG", 1000000,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        signals = detector.detect_expansion("CLIENT-1")
        
        assert len(signals) == 1
        assert signals[0].sim_count == 1000000
    
    def test_empty_client_id(self, detector):
        """Test handling of empty client ID."""
        detector.add_activation("", "NG", 50)
        
        # Should not raise
        signals = detector.detect_expansion("")
        assert isinstance(signals, list)
    
    def test_special_characters_in_country(self, detector, sample_timestamps):
        """Test handling of special characters in country code."""
        detector.add_activation(
            "CLIENT-1", "ZA", 50,
            timestamp=sample_timestamps["60_days_ago"]
        )
        detector.add_activation(
            "CLIENT-1", "NG-1", 50,
            timestamp=sample_timestamps["5_days_ago"]
        )
        
        # Should detect (no validation on country format)
        signals = detector.detect_expansion("CLIENT-1")
        assert len(signals) == 1


# ============================================================================
# Confidence Calculation Tests
# ============================================================================

class TestConfidenceCalculation:
    """Tests for confidence calculation."""
    
    def test_confidence_base_calculation(self, detector_low_threshold):
        """Test base confidence calculation."""
        detector_low_threshold.add_activation("CLIENT-1", "NG", 100, timestamp=datetime.now(timezone.utc))
        
        signals = detector_low_threshold.detect_expansion("CLIENT-1")
        
        # 100 SIMs = 100% confidence (capped)
        assert signals[0].confidence == 100.0
    
    def test_confidence_low_sim_count(self, detector_low_threshold):
        """Test confidence with low SIM count."""
        detector_low_threshold.add_activation("CLIENT-1", "NG", 10, timestamp=datetime.now(timezone.utc))
        
        signals = detector_low_threshold.detect_expansion("CLIENT-1")
        
        # 10 SIMs = 10% confidence
        assert signals[0].confidence == 10.0
    
    def test_confidence_high_risk_country(self, detector_low_threshold):
        """Test confidence adjustment for high-risk countries."""
        # CD (DRC) is a high-risk country
        detector_low_threshold.add_activation("CLIENT-1", "CD", 100, timestamp=datetime.now(timezone.utc))
        
        signals = detector_low_threshold.detect_expansion("CLIENT-1")
        
        # Should be reduced by 20% for high-risk
        assert signals[0].confidence < 100.0
        assert signals[0].confidence == 80.0  # 100 * 0.8
    
    def test_confidence_not_high_risk_country(self, detector_low_threshold):
        """Test confidence for non-high-risk countries."""
        detector_low_threshold.add_activation("CLIENT-1", "ZA", 100, timestamp=datetime.now(timezone.utc))
        
        signals = detector_low_threshold.detect_expansion("CLIENT-1")
        
        # ZA is not high-risk, should be 100%
        assert signals[0].confidence == 100.0
    
    def test_confidence_all_high_risk_countries(self, detector_low_threshold):
        """Test all high-risk countries."""
        high_risk = {"CD", "SS", "SO"}
        
        for country in high_risk:
            detector_low_threshold.add_activation("CLIENT-1", country, 100, timestamp=datetime.now(timezone.utc))
            signals = detector_low_threshold.detect_expansion("CLIENT-1")
            
            assert signals[0].confidence < 100.0


# ============================================================================
# Client Footprint Tests
# ============================================================================

class TestClientFootprint:
    """Tests for get_client_footprint method."""
    
    def test_empty_footprint(self, detector):
        """Test footprint for unknown client."""
        footprint = detector.get_client_footprint("UNKNOWN")
        assert footprint == {}
    
    def test_single_country_footprint(self, detector):
        """Test footprint with single country."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-1", "NG", 30)
        
        footprint = detector.get_client_footprint("CLIENT-1")
        
        assert footprint == {"NG": 80}
    
    def test_multiple_countries_footprint(self, detector):
        """Test footprint with multiple countries."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-1", "KE", 30)
        detector.add_activation("CLIENT-1", "GH", 20)
        
        footprint = detector.get_client_footprint("CLIENT-1")
        
        assert footprint["NG"] == 50
        assert footprint["KE"] == 30
        assert footprint["GH"] == 20
    
    def test_footprint_aggregates_same_country(self, detector):
        """Test that footprint aggregates same country."""
        detector.add_activation("CLIENT-1", "NG", 50)
        detector.add_activation("CLIENT-1", "NG", 30)
        detector.add_activation("CLIENT-1", "NG", 20)
        
        footprint = detector.get_client_footprint("CLIENT-1")
        
        assert footprint["NG"] == 100


# ============================================================================
# Signal Dataclass Tests
# ============================================================================

class TestExpansionSignal:
    """Tests for ExpansionSignal dataclass."""
    
    def test_signal_creation(self):
        """Test creating ExpansionSignal."""
        signal = ExpansionSignal(
            client_id="CLIENT-1",
            new_country="NG",
            sim_count=50,
            confidence=85.5,
            detected_at=datetime.now(timezone.utc),
        )
        
        assert signal.client_id == "CLIENT-1"
        assert signal.new_country == "NG"
        assert signal.sim_count == 50
        assert signal.confidence == 85.5
    
    def test_signal_timezone_aware(self):
        """Test that signal timestamp is timezone-aware."""
        signal = ExpansionSignal(
            client_id="CLIENT-1",
            new_country="NG",
            sim_count=50,
            confidence=85.5,
            detected_at=datetime.now(timezone.utc),
        )
        
        assert signal.detected_at.tzinfo is not None
        assert signal.detected_at.tzinfo == timezone.utc


# ============================================================================
# Processor Class Tests (RBAC)
# ============================================================================

class TestProcessorRBAC:
    """Tests for Processor class RBAC functionality."""
    
    def test_processor_configure_dev(self):
        """Test processor configuration in dev environment."""
        config = AppConfig(
            env="dev",
            kafka_broker="localhost:9092",
            schema_registry_url="http://localhost:8081",
            db_url="sqlite:///test.db"
        )
        
        processor = Processor(config)
        
        assert "analyst" in processor._allowed_roles
        assert "system" in processor._allowed_roles
        assert "service" in processor._allowed_roles
    
    def test_processor_configure_prod(self):
        """Test processor configuration in prod environment."""
        config = AppConfig(
            env="prod",
            kafka_broker="localhost:9092",
            schema_registry_url="http://localhost:8081",
            db_url="sqlite:///test.db"
        )
        
        processor = Processor(config)
        
        assert "analyst" not in processor._allowed_roles
        assert "system" in processor._allowed_roles
        assert "service" in processor._allowed_roles
    
    def test_processor_validate_valid_record(self):
        """Test processor validation with valid record."""
        processor = Processor()
        processor.configure()
        
        record = {
            "access_role": "system",
            "source": "test",
            "data": "test data"
        }
        
        # Should not raise
        processor.validate(record)
    
    def test_processor_validate_invalid_role(self):
        """Test processor validation with invalid role."""
        processor = Processor()
        processor.configure()
        
        record = {
            "access_role": "guest",
            "source": "test",
        }
        
        with pytest.raises(PermissionError, match="access_role not permitted"):
            processor.validate(record)
    
    def test_processor_validate_missing_source(self):
        """Test processor validation with missing source."""
        processor = Processor()
        processor.configure()
        
        record = {
            "access_role": "system",
        }
        
        with pytest.raises(ValueError, match="source is required"):
            processor.validate(record)
    
    def test_processor_validate_non_dict(self):
        """Test processor validation with non-dict record."""
        processor = Processor()
        processor.configure()
        
        with pytest.raises(TypeError, match="record must be a dict"):
            processor.validate("not a dict")
    
    def test_processor_validate_record_too_large(self):
        """Test processor validation with oversized record."""
        processor = Processor()
        processor.configure()
        
        # Create record larger than 100KB
        large_record = {
            "access_role": "system",
            "source": "test",
            "data": "x" * 200000
        }
        
        with pytest.raises(ValueError, match="record too large"):
            processor.validate(large_record)
    
    def test_processor_process_sync(self):
        """Test processor sync processing."""
        processor = Processor()
        processor.configure()
        
        record = {
            "access_role": "system",
            "source": "test",
            "data": "test"
        }
        
        result = processor.process_sync(record)
        
        assert result["processed"] is True
        assert result["data"] == "test"
    
    def test_processor_process_sync_invalid_record(self):
        """Test processor sync processing with invalid record."""
        processor = Processor()
        processor.configure()
        
        record = {
            "access_role": "guest",
            "source": "test",
        }
        
        with pytest.raises(PermissionError):
            processor.process_sync(record)
