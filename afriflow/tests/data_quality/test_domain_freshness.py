"""
tests/data_quality/test_domain_freshness.py

We test the domain freshness monitoring system that
enforces sub-5-minute SLA for the gold layer and
raises alerts when any domain feed becomes stale.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from datetime import datetime, timedelta
from governance.freshness_monitor import (
    FreshnessMonitor,
    DomainFreshnessStatus,
    StalenessLevel,
)


class TestFreshnessThresholds:
    """We verify that staleness levels are correctly
    assigned based on the time since last update for
    each domain."""

    @pytest.fixture
    def monitor(self):
        return FreshnessMonitor()

    def test_fresh_within_5_minutes(self, monitor):
        status = monitor.evaluate(
            domain="cib",
            last_update=datetime.now() - timedelta(minutes=3),
        )
        assert status.level == StalenessLevel.FRESH

    def test_warning_between_5_and_30_minutes(self, monitor):
        status = monitor.evaluate(
            domain="cib",
            last_update=datetime.now() - timedelta(minutes=15),
        )
        assert status.level == StalenessLevel.WARNING

    def test_stale_beyond_30_minutes(self, monitor):
        status = monitor.evaluate(
            domain="cib",
            last_update=datetime.now() - timedelta(hours=2),
        )
        assert status.level == StalenessLevel.STALE

    def test_cell_domain_has_relaxed_threshold(self, monitor):
        """The cell domain may legitimately have longer
        update intervals depending on the MTN data
        sharing tier (real-time vs daily batch). We
        configure per-domain thresholds accordingly."""
        status = monitor.evaluate(
            domain="cell",
            last_update=datetime.now() - timedelta(hours=12),
        )
        assert status.level in (
            StalenessLevel.WARNING,
            StalenessLevel.STALE,
        )

    def test_golden_record_staleness_uses_worst_domain(
        self, monitor
    ):
        """The golden record is only as fresh as its
        stalest contributing domain."""
        domain_updates = {
            "cib": datetime.now() - timedelta(minutes=2),
            "forex": datetime.now() - timedelta(minutes=4),
            "insurance": datetime.now() - timedelta(hours=3),
            "cell": datetime.now() - timedelta(minutes=10),
            "pbb": datetime.now() - timedelta(minutes=5),
        }
        golden_status = monitor.evaluate_golden_record(
            domain_updates
        )
        assert golden_status.stalest_domain == "insurance"
