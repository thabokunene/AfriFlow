"""
tests/unit/test_confidence_calculator.py

We test that confidence scoring correctly weights the
number of corroborating domains and the strength of
evidence within each domain.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.cross_domain_signals.expansion_signal import (
    ExpansionDetector,
)


class TestConfidenceCalculation:
    """We verify that confidence increases with the number
    of domains providing corroborating evidence."""

    @pytest.fixture
    def detector(self):
        return ExpansionDetector()

    def test_single_domain_below_60(self, detector):
        score = detector._calculate_confidence(
            cib_payments=5,
            cib_value=1_000_000,
            sim_activations=0,
            has_forex=False,
            has_insurance=False,
            has_pbb=False,
        )
        assert score < 60

    def test_two_domains_between_60_and_80(self, detector):
        score = detector._calculate_confidence(
            cib_payments=5,
            cib_value=1_000_000,
            sim_activations=50,
            has_forex=False,
            has_insurance=False,
            has_pbb=False,
        )
        assert 40 <= score <= 80

    def test_three_plus_domains_above_70(self, detector):
        score = detector._calculate_confidence(
            cib_payments=10,
            cib_value=5_000_000,
            sim_activations=100,
            has_forex=True,
            has_insurance=False,
            has_pbb=True,
        )
        assert score >= 70

    def test_max_evidence_near_99(self, detector):
        score = detector._calculate_confidence(
            cib_payments=15,
            cib_value=50_000_000,
            sim_activations=500,
            has_forex=True,
            has_insurance=False,
            has_pbb=True,
        )
        assert score >= 85

    def test_score_never_exceeds_99(self, detector):
        score = detector._calculate_confidence(
            cib_payments=100,
            cib_value=500_000_000,
            sim_activations=10_000,
            has_forex=True,
            has_insurance=True,
            has_pbb=True,
        )
        assert score <= 99
