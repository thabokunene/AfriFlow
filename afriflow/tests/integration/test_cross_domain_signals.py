"""
tests/integration/test_cross_domain_signals.py

Integration tests for cross domain signal generation.

These tests verify that when data from multiple domains
is combined, the correct cross domain signals are generated.
This is the core differentiator of AfriFlow: no single domain
can produce these signals alone.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from datetime import datetime, timedelta
from integration.cross_domain_signals.expansion_signal import (
    ExpansionDetector,
    ExpansionSignal,
)


class TestExpansionSignalIntegration:
    """
    Integration tests for the Expansion Signal detector.

    The expansion signal requires correlation between
    CIB payments and cell network SIM activations.
    Neither source alone is sufficient.
    """

    def setup_method(self):
        self.detector = ExpansionDetector()
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.recent = (
            datetime.now() - timedelta(days=30)
        ).strftime("%Y-%m-%d")

    def test_cib_plus_cell_generates_expansion_signal(self):
        """
        CIB payments to Kenya plus cell SIM activations
        in Kenya should generate an expansion signal.
        This is the core cross domain correlation.
        """

        for i in range(5):
            self.detector.ingest_cib_payment({
                "debtor_client_id": "CLIENT-001",
                "debtor_country": "ZA",
                "creditor_country": "KE",
                "creditor_name": f"Supplier-{i}",
                "business_date": self.recent,
                "amount": 1_000_000,
                "payment_type": "SUPPLIER",
            })

        for i in range(3):
            self.detector.ingest_cell_activation({
                "corporate_client_id": "CLIENT-001",
                "activation_country": "KE",
                "activation_date": self.recent,
                "sim_count": 50,
                "city": "Nairobi",
            })

        client_metadata = {
            "CLIENT-001": {
                "client_name": "Test Corp",
                "tier": "Platinum",
                "relationship_manager": "RM-001",
            },
        }

        signals = self.detector.detect_expansions(
            client_metadata, lookback_days=90
        )

        assert len(signals) > 0
        signal = signals[0]
        assert signal.expansion_country == "KE"
        assert signal.cib_new_corridor_payments == 5
        assert signal.cell_new_sim_activations == 150
        assert signal.confidence_score >= 50

    def test_cib_alone_insufficient_for_high_confidence(self):
        """
        CIB payments alone (without cell corroboration)
        should produce a lower confidence signal.
        """

        for i in range(5):
            self.detector.ingest_cib_payment({
                "debtor_client_id": "CLIENT-002",
                "debtor_country": "ZA",
                "creditor_country": "GH",
                "creditor_name": f"Supplier-{i}",
                "business_date": self.recent,
                "amount": 1_000_000,
                "payment_type": "SUPPLIER",
            })

        client_metadata = {
            "CLIENT-002": {
                "client_name": "Test Corp 2",
                "tier": "Gold",
                "relationship_manager": "RM-002",
            },
        }

        signals = self.detector.detect_expansions(
            client_metadata, lookback_days=90
        )

        if signals:
            assert signals[0].confidence_score < 80

    def test_home_country_excluded(self):
        """
        Payments to the client's home country should not
        generate expansion signals.
        """

        for i in range(10):
            self.detector.ingest_cib_payment({
                "debtor_client_id": "CLIENT-003",
                "debtor_country": "ZA",
                "creditor_country": "ZA",
                "creditor_name": f"Local-Supplier-{i}",
                "business_date": self.recent,
                "amount": 5_000_000,
                "payment_type": "SUPPLIER",
            })

        client_metadata = {
            "CLIENT-003": {
                "client_name": "Local Corp",
                "tier": "Silver",
                "relationship_manager": "RM-003",
            },
        }

        signals = self.detector.detect_expansions(
            client_metadata, lookback_days=90
        )

        assert len(signals) == 0

    def test_unhedged_expansion_recommends_fx_products(self):
        """
        Expansion without forex hedging should recommend
        FX products in the signal.
        """

        for i in range(5):
            self.detector.ingest_cib_payment({
                "debtor_client_id": "CLIENT-004",
                "debtor_country": "ZA",
                "creditor_country": "NG",
                "creditor_name": f"Supplier-{i}",
                "business_date": self.recent,
                "amount": 2_000_000,
                "payment_type": "SUPPLIER",
            })

        self.detector.ingest_cell_activation({
            "corporate_client_id": "CLIENT-004",
            "activation_country": "NG",
            "activation_date": self.recent,
            "sim_count": 100,
            "city": "Lagos",
        })

        client_metadata = {
            "CLIENT-004": {
                "client_name": "Expanding Corp",
                "tier": "Platinum",
                "relationship_manager": "RM-004",
            },
        }

        signals = self.detector.detect_expansions(
            client_metadata, lookback_days=90
        )

        assert len(signals) > 0
        signal = signals[0]
        assert signal.forex_hedging_in_place is False

        fx_products = [
            p for p in signal.recommended_products
            if "hedging" in p.lower() or "fx" in p.lower()
        ]
        assert len(fx_products) > 0
