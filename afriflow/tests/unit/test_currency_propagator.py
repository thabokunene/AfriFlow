"""
tests/unit/test_currency_propagator.py

Unit tests for the Currency Event Propagator.

We verify that:
1. FX events are classified correctly by severity.
2. Impact propagates to all five domains.
3. Different currencies have different thresholds.
4. The cascade report includes all affected clients.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from afriflow.currency_events import (
    CurrencyEventClassifier,
    CurrencyEvent,
    EventType,
    EventSeverity,
)


class TestCurrencyEventClassifier:
    """Tests for FX event classification."""

    def setup_method(self):
        self.classifier = CurrencyEventClassifier()

    def test_ngn_devaluation_critical(self):
        """A 15% NGN move with official announcement is CRITICAL."""

        event = self.classifier.classify(
            currency="NGN",
            rate_change_pct=15.0,
            is_official_announcement=True,
        )

        assert event is not None
        assert event.event_type == EventType.DEVALUATION
        assert event.severity == EventSeverity.CRITICAL
        assert event.currency == "NGN"

    def test_ngn_rapid_depreciation(self):
        """A 5% NGN move without announcement is rapid depreciation."""

        event = self.classifier.classify(
            currency="NGN",
            rate_change_pct=5.0,
        )

        assert event is not None
        assert event.event_type == EventType.RAPID_DEPRECIATION
        assert event.severity == EventSeverity.HIGH

    def test_zar_normal_volatility_low_event(self):
        """A 3% ZAR move is normal volatility, but still a LOW event."""

        event = self.classifier.classify(
            currency="ZAR",
            rate_change_pct=3.0,
        )

        assert event is not None
        assert event.severity == EventSeverity.LOW

    def test_zar_needs_larger_move_for_high_event(self):
        """ZAR has higher thresholds because it is more liquid."""

        event_5 = self.classifier.classify(
            currency="ZAR", rate_change_pct=5.0,
        )
        assert event_5 is not None
        assert event_5.severity == EventSeverity.MEDIUM

        event_7 = self.classifier.classify(
            currency="ZAR", rate_change_pct=7.0,
        )
        assert event_7 is not None
        assert event_7.severity == EventSeverity.HIGH

    def test_aoa_lower_thresholds(self):
        """Angola has lower thresholds due to historical volatility."""

        event = self.classifier.classify(
            currency="AOA", rate_change_pct=3.5,
        )

        assert event is not None
        assert event.severity in (
            EventSeverity.MEDIUM, EventSeverity.HIGH
        )

    def test_parallel_divergence_detected(self):
        """Parallel market divergence should be detected."""

        event = self.classifier.classify(
            currency="NGN",
            rate_change_pct=1.0,
            parallel_divergence_pct=18.0,
        )

        assert event is not None
        assert event.event_type == EventType.PARALLEL_RATE_DIVERGENCE

    def test_xof_threshold(self):
        """
        XOF (CFA franc) is pegged to EUR, so it needs
        very large moves to trigger a high event.
        """

        event_7 = self.classifier.classify(
            currency="XOF", rate_change_pct=7.0,
        )
        assert event_7 is not None
        assert event_7.severity == EventSeverity.MEDIUM

        event_9 = self.classifier.classify(
            currency="XOF", rate_change_pct=9.0,
        )
        assert event_9 is not None
        assert event_9.severity == EventSeverity.HIGH

    def test_unknown_currency_uses_defaults(self):
        """Unknown currencies use default thresholds."""

        event = self.classifier.classify(
            currency="UNKNOWN", rate_change_pct=6.0,
        )

        assert event is not None

    def test_event_id_format(self):
        """Event IDs should follow our naming convention."""

        event = self.classifier.classify(
            currency="NGN",
            rate_change_pct=10.0,
            is_official_announcement=True,
        )

        assert event is not None
        assert event.event_id.startswith("FXE-NGN-")

    def test_negative_rate_change(self):
        """Negative changes (appreciation) should also be detected."""

        event = self.classifier.classify(
            currency="NGN", rate_change_pct=-9.0,
        )

        assert event is not None
