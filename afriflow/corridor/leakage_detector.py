"""
@file leakage_detector.py
@description Corridor Leakage Detection - Competitive flow leakage identification
@author Thabo Kunene
@created 2026-03-19

This module detects competitive leakage where payment flows are being
captured by competitors instead of Standard Bank. It identifies corridors
and clients where the bank is losing business.

Key Classes:
- LeakageSignal: Detected leakage event with evidence
- LeakageDetector: Main engine for leakage detection

Features:
- Leakage detection based on volume ratios
- Client-level leakage identification
- Severity scoring (LOW, MEDIUM, HIGH, CRITICAL)
- Evidence collection for RM action

Usage:
    >>> from afriflow.corridor.leakage_detector import LeakageDetector
    >>> detector = LeakageDetector()
    >>> signals = detector.detect_leakage(
    ...     corridor_id="ZA-NG",
    ...     cib_volume=1000000,
    ...     estimated_total=5000000
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.leakage")


class LeakageSeverity(Enum):
    """
    Leakage severity level enumeration.

    Defines the severity of detected leakage:
    - LOW: <20% estimated leakage
    - MEDIUM: 20-40% estimated leakage
    - HIGH: 40-60% estimated leakage
    - CRITICAL: >60% estimated leakage
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class LeakageSignal:
    """
    Detected competitive leakage event.

    Represents a situation where the bank is losing
    payment flows to competitors.

    Attributes:
        signal_id: Unique identifier
        corridor_id: Corridor where leakage detected
        client_id: Client ID (if client-specific)
        severity: Severity level
        cib_volume: Volume captured by CIB
        estimated_total: Estimated total market volume
        leakage_percentage: Estimated leakage %
        evidence: List of evidence items
        detected_at: Detection timestamp
        status: Signal status (NEW, ACTIONED, CLOSED)

    Example:
        >>> signal = LeakageSignal(
        ...     signal_id="LEAK-001",
        ...     corridor_id="ZA-NG",
        ...     severity="HIGH",
        ...     leakage_percentage=45.0
        ... )
    """
    signal_id: str  # Unique signal identifier
    corridor_id: str  # Corridor identifier
    client_id: Optional[str] = None  # Client ID (if specific)
    severity: str = "MEDIUM"  # Severity level
    cib_volume: float = 0.0  # Volume captured by CIB
    estimated_total: float = 0.0  # Estimated total volume
    leakage_percentage: float = 0.0  # Leakage percentage
    evidence: List[str] = field(default_factory=list)  # Evidence items
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "NEW"  # Signal status

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "signal_id": self.signal_id,
            "corridor_id": self.corridor_id,
            "client_id": self.client_id,
            "severity": self.severity,
            "cib_volume": self.cib_volume,
            "estimated_total": self.estimated_total,
            "leakage_percentage": self.leakage_percentage,
            "evidence": self.evidence,
            "detected_at": self.detected_at,
            "status": self.status,
        }


class LeakageDetector:
    """
    Competitive leakage detection engine.

    Identifies corridors and clients where the bank is
    losing payment flows to competitors.

    Detection methods:
    - Volume ratio analysis (CIB vs estimated total)
    - Client flow monitoring
    - Corridor share tracking

    Attributes:
        _signals: Dictionary mapping signal_id to LeakageSignal
        _corridor_baselines: Baseline volumes for corridors

    Example:
        >>> detector = LeakageDetector()
        >>> signals = detector.detect_leakage(
        ...     corridor_id="ZA-NG",
        ...     cib_volume=1000000,
        ...     estimated_total=5000000
        ... )
    """

    # Leakage severity thresholds
    SEVERITY_THRESHOLDS = {
        "LOW": 0.20,  # <20% leakage
        "MEDIUM": 0.40,  # 20-40% leakage
        "HIGH": 0.60,  # 40-60% leakage
        # >60% is CRITICAL
    }

    def __init__(self) -> None:
        """Initialize leakage detector with empty signal store."""
        self._signals: Dict[str, LeakageSignal] = {}
        self._corridor_baselines: Dict[str, float] = {}
        logger.info("LeakageDetector initialized")

    def detect_leakage(
        self,
        corridor_id: str,
        cib_volume: float,
        estimated_total: float,
        client_id: Optional[str] = None
    ) -> List[LeakageSignal]:
        """
        Detect leakage for a corridor or client.

        Args:
            corridor_id: Corridor identifier
            cib_volume: Volume captured by CIB
            estimated_total: Estimated total market volume
            client_id: Optional client ID for client-specific detection

        Returns:
            List of detected LeakageSignal objects
        """
        signals = []

        # Calculate leakage percentage
        if estimated_total > 0:
            leakage_pct = (estimated_total - cib_volume) / estimated_total
        else:
            leakage_pct = 0.0

        # Only create signal if leakage exceeds threshold
        if leakage_pct > self.SEVERITY_THRESHOLDS["LOW"]:
            # Determine severity level
            severity = self._calculate_severity(leakage_pct)

            # Generate unique signal ID
            signal_id = f"LEAK-{corridor_id}-{datetime.now().strftime('%Y%m%d')}"
            if client_id:
                signal_id += f"-{client_id}"

            # Create leakage signal
            signal = LeakageSignal(
                signal_id=signal_id,
                corridor_id=corridor_id,
                client_id=client_id,
                severity=severity,
                cib_volume=cib_volume,
                estimated_total=estimated_total,
                leakage_percentage=leakage_pct * 100,
                evidence=[
                    f"CIB volume: {cib_volume} ZAR",
                    f"Estimated total: {estimated_total} ZAR",
                    f"Leakage: {leakage_pct * 100:.1f}%",
                ],
            )

            # Store signal
            self._signals[signal_id] = signal
            signals.append(signal)

            logger.warning(
                f"Leakage detected: {corridor_id} - {leakage_pct * 100:.1f}% ({severity})"
            )

        return signals

    def _calculate_severity(self, leakage_pct: float) -> str:
        """
        Calculate severity level from leakage percentage.

        Args:
            leakage_pct: Leakage percentage (0-1)

        Returns:
            Severity level string
        """
        if leakage_pct > self.SEVERITY_THRESHOLDS["HIGH"]:
            return LeakageSeverity.CRITICAL.value
        elif leakage_pct > self.SEVERITY_THRESHOLDS["MEDIUM"]:
            return LeakageSeverity.HIGH.value
        elif leakage_pct > self.SEVERITY_THRESHOLDS["LOW"]:
            return LeakageSeverity.MEDIUM.value
        else:
            return LeakageSeverity.LOW.value

    def get_signals(
        self,
        corridor_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[LeakageSignal]:
        """
        Get leakage signals with optional filters.

        Args:
            corridor_id: Filter by corridor
            severity: Filter by severity level
            status: Filter by status

        Returns:
            List of matching LeakageSignal objects
        """
        signals = list(self._signals.values())

        # Apply filters
        if corridor_id:
            signals = [s for s in signals if s.corridor_id == corridor_id]
        if severity:
            signals = [s for s in signals if s.severity == severity]
        if status:
            signals = [s for s in signals if s.status == status]

        return signals

    def mark_actioned(self, signal_id: str) -> bool:
        """
        Mark a leakage signal as actioned.

        Args:
            signal_id: Signal identifier

        Returns:
            True if updated successfully
        """
        signal = self._signals.get(signal_id)
        if signal:
            signal.status = "ACTIONED"
            logger.info(f"Signal {signal_id} marked as actioned")
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get leakage detection statistics."""
        signals = list(self._signals.values())
        severity_counts = {}
        status_counts = {}

        for signal in signals:
            sev = signal.severity
            status = signal.status
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1

        total_leakage = sum(
            s.estimated_total - s.cib_volume for s in signals
        )

        return {
            "total_signals": len(signals),
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts,
            "total_leakage_volume": total_leakage,
        }


__all__ = [
    "LeakageSeverity",
    "LeakageSignal",
    "LeakageDetector",
]
