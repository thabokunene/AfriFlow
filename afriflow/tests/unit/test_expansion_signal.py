"""
tests/unit/test_expansion_signal.py

Unit tests for cross-domain expansion detection signal with
comprehensive error-path and edge-case coverage.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from afriflow.integration.cross_domain_signals.expansion_signal import (
    ExpansionDetector,
    ExpansionSignal,
)
from afriflow.config.settings import Settings, ExpansionThresholds
from afriflow.exceptions import SignalDetectionError, ConfigurationError


class TestExpansionSignal:
    """Test ExpansionSignal dataclass functionality."""

    def test_expansion_signal_creation(self) -> None:
        """Test creating ExpansionSignal with all fields."""
        signal = ExpansionSignal(
            golden_id="GLD-001",
            client_name="Test Corp",
            expansion_country="KE",
            confidence_score=75.5,
            estimated_opportunity_zar=50000.0,
            cib_new_corridor_payments=5,
            cib_corridor_value=5000000.0,
            cell_new_sim_activations=50,
            forex_new_currency_trades=2,
            insurance_new_countries=0,
            pbb_new_countries=0,
            forex_hedging_in_place=False,
            insurance_coverage_in_place=False,
            recommended_products=["FX hedging", "Trade finance"],
            urgency="HIGH"
        )
        assert signal.golden_id == "GLD-001"
        assert signal.expansion_country == "KE"
        assert signal.confidence_score == 75.5

    def test_expansion_signal_to_rm_alert(self) -> None:
        """Test converting signal to RM alert format."""
        signal = ExpansionSignal(
            golden_id="GLD-001",
            client_name="Shoprite Holdings",
            expansion_country="KE",
            confidence_score=85.0,
            estimated_opportunity_zar=100000.0,
            cib_new_corridor_payments=10,
            cib_corridor_value=10000000.0,
            cell_new_sim_activations=100,
            forex_new_currency_trades=5,
            insurance_new_countries=0,
            pbb_new_countries=0,
            forex_hedging_in_place=False,
            insurance_coverage_in_place=False,
            recommended_products=["FX hedging"],
            urgency="HIGH"
        )
        alert = signal.to_rm_alert()
        assert "Expansion Alert" in alert["Subject"]
        assert "Shoprite Holdings" in alert["Subject"]
        assert "KE" in alert["Subject"]
        assert alert["Priority"] == "Urgent"  # confidence >= 80

    def test_expansion_signal_low_priority_alert(self) -> None:
        """Test alert priority for lower confidence."""
        signal = ExpansionSignal(
            golden_id="GLD-001",
            client_name="Test Corp",
            expansion_country="NG",
            confidence_score=65.0,
            estimated_opportunity_zar=25000.0,
            cib_new_corridor_payments=3,
            cib_corridor_value=2000000.0,
            cell_new_sim_activations=20,
            forex_new_currency_trades=0,
            insurance_new_countries=0,
            pbb_new_countries=0,
            forex_hedging_in_place=False,
            insurance_coverage_in_place=False,
            recommended_products=[],
            urgency="MEDIUM"
        )
        alert = signal.to_rm_alert()
        assert alert["Priority"] == "High"  # confidence < 80


class TestExpansionDetector:
    """Test expansion detector functionality and error handling."""

    @pytest.fixture
    def detector(self) -> ExpansionDetector:
        """Create default expansion detector."""
        return ExpansionDetector()

    @pytest.fixture
    def detector_with_custom_settings(self) -> ExpansionDetector:
        """Create detector with custom thresholds."""
        custom_thresholds = ExpansionThresholds(
            min_cib_payments_for_signal=2,
            min_cib_value_for_signal=500000.0,
            min_sim_activations_for_signal=10
        )
        custom_settings = Settings(expansion_thresholds=custom_thresholds)
        return ExpansionDetector(settings=custom_settings)

    @pytest.fixture
    def client_metadata(self) -> dict:
        """Create sample client metadata."""
        return {
            "CIB-1001": {
                "client_name": "Shoprite Holdings",
                "tier": "Platinum",
                "relationship_manager": "RM-JSmith",
                "country": "ZA"
            },
            "CIB-1002": {
                "client_name": "MTN Group",
                "tier": "Gold",
                "relationship_manager": "RM-AJones",
                "country": "ZA"
            }
        }

    # ==================== Initialization Tests ====================

    def test_detector_initialization(self, detector: ExpansionDetector) -> None:
        """Test detector initializes with default settings."""
        assert detector.thresholds is not None
        assert detector.thresholds.min_cib_payments_for_signal >= 1

    def test_detector_with_custom_settings(
        self, detector_with_custom_settings: ExpansionDetector
    ) -> None:
        """Test detector with custom settings."""
        thresholds = detector_with_custom_settings.thresholds
        assert thresholds.min_cib_payments_for_signal == 2
        assert thresholds.min_sim_activations_for_signal == 10

    def test_detector_with_none_settings(self) -> None:
        """Test detector loads default settings when None passed."""
        detector = ExpansionDetector(settings=None)
        assert detector.thresholds is not None

    def test_detector_initialization_error(self) -> None:
        """Test detector handles settings load error."""
        with patch(
            "afriflow.integration.cross_domain_signals.expansion_signal.get_settings",
            side_effect=Exception("Settings load failed")
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                ExpansionDetector()
            assert "Failed to load expansion detector settings" in str(exc_info.value)

    # ==================== Ingestion Tests ====================

    def test_ingest_cib_payment(self, detector: ExpansionDetector) -> None:
        """Test ingesting CIB payment event."""
        payment = {
            "debtor_client_id": "CIB-1001",
            "creditor_country": "KE",
            "amount": 1000000.0
        }
        detector.ingest_cib_payment(payment)
        assert "CIB-1001" in detector._cib_payments
        assert len(detector._cib_payments["CIB-1001"]) == 1

    def test_ingest_cib_payment_missing_client_id(
        self, detector: ExpansionDetector
    ) -> None:
        """Test ingesting payment without client_id."""
        payment = {"creditor_country": "KE", "amount": 1000000.0}
        detector.ingest_cib_payment(payment)
        # Should not add to any client
        assert len(detector._cib_payments) == 0

    def test_ingest_cell_activation(self, detector: ExpansionDetector) -> None:
        """Test ingesting cell activation event."""
        activation = {
            "corporate_client_id": "CIB-1001",
            "activation_country": "KE",
            "sim_count": 50
        }
        detector.ingest_cell_activation(activation)
        assert "CIB-1001" in detector._cell_activations

    def test_ingest_cell_activation_missing_client_id(
        self, detector: ExpansionDetector
    ) -> None:
        """Test ingesting activation without client_id."""
        activation = {"activation_country": "KE", "sim_count": 50}
        detector.ingest_cell_activation(activation)
        assert len(detector._cell_activations) == 0

    def test_ingest_forex_trade(self, detector: ExpansionDetector) -> None:
        """Test ingesting forex trade event."""
        trade = {
            "client_id": "CIB-1001",
            "target_currency": "KES",
            "base_amount": 500000.0
        }
        detector.ingest_forex_trade(trade)
        assert "CIB-1001" in detector._forex_trades

    def test_ingest_forex_trade_missing_client_id(
        self, detector: ExpansionDetector
    ) -> None:
        """Test ingesting trade without client_id."""
        trade = {"target_currency": "KES", "base_amount": 500000.0}
        detector.ingest_forex_trade(trade)
        assert len(detector._forex_trades) == 0

    def test_ingest_multiple_payments(
        self, detector: ExpansionDetector
    ) -> None:
        """Test ingesting multiple payments for same client."""
        for i in range(5):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "creditor_country": "KE",
                "amount": 1000000.0
            })
        assert len(detector._cib_payments["CIB-1001"]) == 5

    # ==================== detect_expansions Tests ====================

    def test_no_signal_from_cib_alone(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test no high-confidence signal from CIB payments only."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(4):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "KE",
                "creditor_name": f"Supplier {i}",
                "business_date": today,
                "amount": 500_000,
                "payment_type": "SUPPLIER",
            })
        signals = detector.detect_expansions(client_metadata)
        high_confidence = [
            s for s in signals if s.confidence_score >= 80
        ]
        assert len(high_confidence) == 0

    def test_signal_from_cib_plus_cell(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test signal generated from CIB + cell evidence."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(5):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "KE",
                "creditor_name": f"Kenya Supplier {i}",
                "business_date": today,
                "amount": 1_000_000,
                "payment_type": "SUPPLIER",
            })
        detector.ingest_cell_activation({
            "corporate_client_id": "CIB-1001",
            "activation_country": "KE",
            "activation_date": today,
            "sim_count": 50,
            "city": "Nairobi",
        })
        signals = detector.detect_expansions(client_metadata)
        assert len(signals) >= 1
        assert signals[0].expansion_country == "KE"
        assert signals[0].confidence_score >= 50

    def test_unhedged_exposure_flagged(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test unhedged exposure is flagged."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(6):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "KE",
                "creditor_name": f"KE Supplier {i}",
                "business_date": today,
                "amount": 2_000_000,
                "payment_type": "SUPPLIER",
            })
        detector.ingest_cell_activation({
            "corporate_client_id": "CIB-1001",
            "activation_country": "KE",
            "activation_date": today,
            "sim_count": 100,
            "city": "Nairobi",
        })
        signals = detector.detect_expansions(client_metadata)
        assert len(signals) >= 1
        assert signals[0].forex_hedging_in_place is False

    def test_home_country_excluded(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test home country payments don't trigger expansion signals."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(20):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "ZA",
                "creditor_name": f"Local Supplier {i}",
                "business_date": today,
                "amount": 5_000_000,
                "payment_type": "SUPPLIER",
            })
        signals = detector.detect_expansions(client_metadata)
        za_signals = [
            s for s in signals
            if s.expansion_country == "ZA"
        ]
        assert len(za_signals) == 0

    def test_recommended_products_include_fx_when_unhedged(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test FX products recommended when unhedged."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(5):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "GH",
                "creditor_name": f"GH Supplier {i}",
                "business_date": today,
                "amount": 800_000,
                "payment_type": "SUPPLIER",
            })
        detector.ingest_cell_activation({
            "corporate_client_id": "CIB-1001",
            "activation_country": "GH",
            "activation_date": today,
            "sim_count": 30,
            "city": "Accra",
        })
        signals = detector.detect_expansions(client_metadata)
        if signals:
            products = signals[0].recommended_products
            fx_products = [
                p for p in products if "FX" in p or "hedging" in p
            ]
            assert len(fx_products) >= 1

    def test_opportunity_estimate_positive(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test opportunity estimate is positive."""
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(10):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "NG",
                "creditor_name": f"NG Supplier {i}",
                "business_date": today,
                "amount": 3_000_000,
                "payment_type": "SUPPLIER",
            })
        detector.ingest_cell_activation({
            "corporate_client_id": "CIB-1001",
            "activation_country": "NG",
            "activation_date": today,
            "sim_count": 200,
            "city": "Lagos",
        })
        signals = detector.detect_expansions(client_metadata)
        assert len(signals) >= 1
        assert signals[0].estimated_opportunity_zar > 0

    def test_detect_expansions_empty_data(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test detection with no ingested data."""
        signals = detector.detect_expansions(client_metadata)
        assert signals == []

    def test_detect_expansions_error_handling(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test detection error handling."""
        # Corrupt internal state to trigger error
        detector._cib_payments = "invalid"  # type: ignore

        with pytest.raises(SignalDetectionError) as exc_info:
            detector.detect_expansions(client_metadata)
        assert "Expansion detection failed" in str(exc_info.value)

    def test_detect_expansions_sorts_by_confidence(
        self, detector: ExpansionDetector, client_metadata: dict
    ) -> None:
        """Test results are sorted by confidence (highest first)."""
        # Add data for multiple countries
        for country, count in [("KE", 10), ("NG", 5), ("GH", 3)]:
            for i in range(count):
                detector.ingest_cib_payment({
                    "debtor_client_id": "CIB-1001",
                    "debtor_country": "ZA",
                    "creditor_country": country,
                    "amount": 1_000_000,
                })
            detector.ingest_cell_activation({
                "corporate_client_id": "CIB-1001",
                "activation_country": country,
                "sim_count": count * 20,
            })

        signals = detector.detect_expansions(client_metadata)

        # Verify sorted by confidence descending
        for i in range(len(signals) - 1):
            assert signals[i].confidence_score >= signals[i + 1].confidence_score

    def test_detect_with_custom_threshold(
        self, detector_with_custom_settings: ExpansionDetector,
        client_metadata: dict
    ) -> None:
        """Test detection with lower thresholds."""
        # With lower thresholds, fewer events should trigger signal
        for i in range(2):  # Only 2 payments (threshold is 2)
            detector_with_custom_settings.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "debtor_country": "ZA",
                "creditor_country": "KE",
                "amount": 600_000,  # Above 500k threshold
            })
        detector_with_custom_settings.ingest_cell_activation({
            "corporate_client_id": "CIB-1001",
            "activation_country": "KE",
            "sim_count": 15,  # Above 10 threshold
        })

        signals = detector_with_custom_settings.detect_expansions(client_metadata)
        assert len(signals) >= 1

    def test_detect_with_missing_client_metadata(
        self, detector: ExpansionDetector
    ) -> None:
        """Test detection when client not in metadata."""
        detector.ingest_cib_payment({
            "debtor_client_id": "UNKNOWN-CLIENT",
            "creditor_country": "KE",
            "amount": 1_000_000,
        })

        # Should not raise, should handle gracefully
        signals = detector.detect_expansions({})
        assert isinstance(signals, list)

    # ==================== _get_cib_corridors Tests ====================

    def test_get_cib_corridors_excludes_home(
        self, detector: ExpansionDetector
    ) -> None:
        """Test corridor calculation excludes home country."""
        detector.ingest_cib_payment({
            "debtor_client_id": "CIB-1001",
            "creditor_country": "ZA",  # Home country
            "amount": 1_000_000,
        })
        detector.ingest_cib_payment({
            "debtor_client_id": "CIB-1001",
            "creditor_country": "KE",  # Foreign
            "amount": 500_000,
        })

        corridors = detector._get_cib_corridors("CIB-1001", "ZA")

        assert "ZA" not in corridors
        assert "KE" in corridors
        assert corridors["KE"]["payments"] == 1

    def test_get_cib_corridors_aggregates(
        self, detector: ExpansionDetector
    ) -> None:
        """Test corridor aggregation."""
        for i in range(3):
            detector.ingest_cib_payment({
                "debtor_client_id": "CIB-1001",
                "creditor_country": "KE",
                "amount": 1_000_000 * (i + 1),
            })

        corridors = detector._get_cib_corridors("CIB-1001", "ZA")

        assert corridors["KE"]["payments"] == 3
        assert corridors["KE"]["value"] == 6_000_000  # 1M + 2M + 3M

    def test_get_cib_corridors_unknown_client(
        self, detector: ExpansionDetector
    ) -> None:
        """Test corridor lookup for unknown client."""
        corridors = detector._get_cib_corridors("UNKNOWN", "ZA")
        assert corridors == {}
