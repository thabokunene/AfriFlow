"""
Unified Golden Record package for AfriFlow.

We maintain a unified, consistent, and fresh view of
each client entity across all five domains.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .consistency_checker import (
    ConsistencyChecker,
    ConsistencyReport,
    ConsistencyIssue,
    ConsistencyCheckType,
    ConsistencySeverity,
)
from .freshness_monitor import (
    GoldenRecordFreshnessMonitor,
    GoldenRecordFreshness,
    DomainFreshnessStatus,
    DomainStaleness,
    DOMAIN_SLA_MINUTES,
)

__all__ = [
    "ConsistencyChecker",
    "ConsistencyReport",
    "ConsistencyIssue",
    "ConsistencyCheckType",
    "ConsistencySeverity",
    "GoldenRecordFreshnessMonitor",
    "GoldenRecordFreshness",
    "DomainFreshnessStatus",
    "DomainStaleness",
    "DOMAIN_SLA_MINUTES",
]
