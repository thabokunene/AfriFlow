"""
Leakage Detector

Detects competitive leakage where payment flows are being
captured by competitors instead of Standard Bank.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import logging

from afriflow.logging_config import get_logger

logger = get_logger("corridor.leakage_detector")


@dataclass
class LeakageSignal:
    """A detected leakage signal."""
    signal_id: str
    corridor_id: str
    client_id: Optional[str]
    leakage_type: str
    estimated_leakage: float
    confidence: float
    evidence: List[str]
    detected_at: datetime
    status: str = "new"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "corridor_id": self.corridor_id,
            "client_id": self.client_id,
            "leakage_type": self.leakage_type,
            "estimated_leakage": self.estimated_leakage,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
            "status": self.status,
        }


class LeakageDetector:
    """
    Competitive leakage detection.

    Identifies corridors where:
    - CIB has payments but FX has no hedging
    - Cell shows activity but PBB has no payroll
    - Insurance has no coverage despite operations
    - MoMo flows exceed formal CIB flows
    """

    def __init__(self):
        self._signals: Dict[str, LeakageSignal] = {}
        self._corridor_baselines: Dict[str, Dict[str, float]] = {}

        logger.info("LeakageDetector initialized")

    def detect_leakage(
        self,
        corridor_id: str,
        client_id: Optional[str],
        cib_volume: float,
        fx_capture: float,
        insurance_capture: float,
        pbb_capture: float,
        cell_activity: float,
    ) -> List[LeakageSignal]:
        """
        Detect leakage for a corridor.

        Args:
            corridor_id: Corridor to analyze
            client_id: Optional client identifier
            cib_volume: CIB payment volume
            fx_capture: FX hedging volume
            insurance_capture: Insurance premium
            pbb_capture: PBB deposits/payroll
            cell_activity: Cell/MoMo activity indicator

        Returns:
            List of LeakageSignal objects
        """
        signals = []
        now = datetime.now()

        # Check FX leakage
        if cib_volume > 0 and fx_capture == 0:
            signal = self._create_signal(
                corridor_id=corridor_id,
                client_id=client_id,
                leakage_type="fx_gap",
                estimated_leakage=cib_volume * 0.003,
                confidence=0.85,
                evidence=[
                    f"CIB volume: {cib_volume}",
                    "FX hedging: ZERO",
                    "Expected FX capture: 60-80%",
                ],
                detected_at=now,
            )
            signals.append(signal)

        # Check insurance leakage
        if cib_volume > 1000000 and insurance_capture == 0:
            signal = self._create_signal(
                corridor_id=corridor_id,
                client_id=client_id,
                leakage_type="insurance_gap",
                estimated_leakage=cib_volume * 0.002,
                confidence=0.75,
                evidence=[
                    f"CIB volume: {cib_volume}",
                    "Insurance coverage: ZERO",
                    "Expected premium: 0.1-0.3%",
                ],
                detected_at=now,
            )
            signals.append(signal)

        # Check PBB leakage (payroll capture)
        if cell_activity > 100 and pbb_capture == 0:
            signal = self._create_signal(
                corridor_id=corridor_id,
                client_id=client_id,
                leakage_type="payroll_gap",
                estimated_leakage=cell_activity * 2500,
                confidence=0.70,
                evidence=[
                    f"Cell activity: {cell_activity} SIMs",
                    "Payroll capture: ZERO",
                    "Expected employees: ~{int(cell_activity * 0.36)}",
                ],
                detected_at=now,
            )
            signals.append(signal)

        # Store signals
        for signal in signals:
            self._signals[signal.signal_id] = signal

        if signals:
            logger.warning(
                f"Detected {len(signals)} leakage signals "
                f"for corridor {corridor_id}"
            )

        return signals

    def _create_signal(
        self,
        corridor_id: str,
        client_id: Optional[str],
        leakage_type: str,
        estimated_leakage: float,
        confidence: float,
        evidence: List[str],
        detected_at: datetime,
    ) -> LeakageSignal:
        """Create a leakage signal."""
        import uuid

        signal_id = f"LEAK-{uuid.uuid4().hex[:12].upper()}"

        return LeakageSignal(
            signal_id=signal_id,
            corridor_id=corridor_id,
            client_id=client_id,
            leakage_type=leakage_type,
            estimated_leakage=estimated_leakage,
            confidence=confidence,
            evidence=evidence,
            detected_at=detected_at,
        )

    def get_signals_for_corridor(
        self, corridor_id: str
    ) -> List[LeakageSignal]:
        """Get all leakage signals for a corridor."""
        return [
            s for s in self._signals.values()
            if s.corridor_id == corridor_id
        ]

    def get_all_signals(
        self, status: Optional[str] = None
    ) -> List[LeakageSignal]:
        """Get all leakage signals."""
        signals = list(self._signals.values())
        if status:
            signals = [s for s in signals if s.status == status]
        return signals

    def mark_signal_actioned(
        self, signal_id: str
    ) -> None:
        """Mark a signal as actioned."""
        if signal_id not in self._signals:
            raise ValueError(f"Signal {signal_id} not found")
        self._signals[signal_id].status = "actioned"

    def get_statistics(self) -> Dict[str, Any]:
        """Get leakage detection statistics."""
        signals = list(self._signals.values())
        total_leakage = sum(s.estimated_leakage for s in signals)

        type_counts = {}
        for signal in signals:
            ltype = signal.leakage_type
            type_counts[ltype] = type_counts.get(ltype, 0) + 1

        status_counts = {}
        for signal in signals:
            status = signal.status
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_signals": len(signals),
            "total_estimated_leakage": total_leakage,
            "type_breakdown": type_counts,
            "status_breakdown": status_counts,
            "avg_confidence": (
                sum(s.confidence for s in signals) / len(signals)
                if signals else 0
            ),
        }
