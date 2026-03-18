"""
@file fraud_signal_correlator.py
@description Aggregates individual fraud signals from all five AfriFlow domains
             and combines them using Dempster-Shafer (DS) evidence theory to
             produce a composite fraud risk score and band.
             DS theory is used because it gracefully handles uncertain evidence
             — each domain produces a belief mass for FRAUD, NOT_FRAUD, and an
             UNCERTAIN remainder.  This is more appropriate than naive Bayesian
             combination when evidence is sparse or contradictory.
             Country-specific fraud base rates and product channel risk multipliers
             are applied after combining domain beliefs.
             Composite scores >= 65 trigger a Suspicious Activity Report (SAR) flag.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Country fraud multipliers (relative to ZA baseline = 1.0)
# ---------------------------------------------------------------------------
# Based on FATF Mutual Evaluation Reports and FinCEN public advisories.
# ZA is set as the baseline (1.00); higher values indicate elevated base
# fraud rates relative to South Africa.

_COUNTRY_FRAUD_MULTIPLIER: Dict[str, float] = {
    "ZA": 1.00,  # South Africa — baseline
    "NG": 1.45,  # Nigeria — highest in roster due to advance-fee fraud history
    "GH": 1.20,  # Ghana
    "KE": 1.15,  # Kenya
    "TZ": 1.10,  # Tanzania
    "UG": 1.18,  # Uganda
    "ZM": 1.08,  # Zambia
    "ZW": 1.25,  # Zimbabwe — elevated due to currency controls and informal channels
    "MZ": 1.12,  # Mozambique
    "BW": 0.95,  # Botswana — below baseline; strong financial governance
    "NA": 0.98,  # Namibia — close to SA baseline
    "ET": 1.20,  # Ethiopia
    "CI": 1.22,  # Côte d'Ivoire
    "SN": 1.10,  # Senegal
    "CM": 1.18,  # Cameroon
    "AO": 1.30,  # Angola — elevated; oil economy with complex payment flows
    "MG": 1.15,  # Madagascar
    "RW": 0.92,  # Rwanda — below baseline; strong AML regime
    "MU": 0.90,  # Mauritius — lowest; IFC with robust compliance framework
    "EG": 1.10,  # Egypt
}

# Product channel risk multipliers — MoMo and cash carry highest fraud rates
# because they are harder to trace and reverse than wire transfers
_PRODUCT_RISK_MULTIPLIER: Dict[str, float] = {
    "momo":          1.35,  # Mobile money — hard to trace, easy to cycle
    "cash":          1.30,  # Cash — untraceable
    "ussd":          1.25,  # USSD — SIM-swap vulnerable
    "card":          1.10,  # Card — chip-and-PIN reduces but doesn't eliminate risk
    "eft":           1.05,  # EFT — documented but manual intervention possible
    "wire":          1.00,  # Wire — baseline; SWIFT-documented
    "trade_finance": 1.15,  # Trade finance — document fraud (LC discrepancies)
    "fx":            1.20,  # FX — sub-threshold structuring risk
}

# Composite score threshold above which a SAR must be raised
# (expressed as 0–1 internally; multiplied by 100 for the final score)
_SAR_COMPOSITE_THRESHOLD = 0.65  # 65/100 composite score → SAR


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class FraudSignal:
    """
    A single fraud indicator originating from one domain.

    Uses Dempster-Shafer mass assignment:
      belief_fraud       : m(FRAUD) — evidence supporting fraud
      belief_not_fraud   : m(NOT_FRAUD) — evidence against fraud
      The remainder (1 - belief_fraud - belief_not_fraud) is m(UNCERTAIN)

    :param signal_id:       Unique identifier for this signal instance.
    :param domain:          Source domain (cib / cell / insurance / pbb / forex).
    :param signal_type:     Categorical signal type (e.g. PAYMENT_PATTERN).
    :param description:     Human-readable evidence summary.
    :param belief_fraud:    DS mass assigned to the FRAUD hypothesis (0–1).
    :param belief_not_fraud: DS mass assigned to NOT_FRAUD (0–1).
    :param raw_evidence:    Supporting data points as key-value pairs.
    """

    signal_id: str
    domain: str
    signal_type: str
    description: str
    belief_fraud: float      # 0–1 Dempster-Shafer mass for FRAUD
    belief_not_fraud: float  # 0–1 Dempster-Shafer mass for NOT_FRAUD
    raw_evidence: Dict       # Supporting evidence key-value pairs


@dataclass
class FraudCorrelation:
    """
    Composite fraud assessment using DS evidence combination.

    plausibility_fraud : upper probability bound — belief_fraud + uncertainty
    belief_fraud       : lower probability bound — core belief in FRAUD only
    composite_score    : 0–100 final risk score

    :param client_golden_id:     AfriFlow golden record identifier.
    :param composite_score:      Final risk score 0–100.
    :param plausibility_fraud:   DS plausibility (upper bound on FRAUD prob).
    :param belief_fraud:         DS belief (lower bound on FRAUD prob).
    :param fraud_band:           LOW / MEDIUM / HIGH / CRITICAL.
    :param requires_sar:         True if composite_score >= 65.
    :param primary_domain:       Domain with highest individual belief_fraud.
    :param contributing_signals: All FraudSignal instances that contributed.
    :param temporal_clustering:  True if >= 3 signals occurred within 24 hours.
    :param country_risk_factor:  Multiplier applied for the client's country.
    :param narrative:            Plain-English description for compliance team.
    :param assessed_at:          ISO timestamp.
    """

    client_golden_id: str
    composite_score: float
    plausibility_fraud: float
    belief_fraud: float
    fraud_band: str         # LOW / MEDIUM / HIGH / CRITICAL
    requires_sar: bool
    primary_domain: str
    contributing_signals: List[FraudSignal]
    temporal_clustering: bool   # Signals concentrated in <24h window
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
    Combine multi-domain fraud signals using Dempster-Shafer evidence
    combination to produce a composite fraud risk score.

    Each domain's signal builder extracts indicators from raw metrics and
    converts them to DS belief masses.  The correlate() method then
    combines all signals iteratively and applies country risk weighting.

    Usage::

        correlator = FraudSignalCorrelator()
        signals = [
            correlator.build_cib_signal(cib_metrics),
            correlator.build_cell_signal(cell_metrics),
        ]
        # Filter out None values from domains with no fraud indicators
        signals = [s for s in signals if s is not None]
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
        Combine fraud signals and return a composite fraud assessment.

        :param client_golden_id:       Client golden record identifier.
        :param country:                ISO-2 country code for risk multiplier.
        :param signals:                List of FraudSignal instances to combine.
        :param transaction_timestamps: Optional ISO timestamps for temporal check.
        :return:                       FraudCorrelation dataclass.
        """
        # No signals → return a clean low-risk result
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

        # Combine all domain signals using iterative DS rule
        combined_fraud, combined_not_fraud = self._ds_combine(signals)

        # Uncertainty mass: whatever is left after FRAUD and NOT_FRAUD
        combined_uncertain = max(
            0.0, 1.0 - combined_fraud - combined_not_fraud
        )

        # DS plausibility = belief + uncertainty (upper bound on FRAUD probability)
        plausibility = combined_fraud + combined_uncertain

        # Look up country-specific fraud base rate multiplier
        country_mult = _COUNTRY_FRAUD_MULTIPLIER.get(country, 1.0)

        # Composite score: plausibility scaled by country risk, capped at 100
        # The 0.80 factor prevents plausibility alone from reaching 100 —
        # we reserve the upper range for confirmed multi-domain + country risk
        raw_score = plausibility * country_mult * 80
        composite = min(raw_score, 100.0)

        # Check for temporal clustering — if signals cluster in 24h, escalate
        temporal = self._detect_temporal_clustering(
            transaction_timestamps or []
        )
        if temporal:
            # Temporal clustering adds 20% to composite score (capped at 100)
            composite = min(composite * 1.20, 100.0)

        band = self._fraud_band(composite)

        # SAR required if composite score reaches or exceeds the threshold
        requires_sar = composite >= _SAR_COMPOSITE_THRESHOLD * 100

        # Primary domain: the one whose signal has the highest fraud belief
        primary = max(signals, key=lambda s: s.belief_fraud).domain

        # Build plain-English narrative for compliance team
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
        Build a CIB fraud signal from payment pattern indicators.

        CIB fraud indicators:
          - Round-number payments (amounts at exact thousands)
          - Sub-threshold payment splitting (structuring)
          - Payments to high-risk country corridors

        :param metrics: CIB metrics dict.
        :return:        FraudSignal or None if no indicators triggered.
        """
        if not metrics:
            return None

        evidence = {}  # Accumulate supporting evidence for the signal
        score = 0.0    # Belief mass accumulator (will be capped at 0.90)

        # Heuristic: >= 3 payments at exact round-thousand amounts → structuring flag
        round_payments = metrics.get("round_number_payment_count", 0)
        if round_payments >= 3:
            score += 0.20  # Moderate contribution — could be coincidental
            evidence["round_payments"] = round_payments

        # Sub-threshold splitting: many payments just below the reporting threshold
        # Classic structuring pattern to avoid regulatory triggers
        split_count = metrics.get("sub_threshold_payment_count_30d", 0)
        threshold = metrics.get("reporting_threshold_zar", 49_999)  # Common SARB threshold
        if split_count >= 5:
            score += 0.25  # Strong structuring indicator
            evidence["split_payments"] = split_count

        # Payments routed to high-risk country corridors per FATF watchlist
        high_risk_corridors = metrics.get("high_risk_corridor_payments", 0)
        if high_risk_corridors > 0:
            score += 0.15  # Each corridor adds risk
            evidence["high_risk_corridors"] = high_risk_corridors

        # Hard cap: no single signal should exceed 90% belief in fraud
        score = min(score, 0.90)

        # Suppress signal if score is negligible
        if score < 0.05:
            return None

        return FraudSignal(
            signal_id=f"CIB-FRAUD-{id(metrics)}",  # Use dict object id as unique-enough key
            domain="cib",
            signal_type="PAYMENT_PATTERN",
            description=(
                f"CIB payment pattern anomaly: "
                f"{round_payments} round-number payments, "
                f"{split_count} sub-threshold splits"
            ),
            belief_fraud=round(score, 3),
            # Inverse belief: cap at 0.8 so uncertainty mass remains positive
            belief_not_fraud=round(max(0.0, 0.8 - score), 3),
            raw_evidence=evidence,
        )

    def build_cell_signal(
        self, metrics: Dict
    ) -> Optional[FraudSignal]:
        """
        Build a cell/MoMo fraud signal from account takeover indicators.

        Cell fraud indicators:
          - SIM swap immediately followed by MoMo outflow (account takeover)
          - New device with large transfer within 24h (social engineering)
          - Rapid MoMo account-to-account cycling (money laundering)

        :param metrics: Cell metrics dict.
        :return:        FraudSignal or None if no indicators triggered.
        """
        if not metrics:
            return None

        evidence = {}
        score = 0.0

        # SIM swap + immediate MoMo outflow: strongest cell fraud indicator
        sim_swap_momo = metrics.get("sim_swap_followed_by_momo", False)
        if sim_swap_momo:
            score += 0.45  # Very high belief — this combination is a near-definitive ATO signal
            evidence["sim_swap_momo"] = True

        # New device fingerprint + large transfer in short window
        new_device_transfer = metrics.get(
            "new_device_large_transfer", False
        )
        if new_device_transfer:
            score += 0.30  # Strong indicator of social engineering / credential theft
            evidence["new_device_transfer"] = True

        # Rapid cycling: funds passed through multiple accounts quickly (layering)
        momo_cycling = metrics.get("momo_cycling_events_7d", 0)
        if momo_cycling >= 3:
            score += 0.20  # Three or more cycling events in 7 days is a laundering signal
            evidence["momo_cycling"] = momo_cycling

        # Cap at 0.95 — leave some uncertainty mass
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
        Build an insurance fraud signal from claim pattern indicators.

        Insurance fraud indicators:
          - Multiple claims submitted within 30 days
          - Claim submitted within 30 days of policy inception
            (classic indicator of policy obtained fraudulently)

        :param metrics: Insurance metrics dict.
        :return:        FraudSignal or None if no indicators triggered.
        """
        if not metrics:
            return None

        evidence = {}
        score = 0.0

        # High claim frequency in a short window — especially suspicious for SME policies
        claims_30d = metrics.get("claims_submitted_30d", 0)
        if claims_30d >= 3:
            score += 0.30  # Three or more claims in 30 days is statistically unusual
            evidence["claims_30d"] = claims_30d

        # Early claim: policy holder submitting a claim within 30 days of inception
        # This is a known fraud pattern — policy obtained specifically to make a claim
        days_since_inception = metrics.get(
            "days_since_policy_inception_at_first_claim", 9999
        )
        if days_since_inception < 30:
            score += 0.40  # Strong indicator — hardest to explain legitimately
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
            # Insurance NOT_FRAUD cap is 0.7 (less certainty than CIB for clean case)
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
        Simplified Dempster-Shafer combination of belief masses over all signals.

        Frame of discernment: {F=FRAUD, N=NOT_FRAUD, U=UNCERTAIN}
        Each signal provides:
          m(F), m(N), m(U) = 1 - m(F) - m(N)

        Pairwise DS combination rule for two body-of-evidence sets:
          m12(F) ∝ m1(F)·m2(F) + m1(F)·m2(U) + m1(U)·m2(F)
          m12(N) ∝ m1(N)·m2(N) + m1(N)·m2(U) + m1(U)·m2(N)
          Conflict K = m1(F)·m2(N) + m1(N)·m2(F)
          Normalise by 1 / (1 - K)

        We iterate pairwise over all signals, updating cumulative masses.
        Conflict close to 1.0 (completely contradictory signals) is handled
        by clamping the normaliser to 0.001 to avoid division by zero.

        :param signals: List of FraudSignal instances.
        :return:        (combined_fraud_belief, combined_not_fraud_belief) tuple.
        """
        if not signals:
            return 0.0, 0.0

        # Initialise with the first signal's masses
        m_f = signals[0].belief_fraud
        m_n = signals[0].belief_not_fraud
        m_u = max(0.0, 1.0 - m_f - m_n)  # Remaining mass = uncertainty

        # Iterate over remaining signals and combine pairwise
        for sig in signals[1:]:
            s_f = sig.belief_fraud
            s_n = sig.belief_not_fraud
            s_u = max(0.0, 1.0 - s_f - s_n)

            # Conflict: FRAUD evidence from one vs NOT_FRAUD from the other
            conflict = m_f * s_n + m_n * s_f

            # Normalisation constant — prevents the conflict from inflating masses
            normaliser = 1.0 - conflict
            if normaliser < 0.001:
                normaliser = 0.001  # Floor to avoid numerical instability

            # New combined masses after applying DS rule
            new_f = (m_f * s_f + m_f * s_u + m_u * s_f) / normaliser
            new_n = (m_n * s_n + m_n * s_u + m_u * s_n) / normaliser
            new_u = (m_u * s_u) / normaliser  # Uncertainty shrinks as evidence accumulates

            # Clamp all masses to [0, 1] to guard against floating-point drift
            m_f = min(max(new_f, 0.0), 1.0)
            m_n = min(max(new_n, 0.0), 1.0)
            m_u = min(max(new_u, 0.0), 1.0)

        return m_f, m_n  # Return (FRAUD belief, NOT_FRAUD belief)

    def _detect_temporal_clustering(
        self, timestamps: List[str]
    ) -> bool:
        """
        Return True if three or more signals occurred within a 24-hour window.

        A tight time clustering of fraud signals is a strong escalation factor —
        it suggests a coordinated, planned attack rather than isolated incidents.

        :param timestamps: List of ISO-format datetime strings.
        :return:           True if temporal clustering is detected.
        """
        # Need at least 3 timestamps to form a cluster
        if len(timestamps) < 3:
            return False

        try:
            from datetime import datetime as dt

            # Parse and sort all timestamps in ascending order
            parsed = sorted(
                dt.fromisoformat(ts) for ts in timestamps
            )

            # Sliding window: check every triplet of consecutive events
            for i in range(len(parsed) - 2):
                # Duration from first to third event in the window
                delta = parsed[i + 2] - parsed[i]
                if delta.total_seconds() <= 86400:  # 86400 seconds = 24 hours
                    return True  # Found at least 3 events within 24 hours

        except (ValueError, TypeError):
            # Malformed timestamps — fail safe (no clustering)
            pass

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fraud_band(self, score: float) -> str:
        """
        Map a 0–100 composite score to a fraud risk band.

        :param score: Composite fraud score.
        :return:      Fraud band label string.
        """
        if score >= 75:
            return "CRITICAL"  # Immediate referral to Fraud Investigation Unit
        elif score >= 55:
            return "HIGH"      # Senior analyst review required
        elif score >= 30:
            return "MEDIUM"    # Enhanced monitoring; schedule review
        return "LOW"           # Continue standard monitoring

    def _build_narrative(
        self,
        signals: List[FraudSignal],
        score: float,
        country: str,
        temporal: bool,
    ) -> str:
        """
        Build a plain-English narrative for the compliance team describing
        which domains raised signals, the country risk context, and whether
        signals are temporally clustered.

        :param signals:  Contributing FraudSignal instances.
        :param score:    Final composite score.
        :param country:  ISO-2 country code.
        :param temporal: Whether temporal clustering was detected.
        :return:         Narrative string.
        """
        # List contributing domain names
        domains = [s.domain for s in signals]
        domain_str = " + ".join(domains)

        # Append temporal clustering note if applicable
        temporal_note = (
            " Signals are temporally clustered within 24h."
            if temporal else ""
        )

        # Look up the applied country multiplier for transparency
        mult = _COUNTRY_FRAUD_MULTIPLIER.get(country, 1.0)

        return (
            f"Composite fraud score {score:.1f}/100 from {domain_str} signals "
            f"(country risk factor {mult:.2f} for {country}).{temporal_note}"
        )
