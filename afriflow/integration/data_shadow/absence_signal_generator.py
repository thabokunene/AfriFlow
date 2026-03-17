"""
Data Shadow - Absence Signal Generator

We generate structured absence signals from raw domain
snapshots. An absence signal is created when a domain
has NO data for a client that we know to be active in
other domains.

Types of absence signals:
  FOREX_ABSENT   — CIB active, no forex exposure or hedges
  INSURANCE_ABSENT — CIB active in corridor, no insurance
  CELL_ABSENT    — Corporate payroll running, no SIM data
  PBB_ABSENT     — Salary payments going out, no PBB accounts
  CIB_ABSENT     — Cell/PBB active, no CIB relationship

These are weaker signals than the gap_detector (which
does threshold-based scoring). Absence signals are the
raw inputs; gap_detector scores and ranks them.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from afriflow.logging_config import get_logger

logger = get_logger("integration.data_shadow.absence_signal_generator")


class AbsenceType(Enum):
    """Type of domain absence."""
    FOREX_ABSENT = "forex_absent"
    INSURANCE_ABSENT = "insurance_absent"
    CELL_ABSENT = "cell_absent"
    PBB_ABSENT = "pbb_absent"
    CIB_ABSENT = "cib_absent"
    DATA_STALE = "data_stale"         # Domain present but outdated
    PARTIAL_ABSENCE = "partial_absence"  # Some data but incomplete


@dataclass
class AbsenceSignal:
    """
    A raw absence signal for a client in a specific domain.

    Attributes:
        signal_id: Unique signal identifier
        client_golden_id: Client identifier
        absence_type: Type of absence detected
        absent_domain: Domain where data is missing
        present_domains: Domains where client IS active
        estimated_revenue_risk_usd: Potential revenue at risk
        signal_strength: 0–1 strength of the absence signal
        context: Supporting evidence dict
        generated_at: Signal generation timestamp
    """
    signal_id: str
    client_golden_id: str
    absence_type: AbsenceType
    absent_domain: str
    present_domains: List[str]
    estimated_revenue_risk_usd: float
    signal_strength: float
    context: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class AbsenceSignalGenerator:
    """
    We generate absence signals from multi-domain snapshots.

    For each client, we compare their activity profile across
    all five domains (CIB, Forex, Insurance, Cell, PBB) and
    flag any domains where we would expect activity but find none.

    Attributes:
        signals: Generated signals by client ID
    """

    # Revenue risk estimates per absent domain (USD per year)
    DOMAIN_REVENUE_RISK = {
        "forex": 50_000,
        "insurance": 30_000,
        "cell": 15_000,
        "pbb": 8_000,
        "cib": 100_000,
    }

    def __init__(self) -> None:
        self.signals: Dict[str, List[AbsenceSignal]] = {}
        self._counter = 0
        logger.info("AbsenceSignalGenerator initialized")

    def generate(
        self,
        client_golden_id: str,
        domain_snapshots: Dict[str, Optional[Dict[str, Any]]],
    ) -> List[AbsenceSignal]:
        """
        Generate absence signals for a client.

        Args:
            client_golden_id: Client golden record ID
            domain_snapshots: Dict of domain → snapshot data
                              (None means domain data absent)

        Returns:
            List of AbsenceSignal instances
        """
        signals: List[AbsenceSignal] = []
        present = [d for d, v in domain_snapshots.items() if v is not None]
        absent = [d for d, v in domain_snapshots.items() if v is None]

        if not present:
            logger.debug(f"No domain data at all for {client_golden_id}")
            return signals

        # Generate absence signals based on what's present vs absent
        for absent_domain in absent:
            signal = self._evaluate_absence(
                client_golden_id, absent_domain, present, domain_snapshots
            )
            if signal:
                signals.append(signal)

        # Also check for stale data
        for domain, snapshot in domain_snapshots.items():
            if snapshot and self._is_stale(snapshot):
                signal = self._create_stale_signal(
                    client_golden_id, domain, snapshot, present
                )
                signals.append(signal)

        if client_golden_id not in self.signals:
            self.signals[client_golden_id] = []
        self.signals[client_golden_id].extend(signals)

        logger.debug(
            f"Generated {len(signals)} absence signals for {client_golden_id}"
        )
        return signals

    def generate_batch(
        self,
        client_snapshots: List[Dict[str, Any]],
    ) -> Dict[str, List[AbsenceSignal]]:
        """
        Generate absence signals for multiple clients.

        Args:
            client_snapshots: List of dicts with keys:
                {client_golden_id: str, domain_snapshots: Dict}

        Returns:
            Dict of client_id → List[AbsenceSignal]
        """
        results = {}
        for item in client_snapshots:
            cid = item["client_golden_id"]
            results[cid] = self.generate(cid, item["domain_snapshots"])
        return results

    def _evaluate_absence(
        self,
        client_id: str,
        absent_domain: str,
        present_domains: List[str],
        snapshots: Dict[str, Any],
    ) -> Optional[AbsenceSignal]:
        """Evaluate whether an absence is significant given what's present."""
        # Determine signal strength based on what IS present
        strength = self._compute_signal_strength(absent_domain, present_domains, snapshots)

        if strength < 0.15:
            return None  # Too weak to report

        return self._create_absence_signal(
            client_id, absent_domain, present_domains, strength, snapshots
        )

    def _compute_signal_strength(
        self,
        absent_domain: str,
        present_domains: List[str],
        snapshots: Dict[str, Any],
    ) -> float:
        """Compute signal strength based on presence/absence combination."""
        # Key rules: which present domains imply which absent domains
        rules: Dict[str, List[str]] = {
            "forex": ["cib"],            # CIB without forex is suspicious
            "insurance": ["cib"],        # Large CIB without insurance
            "cell": ["cib", "pbb"],      # Corporate without cell
            "pbb": ["cib"],              # CIB without any PBB = no retail
            "cib": ["cell", "pbb"],      # Retail without CIB
        }
        implying = rules.get(absent_domain, [])
        overlap = [d for d in implying if d in present_domains]

        if not overlap:
            return 0.0

        # Scale by CIB activity size if available
        base_strength = len(overlap) / max(len(implying), 1)
        cib_data = snapshots.get("cib", {}) or {}
        cib_volume = cib_data.get("annual_payment_volume_usd", 0)

        if cib_volume > 1_000_000:
            return min(1.0, base_strength * 1.3)
        elif cib_volume > 100_000:
            return min(1.0, base_strength * 1.1)
        return base_strength

    def _create_absence_signal(
        self,
        client_id: str,
        absent_domain: str,
        present_domains: List[str],
        strength: float,
        snapshots: Dict[str, Any],
    ) -> AbsenceSignal:
        """Create an AbsenceSignal dataclass instance."""
        self._counter += 1
        absence_type_map = {
            "forex": AbsenceType.FOREX_ABSENT,
            "insurance": AbsenceType.INSURANCE_ABSENT,
            "cell": AbsenceType.CELL_ABSENT,
            "pbb": AbsenceType.PBB_ABSENT,
            "cib": AbsenceType.CIB_ABSENT,
        }
        cib_volume = (snapshots.get("cib", {}) or {}).get(
            "annual_payment_volume_usd", 0
        )
        revenue_risk = self.DOMAIN_REVENUE_RISK.get(absent_domain, 10_000)

        return AbsenceSignal(
            signal_id=f"ABS-{client_id}-{self._counter:04d}",
            client_golden_id=client_id,
            absence_type=absence_type_map.get(
                absent_domain, AbsenceType.PARTIAL_ABSENCE
            ),
            absent_domain=absent_domain,
            present_domains=present_domains,
            estimated_revenue_risk_usd=revenue_risk,
            signal_strength=round(strength, 3),
            context={
                "present_domains": present_domains,
                "cib_volume_usd": cib_volume,
            },
        )

    def _is_stale(self, snapshot: Dict[str, Any]) -> bool:
        """Check if snapshot data is older than 48 hours."""
        last_updated = snapshot.get("last_updated")
        if not last_updated:
            return False
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except ValueError:
                return False
        delta = (datetime.utcnow() - last_updated).total_seconds()
        return delta > 48 * 3600

    def _create_stale_signal(
        self,
        client_id: str,
        domain: str,
        snapshot: Dict[str, Any],
        present_domains: List[str],
    ) -> AbsenceSignal:
        """Create a DATA_STALE signal."""
        self._counter += 1
        return AbsenceSignal(
            signal_id=f"ABS-{client_id}-{self._counter:04d}",
            client_golden_id=client_id,
            absence_type=AbsenceType.DATA_STALE,
            absent_domain=domain,
            present_domains=present_domains,
            estimated_revenue_risk_usd=0.0,
            signal_strength=0.3,
            context={"stale_domain": domain, "last_updated": str(snapshot.get("last_updated"))},
        )

    def get_signals_by_type(
        self,
        absence_type: AbsenceType,
    ) -> List[AbsenceSignal]:
        """Get all signals of a specific type across all clients."""
        return [
            sig
            for signals in self.signals.values()
            for sig in signals
            if sig.absence_type == absence_type
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get signal generation statistics."""
        all_signals = [
            sig for signals in self.signals.values() for sig in signals
        ]
        by_type: Dict[str, int] = {}
        for sig in all_signals:
            key = sig.absence_type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_clients": len(self.signals),
            "total_signals": len(all_signals),
            "by_absence_type": by_type,
            "high_strength_signals": sum(
                1 for s in all_signals if s.signal_strength >= 0.7
            ),
        }


if __name__ == "__main__":
    gen = AbsenceSignalGenerator()

    snapshots = {
        "cib": {"annual_payment_volume_usd": 2_500_000, "last_updated": "2024-11-17T10:00:00"},
        "forex": None,       # No FX data!
        "insurance": None,   # No insurance!
        "cell": {"corporate_sim_count": 250},
        "pbb": None,
    }

    signals = gen.generate("GLD-001", snapshots)
    print(f"Generated {len(signals)} absence signals:")
    for sig in signals:
        print(f"  [{sig.signal_strength:.2f}] {sig.absence_type.value}: "
              f"absent={sig.absent_domain}, "
              f"revenue_risk=USD {sig.estimated_revenue_risk_usd:,.0f}")

    print(f"\nStats: {gen.get_statistics()}")
