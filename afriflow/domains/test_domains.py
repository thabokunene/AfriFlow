"""
@file test_domains.py
@description Comprehensive unit test suite for the shared domain components and configurations in AfriFlow.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Unit Tests for Domains Module.

We test all domain modules to ensure correctness,
error handling, and backward compatibility.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Pytest framework for running unit and integration tests
import pytest
# Standard library for interacting with the operating system (e.g., env variables)
import os
# Datetime utilities for time-based testing and validation
from datetime import datetime, timedelta, timezone
# Typing hints for improved code clarity and static analysis
from typing import Dict, Any

# Core application configuration management and singleton access
from afriflow.domains.shared.config import AppConfig, get_config, reset_config
# Currency and country mapping utilities for multi-market data processing
from afriflow.domains.shared.currency_map import (
    get_currency_for_country,
    get_country_for_currency,
    is_major_currency,
    is_african_currency,
)
# Deflation factors for SIM usage normalization in telecom analytics
from afriflow.domains.shared.sim_deflation_factors import (
    get_deflation_factor,
    get_deflation_confidence,
    get_avg_sims_per_person,
)
# System-wide constants for messaging, formats, and business thresholds
from afriflow.domains.shared.constants import (
    ISO_DATE_FORMAT,
    TOPIC_CIB_PAYMENTS,
    MATCH_THRESHOLD,
)


class TestConfig:
    """
    Test suite for the configuration management module.
    Ensures that environment variables are correctly loaded and validated.
    """

    def setup_method(self) -> None:
        """
        Setup hook that runs before each test method in this class.
        Resets the configuration singleton to ensure test isolation.
        """
        reset_config()

    def test_config_load_defaults(self) -> None:
        """
        Verifies that the configuration loads default values correctly
        when no environment overrides are provided.
        """
        # Load the configuration object with defaults
        config = AppConfig.load()

        # Assert default environment and connectivity settings
        assert config.env == "dev"
        assert config.kafka_broker == "localhost:9092"
        assert "localhost:8081" in config.schema_registry_url

    def test_config_from_env(self, monkeypatch: Any) -> None:
        """
        Verifies that environment variables correctly override default
        configuration values using pytest's monkeypatch.
        
        :param monkeypatch: Pytest fixture for mocking environment variables.
        """
        # Mock environment variables for production scenario
        monkeypatch.setenv("APP_ENV", "prod")
        monkeypatch.setenv("KAFKA_BROKER", "kafka.prod:9092")

        # Reload configuration to pick up mocked environment
        config = AppConfig.load()

        # Assert that the overrides were applied
        assert config.env == "prod"
        assert config.kafka_broker == "kafka.prod:9092"

    def test_config_validate(self) -> None:
        """
        Tests the configuration validation logic to ensure it doesn't 
        raise exceptions for valid default setups.
        """
        config = AppConfig.load()
        # Should complete without raising validation errors
        config.validate()

    def test_get_config_singleton(self) -> None:
        """
        Ensures that get_config implements a singleton pattern correctly.
        """
        # Retrieve two instances and verify they are the same object in memory
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config(self) -> None:
        """
        Verifies that reset_config clears the current singleton instance.
        """
        # Initialize the config
        get_config()
        # Reset the singleton state
        reset_config()

        # Verify that a subsequent call creates a new instance
        new_config = get_config()
        assert new_config is not None


class TestCurrencyMap:
    """
    Test suite for currency and country mapping logic.
    Ensures accuracy in cross-border financial data processing.
    """

    def test_get_currency_for_country(self) -> None:
        """
        Tests the mapping of ISO country codes to their primary currencies.
        """
        # Test common African markets: South Africa, Nigeria, Kenya
        assert get_currency_for_country("ZA") == "ZAR"
        assert get_currency_for_country("NG") == "NGN"
        assert get_currency_for_country("KE") == "KES"

    def test_get_currency_unknown_country(self) -> None:
        """
        Ensures that unknown country codes fallback to USD as a safe default.
        """
        assert get_currency_for_country("XX") == "USD"

    def test_get_country_for_currency(self) -> None:
        """
        Tests the reverse mapping from currency codes back to primary countries.
        """
        assert get_country_for_currency("ZAR") == "ZA"
        assert get_country_for_currency("NGN") == "NG"

    def test_is_major_currency(self) -> None:
        """Test major currency detection."""
        assert is_major_currency("USD") is True
        assert is_major_currency("EUR") is True
        assert is_major_currency("ZAR") is True
        assert is_major_currency("TZS") is False

    def test_is_african_currency(self) -> None:
        """Test African currency detection."""
        assert is_african_currency("ZAR") is True
        assert is_african_currency("NGN") is True
        assert is_african_currency("USD") is False
        assert is_african_currency("EUR") is False


class TestSimDeflationFactors:
    """Tests for SIM deflation factors module."""

    def test_get_deflation_factor_known_country(self) -> None:
        """Test deflation factor for known countries."""
        assert get_deflation_factor("ZA") == 0.77
        assert get_deflation_factor("NG") == 0.36
        assert get_deflation_factor("KE") == 0.48

    def test_get_deflation_factor_unknown_country(self) -> None:
        """Test deflation factor for unknown countries."""
        assert get_deflation_factor("XX") == 0.50

    def test_get_deflation_confidence(self) -> None:
        """Test confidence levels."""
        assert get_deflation_confidence("ZA") == "high"
        assert get_deflation_confidence("NG") == "medium"
        assert get_deflation_confidence("ZM") == "low"

    def test_get_avg_sims_per_person(self) -> None:
        """Test average SIMs per person."""
        assert get_avg_sims_per_person("ZA") == 1.3
        assert get_avg_sims_per_person("NG") == 2.8

    def test_invalid_country_code(self) -> None:
        """Test invalid country code handling."""
        with pytest.raises(ValueError):
            get_deflation_factor("")


class TestConstants:
    """Tests for constants module."""

    def test_date_formats(self) -> None:
        """Test date format constants."""
        assert ISO_DATE_FORMAT == "%Y-%m-%d"
        assert isinstance(ISO_DATE_FORMAT, str)

    def test_kafka_topics(self) -> None:
        """Test Kafka topic constants."""
        assert TOPIC_CIB_PAYMENTS == "cib.payments.v1"
        assert isinstance(TOPIC_CIB_PAYMENTS, str)

    def test_match_threshold(self) -> None:
        """Test entity resolution threshold."""
        assert MATCH_THRESHOLD == 85
        assert isinstance(MATCH_THRESHOLD, int)


class TestFlowDriftDetector:
    """Tests for flow drift detector."""

    def test_add_observation(self) -> None:
        """Test adding observations."""
        from afriflow.domains.cib.processing.flink.flow_drift_detector import (
            FlowDriftDetector,
        )

        detector = FlowDriftDetector()
        detector.add_observation("CLIENT-001", "ZA-NG", 100000)

        stats = detector.get_statistics("CLIENT-001", "ZA-NG")
        assert stats["count"] == 1

    def test_detect_drift_no_drift(self) -> None:
        """Test no drift detection when stable."""
        from afriflow.domains.cib.processing.flink.flow_drift_detector import (
            FlowDriftDetector,
        )

        detector = FlowDriftDetector(threshold_percentage=20.0)

        # Add stable data
        for _ in range(60):
            detector.add_observation("CLIENT-001", "ZA-NG", 100000)

        alert = detector.detect_drift("CLIENT-001", "ZA-NG")
        assert alert is None

    def test_detect_drift_increase(self) -> None:
        """Test drift detection on increase."""
        from afriflow.domains.cib.processing.flink.flow_drift_detector import (
            FlowDriftDetector,
        )

        detector = FlowDriftDetector(threshold_percentage=20.0)

        # Add low values
        for _ in range(30):
            detector.add_observation("CLIENT-001", "ZA-NG", 100000)

        # Add high values
        for _ in range(30):
            detector.add_observation("CLIENT-001", "ZA-NG", 150000)

        alert = detector.detect_drift("CLIENT-001", "ZA-NG")
        assert alert is not None
        assert alert.direction == "increase"

    def test_get_statistics(self) -> None:
        """Test statistics calculation."""
        from afriflow.domains.cib.processing.flink.flow_drift_detector import (
            FlowDriftDetector,
        )

        detector = FlowDriftDetector()

        for value in [100, 200, 300]:
            detector.add_observation("CLIENT-001", "ZA-NG", value)

        stats = detector.get_statistics("CLIENT-001", "ZA-NG")
        assert stats["count"] == 3
        assert stats["mean"] == 200
        assert stats["min"] == 100
        assert stats["max"] == 300


class TestExpansionDetector:
    """Tests for expansion detector."""

    def test_add_activation(self) -> None:
        """Test adding activations."""
        from afriflow.domains.cell.processing.flink.expansion_detector import (
            ExpansionDetector,
        )

        detector = ExpansionDetector()
        detector.add_activation("CLIENT-001", "ZA", 50)

        footprint = detector.get_client_footprint("CLIENT-001")
        assert footprint.get("ZA", 0) == 50

    def test_detect_expansion(self) -> None:
        """Test expansion detection."""
        from afriflow.domains.cell.processing.flink.expansion_detector import (
            ExpansionDetector,
        )

        detector = ExpansionDetector(min_sim_threshold=10)

        # Add historical data
        detector.add_activation(
            "CLIENT-001", "ZA", 50,
            datetime.now(timezone.utc) - timedelta(days=60)
        )

        # Add new country activation
        detector.add_activation("CLIENT-001", "NG", 100)

        signals = detector.detect_expansion("CLIENT-001")
        assert len(signals) == 1
        assert signals[0].new_country == "NG"

    def test_no_expansion_below_threshold(self) -> None:
        """Test no expansion below threshold."""
        from afriflow.domains.cell.processing.flink.expansion_detector import (
            ExpansionDetector,
        )

        detector = ExpansionDetector(min_sim_threshold=50)

        # Add historical data
        detector.add_activation(
            "CLIENT-001", "ZA", 50,
            datetime.now(timezone.utc) - timedelta(days=60)
        )

        # Add new country below threshold
        detector.add_activation("CLIENT-001", "NG", 20)

        signals = detector.detect_expansion("CLIENT-001")
        assert len(signals) == 0

    def test_get_client_footprint(self) -> None:
        """Test client footprint retrieval."""
        from afriflow.domains.cell.processing.flink.expansion_detector import (
            ExpansionDetector,
        )

        detector = ExpansionDetector()

        detector.add_activation("CLIENT-001", "ZA", 50)
        detector.add_activation("CLIENT-001", "NG", 100)
        detector.add_activation("CLIENT-001", "KE", 75)

        footprint = detector.get_client_footprint("CLIENT-001")
        assert footprint["ZA"] == 50
        assert footprint["NG"] == 100
        assert footprint["KE"] == 75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
