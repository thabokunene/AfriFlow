"""
Cross-Domain Anomaly Detector

A single-domain anomaly is interesting. A cross-domain anomaly
is alarming — it means something real is happening.

We look for patterns where multiple domains deviate simultaneously:

  Pattern 1: CIB + Forex spike — large cross-border payment AND
             a simultaneous FX rate move → structured transaction?

  Pattern 2: Cell expansion + CIB silence — SIM activations surge
             in new country while CIB payment corridor stays flat
             → competitor bank used for new market entry.

  Pattern 3: Insurance + PBB divergence — insurance claims spike
             while PBB balances grow → fraud ring suspicion.

  Pattern 4: Cell + CIB payroll gap — MoMo payroll disbursements
             exceed linked bank payroll → salary diversion.

  Pattern 5: All-domain silence — client goes quiet across all
             channels simultaneously → possible wind-down or
             acquisition by competitor.

Each anomaly is scored 0–100. We also compute a cross-domain
correlation coefficient to measure how synchronised the deviations
are (high correlation = structural anomaly, not noise).

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Anomaly pattern registry
# ---------------------------------------------------------------------------

_PATTERN_THRESHOLDS: Dict[str, float] = {
    "STRUCTURED_TRANSACTION":   65.0,
    "COMPETITOR_MARKET_ENTRY":  55.0,
    "FRAUD_RING_SUSPICION":     70.0,
    "SALARY_DIVERSION":         60.0,
    "ALL_DOMAIN_SILENCE":       50.0,
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class DomainDeviation:
    """A single domain's deviation from its baseline."""

    domain: str
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    direction: str    # UP / DOWN / FLAT


@dataclass
class CrossDomainAnomaly:
    """
    A detected cross-domain anomaly pattern.

    anomaly_score : 0–100 composite severity
    pattern_type  : the named pattern (see module docstring)
    correlation   : Pearson-like coefficient of domain deviations
    """

    anomaly_id: str
    client_golden_id: str
    pattern_type: str
    anomaly_score: float
    correlation_coefficient: float
    severity: str     # LOW / MEDIUM / HIGH / CRITICAL
    contributing_domains: List[str]
    deviations: List[DomainDeviation]
    narrative: str
    requires_sar: bool    # Suspicious Activity Report threshold
    detected_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class CrossDomainAnomalyDetector:
    """
    Detect cross-domain behavioural anomalies for a single client.

    Each domain profile should contain recent metrics and historical
    baseline statistics (mean, std). If baselines are absent we
    fall back to inter-domain comparison.

    Usage::

        detector = CrossDomainAnomalyDetector()
        anomalies = detector.detect(
            golden_id="GLD-001",
            cib_metrics={"payment_volume_zar": 85_000_000, "baseline_mean": 20_000_000, "baseline_std": 5_000_000},
            forex_metrics={...},
            ...
        )
    """

    _SAR_THRESHOLD = 70.0   # Anomaly score above this → flag for SAR

    def detect(
        self,
        golden_id: str,
        cib_metrics: Optional[Dict] = None,
        forex_metrics: Optional[Dict] = None,
        insurance_metrics: Optional[Dict] = None,
        cell_metrics: Optional[Dict] = None,
        pbb_metrics: Optional[Dict] = None,
    ) -> List[CrossDomainAnomaly]:
        """Detect all applicable cross-domain anomaly patterns."""

        deviations = self._compute_deviations(
            cib_metrics, forex_metrics, insurance_metrics,
            cell_metrics, pbb_metrics
        )

        anomalies: List[CrossDomainAnomaly] = []

        # --- Pattern 1: Structured transaction ---
        a = self._detect_structured_transaction(
            golden_id, deviations,
            cib_metrics, forex_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 2: Competitor market entry ---
        a = self._detect_competitor_entry(
            golden_id, deviations,
            cib_metrics, cell_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 3: Fraud ring suspicion ---
        a = self._detect_fraud_ring(
            golden_id, deviations,
            insurance_metrics, pbb_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 4: Salary diversion ---
        a = self._detect_salary_diversion(
            golden_id, deviations,
            cell_metrics, pbb_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 5: All-domain silence ---
        a = self._detect_all_domain_silence(
            golden_id, deviations
        )
        if a:
            anomalies.append(a)

        return anomalies

    # ------------------------------------------------------------------
    # Deviation computation
    # ------------------------------------------------------------------

    def _compute_deviations(
        self,
        cib: Optional[Dict],
        forex: Optional[Dict],
        insurance: Optional[Dict],
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> Dict[str, DomainDeviation]:
        """Compute z-score deviations for each available domain."""

        devs: Dict[str, DomainDeviation] = {}

        pairs = [
            ("cib", cib, "payment_volume_zar"),
            ("forex", forex, "daily_notional_zar"),
            ("insurance", insurance, "claim_count_30d"),
            ("cell", cell, "momo_transaction_count_30d"),
            ("pbb", pbb, "average_balance_zar"),
        ]

        for domain, metrics, primary_metric in pairs:
            if not metrics:
                continue
            current = metrics.get(primary_metric, 0.0)
            mean = metrics.get("baseline_mean", current)
            std = metrics.get("baseline_std", 1.0)
            if std == 0:
                std = 1.0
            z = (current - mean) / std
            direction = "UP" if z > 0.5 else ("DOWN" if z < -0.5 else "FLAT")
            devs[domain] = DomainDeviation(
                domain=domain,
                metric_name=primary_metric,
                current_value=current,
                baseline_mean=mean,
                baseline_std=std,
                z_score=round(z, 3),
                direction=direction,
            )

        return devs

    # ------------------------------------------------------------------
    # Pattern detectors
    # ------------------------------------------------------------------

    def _detect_structured_transaction(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        cib: Optional[Dict],
        forex: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        CIB large payment spike + simultaneous FX move.
        Classic structuring: breaking a large payment into
        sub-threshold tranches while using spot FX.
        """
        if "cib" not in devs or "forex" not in devs:
            return None

        cib_z = devs["cib"].z_score
        forex_z = devs["forex"].z_score

        if cib_z < 2.0 or forex_z < 1.5:
            return None

        score = min((cib_z * 15 + forex_z * 12), 100)
        if score < _PATTERN_THRESHOLDS["STRUCTURED_TRANSACTION"]:
            return None

        corr = self._correlation([cib_z, forex_z])

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-STRUCT-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="STRUCTURED_TRANSACTION",
            anomaly_score=round(score, 1),
            correlation_coefficient=round(corr, 3),
            severity=self._severity(score),
            contributing_domains=["cib", "forex"],
            deviations=[devs["cib"], devs["forex"]],
            narrative=(
                f"CIB payment volume is {cib_z:.1f} standard deviations "
                f"above baseline while FX notional is {forex_z:.1f} σ "
                f"above baseline simultaneously. Pattern consistent with "
                f"structured cross-border payments."
            ),
            requires_sar=score >= self._SAR_THRESHOLD,
        )

    def _detect_competitor_entry(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        cib: Optional[Dict],
        cell: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        Cell SIM surge in new country + CIB silence in same country.
        Client is expanding but using a competitor bank.
        """
        if "cell" not in devs or "cib" not in devs:
            return None

        cell_z = devs["cell"].z_score
        cib_z = devs["cib"].z_score

        # Cell UP + CIB FLAT/DOWN = competitor capture
        if cell_z < 1.5 or cib_z > 0.5:
            return None

        score = min(cell_z * 18 + abs(cib_z) * 10, 100)
        if score < _PATTERN_THRESHOLDS["COMPETITOR_MARKET_ENTRY"]:
            return None

        corr = self._correlation([cell_z, -cib_z])

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-COMP-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="COMPETITOR_MARKET_ENTRY",
            anomaly_score=round(score, 1),
            correlation_coefficient=round(corr, 3),
            severity=self._severity(score),
            contributing_domains=["cell", "cib"],
            deviations=[devs["cell"], devs["cib"]],
            narrative=(
                f"Cell MoMo activity is {cell_z:.1f} σ above baseline "
                f"while CIB payment volumes are flat/declining "
                f"({cib_z:.1f} σ). Pattern consistent with geographic "
                f"expansion being banked elsewhere."
            ),
            requires_sar=False,
        )

    def _detect_fraud_ring(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        insurance: Optional[Dict],
        pbb: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        Insurance claims spike + PBB balance growth.
        Fraudulent claims being funnelled into bank accounts.
        """
        if "insurance" not in devs or "pbb" not in devs:
            return None

        ins_z = devs["insurance"].z_score
        pbb_z = devs["pbb"].z_score

        if ins_z < 2.5 or pbb_z < 1.5:
            return None

        score = min(ins_z * 18 + pbb_z * 12, 100)
        if score < _PATTERN_THRESHOLDS["FRAUD_RING_SUSPICION"]:
            return None

        corr = self._correlation([ins_z, pbb_z])

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-FRAUD-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="FRAUD_RING_SUSPICION",
            anomaly_score=round(score, 1),
            correlation_coefficient=round(corr, 3),
            severity=self._severity(score),
            contributing_domains=["insurance", "pbb"],
            deviations=[devs["insurance"], devs["pbb"]],
            narrative=(
                f"Insurance claim count is {ins_z:.1f} σ above baseline "
                f"while PBB balances grew {pbb_z:.1f} σ in the same period. "
                f"Timing correlation warrants fraud investigation."
            ),
            requires_sar=score >= self._SAR_THRESHOLD,
        )

    def _detect_salary_diversion(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        MoMo payroll disbursements exceed linked bank payroll.
        Salary being diverted through informal channels.
        """
        if not cell or not pbb:
            return None

        momo_payroll = cell.get("momo_payroll_disbursements_zar", 0.0)
        bank_payroll = pbb.get("payroll_credits_zar", 0.0)

        if bank_payroll == 0 or momo_payroll == 0:
            return None

        diversion_ratio = momo_payroll / (momo_payroll + bank_payroll)
        if diversion_ratio < 0.40:
            return None

        score = min(diversion_ratio * 100 * 0.8, 100)
        if score < _PATTERN_THRESHOLDS["SALARY_DIVERSION"]:
            return None

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-SAL-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="SALARY_DIVERSION",
            anomaly_score=round(score, 1),
            correlation_coefficient=round(diversion_ratio, 3),
            severity=self._severity(score),
            contributing_domains=["cell", "pbb"],
            deviations=[
                d for k, d in devs.items() if k in ("cell", "pbb")
            ],
            narrative=(
                f"{diversion_ratio*100:.0f}% of payroll is being "
                f"disbursed via MoMo channels (R{momo_payroll:,.0f}) "
                f"vs bank payroll credits (R{bank_payroll:,.0f}). "
                f"Possible payroll diversion to mobile wallets."
            ),
            requires_sar=score >= self._SAR_THRESHOLD,
        )

    def _detect_all_domain_silence(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
    ) -> Optional[CrossDomainAnomaly]:
        """
        All present domains show declining signal simultaneously.
        Client may be winding down or moving entirely to competitor.
        """
        if len(devs) < 2:
            return None

        down_domains = [
            d for d in devs.values() if d.z_score < -1.0
        ]

        if len(down_domains) < 2:
            return None

        fraction_down = len(down_domains) / len(devs)
        if fraction_down < 0.6:
            return None

        avg_z = sum(d.z_score for d in down_domains) / len(down_domains)
        score = min(abs(avg_z) * 15 * fraction_down, 100)

        if score < _PATTERN_THRESHOLDS["ALL_DOMAIN_SILENCE"]:
            return None

        domain_names = [d.domain for d in down_domains]

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-SILENCE-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="ALL_DOMAIN_SILENCE",
            anomaly_score=round(score, 1),
            correlation_coefficient=round(fraction_down, 3),
            severity=self._severity(score),
            contributing_domains=domain_names,
            deviations=down_domains,
            narrative=(
                f"{len(down_domains)} of {len(devs)} domains "
                f"({', '.join(domain_names)}) are simultaneously "
                f"declining. Average z-score: {avg_z:.1f}. "
                f"Consistent with relationship wind-down."
            ),
            requires_sar=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _correlation(self, z_scores: List[float]) -> float:
        """Simplified 'agreement' score for a set of z-scores."""
        if len(z_scores) < 2:
            return 0.0
        signs = [1 if z > 0 else -1 for z in z_scores if z != 0]
        if not signs:
            return 0.0
        return abs(sum(signs)) / len(signs)

    def _severity(self, score: float) -> str:
        if score >= 80:
            return "CRITICAL"
        elif score >= 65:
            return "HIGH"
        elif score >= 45:
            return "MEDIUM"
        return "LOW"
