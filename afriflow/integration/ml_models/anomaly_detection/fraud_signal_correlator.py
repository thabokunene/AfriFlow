"""
Fraud Signal Correlator

We aggregate individual fraud signals from all five domains
and compute a composite fraud risk score using weighted
evidence combination.

Individual domain fraud signals:
  CIB   : Round-number payments, corridor velocity, split-payment
  Forex : Sub-threshold FX, same-day reversal, ghost counterparty
  Cell  : SIM swap followed by MoMo outflow, USSD takeover pattern
  PBB   : Unusual cash deposit series, rapid withdrawal post-credit
  Insurance : Claim timing anomaly, multiple claims same incident

We use Dempster-Shafer evidence theory to combine signals:
  - Each domain produces a belief mass for {FRAUD, NOT_FRAUD, UNCERTAIN}
  - We combine beliefs using the DS combination rule
  - Final plausibility of FRAUD drives the composite score

For pan-African context we also maintain:
  - Country risk multipliers (NG > KE > ZA for fraud base rates)
  - Product risk multipliers (MoMo > Cash > Card > Wire)
  - Temporal clustering detection (signals in tight time window)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Country fraud multipliers (relative to ZA baseline = 1.0)
# Based on public FinCEN / FATF risk assessments
# ---------------------------------------------------------------------------

_COUNTRY_FRAUD_MULTIPLIER: Dict[str, float] = {
    "ZA": 1.00, "NG": 1.45, "GH": 1.20, "KE": 1.15,
    "TZ": 1.10, "UG": 1.18, "ZM": 1.08, "ZW": 1.25,
    "MZ": 1.12, "BW": 0.95, "NA": 0.98, "ET": 1.20,
    "CI": 1.22, "SN": 1.10, "CM": 1.18, "AO": 1.30,
    "MG": 1.15, "RW": 0.92, "MU": 0.90, "EG": 1.10,
}

# Product channel risk multipliers
_PRODUCT_RISK_MULTIPLIER: Dict[str, float] = {
    "momo": 1.35, "cash": 1.30, "ussd": 1.25,
    "card": 1.10, "eft": 1.05, "wire": 1.00,
    "trade_finance": 1.15, "fx": 1.20,
}

# SAR (Suspicious Activity Report) threshold
_SAR_COMPOSITE_THRESHOLD = 0.65


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class FraudSignal:
    """
    A single fraud indicator from one domain.

    belief_fraud       : 0–1 mass assigned to FRAUD hypothesis
    belief_not_fraud   : 0–1 mass assigned to NOT_FRAUD
    The remainder is assigned to UNCERTAIN.
    """

    signal_id: str
    domain: str
    signal_type: str
    description: str
    belief_fraud: float      # 0–1
    belief_not_fraud: float  # 0–1
    raw_evidence: Dict       # supporting data points


@dataclass
class FraudCorrelation:
    """
    Composite fraud assessment using DS evidence combination.

    plausibility_fraud : Upper bound on FRAUD probability (0–1)
    belief_fraud       : Lower bound (core belief in FRAUD)
    composite_score    : 0–100 risk score
    """

    client_golden_id: str
    composite_score: float
    plausibility_fraud: float
    belief_fraud: float
    fraud_band: str         # LOW / MEDIUM / HIGH / CRITICAL
    requires_sar: bool
    primary_domain: str
    contributing_signals: List[FraudSignal]
    temporal_clustering: bool   # Signals concentrated in <24h
    country_risk_factor: float
    narrative: str
    assessed_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Correlator
# ---------------------------------------------------------------------------

class FraudSignalCorrelator:
    """
    Combine multi-domain fraud signals using Dempster-Shafer
    evidence combination to produce a composite fraud risk score.

    Usage::

        correlator = FraudSignalCorrelator()
        signals = [
            correlator.build_cib_signal(cib_metrics),
            correlator.build_cell_signal(cell_metrics),
        ]
        result = correlator.correlate("GLD-001", "NG", signals)
    """

    def correlate(
        self,
        client_golden_id: str,
        country: str,
        signals: List[FraudSignal],
        transaction_timestamps: Optional[List[str]] = None,
    ) -> FraudCorrelation:
        """
        Combine fraud signals and return composite assessment.
        """
        if not signals:
            return FraudCorrelation(
                client_golden_id=client_golden_id,
                composite_score=0.0,
                plausibility_fraud=0.0,
                belief_fraud=0.0,
                fraud_band="LOW",
                requires_sar=False,
                primary_domain="none",
                contributing_signals=[],
                temporal_clustering=False,
                country_risk_factor=1.0,
                narrative="No fraud signals detected.",
            )

        # DS combination of all signals
        combined_fraud, combined_not_fraud = self._ds_combine(signals)
        combined_uncertain = max(
            0.0, 1.0 - combined_fraud - combined_not_fraud
        )

        # Plausibility = belief + uncertainty (upper probability)
        plausibility = combined_fraud + combined_uncertain

        # Country multiplier
        country_mult = _COUNTRY_FRAUD_MULTIPLIER.get(country, 1.0)

        # Composite score: plausibility × country risk × 100
        raw_score = plausibility * country_mult * 80
        composite = min(raw_score, 100.0)

        temporal = self._detect_temporal_clustering(
            transaction_timestamps or []
        )
        if temporal:
            composite = min(composite * 1.20, 100.0)

        band = self._fraud_band(composite)
        requires_sar = composite >= _SAR_COMPOSITE_THRESHOLD * 100

        # Primary domain is the one with highest individual belief_fraud
        primary = max(signals, key=lambda s: s.belief_fraud).domain

        narrative = self._build_narrative(
            signals, composite, country, temporal
        )

        return FraudCorrelation(
            client_golden_id=client_golden_id,
            composite_score=round(composite, 1),
            plausibility_fraud=round(plausibility, 3),
            belief_fraud=round(combined_fraud, 3),
            fraud_band=band,
            requires_sar=requires_sar,
            primary_domain=primary,
            contributing_signals=signals,
            temporal_clustering=temporal,
            country_risk_factor=country_mult,
            narrative=narrative,
        )

    # ------------------------------------------------------------------
    # Signal builders
    # ------------------------------------------------------------------

    def build_cib_signal(
        self, metrics: Dict
    ) -> Optional[FraudSignal]:
        """
        CIB fraud indicators: round-number payments, rapid split
        payment series, ghost counterparty countries.
        """
        if not metrics:
            return None

        evidence = {}
        score = 0.0

        # Round-number heuristic: > 3 payments at exact round thousands
        round_payments = metrics.get("round_number_payment_count", 0)
        if round_payments >= 3:
            score += 0.20
            evidence["round_payments"] = round_payments

        # Payment splitting: many payments just below threshold
        split_count = metrics.get("sub_threshold_payment_count_30d", 0)
        threshold = metrics.get("reporting_threshold_zar", 49_999)
        if split_count >= 5:
            score += 0.25
            evidence["split_payments"] = split_count

        # High-risk corridor payments
        high_risk_corridors = metrics.get("high_risk_corridor_payments", 0)
        if high_risk_corridors > 0:
            score += 0.15
            evidence["high_risk_corridors"] = high_risk_corridors

        score = min(score, 0.90)
        if score < 0.05:
            return None

        return FraudSignal(
            signal_id=f"CIB-FRAUD-{id(metrics)}",
            domain="cib",
            signal_type="PAYMENT_PATTERN",
            description=(
                f"CIB payment pattern anomaly: "
                f"{round_payments} round-number payments, "
                f"{split_count} sub-threshold splits"
            ),
            belief_fraud=round(score, 3),
            belief_not_fraud=round(max(0.0, 0.8 - score), 3),
            raw_evidence=evidence,
        )

    def build_cell_signal(
        self, metrics: Dict
    ) -> Optional[FraudSignal]:
        """
        Cell fraud indicators: SIM swap + immediate MoMo outflow,
        USSD session from new device followed by large transfer.
        """
        if not metrics:
            return None

        evidence = {}
        score = 0.0

        sim_swap_momo = metrics.get("sim_swap_followed_by_momo", False)
        if sim_swap_momo:
            score += 0.45
            evidence["sim_swap_momo"] = True

        new_device_transfer = metrics.get(
            "new_device_large_transfer", False
        )
        if new_device_transfer:
            score += 0.30
            evidence["new_device_transfer"] = True

        # Rapid account-to-account cycling via MoMo
        momo_cycling = metrics.get("momo_cycling_events_7d", 0)
        if momo_cycling >= 3:
            score += 0.20
            evidence["momo_cycling"] = momo_cycling

        score = min(score, 0.95)
        if score < 0.05:
            return None

        return FraudSignal(
            signal_id=f"CELL-FRAUD-{id(metrics)}",
            domain="cell",
            signal_type="ACCOUNT_TAKEOVER",
            description=(
                f"Cell fraud signals: SIM-swap-MoMo={sim_swap_momo}, "
                f"new-device-transfer={new_device_transfer}, "
                f"MoMo cycling events={momo_cycling}"
            ),
            belief_fraud=round(score, 3),
            belief_not_fraud=round(max(0.0, 0.8 - score), 3),
            raw_evidence=evidence,
        )

    def build_insurance_signal(
        self, metrics: Dict
    ) -> Optional[FraudSignal]:
        """
        Insurance fraud: multiple claims in short window,
        claim submitted immediately after policy inception.
        """
        if not metrics:
            return None

        evidence = {}
        score = 0.0

        claims_30d = metrics.get("claims_submitted_30d", 0)
        if claims_30d >= 3:
            score += 0.30
            evidence["claims_30d"] = claims_30d

        days_since_inception = metrics.get(
            "days_since_policy_inception_at_first_claim", 9999
        )
        if days_since_inception < 30:
            score += 0.40
            evidence["early_claim_days"] = days_since_inception

        score = min(score, 0.90)
        if score < 0.05:
            return None

        return FraudSignal(
            signal_id=f"INS-FRAUD-{id(metrics)}",
            domain="insurance",
            signal_type="CLAIM_PATTERN",
            description=(
                f"Insurance: {claims_30d} claims in 30 days; "
                f"first claim {days_since_inception} days post-inception"
            ),
            belief_fraud=round(score, 3),
            belief_not_fraud=round(max(0.0, 0.7 - score), 3),
            raw_evidence=evidence,
        )

    # ------------------------------------------------------------------
    # DS combination
    # ------------------------------------------------------------------

    def _ds_combine(
        self, signals: List[FraudSignal]
    ) -> Tuple[float, float]:
        """
        Simplified Dempster-Shafer combination of belief masses.

        We represent the frame {F=FRAUD, N=NOT_FRAUD, U=UNCERTAIN}.
        Each signal provides m(F), m(N), m(U) = 1 - m(F) - m(N).

        Full DS combination for two signals:
          m12(F) ∝ m1(F)·m2(F) + m1(F)·m2(U) + m1(U)·m2(F)
          m12(N) ∝ m1(N)·m2(N) + m1(N)·m2(U) + m1(U)·m2(N)
          Conflict K = m1(F)·m2(N) + m1(N)·m2(F)
          Normalise by 1/(1-K)

        We iterate pairwise over all signals.
        """
        if not signals:
            return 0.0, 0.0

        # Start with first signal
        m_f = signals[0].belief_fraud
        m_n = signals[0].belief_not_fraud
        m_u = max(0.0, 1.0 - m_f - m_n)

        for sig in signals[1:]:
            s_f = sig.belief_fraud
            s_n = sig.belief_not_fraud
            s_u = max(0.0, 1.0 - s_f - s_n)

            conflict = m_f * s_n + m_n * s_f
            normaliser = 1.0 - conflict
            if normaliser < 0.001:
                normaliser = 0.001

            new_f = (m_f * s_f + m_f * s_u + m_u * s_f) / normaliser
            new_n = (m_n * s_n + m_n * s_u + m_u * s_n) / normaliser
            new_u = (m_u * s_u) / normaliser

            # Clamp
            m_f = min(max(new_f, 0.0), 1.0)
            m_n = min(max(new_n, 0.0), 1.0)
            m_u = min(max(new_u, 0.0), 1.0)

        return m_f, m_n

    def _detect_temporal_clustering(
        self, timestamps: List[str]
    ) -> bool:
        """
        Return True if ≥3 signals occurred within a 24-hour window.
        """
        if len(timestamps) < 3:
            return False
        # We use ISO timestamps — compare by string prefix (date + hour)
        # A more robust check would parse timestamps, but stdlib datetime
        # parsing handles ISO format natively.
        try:
            from datetime import datetime as dt
            parsed = sorted(
                dt.fromisoformat(ts) for ts in timestamps
            )
            for i in range(len(parsed) - 2):
                delta = parsed[i + 2] - parsed[i]
                if delta.total_seconds() <= 86400:
                    return True
        except (ValueError, TypeError):
            pass
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fraud_band(self, score: float) -> str:
        if score >= 75:
            return "CRITICAL"
        elif score >= 55:
            return "HIGH"
        elif score >= 30:
            return "MEDIUM"
        return "LOW"

    def _build_narrative(
        self,
        signals: List[FraudSignal],
        score: float,
        country: str,
        temporal: bool,
    ) -> str:
        domains = [s.domain for s in signals]
        domain_str = " + ".join(domains)
        temporal_note = (
            " Signals are temporally clustered within 24h."
            if temporal else ""
        )
        mult = _COUNTRY_FRAUD_MULTIPLIER.get(country, 1.0)
        return (
            f"Composite fraud score {score:.1f}/100 from {domain_str} signals "
            f"(country risk factor {mult:.2f} for {country}).{temporal_note}"
        )
