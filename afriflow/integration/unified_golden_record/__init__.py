"""
@file __init__.py
@description Public API for the unified_golden_record package. Re-exports
    ConsistencyChecker, GoldenRecordFreshnessMonitor, and their supporting
    data-classes so callers can import everything from a single entry point.
    Maintains a unified, consistent, and fresh view of each client entity
    across all five AfriFlow domains: CIB, Forex, Insurance, Cell, and PBB.
@author Thabo Kunene
@created 2026-03-18
"""
# Package-level note:
# The golden record is only as good as its worst domain contribution.
# This package provides both the consistency gate (does domain data agree?)
# and the freshness gate (is each domain within its SLA?) before a record
# is surfaced to relationship managers or NBA scoring models.
#
# DISCLAIMER: This project is not a sanctioned initiative
# of Standard Bank Group, MTN, or any affiliated entity.
# It is a demonstration of concept, domain knowledge,
# and data engineering skill by Thabo Kunene.

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
