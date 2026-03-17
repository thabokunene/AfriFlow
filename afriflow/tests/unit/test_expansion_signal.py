"""
tests/unit/test_expansion_signal.py

We test the cross-domain expansion detection signal
that combines CIB payment patterns with cell network
SIM activations, forex hedging status, insurance
coverage, and PBB payroll data.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from datetime import datetime, timedelta
from integration.cross_domain_signals.expansion_signal import (
    ExpansionDetector,
    ExpansionSignal,
)


class TestExpansionDetection:
    """We test that expansion signals are generated only
    when sufficient cross-domain evidence exists."""

    @pytest.fixture
    def detector(self):
        return ExpansionDetector()

    @pytest.fixture
    def client_metadata(self):
        return {
            "CIB-1001": {
                "client_name": "Shoprite Holdings",
                "tier": "Platinum",
                "relationship_manager": "RM-JSmith",
            }
        }

    def test_no_signal_from_cib_alone(
        self, detector, client_metadata
    ):
        """A few payments to Kenya without cell data
        should not generate a high-confidence signal."""
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
        self, detector, client_metadata
    ):
        """CIB payments plus SIM activations in the
        same country should produce a credible signal."""
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
        self, detector, client_metadata
    ):
        """When a client expands but has no FX hedging
        in the new currency, we flag the gap."""
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
        self, detector, client_metadata
    ):
        """Payments within the home country should not
        trigger expansion signals."""
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
        self, detector, client_metadata
    ):
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
        self, detector, client_metadata
    ):
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
