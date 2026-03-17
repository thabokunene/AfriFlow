"""
Unified Golden Record - Freshness Monitor

We monitor the freshness of each domain's contribution
to the unified golden record. A golden record is only as
current as its stalest domain input.

Domain SLAs (maximum acceptable latency):
  CIB payments:   4 hours  (high-value, time-sensitive)
  Forex positions: 1 hour  (market-linked)
  Insurance:       24 hours (daily batch acceptable)
  Cell/MoMo:       6 hours  (near-real-time required)
  PBB:             12 hours (twice-daily batch)

We track staleness per client per domain, and surface
golden records that have fallen behind their SLAs for
remediation before they reach RM briefings.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.logging_config import get_logger

logger = get_logger("integration.unified_golden_record.freshness_monitor")


class DomainStaleness(Enum):
    """Staleness level for a domain contribution."""
    FRESH = "fresh"             # Within SLA
    SLIGHTLY_STALE = "slightly_stale"  # 1–2x SLA
    STALE = "stale"             # 2–5x SLA
    VERY_STALE = "very_stale"   # >5x SLA
    MISSING = "missing"         # No data at all


# Domain-level freshness SLAs in minutes
DOMAIN_SLA_MINUTES: Dict[str, int] = {
    "cib": 240,        # 4 hours
    "forex": 60,       # 1 hour
    "insurance": 1440, # 24 hours
    "cell": 360,       # 6 hours
    "pbb": 720,        # 12 hours
}


@dataclass
class DomainFreshnessStatus:
    """
    Freshness status for a single domain in a golden record.

    Attributes:
        golden_id: Golden record identifier
        domain: Domain name
        last_updated: Last update timestamp
        sla_minutes: SLA in minutes
        latency_minutes: Current latency
        staleness: Staleness classification
        is_sla_breached: True if beyond SLA
    """
    golden_id: str
    domain: str
    last_updated: Optional[datetime]
    sla_minutes: int
    latency_minutes: float
    staleness: DomainStaleness
    is_sla_breached: bool


@dataclass
class GoldenRecordFreshness:
    """
    Aggregated freshness view for an entire golden record.

    Attributes:
        golden_id: Golden record identifier
        domain_statuses: Freshness per domain
        overall_staleness: Worst staleness across all domains
        stale_domains: Domains that are stale
        missing_domains: Domains with no data
        last_checked: When freshness was last evaluated
    """
    golden_id: str
    domain_statuses: List[DomainFreshnessStatus]
    overall_staleness: DomainStaleness
    stale_domains: List[str]
    missing_domains: List[str]
    last_checked: datetime = field(default_factory=datetime.utcnow)

    def is_fully_fresh(self) -> bool:
        return self.overall_staleness == DomainStaleness.FRESH

    def is_usable(self) -> bool:
        """True if staleness is acceptable for RM briefings (not VERY_STALE)."""
        return self.overall_staleness not in [
            DomainStaleness.VERY_STALE, DomainStaleness.MISSING
        ]


def _classify_staleness(latency_minutes: float, sla_minutes: int) -> DomainStaleness:
    ratio = latency_minutes / sla_minutes if sla_minutes > 0 else float("inf")
    if ratio <= 1.0:
        return DomainStaleness.FRESH
    elif ratio <= 2.0:
        return DomainStaleness.SLIGHTLY_STALE
    elif ratio <= 5.0:
        return DomainStaleness.STALE
    else:
        return DomainStaleness.VERY_STALE


def _staleness_rank(s: DomainStaleness) -> int:
    return {
        DomainStaleness.FRESH: 0,
        DomainStaleness.SLIGHTLY_STALE: 1,
        DomainStaleness.STALE: 2,
        DomainStaleness.VERY_STALE: 3,
        DomainStaleness.MISSING: 4,
    }[s]


class GoldenRecordFreshnessMonitor:
    """
    We monitor the freshness of unified golden records.

    We track last-update timestamps per domain per client
    and surface staleness issues before they affect RM
    briefing quality or NBA model scoring.

    Attributes:
        domain_slas: SLA minutes per domain
        freshness_cache: Freshness per golden_id
    """

    def __init__(
        self,
        custom_slas: Optional[Dict[str, int]] = None
    ) -> None:
        self.domain_slas = {**DOMAIN_SLA_MINUTES, **(custom_slas or {})}
        self.freshness_cache: Dict[str, GoldenRecordFreshness] = {}
        logger.info(
            f"GoldenRecordFreshnessMonitor initialized, "
            f"domains: {list(self.domain_slas.keys())}"
        )

    def check_freshness(
        self,
        golden_id: str,
        domain_updates: Dict[str, Optional[datetime]],
        reference_time: Optional[datetime] = None,
    ) -> GoldenRecordFreshness:
        """
        Check freshness of all domains for a golden record.

        Args:
            golden_id: Golden record identifier
            domain_updates: Dict of domain → last_update datetime (None = missing)
            reference_time: Time to compute latency against (defaults to now)

        Returns:
            GoldenRecordFreshness with domain breakdown
        """
        now = reference_time or datetime.utcnow()
        statuses: List[DomainFreshnessStatus] = []

        for domain, sla_minutes in self.domain_slas.items():
            last_updated = domain_updates.get(domain)

            if last_updated is None:
                status = DomainFreshnessStatus(
                    golden_id=golden_id,
                    domain=domain,
                    last_updated=None,
                    sla_minutes=sla_minutes,
                    latency_minutes=float("inf"),
                    staleness=DomainStaleness.MISSING,
                    is_sla_breached=True,
                )
            else:
                latency = (now - last_updated).total_seconds() / 60
                staleness = _classify_staleness(latency, sla_minutes)
                status = DomainFreshnessStatus(
                    golden_id=golden_id,
                    domain=domain,
                    last_updated=last_updated,
                    sla_minutes=sla_minutes,
                    latency_minutes=round(latency, 1),
                    staleness=staleness,
                    is_sla_breached=latency > sla_minutes,
                )

            statuses.append(status)

        worst = max(statuses, key=lambda s: _staleness_rank(s.staleness))
        stale = [s.domain for s in statuses if s.staleness not in (
            DomainStaleness.FRESH, DomainStaleness.SLIGHTLY_STALE
        )]
        missing = [s.domain for s in statuses if s.staleness == DomainStaleness.MISSING]

        result = GoldenRecordFreshness(
            golden_id=golden_id,
            domain_statuses=statuses,
            overall_staleness=worst.staleness,
            stale_domains=stale,
            missing_domains=missing,
        )
        self.freshness_cache[golden_id] = result
        return result

    def check_batch(
        self,
        records: List[Dict[str, Any]],
    ) -> List[GoldenRecordFreshness]:
        """
        Check freshness for a batch of golden records.

        Each dict must have 'golden_id' and 'domain_updates' keys.
        """
        return [
            self.check_freshness(r["golden_id"], r["domain_updates"])
            for r in records
        ]

    def get_stale_records(
        self,
        min_staleness: DomainStaleness = DomainStaleness.STALE,
    ) -> List[GoldenRecordFreshness]:
        """Get all golden records at or above a staleness threshold."""
        min_rank = _staleness_rank(min_staleness)
        return [
            r for r in self.freshness_cache.values()
            if _staleness_rank(r.overall_staleness) >= min_rank
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get freshness monitoring statistics."""
        all_statuses = [
            s
            for r in self.freshness_cache.values()
            for s in r.domain_statuses
        ]
        by_domain: Dict[str, Dict[str, int]] = {}
        for s in all_statuses:
            if s.domain not in by_domain:
                by_domain[s.domain] = {}
            key = s.staleness.value
            by_domain[s.domain][key] = by_domain[s.domain].get(key, 0) + 1

        return {
            "total_golden_records_monitored": len(self.freshness_cache),
            "stale_records": len(self.get_stale_records()),
            "missing_data_records": sum(
                1 for r in self.freshness_cache.values()
                if r.missing_domains
            ),
            "freshness_by_domain": by_domain,
        }


if __name__ == "__main__":
    monitor = GoldenRecordFreshnessMonitor()
    now = datetime.utcnow()

    updates = {
        "cib": now - timedelta(hours=2),       # Fresh (SLA=4h)
        "forex": now - timedelta(hours=3),     # Stale! (SLA=1h)
        "insurance": now - timedelta(hours=12), # Fresh (SLA=24h)
        "cell": now - timedelta(hours=8),       # Stale (SLA=6h)
        "pbb": None,                            # Missing!
    }

    result = monitor.check_freshness("GLD-001", updates)
    print(f"Golden record GLD-001:")
    print(f"  Overall staleness: {result.overall_staleness.value}")
    print(f"  Stale domains: {result.stale_domains}")
    print(f"  Missing domains: {result.missing_domains}")
    print(f"  Usable for briefing: {result.is_usable()}")
    for s in result.domain_statuses:
        print(f"  {s.domain}: {s.staleness.value} ({s.latency_minutes:.0f}min, SLA={s.sla_minutes}min)")
