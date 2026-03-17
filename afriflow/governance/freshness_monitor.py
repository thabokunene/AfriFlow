"""
governance/freshness_monitor.py

Domain freshness monitoring with circuit breaker
support.

We enforce sub-5-minute SLA for the gold layer and
prevent stale or corrupt data from polluting downstream
consumers. When a domain feed drops below quality
thresholds, we fall back to the last known good state.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, Optional


class StalenessLevel(Enum):
    """Staleness classification for a domain feed."""

    FRESH = auto()
    WARNING = auto()
    STALE = auto()
    CIRCUIT_BROKEN = auto()


@dataclass
class DomainFreshnessStatus:
    """Freshness status for a single domain feed."""

    domain: str
    level: StalenessLevel
    last_update: datetime
    minutes_since_update: float
    threshold_warning_minutes: float
    threshold_stale_minutes: float
    is_circuit_broken: bool
    message: str


@dataclass
class GoldenRecordFreshnessStatus:
    """Freshness status for the unified golden record
    based on the stalest contributing domain."""

    overall_level: StalenessLevel
    stalest_domain: str
    stalest_minutes: float
    domain_statuses: Dict[str, DomainFreshnessStatus]


class FreshnessMonitor:
    """We monitor the freshness of each domain feed
    and the overall golden record.

    The golden record is only as fresh as its stalest
    contributing domain. We support per-domain thresholds
    because the cell domain (MTN feed) may have longer
    update intervals than the CIB domain depending on
    the data sharing tier.
    """

    DEFAULT_THRESHOLDS: Dict[str, Dict[str, float]] = {
        "cib": {
            "warning_minutes": 5.0,
            "stale_minutes": 30.0,
        },
        "forex": {
            "warning_minutes": 2.0,
            "stale_minutes": 15.0,
        },
        "insurance": {
            "warning_minutes": 60.0,
            "stale_minutes": 360.0,
        },
        "cell": {
            "warning_minutes": 120.0,
            "stale_minutes": 1440.0,
        },
        "pbb": {
            "warning_minutes": 30.0,
            "stale_minutes": 120.0,
        },
    }

    def evaluate(
        self,
        domain: str,
        last_update: datetime,
        now: Optional[datetime] = None,
    ) -> DomainFreshnessStatus:
        """We evaluate the freshness of a single domain
        feed."""
        if now is None:
            now = datetime.now()

        delta = now - last_update
        minutes = delta.total_seconds() / 60.0

        thresholds = self.DEFAULT_THRESHOLDS.get(
            domain,
            {"warning_minutes": 30.0, "stale_minutes": 120.0},
        )

        warning_t = thresholds["warning_minutes"]
        stale_t = thresholds["stale_minutes"]

        if minutes < warning_t:
            level = StalenessLevel.FRESH
            message = f"{domain} is fresh ({minutes:.1f}m)"
        elif minutes < stale_t:
            level = StalenessLevel.WARNING
            message = (
                f"{domain} is behind "
                f"({minutes:.1f}m, warn at {warning_t}m)"
            )
        else:
            level = StalenessLevel.STALE
            message = (
                f"{domain} is STALE "
                f"({minutes:.1f}m, limit {stale_t}m)"
            )

        return DomainFreshnessStatus(
            domain=domain,
            level=level,
            last_update=last_update,
            minutes_since_update=minutes,
            threshold_warning_minutes=warning_t,
            threshold_stale_minutes=stale_t,
            is_circuit_broken=(
                level == StalenessLevel.STALE
            ),
            message=message,
        )

    def evaluate_golden_record(
        self,
        domain_updates: Dict[str, datetime],
        now: Optional[datetime] = None,
    ) -> GoldenRecordFreshnessStatus:
        """We evaluate the overall freshness of the
        golden record based on all contributing domains."""
        if now is None:
            now = datetime.now()

        statuses = {}
        stalest_domain = None
        stalest_minutes = 0.0

        for domain, last_update in domain_updates.items():
            status = self.evaluate(domain, last_update, now)
            statuses[domain] = status

            if status.minutes_since_update > stalest_minutes:
                stalest_minutes = status.minutes_since_update
                stalest_domain = domain

        overall = StalenessLevel.FRESH
        for status in statuses.values():
            if status.level == StalenessLevel.STALE:
                overall = StalenessLevel.STALE
                break
            if status.level == StalenessLevel.WARNING:
                overall = StalenessLevel.WARNING

        return GoldenRecordFreshnessStatus(
            overall_level=overall,
            stalest_domain=stalest_domain or "unknown",
            stalest_minutes=stalest_minutes,
            domain_statuses=statuses,
        )
