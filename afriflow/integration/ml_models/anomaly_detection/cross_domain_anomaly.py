"""
@file cross_domain_anomaly.py
@description Detects cross-domain behavioural anomaly patterns by computing
             z-score deviations in each domain and flagging combinations that
             match named patterns (structured transactions, competitor market
             entry, fraud rings, salary diversion, all-domain silence).
             A single-domain anomaly is interesting; a cross-domain anomaly
             is alarming — it signals a real structural change.
             Anomaly scores of 70+ trigger a Suspicious Activity Report (SAR)
             flag for compliance review.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

import math        # Available for future statistical extensions
import statistics  # Available for future distribution calculations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Anomaly pattern registry
# ---------------------------------------------------------------------------
# Each pattern has a minimum composite score threshold to be reported.
# Thresholds are tuned to balance signal/noise: too low → alert fatigue;
# too high → missed real events.

_PATTERN_THRESHOLDS: Dict[str, float] = {
    "STRUCTURED_TRANSACTION":   65.0,  # CIB + FX spike — possible payment structuring
    "COMPETITOR_MARKET_ENTRY":  55.0,  # Cell surge + CIB flat — banking elsewhere
    "FRAUD_RING_SUSPICION":     70.0,  # Claims spike + PBB balance growth — fraud
    "SALARY_DIVERSION":         60.0,  # MoMo payroll > bank payroll — diversion
    "ALL_DOMAIN_SILENCE":       50.0,  # All domains declining — wind-down risk
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class DomainDeviation:
    """
    A single domain's deviation from its established baseline.

    z_score is the standard deviation distance from the baseline mean.
    Positive z = above baseline; negative z = below baseline.

    :param domain:         Domain name (cib / forex / insurance / cell / pbb).
    :param metric_name:    Primary metric being measured.
    :param current_value:  Latest observed metric value.
    :param baseline_mean:  Historical mean for the metric.
    :param baseline_std:   Historical standard deviation.
    :param z_score:        (current - mean) / std.
    :param direction:      UP (z > 0.5) / DOWN (z < -0.5) / FLAT.
    """

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

    anomaly_score       : 0–100 composite severity
    pattern_type        : named pattern (see _PATTERN_THRESHOLDS)
    correlation_coefficient : how synchronised the domain deviations are
                             (higher = more structural, less noise)

    :param anomaly_id:              Unique ID for this anomaly.
    :param client_golden_id:        AfriFlow golden record identifier.
    :param pattern_type:            Named anomaly pattern.
    :param anomaly_score:           Composite severity 0–100.
    :param correlation_coefficient: Agreement metric for domain deviations.
    :param severity:                LOW / MEDIUM / HIGH / CRITICAL.
    :param contributing_domains:    List of domains driving the anomaly.
    :param deviations:              Per-domain DomainDeviation details.
    :param narrative:               Plain-English explanation for compliance.
    :param requires_sar:            True if score >= SAR threshold (70).
    :param detected_at:             ISO timestamp.
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

    Each domain profile dict should contain the primary metric value
    plus baseline statistics (baseline_mean, baseline_std).  If baselines
    are absent we fall back to using the current value as its own mean,
    which produces a z-score of 0 (no anomaly from baseline).

    Usage::

        detector = CrossDomainAnomalyDetector()
        anomalies = detector.detect(
            golden_id="GLD-001",
            cib_metrics={"payment_volume_zar": 85_000_000,
                         "baseline_mean": 20_000_000,
                         "baseline_std": 5_000_000},
            forex_metrics={...},
        )
    """

    # Anomaly score above this threshold → flag for Suspicious Activity Report
    _SAR_THRESHOLD = 70.0

    def detect(
        self,
        golden_id: str,
        cib_metrics: Optional[Dict] = None,
        forex_metrics: Optional[Dict] = None,
        insurance_metrics: Optional[Dict] = None,
        cell_metrics: Optional[Dict] = None,
        pbb_metrics: Optional[Dict] = None,
    ) -> List[CrossDomainAnomaly]:
        """
        Detect all applicable cross-domain anomaly patterns for a client.

        :param golden_id:         Client golden record identifier.
        :param cib_metrics:       CIB domain metrics dict with baseline stats.
        :param forex_metrics:     Forex domain metrics dict.
        :param insurance_metrics: Insurance domain metrics dict.
        :param cell_metrics:      Cell domain metrics dict.
        :param pbb_metrics:       PBB domain metrics dict.
        :return:                  List of CrossDomainAnomaly instances detected.
        """

        # First compute per-domain z-score deviations — reused by all pattern detectors
        deviations = self._compute_deviations(
            cib_metrics, forex_metrics, insurance_metrics,
            cell_metrics, pbb_metrics
        )

        anomalies: List[CrossDomainAnomaly] = []

        # --- Pattern 1: Structured transaction (CIB + Forex spike) ---
        a = self._detect_structured_transaction(
            golden_id, deviations,
            cib_metrics, forex_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 2: Competitor market entry (Cell surge + CIB flat) ---
        a = self._detect_competitor_entry(
            golden_id, deviations,
            cib_metrics, cell_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 3: Fraud ring suspicion (Insurance spike + PBB growth) ---
        a = self._detect_fraud_ring(
            golden_id, deviations,
            insurance_metrics, pbb_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 4: Salary diversion (MoMo payroll > bank payroll) ---
        a = self._detect_salary_diversion(
            golden_id, deviations,
            cell_metrics, pbb_metrics
        )
        if a:
            anomalies.append(a)

        # --- Pattern 5: All-domain silence (broad declining signal) ---
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
        """
        Compute z-score deviations for each available domain.

        Each domain has one representative primary metric.  The z-score
        is (current - baseline_mean) / baseline_std.  If the domain dict
        is absent, no entry is created in the output.

        :param cib:       CIB metrics dict.
        :param forex:     Forex metrics dict.
        :param insurance: Insurance metrics dict.
        :param cell:      Cell metrics dict.
        :param pbb:       PBB metrics dict.
        :return:          Dict mapping domain name to DomainDeviation.
        """

        devs: Dict[str, DomainDeviation] = {}

        # (domain_name, metrics_dict, primary_metric_key) triples
        pairs = [
            ("cib",       cib,       "payment_volume_zar"),
            ("forex",     forex,     "daily_notional_zar"),
            ("insurance", insurance, "claim_count_30d"),
            ("cell",      cell,      "momo_transaction_count_30d"),
            ("pbb",       pbb,       "average_balance_zar"),
        ]

        for domain, metrics, primary_metric in pairs:
            if not metrics:
                continue  # Skip missing domains entirely

            current = metrics.get(primary_metric, 0.0)

            # If baseline is absent, use current value as mean (z-score = 0)
            mean = metrics.get("baseline_mean", current)
            std = metrics.get("baseline_std", 1.0)

            # Guard against zero std — would cause division by zero
            if std == 0:
                std = 1.0

            z = (current - mean) / std

            # Classify direction: ±0.5 std is considered "FLAT"
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
        CIB large payment spike + simultaneous FX notional spike.

        Classic structuring pattern: breaking a large payment into
        sub-reporting-threshold tranches while executing matching FX
        on the same day.  Both CIB and FX must be simultaneously elevated.

        Minimum z-scores: CIB >= 2.0 std, FX >= 1.5 std.

        :param golden_id: Client identifier.
        :param devs:      Pre-computed domain deviations.
        :param cib:       CIB metrics dict.
        :param forex:     Forex metrics dict.
        :return:          CrossDomainAnomaly or None if pattern not triggered.
        """
        # Both CIB and FX must have data for this pattern to fire
        if "cib" not in devs or "forex" not in devs:
            return None

        cib_z = devs["cib"].z_score
        forex_z = devs["forex"].z_score

        # Z-score thresholds: CIB must be >= 2 std above baseline (major spike)
        # FX must be >= 1.5 std (notable but slightly lower bar)
        if cib_z < 2.0 or forex_z < 1.5:
            return None

        # Score formula: each std above threshold contributes points
        score = min((cib_z * 15 + forex_z * 12), 100)

        # Apply minimum pattern threshold
        if score < _PATTERN_THRESHOLDS["STRUCTURED_TRANSACTION"]:
            return None

        # Correlation: are both z-scores pointing in the same direction?
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
        Cell SIM surge in new country + CIB silence in that same country.

        When the client is expanding geographically (new SIM activations)
        but CIB payment volumes remain flat or declining, the new market
        activity is being banked by a competitor.

        Pattern condition: Cell z-score >= 1.5 AND CIB z-score <= 0.5.

        :param golden_id: Client identifier.
        :param devs:      Pre-computed domain deviations.
        :param cib:       CIB metrics dict.
        :param cell:      Cell metrics dict.
        :return:          CrossDomainAnomaly or None.
        """
        if "cell" not in devs or "cib" not in devs:
            return None

        cell_z = devs["cell"].z_score
        cib_z = devs["cib"].z_score

        # Cell UP (expansion) while CIB FLAT or DOWN (not capturing the flows)
        if cell_z < 1.5 or cib_z > 0.5:
            return None

        # Score: cell surge weighted more heavily; CIB flat adds to severity
        score = min(cell_z * 18 + abs(cib_z) * 10, 100)

        if score < _PATTERN_THRESHOLDS["COMPETITOR_MARKET_ENTRY"]:
            return None

        # Correlation: invert CIB z-score (opposite direction = correlated signal)
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
            requires_sar=False,  # Competitor capture is a revenue risk, not SAR trigger
        )

    def _detect_fraud_ring(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        insurance: Optional[Dict],
        pbb: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        Insurance claims spike + simultaneous PBB balance growth.

        Fraudulent claims are being paid out and immediately deposited
        into bank accounts — the claims spike and balance growth are
        causally linked.  Both must be significantly elevated.

        Minimum z-scores: Insurance >= 2.5 std, PBB >= 1.5 std.

        :param golden_id: Client identifier.
        :param devs:      Pre-computed domain deviations.
        :param insurance: Insurance metrics dict.
        :param pbb:       PBB metrics dict.
        :return:          CrossDomainAnomaly or None.
        """
        if "insurance" not in devs or "pbb" not in devs:
            return None

        ins_z = devs["insurance"].z_score
        pbb_z = devs["pbb"].z_score

        # Higher thresholds for fraud ring — require strong evidence before flagging
        if ins_z < 2.5 or pbb_z < 1.5:
            return None

        # Insurance claims weighted more (primary signal); PBB balance growth secondary
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
            requires_sar=score >= self._SAR_THRESHOLD,  # SAR if score >= 70
        )

    def _detect_salary_diversion(
        self,
        golden_id: str,
        devs: Dict[str, DomainDeviation],
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> Optional[CrossDomainAnomaly]:
        """
        MoMo payroll disbursements significantly exceed bank payroll credits.

        When more than 40% of total payroll flows through MoMo channels
        rather than the bank, salary is being diverted to mobile wallets —
        possibly to avoid garnishments, tax obligations, or exchange controls.

        Trigger condition: MoMo share of total payroll >= 40%.

        :param golden_id: Client identifier.
        :param devs:      Pre-computed domain deviations.
        :param cell:      Cell metrics dict (contains MoMo payroll figure).
        :param pbb:       PBB metrics dict (contains bank payroll credits).
        :return:          CrossDomainAnomaly or None.
        """
        # Both raw metrics required — z-scores alone are insufficient here
        if not cell or not pbb:
            return None

        # Gross MoMo payroll disbursements in the period (ZAR)
        momo_payroll = cell.get("momo_payroll_disbursements_zar", 0.0)

        # Gross payroll credits processed through the bank account (ZAR)
        bank_payroll = pbb.get("payroll_credits_zar", 0.0)

        # Cannot compute a ratio if either side is zero
        if bank_payroll == 0 or momo_payroll == 0:
            return None

        # Fraction of total payroll flowing through MoMo channels
        diversion_ratio = momo_payroll / (momo_payroll + bank_payroll)

        # Only flag if MoMo accounts for 40%+ of payroll
        if diversion_ratio < 0.40:
            return None

        # Score: 40% diversion → score ≈ 32; 80% → score ≈ 64; 100% → score = 80
        score = min(diversion_ratio * 100 * 0.8, 100)

        if score < _PATTERN_THRESHOLDS["SALARY_DIVERSION"]:
            return None

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-SAL-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="SALARY_DIVERSION",
            anomaly_score=round(score, 1),
            # Use diversion_ratio as correlation proxy (0–1 measure of signal strength)
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
        All present domains show simultaneously declining signal.

        When a broad majority of domains are declining together (not just
        one), the client may be winding down, being acquired, or migrating
        entirely to a competitor bank.

        Trigger conditions:
          - At least 2 domains with data.
          - At least 2 domains with z-score < -1.0 (clearly below baseline).
          - At least 60% of observed domains are declining.

        :param golden_id: Client identifier.
        :param devs:      Pre-computed domain deviations.
        :return:          CrossDomainAnomaly or None.
        """
        # Need at least 2 domains to establish a pattern (1 could be noise)
        if len(devs) < 2:
            return None

        # Identify domains that are meaningfully below baseline (z < -1.0)
        down_domains = [
            d for d in devs.values() if d.z_score < -1.0
        ]

        # Require at least 2 declining domains
        if len(down_domains) < 2:
            return None

        # Require that declining domains represent at least 60% of observed domains
        fraction_down = len(down_domains) / len(devs)
        if fraction_down < 0.6:
            return None

        # Score based on average z-score depth and fraction of domains declining
        avg_z = sum(d.z_score for d in down_domains) / len(down_domains)
        score = min(abs(avg_z) * 15 * fraction_down, 100)

        if score < _PATTERN_THRESHOLDS["ALL_DOMAIN_SILENCE"]:
            return None

        # Names of the declining domains for the narrative
        domain_names = [d.domain for d in down_domains]

        return CrossDomainAnomaly(
            anomaly_id=f"XDOM-SILENCE-{golden_id}",
            client_golden_id=golden_id,
            pattern_type="ALL_DOMAIN_SILENCE",
            anomaly_score=round(score, 1),
            # Use fraction_down as the correlation proxy — higher = more domains aligned
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
            requires_sar=False,  # Wind-down is a commercial risk, not a SAR trigger
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _correlation(self, z_scores: List[float]) -> float:
        """
        Compute a simplified directional agreement coefficient for a set
        of z-scores.  Returns the absolute fraction of scores that share
        the same sign — 1.0 = fully correlated, 0.0 = mixed direction.

        This is not a Pearson correlation; it is a fast proxy to measure
        whether the anomalous deviations are all pointing the same way.

        :param z_scores: List of z-scores to evaluate.
        :return:         Agreement coefficient in [0, 1].
        """
        if len(z_scores) < 2:
            return 0.0

        # Map each z-score to +1 or -1 (exclude exact zero)
        signs = [1 if z > 0 else -1 for z in z_scores if z != 0]
        if not signs:
            return 0.0

        # Absolute sum of signs / count = how aligned they are
        return abs(sum(signs)) / len(signs)

    def _severity(self, score: float) -> str:
        """
        Map a 0–100 anomaly score to a severity label.

        :param score: Anomaly composite score.
        :return:      Severity label string.
        """
        if score >= 80:
            return "CRITICAL"
        elif score >= 65:
            return "HIGH"
        elif score >= 45:
            return "MEDIUM"
        return "LOW"
