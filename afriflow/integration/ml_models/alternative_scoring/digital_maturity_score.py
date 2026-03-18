"""
@file digital_maturity_score.py
@description Measures how digitally engaged a corporate client's organisation
             and workforce are across the AfriFlow domain stack.  Digital
             maturity predicts product affinity for API banking, MoMo payroll,
             online FX dealing, and digital insurance self-service.
             Output is a composite 0–100 score mapped to five maturity
             segments (Laggard → Leader) plus a list of recommended products.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dimension weights
# ---------------------------------------------------------------------------
# Five dimensions cover the full digital engagement stack.
# USSD/app adoption is weighted highest (0.30) because it is the broadest
# signal across both formal and informal employee segments.

_DIMENSION_WEIGHTS: Dict[str, float] = {
    "ussd_app_adoption":   0.30,  # What % of transactions flow through digital channels
    "momo_penetration":    0.25,  # What fraction of the workforce is MoMo-enabled
    "digital_payment_mix": 0.20,  # EFT / online vs cash / cheque in CIB/PBB
    "online_insurance":    0.10,  # Self-service claims and renewals (smallest weight — niche)
    "fx_digital_usage":    0.15,  # Electronic FX execution vs phone/relationship desk
}

# Segment thresholds: list of (min_score, segment_label) in descending order.
# The first threshold that the composite score equals or exceeds is applied.
_DIGITAL_SEGMENTS: List[tuple] = [
    (86, "Leader"),      # Full STP, TMS-integrated, API banking
    (71, "Advanced"),    # Digital-first, some API integration
    (51, "Developing"),  # Digital-first transactions but not workflows
    (31, "Emerging"),    # Adopting digital but inconsistent
    (0,  "Laggard"),     # Still branch-first, relationship-driven
]


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class DigitalDimension:
    """
    One dimension of digital maturity assessment.

    :param name:           Dimension key (matches _DIMENSION_WEIGHTS).
    :param score:          Raw dimension score 0–100.
    :param weight:         This dimension's fractional weight in the composite.
    :param weighted_score: score × weight — contribution to composite.
    :param evidence:       Human-readable description of the underlying data.
    :param data_present:   False if source domain data was unavailable.
    """

    name: str
    score: float          # 0–100 raw dimension score
    weight: float
    weighted_score: float
    evidence: str
    data_present: bool    # False → excluded from composite calculation


@dataclass
class DigitalMaturityScore:
    """
    Digital maturity assessment for a corporate client.

    :param client_golden_id:    AfriFlow golden record identifier.
    :param composite_score:     Weighted average of present dimensions (0–100).
    :param digital_segment:     Named maturity tier (Laggard → Leader).
    :param dimensions:          Per-dimension score breakdown.
    :param data_completeness:   Sum of weights for present dimensions (0–1).
    :param product_affinities:  Products this segment is most receptive to.
    :param scored_at:           ISO timestamp of scoring.
    """

    client_golden_id: str
    composite_score: float    # 0–100
    digital_segment: str
    dimensions: List[DigitalDimension]
    data_completeness: float
    product_affinities: List[str]   # Products this segment is receptive to
    scored_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class DigitalMaturityScorer:
    """
    Score the digital maturity of a corporate client using cross-domain
    digital engagement signals.

    Usage::

        scorer = DigitalMaturityScorer()
        result = scorer.score(
            golden_record={"golden_id": "GLD-001"},
            cell_profile={"ussd_session_pct_digital": 0.72, ...},
            cib_profile={"digital_payment_pct": 0.88, ...},
        )
    """

    def score(
        self,
        golden_record: Dict,
        cell_profile: Optional[Dict] = None,
        cib_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
        forex_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
    ) -> DigitalMaturityScore:
        """
        Compute digital maturity score for one client.

        :param golden_record:    Mandatory golden record dict.
        :param cell_profile:     Cell/MoMo domain profile.
        :param cib_profile:      CIB domain profile.
        :param insurance_profile: Insurance domain profile.
        :param forex_profile:    Forex domain profile.
        :param pbb_profile:      PBB domain profile.
        :return:                 DigitalMaturityScore dataclass.
        """
        # Extract client identifier for output labelling
        client_id = golden_record.get("golden_id", "UNKNOWN")

        # Score each dimension — order is cosmetic but kept consistent
        dimensions = [
            self._score_ussd_app(cell_profile, pbb_profile),
            self._score_momo_penetration(cell_profile, pbb_profile),
            self._score_digital_payments(cib_profile, pbb_profile),
            self._score_online_insurance(insurance_profile),
            self._score_fx_digital(forex_profile),
        ]

        # Compute weighted composite only over dimensions that have data
        present = [d for d in dimensions if d.data_present]
        if not present:
            # Default to 25 (Laggard/Emerging boundary) if no data is present
            composite = 25.0
            completeness = 0.0
        else:
            present_weight = sum(d.weight for d in present)
            completeness = present_weight  # 0–1 coverage fraction
            composite = sum(
                d.score * d.weight for d in present
            ) / present_weight  # Re-normalise over present dimensions

        # Map composite score to a named maturity segment
        segment = self._segment(composite)

        # Look up product affinities for the assigned segment
        affinities = self._product_affinities(segment)

        return DigitalMaturityScore(
            client_golden_id=client_id,
            composite_score=round(composite, 1),
            digital_segment=segment,
            dimensions=dimensions,
            data_completeness=round(completeness, 3),
            product_affinities=affinities,
        )

    # ------------------------------------------------------------------
    # Dimension scorers
    # ------------------------------------------------------------------

    def _score_ussd_app(
        self,
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> DigitalDimension:
        """
        Score USSD/app adoption using the digital session percentage
        and total app session count from the cell and PBB domains.

        :param cell: Cell profile dict.
        :param pbb:  PBB profile dict.
        :return:     DigitalDimension for ussd_app_adoption.
        """
        name = "ussd_app_adoption"
        weight = _DIMENSION_WEIGHTS[name]

        if not cell and not pbb:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No mobile data available",
                data_present=False,
            )

        # Fraction of USSD sessions that are digital (not branch-initiated)
        digital_pct = (cell or pbb or {}).get(
            "ussd_session_pct_digital", 0.0
        )

        # Raw count of app sessions in the last 30 days
        app_sessions = (cell or {}).get("app_session_count_30d", 0)

        # digital_pct contributes 70 pts (scale 0–1 → 0–70)
        # app sessions contribute up to 30 pts (100 sessions = 30 pts cap)
        score = digital_pct * 70 + min(app_sessions / 100, 30)
        score = min(score, 100)  # Hard cap at 100

        return DigitalDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(score * weight, 3),
            evidence=(
                f"{digital_pct*100:.0f}% digital USSD sessions; "
                f"{app_sessions} app sessions/month"
            ),
            data_present=True,
        )

    def _score_momo_penetration(
        self,
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> DigitalDimension:
        """
        Score MoMo workforce penetration: the fraction of estimated
        employees who are MoMo-enabled.

        High MoMo penetration indicates a digitally engaged workforce
        and a receptive base for payroll banking migration.

        :param cell: Cell profile dict.
        :param pbb:  PBB profile dict (unused here; included for future use).
        :return:     DigitalDimension for momo_penetration.
        """
        name = "momo_penetration"
        weight = _DIMENSION_WEIGHTS[name]

        # MoMo data only comes from the cell domain
        if not cell:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No MoMo data available",
                data_present=False,
            )

        # Total headcount estimate from SIM deflation model
        employee_count = cell.get("estimated_employee_count", 1)

        # Number of employees with an active MoMo wallet
        momo_enabled = cell.get("momo_enabled_employee_count", 0)

        # Penetration rate (0–1); guard against zero headcount
        penetration = momo_enabled / employee_count if employee_count > 0 else 0.0

        # Score is directly proportional to penetration — 100% MoMo = 100 pts
        score = min(penetration * 100, 100)

        return DigitalDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(score * weight, 3),
            evidence=(
                f"{momo_enabled} of {employee_count} employees "
                f"MoMo-enabled ({penetration*100:.0f}%)"
            ),
            data_present=True,
        )

    def _score_digital_payments(
        self,
        cib: Optional[Dict],
        pbb: Optional[Dict],
    ) -> DigitalDimension:
        """
        Score digital payment channel mix using digital payment
        percentage and straight-through processing (STP) rate.

        STP rate measures how many transactions complete without
        human intervention — a strong indicator of process digitalisation.

        :param cib: CIB profile dict.
        :param pbb: PBB profile dict.
        :return:    DigitalDimension for digital_payment_mix.
        """
        name = "digital_payment_mix"
        weight = _DIMENSION_WEIGHTS[name]

        if not cib and not pbb:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No payment channel data available",
                data_present=False,
            )

        # Fraction of payments made via digital channels (EFT, online, API)
        digital_pct = (cib or pbb or {}).get("digital_payment_pct", 0.0)

        # STP rate: fraction of transactions that are fully automated end-to-end
        stp_rate = (cib or {}).get("straight_through_processing_rate", 0.0)

        # Score: digital_pct weighted at 70%, STP rate at 30%
        # Both inputs are already fractions (0–1), so multiply by 100 at the end
        score = digital_pct * 70 + stp_rate * 30
        score = min(score * 100, 100)  # Scale to 0–100

        return DigitalDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(score * weight, 3),
            evidence=(
                f"{digital_pct*100:.0f}% payments digital; "
                f"STP rate {stp_rate*100:.0f}%"
            ),
            data_present=True,
        )

    def _score_online_insurance(
        self, insurance: Optional[Dict]
    ) -> DigitalDimension:
        """
        Score online insurance engagement using the fraction of claims
        submitted online and the self-service renewal rate.

        :param insurance: Insurance profile dict.
        :return:          DigitalDimension for online_insurance.
        """
        name = "online_insurance"
        weight = _DIMENSION_WEIGHTS[name]

        if not insurance:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No insurance channel data available",
                data_present=False,
            )

        # Fraction of insurance claims submitted via online portal / app
        online_claims_pct = insurance.get(
            "online_claims_submission_pct", 0.0
        )

        # Fraction of policy renewals handled by client without agent involvement
        self_service_renewals = insurance.get(
            "self_service_renewal_pct", 0.0
        )

        # Claims submission (60%) is weighted more than renewals (40%)
        # because it represents proactive digital adoption under stress
        score = online_claims_pct * 60 + self_service_renewals * 40
        score = min(score * 100, 100)  # Scale to 0–100

        return DigitalDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(score * weight, 3),
            evidence=(
                f"{online_claims_pct*100:.0f}% claims online; "
                f"{self_service_renewals*100:.0f}% self-service renewals"
            ),
            data_present=True,
        )

    def _score_fx_digital(
        self, forex: Optional[Dict]
    ) -> DigitalDimension:
        """
        Score FX digital channel adoption using electronic execution
        percentage and Treasury Management System (TMS) API connectivity.

        API-connected TMS clients are fully digital FX participants —
        they receive a 30-point bonus regardless of electronic execution %.

        :param forex: Forex profile dict.
        :return:      DigitalDimension for fx_digital_usage.
        """
        name = "fx_digital_usage"
        weight = _DIMENSION_WEIGHTS[name]

        if not forex:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No FX channel data available",
                data_present=False,
            )

        # Fraction of FX trades executed electronically (online platform / API)
        electronic_execution_pct = forex.get(
            "electronic_execution_pct", 0.0
        )

        # Boolean: is the client's TMS connected via API (straight-through FX)
        api_connected = forex.get("api_tms_connected", False)

        # Electronic execution contributes 70 pts (fraction × 70)
        score = electronic_execution_pct * 70

        # API TMS connection is a binary 30-pt bonus — highest digital maturity signal
        if api_connected:
            score += 30

        score = min(score * 100, 100)  # Scale to 0–100

        return DigitalDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(score * weight, 3),
            evidence=(
                f"{electronic_execution_pct*100:.0f}% FX electronic; "
                f"API TMS={'Yes' if api_connected else 'No'}"
            ),
            data_present=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _segment(self, score: float) -> str:
        """
        Map a composite 0–100 score to a named digital maturity segment
        using the sorted _DIGITAL_SEGMENTS threshold list.

        :param score: Composite digital maturity score.
        :return:      Segment label string.
        """
        # Iterate thresholds in descending order; return first match
        for threshold, label in _DIGITAL_SEGMENTS:
            if score >= threshold:
                return label
        return "Laggard"  # Fallback — should never be reached given (0, "Laggard")

    def _product_affinities(self, segment: str) -> List[str]:
        """
        Return a list of products the client is most likely to adopt
        given their digital maturity segment.

        Products are ordered from highest to lowest affinity within
        each segment.

        :param segment: Digital maturity segment label.
        :return:        List of product name strings.
        """
        # Product affinity map: each segment has a curated list of recommended products
        affinities: Dict[str, List[str]] = {
            "Leader": [
                "API Banking Integration",           # Full STP integration
                "FX Algorithmic Execution",          # Algo-driven FX
                "Real-time Cross-border Payments",   # Instant cross-border
                "Digital Trade Finance Portal",      # Paperless LC / guarantees
            ],
            "Advanced": [
                "CIB Online Portal Upgrade",         # Existing portal enhancement
                "MoMo Payroll API",                  # Payroll via MoMo API
                "Online FX Dealing",                 # Web-based FX dealing
                "Digital Insurance Self-Service",    # App-based claims
            ],
            "Developing": [
                "MoMo Salary Payment",               # Digital salary disbursement
                "FX Online Rate Alert",              # Rate monitoring / basic online FX
                "E-Statement & Digital Reporting",   # Digital reporting migration
            ],
            "Emerging": [
                "Online Account Opening",            # Onboarding campaign
                "MoMo Starter Pack",                 # First MoMo wallet activation
                "USSD Payment Service",              # Basic digital payment entry
            ],
            "Laggard": [
                "Dedicated Digital Adoption Relationship Manager",  # Hands-on digital coaching
                "Branch-to-Digital Migration Programme",            # Structured migration plan
            ],
        }
        return affinities.get(segment, [])
