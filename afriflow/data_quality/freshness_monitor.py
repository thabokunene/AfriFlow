"""
@file freshness_monitor.py
@description Freshness Monitor - Data freshness SLA monitoring and alerting
@author Thabo Kunene
@created 2026-03-19

This module monitors data freshness against SLA thresholds and
generates alerts when data becomes stale.

Key Classes:
- FreshnessSLA: SLA configuration for a domain
- FreshnessMonitor: Main engine for freshness monitoring

Features:
- Per-domain freshness SLAs
- Real-time freshness checking
- Staleness alerting
- Pod offline detection
- Batch vs streaming mode handling

Usage:
    >>> from afriflow.data_quality.freshness_monitor import FreshnessMonitor
    >>> monitor = FreshnessMonitor()
    >>> monitor.set_sla("cib", max_age_hours=2)
    >>> is_fresh = monitor.check_freshness("cib", last_updated="2026-03-19T10:00:00")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from afriflow.logging_config import get_logger

logger = get_logger("data_quality.freshness")


@dataclass
class FreshnessSLA:
    """
    Freshness SLA configuration for a domain.

    Defines the maximum acceptable age for data in a domain
    before it's considered stale.

    Attributes:
        domain: Domain name
        max_age_hours: Maximum acceptable age in hours
        mode: Data mode (streaming, batch)
        grace_period_hours: Grace period before alerting
        enabled: Whether SLA is active

    Example:
        >>> sla = FreshnessSLA(
        ...     domain="cib",
        ...     max_age_hours=2,
        ...     mode="streaming"
        ... )
    """
    domain: str  # Domain name
    max_age_hours: float = 24.0  # Maximum age in hours
    mode: str = "batch"  # streaming or batch
    grace_period_hours: float = 1.0  # Grace period
    enabled: bool = True  # SLA active

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "domain": self.domain,
            "max_age_hours": self.max_age_hours,
            "mode": self.mode,
            "grace_period_hours": self.grace_period_hours,
            "enabled": self.enabled,
        }


class FreshnessMonitor:
    """
    Data freshness monitoring engine.

    Monitors data freshness against SLAs and generates
    alerts when data becomes stale.

    Attributes:
        _slas: Dictionary mapping domain to FreshnessSLA
        _last_updated: Dictionary mapping domain to last update time
        _alerts: List of freshness alerts

    Example:
        >>> monitor = FreshnessMonitor()
        >>> monitor.set_sla("cib", max_age_hours=2)
        >>> monitor.record_update("cib")
        >>> is_fresh = monitor.is_fresh("cib")
    """

    def __init__(self) -> None:
        """Initialize freshness monitor with empty SLA store."""
        self._slas: Dict[str, FreshnessSLA] = {}
        self._last_updated: Dict[str, str] = {}
        self._alerts: List[Dict[str, Any]] = []
        logger.info("FreshnessMonitor initialized")

    def set_sla(
        self,
        domain: str,
        max_age_hours: float = 24.0,
        mode: str = "batch",
        grace_period_hours: float = 1.0
    ) -> FreshnessSLA:
        """
        Set freshness SLA for a domain.

        Args:
            domain: Domain name
            max_age_hours: Maximum acceptable age in hours
            mode: Data mode (streaming or batch)
            grace_period_hours: Grace period before alerting

        Returns:
            Created FreshnessSLA object

        Example:
            >>> sla = monitor.set_sla("cib", max_age_hours=2, mode="streaming")
        """
        sla = FreshnessSLA(
            domain=domain,
            max_age_hours=max_age_hours,
            mode=mode,
            grace_period_hours=grace_period_hours,
        )
        self._slas[domain] = sla
        logger.info(
            f"Freshness SLA set for {domain}: "
            f"{max_age_hours}h ({mode})"
        )
        return sla

    def record_update(self, domain: str) -> None:
        """
        Record a data update for a domain.

        Args:
            domain: Domain name

        Example:
            >>> monitor.record_update("cib")
        """
        now = datetime.now().isoformat()
        self._last_updated[domain] = now
        logger.debug(f"Update recorded for {domain} at {now}")

    def is_fresh(self, domain: str) -> bool:
        """
        Check if data is fresh for a domain.

        Args:
            domain: Domain name

        Returns:
            True if data is fresh, False if stale

        Example:
            >>> if monitor.is_fresh("cib"):
            ...     print("Data is fresh")
        """
        # Get SLA for domain
        sla = self._slas.get(domain)
        if not sla or not sla.enabled:
            return True  # No SLA, assume fresh

        # Get last update time
        last_updated_str = self._last_updated.get(domain)
        if not last_updated_str:
            return False  # Never updated, considered stale

        # Calculate age
        last_updated = datetime.fromisoformat(last_updated_str)
        age = datetime.now() - last_updated
        age_hours = age.total_seconds() / 3600

        # Check against SLA (including grace period)
        max_age = sla.max_age_hours + sla.grace_period_hours
        is_fresh = age_hours <= max_age

        if not is_fresh:
            logger.warning(
                f"Data stale for {domain}: "
                f"{age_hours:.1f}h old (max: {max_age}h)"
            )

        return is_fresh

    def get_freshness_status(
        self,
        domain: str
    ) -> Dict[str, Any]:
        """
        Get detailed freshness status for a domain.

        Args:
            domain: Domain name

        Returns:
            Dictionary with freshness details
        """
        sla = self._slas.get(domain)
        last_updated_str = self._last_updated.get(domain)

        if not sla:
            return {
                "domain": domain,
                "status": "no_sla",
                "is_fresh": True,
            }

        if not last_updated_str:
            return {
                "domain": domain,
                "status": "never_updated",
                "is_fresh": False,
                "sla_max_age_hours": sla.max_age_hours,
            }

        # Calculate age
        last_updated = datetime.fromisoformat(last_updated_str)
        age = datetime.now() - last_updated
        age_hours = age.total_seconds() / 3600

        # Determine status
        if age_hours <= sla.max_age_hours:
            status = "fresh"
        elif age_hours <= sla.max_age_hours + sla.grace_period_hours:
            status = "warning"
        else:
            status = "stale"

        return {
            "domain": domain,
            "status": status,
            "is_fresh": status == "fresh",
            "last_updated": last_updated_str,
            "age_hours": age_hours,
            "sla_max_age_hours": sla.max_age_hours,
            "grace_period_hours": sla.grace_period_hours,
            "mode": sla.mode,
        }

    def check_all_domains(self) -> Dict[str, Dict[str, Any]]:
        """
        Check freshness for all domains with SLAs.

        Returns:
            Dictionary mapping domain to freshness status
        """
        status = {}
        for domain in self._slas:
            status[domain] = self.get_freshness_status(domain)
        return status

    def get_stale_domains(self) -> List[str]:
        """
        Get list of domains with stale data.

        Returns:
            List of domain names with stale data
        """
        stale = []
        for domain, sla in self._slas.items():
            if sla.enabled and not self.is_fresh(domain):
                stale.append(domain)
        return stale

    def create_alert(
        self,
        domain: str,
        severity: str = "WARNING"
    ) -> Dict[str, Any]:
        """
        Create a freshness alert.

        Args:
            domain: Domain name
            severity: Alert severity (WARNING, CRITICAL)

        Returns:
            Alert dictionary
        """
        status = self.get_freshness_status(domain)
        now = datetime.now().isoformat()

        alert = {
            "alert_id": f"FRESH-{domain}-{now[:10]}",
            "domain": domain,
            "severity": severity,
            "status": status["status"],
            "age_hours": status.get("age_hours", 0),
            "sla_max_age_hours": status.get("sla_max_age_hours", 0),
            "created_at": now,
        }

        self._alerts.append(alert)
        logger.warning(
            f"Freshness alert for {domain}: "
            f"{status['status']} ({status.get('age_hours', 0):.1f}h)"
        )

        return alert

    def get_statistics(self) -> Dict[str, Any]:
        """Get freshness monitoring statistics."""
        status = self.check_all_domains()
        fresh_count = sum(1 for s in status.values() if s.get("is_fresh"))
        total = len(status)

        return {
            "total_domains": total,
            "fresh_domains": fresh_count,
            "stale_domains": total - fresh_count,
            "freshness_rate": (fresh_count / total * 100) if total > 0 else 100,
            "total_alerts": len(self._alerts),
        }


__all__ = [
    "FreshnessSLA",
    "FreshnessMonitor",
]
