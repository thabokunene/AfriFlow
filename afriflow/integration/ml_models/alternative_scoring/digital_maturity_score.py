"""
Digital Maturity Score

Measures how digitally engaged a corporate client's organisation
and workforce are across the AfriFlow domain stack.

Digital maturity predicts:
  - Willingness to adopt digital banking products (CIB portals)
  - Speed of FX hedging decision-making (straight-through processing)
  - MoMo payroll adoption rate (cell domain)
  - Online insurance self-service usage
  - API banking potential (Treasury Management System integration)

Score dimensions (0–100 each):

  1. USSD/App adoption      — what % of transactions are digital
  2. MoMo penetration       — payroll on mobile vs bank branch
  3. Digital payment mix    — EFT/online vs cash/cheque in CIB
  4. Online insurance       — self-service claims and renewals
  5. FX digital usage       — electronic execution vs relationship desk

Segments:
  10–30  : Laggard   — still branch-first, relationship-driven
  31–50  : Emerging  — adopting digital but inconsistent
  51–70  : Developing — digital-first transactions but not workflows
  71–85  : Advanced  — digital-first, some API integration
  86–100 : Leader    — full STP, TMS-integrated, API banking

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


_DIMENSION_WEIGHTS: Dict[str, float] = {
    "ussd_app_adoption":   0.30,
    "momo_penetration":    0.25,
    "digital_payment_mix": 0.20,
    "online_insurance":    0.10,
    "fx_digital_usage":    0.15,
}

_DIGITAL_SEGMENTS: List[tuple] = [
    (86, "Leader"),
    (71, "Advanced"),
    (51, "Developing"),
    (31, "Emerging"),
    (0,  "Laggard"),
]


@dataclass
class DigitalDimension:
    """One dimension of digital maturity."""

    name: str
    score: float          # 0–100
    weight: float
    weighted_score: float
    evidence: str
    data_present: bool


@dataclass
class DigitalMaturityScore:
    """Digital maturity assessment for a corporate client."""

    client_golden_id: str
    composite_score: float    # 0–100
    digital_segment: str
    dimensions: List[DigitalDimension]
    data_completeness: float
    product_affinities: List[str]   # Products this segment is receptive to
    scored_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class DigitalMaturityScorer:
    """
    Score the digital maturity of a corporate client.

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
        client_id = golden_record.get("golden_id", "UNKNOWN")

        dimensions = [
            self._score_ussd_app(cell_profile, pbb_profile),
            self._score_momo_penetration(cell_profile, pbb_profile),
            self._score_digital_payments(cib_profile, pbb_profile),
            self._score_online_insurance(insurance_profile),
            self._score_fx_digital(forex_profile),
        ]

        present = [d for d in dimensions if d.data_present]
        if not present:
            composite = 25.0  # Default: emerging
            completeness = 0.0
        else:
            present_weight = sum(d.weight for d in present)
            completeness = present_weight
            composite = sum(
                d.score * d.weight for d in present
            ) / present_weight

        segment = self._segment(composite)
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
        name = "ussd_app_adoption"
        weight = _DIMENSION_WEIGHTS[name]

        if not cell and not pbb:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No mobile data available",
                data_present=False,
            )

        digital_pct = (cell or pbb or {}).get(
            "ussd_session_pct_digital", 0.0
        )
        app_sessions = (cell or {}).get("app_session_count_30d", 0)

        score = digital_pct * 70 + min(app_sessions / 100, 30)
        score = min(score, 100)

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
        name = "momo_penetration"
        weight = _DIMENSION_WEIGHTS[name]

        if not cell:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No MoMo data available",
                data_present=False,
            )

        employee_count = cell.get("estimated_employee_count", 1)
        momo_enabled = cell.get("momo_enabled_employee_count", 0)

        penetration = momo_enabled / employee_count if employee_count > 0 else 0.0
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
        name = "digital_payment_mix"
        weight = _DIMENSION_WEIGHTS[name]

        if not cib and not pbb:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No payment channel data available",
                data_present=False,
            )

        digital_pct = (cib or pbb or {}).get("digital_payment_pct", 0.0)
        stp_rate = (cib or {}).get("straight_through_processing_rate", 0.0)

        score = digital_pct * 70 + stp_rate * 30
        score = min(score * 100, 100)

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
        name = "online_insurance"
        weight = _DIMENSION_WEIGHTS[name]

        if not insurance:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No insurance channel data available",
                data_present=False,
            )

        online_claims_pct = insurance.get(
            "online_claims_submission_pct", 0.0
        )
        self_service_renewals = insurance.get(
            "self_service_renewal_pct", 0.0
        )

        score = online_claims_pct * 60 + self_service_renewals * 40
        score = min(score * 100, 100)

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
        name = "fx_digital_usage"
        weight = _DIMENSION_WEIGHTS[name]

        if not forex:
            return DigitalDimension(
                name=name, score=0.0, weight=weight,
                weighted_score=0.0,
                evidence="No FX channel data available",
                data_present=False,
            )

        electronic_execution_pct = forex.get(
            "electronic_execution_pct", 0.0
        )
        api_connected = forex.get("api_tms_connected", False)

        score = electronic_execution_pct * 70
        if api_connected:
            score += 30
        score = min(score * 100, 100)

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
        for threshold, label in _DIGITAL_SEGMENTS:
            if score >= threshold:
                return label
        return "Laggard"

    def _product_affinities(self, segment: str) -> List[str]:
        affinities: Dict[str, List[str]] = {
            "Leader": [
                "API Banking Integration",
                "FX Algorithmic Execution",
                "Real-time Cross-border Payments",
                "Digital Trade Finance Portal",
            ],
            "Advanced": [
                "CIB Online Portal Upgrade",
                "MoMo Payroll API",
                "Online FX Dealing",
                "Digital Insurance Self-Service",
            ],
            "Developing": [
                "MoMo Salary Payment",
                "FX Online Rate Alert",
                "E-Statement & Digital Reporting",
            ],
            "Emerging": [
                "Online Account Opening",
                "MoMo Starter Pack",
                "USSD Payment Service",
            ],
            "Laggard": [
                "Dedicated Digital Adoption Relationship Manager",
                "Branch-to-Digital Migration Programme",
            ],
        }
        return affinities.get(segment, [])
