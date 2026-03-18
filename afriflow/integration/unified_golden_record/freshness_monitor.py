"""
@file freshness_monitor.py
@description Monitors the freshness of each domain's contribution to the unified
    golden record. A golden record is only as current as its stalest domain input.
    Tracks latency per domain per client, classifies staleness into four bands
    (FRESH/SLIGHTLY_STALE/STALE/VERY_STALE/MISSING), and surfaces records that
    have breached their SLAs before they reach RM briefings or NBA scoring.
@author Thabo Kunene
@created 2026-03-18
"""
# Domain SLAs (maximum acceptable ingestion latency):
#   CIB payments:    4 hours  — high-value, time-sensitive transactions
#   Forex positions: 1 hour   — market-linked; intraday positions change rapidly
#   Insurance:      24 hours  — daily batch acceptable for policy data
#   Cell/MoMo:       6 hours  — near-real-time required for workforce signals
#   PBB:            12 hours  — twice-daily payroll batch is sufficient
#
# DISCLAIMER: This project is not a sanctioned initiative
# of Standard Bank Group, MTN, or any affiliated entity.
# It is a demonstration of concept, domain knowledge,
# and data engineering skill by Thabo Kunene.

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.logging_config import get_logger

logger = get_logger("integration.unified_golden_record.freshness_monitor")


class DomainStaleness(Enum):
    """Staleness level for a domain's contribution to a golden record.

    Bands are defined relative to the domain's SLA:
      FRESH          → latency <= 1x SLA   (within acceptable window)
      SLIGHTLY_STALE → latency 1–2x SLA   (approaching breach)
      STALE          → latency 2–5x SLA   (SLA breached)
      VERY_STALE     → latency > 5x SLA   (serious data quality concern)
      MISSING        → no data at all      (domain did not feed this record)
    """
    FRESH = "fresh"                        # Within SLA — safe for RM use
    SLIGHTLY_STALE = "slightly_stale"      # Approaching SLA breach — monitor
    STALE = "stale"                        # SLA breached — investigate pipeline
    VERY_STALE = "very_stale"              # Serious staleness — not usable for briefings
    MISSING = "missing"                    # Domain never contributed to this record


# Domain-level freshness SLAs in minutes — the maximum acceptable data latency
# for each domain before its contribution is considered stale.
DOMAIN_SLA_MINUTES: Dict[str, int] = {
    "cib": 240,        # 4 hours — high-value corporate payment flows
    "forex": 60,       # 1 hour  — intraday positions change with market moves
    "insurance": 1440, # 24 hours — daily policy batch is acceptable
    "cell": 360,       # 6 hours  — near-real-time workforce signals
    "pbb": 720,        # 12 hours — twice-daily payroll ingestion
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
    """Classify a latency value into a DomainStaleness band.

    Uses ratio = latency / SLA to classify relative to the domain's own SLA
    rather than absolute minutes, so a 2-hour-old CIB record and a 2-hour-old
    forex record are treated differently (CIB SLA = 4h; forex SLA = 1h).

    :param latency_minutes: Minutes elapsed since the domain last updated.
    :param sla_minutes: Domain SLA in minutes from DOMAIN_SLA_MINUTES.
    :return: DomainStaleness classification for this latency.
    """
    # Guard: if SLA is 0 (misconfiguration), treat as infinitely stale
    ratio = latency_minutes / sla_minutes if sla_minutes > 0 else float("inf")
    if ratio <= 1.0:
        return DomainStaleness.FRESH          # Within SLA
    elif ratio <= 2.0:
        return DomainStaleness.SLIGHTLY_STALE # Up to 2x SLA — monitor
    elif ratio <= 5.0:
        return DomainStaleness.STALE          # 2–5x SLA — investigate
    else:
        return DomainStaleness.VERY_STALE     # >5x SLA — critical


def _staleness_rank(s: DomainStaleness) -> int:
    """Return an integer rank for a DomainStaleness value.

    Used by max() to identify the worst staleness level across all domains
    in a golden record without comparing enum members directly.

    :param s: DomainStaleness value to rank.
    :return: Integer rank (0 = FRESH, 4 = MISSING/worst).
    """
    return {
        DomainStaleness.FRESH: 0,           # Best: data is current
        DomainStaleness.SLIGHTLY_STALE: 1,  # Approaching SLA
        DomainStaleness.STALE: 2,           # SLA breached
        DomainStaleness.VERY_STALE: 3,      # Serious lateness
        DomainStaleness.MISSING: 4,         # Worst: no data at all
    }[s]


class GoldenRecordFreshnessMonitor:
    """We monitor the freshness of unified golden records across all domains.

    Tracks last-update timestamps per domain per client and surfaces
    staleness issues before they propagate to RM briefings or NBA
    model scoring, where stale data could trigger incorrect recommendations.

    Attributes:
        domain_slas: Dict of domain → SLA minutes (merged from defaults + custom overrides)
        freshness_cache: Dict of golden_id → most recent GoldenRecordFreshness result
    """

    def __init__(
        self,
        custom_slas: Optional[Dict[str, int]] = None
    ) -> None:
        """Initialise the monitor with default SLAs and optional custom overrides.

        :param custom_slas: Optional dict of domain → SLA minutes to override defaults.
                            Useful for testing or environment-specific SLA adjustments.
        """
        # Merge: start with platform defaults, then apply any custom overrides
        self.domain_slas = {**DOMAIN_SLA_MINUTES, **(custom_slas or {})}
        # In-memory cache: updated on every check_freshness() call
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
        """Check freshness of all domains for a single golden record.

        Computes latency for each domain relative to reference_time (or now),
        classifies each into a staleness band, and assembles an aggregate
        GoldenRecordFreshness that reflects the worst domain.

        :param golden_id: Golden record identifier being checked.
        :param domain_updates: Dict of domain → last_update datetime (None = no data).
        :param reference_time: Time to measure latency against; defaults to UTC now.
        :return: GoldenRecordFreshness with per-domain status and aggregate staleness.
        """
        # Use provided reference time or default to UTC now for reproducibility in tests
        now = reference_time or datetime.utcnow()
        statuses: List[DomainFreshnessStatus] = []

        for domain, sla_minutes in self.domain_slas.items():
            last_updated = domain_updates.get(domain)

            if last_updated is None:
                # Domain has never written to this golden record — treat as missing
                status = DomainFreshnessStatus(
                    golden_id=golden_id,
                    domain=domain,
                    last_updated=None,
                    sla_minutes=sla_minutes,
                    latency_minutes=float("inf"),  # Infinite latency: no timestamp
                    staleness=DomainStaleness.MISSING,
                    is_sla_breached=True,           # Missing always breaches SLA
                )
            else:
                # Compute latency in minutes from the last domain update to now
                latency = (now - last_updated).total_seconds() / 60
                staleness = _classify_staleness(latency, sla_minutes)
                status = DomainFreshnessStatus(
                    golden_id=golden_id,
                    domain=domain,
                    last_updated=last_updated,
                    sla_minutes=sla_minutes,
                    latency_minutes=round(latency, 1),
                    staleness=staleness,
                    is_sla_breached=latency > sla_minutes,  # Any latency > SLA is a breach
                )

            statuses.append(status)

        # The overall staleness is the worst single-domain staleness
        worst = max(statuses, key=lambda s: _staleness_rank(s.staleness))
        # Domains at STALE or worse need investigation (SLIGHTLY_STALE is just a warning)
        stale = [s.domain for s in statuses if s.staleness not in (
            DomainStaleness.FRESH, DomainStaleness.SLIGHTLY_STALE
        )]
        # Domains with no data at all — these may indicate pipeline outages
        missing = [s.domain for s in statuses if s.staleness == DomainStaleness.MISSING]

        result = GoldenRecordFreshness(
            golden_id=golden_id,
            domain_statuses=statuses,
            overall_staleness=worst.staleness,
            stale_domains=stale,
            missing_domains=missing,
        )
        # Update the in-memory cache for subsequent get_stale_records() calls
        self.freshness_cache[golden_id] = result
        return result

    def check_batch(
        self,
        records: List[Dict[str, Any]],
    ) -> List[GoldenRecordFreshness]:
        """Check freshness for a batch of golden records in sequence.

        Each dict in the list must have 'golden_id' and 'domain_updates' keys.
        Delegates to check_freshness() for each record so the cache is populated
        for all records after this call.

        :param records: List of dicts with 'golden_id' and 'domain_updates'.
        :return: List of GoldenRecordFreshness in the same order as input.
        """
        return [
            self.check_freshness(r["golden_id"], r["domain_updates"])
            for r in records
        ]

    def get_stale_records(
        self,
        min_staleness: DomainStaleness = DomainStaleness.STALE,
    ) -> List[GoldenRecordFreshness]:
        """Get all golden records at or above a given staleness threshold.

        Uses _staleness_rank() for threshold comparison so the caller can pass
        any DomainStaleness value as the minimum acceptable level.

        :param min_staleness: Minimum staleness level to include (default: STALE).
        :return: List of GoldenRecordFreshness objects from the cache.
        """
        min_rank = _staleness_rank(min_staleness)
        # Return records whose overall staleness rank meets or exceeds the minimum
        return [
            r for r in self.freshness_cache.values()
            if _staleness_rank(r.overall_staleness) >= min_rank
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated freshness statistics across all monitored golden records.

        Used by monitoring dashboards and CI health checks to track data pipeline
        SLA compliance per domain across the full golden record population.

        :return: Dict with record counts, stale record count, and per-domain breakdown.
        """
        # Flatten all domain statuses from the cache into a single list
        all_statuses = [
            s
            for r in self.freshness_cache.values()
            for s in r.domain_statuses
        ]
        # Build per-domain staleness band counts for the freshness_by_domain output
        by_domain: Dict[str, Dict[str, int]] = {}
        for s in all_statuses:
            if s.domain not in by_domain:
                by_domain[s.domain] = {}
            key = s.staleness.value
            # Increment the count for this domain+staleness combination
            by_domain[s.domain][key] = by_domain[s.domain].get(key, 0) + 1

        return {
            "total_golden_records_monitored": len(self.freshness_cache),
            # Count of records where overall staleness is STALE or worse
            "stale_records": len(self.get_stale_records()),
            # Count of records where at least one domain has no data
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
