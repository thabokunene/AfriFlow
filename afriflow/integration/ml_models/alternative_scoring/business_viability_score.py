"""
Business Viability Score

We score the operational health of African businesses using
non-traditional signals — particularly relevant for SMEs and
informal businesses that have thin credit bureau footprints.

Traditional credit scoring fails African SMEs because:
  - Many have no audited financials
  - FICO/bureau data is sparse outside South Africa
  - Bank statement history is often <12 months
  - Asset ownership is informal (no title deeds)

We replace these with cross-domain behavioural proxies:

  Revenue proxy      : Inbound payment frequency (CIB/PBB)
  Payroll regularity : Payroll timing consistency (cell+PBB)
  Supplier trust     : Trade finance utilisation pattern (CIB)
  Market presence    : Geographic SIM footprint (cell)
  Forex sophistication: Hedging vs naked exposure (forex)
  Insurance coverage : Proportional coverage vs revenue (insurance)

Score components (0–100 each):
  1. Cash flow regularity score     (25%)
  2. Payroll reliability score      (20%)
  3. Trade finance utilisation      (20%)
  4. Geographic market coverage     (15%)
  5. Risk management maturity       (10%)
  6. Insurance adequacy             (10%)

Final score: 300–850 (scaled to mirror credit score convention)

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Score component weights
# ---------------------------------------------------------------------------

_COMPONENT_WEIGHTS: Dict[str, float] = {
    "cash_flow_regularity":    0.25,
    "payroll_reliability":     0.20,
    "trade_finance_quality":   0.20,
    "geographic_coverage":     0.15,
    "risk_management":         0.10,
    "insurance_adequacy":      0.10,
}

# Score range maps to 300–850 (credit score convention)
_SCORE_MIN = 300
_SCORE_MAX = 850


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class ScoreComponent:
    """One of six viability score components."""

    name: str
    weight: float
    raw_score: float       # 0–100
    weighted_score: float  # raw × weight × 100
    description: str
    data_present: bool


@dataclass
class BusinessViabilityScore:
    """
    Final business viability assessment.

    viability_score : 300–850 (higher = more viable)
    viability_band  : DISTRESSED / MARGINAL / STABLE / STRONG / EXCELLENT
    """

    client_golden_id: str
    viability_score: int
    viability_band: str
    component_scores: List[ScoreComponent]
    data_completeness: float   # 0–1
    lending_recommendation: str
    max_facility_multiple: float   # × annual revenue estimate
    scored_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class BusinessViabilityScorer:
    """
    Score business viability using cross-domain signals.

    Domain profiles follow the AfriFlow profile contract.
    Missing domains reduce completeness but do not block scoring.

    Usage::

        scorer = BusinessViabilityScorer()
        result = scorer.score(
            golden_record={"golden_id": "GLD-001", "canonical_name": "Acme Ltd"},
            cib_profile={"monthly_inbound_payments": 8, "payment_cv": 0.12, ...},
            cell_profile={...},
        )
    """

    def score(
        self,
        golden_record: Dict,
        cib_profile: Optional[Dict] = None,
        cell_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
        forex_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
    ) -> BusinessViabilityScore:
        client_id = golden_record.get("golden_id", "UNKNOWN")
        components: List[ScoreComponent] = []

        # 1. Cash flow regularity
        components.append(
            self._score_cash_flow(cib_profile, pbb_profile)
        )

        # 2. Payroll reliability
        components.append(
            self._score_payroll_reliability(pbb_profile, cell_profile)
        )

        # 3. Trade finance quality
        components.append(
            self._score_trade_finance(cib_profile)
        )

        # 4. Geographic market coverage
        components.append(
            self._score_geographic_coverage(cell_profile, cib_profile)
        )

        # 5. Risk management maturity
        components.append(
            self._score_risk_management(forex_profile, insurance_profile)
        )

        # 6. Insurance adequacy
        components.append(
            self._score_insurance_adequacy(
                insurance_profile, cib_profile
            )
        )

        # Weighted composite (0–100)
        present = [c for c in components if c.data_present]
        if not present:
            composite_0_100 = 50.0
            completeness = 0.0
        else:
            present_weight = sum(c.weight for c in present)
            completeness = present_weight
            composite_0_100 = sum(
                c.raw_score * c.weight for c in present
            ) / present_weight

        # Scale to 300–850
        viability_score = int(
            _SCORE_MIN + composite_0_100 / 100 * (_SCORE_MAX - _SCORE_MIN)
        )

        band = self._band(viability_score)
        recommendation, facility_multiple = self._lending_params(
            band, completeness
        )

        return BusinessViabilityScore(
            client_golden_id=client_id,
            viability_score=viability_score,
            viability_band=band,
            component_scores=components,
            data_completeness=round(completeness, 3),
            lending_recommendation=recommendation,
            max_facility_multiple=facility_multiple,
        )

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def _score_cash_flow(
        self,
        cib: Optional[Dict],
        pbb: Optional[Dict],
    ) -> ScoreComponent:
        name = "cash_flow_regularity"
        weight = _COMPONENT_WEIGHTS[name]

        if not cib and not pbb:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No cash flow data available",
                data_present=False,
            )

        monthly_payments = (
            (cib or {}).get("monthly_inbound_payments", 0) +
            (pbb or {}).get("monthly_credits", 0)
        )
        # Coefficient of variation of payment amounts (lower = more regular)
        payment_cv = (cib or pbb or {}).get("payment_cv", 1.0)

        regularity_score = min(monthly_payments / 20 * 60, 60)
        cv_score = max(0, 40 - payment_cv * 80)
        raw = min(regularity_score + cv_score, 100)

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=round(raw, 1),
            weighted_score=round(raw * weight, 3),
            description=(
                f"{monthly_payments} monthly inbound payments; "
                f"payment CV={payment_cv:.2f}"
            ),
            data_present=True,
        )

    def _score_payroll_reliability(
        self,
        pbb: Optional[Dict],
        cell: Optional[Dict],
    ) -> ScoreComponent:
        name = "payroll_reliability"
        weight = _COMPONENT_WEIGHTS[name]

        if not pbb and not cell:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No payroll data available",
                data_present=False,
            )

        # Days deviation from expected payroll date (lower = more reliable)
        avg_days_late = (pbb or {}).get("avg_payroll_days_late", 5)
        is_regular = (cell or {}).get("payroll_is_regular", True)

        timeliness = max(0, 70 - avg_days_late * 8)
        regularity = 30 if is_regular else 0
        raw = min(timeliness + regularity, 100)

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=round(raw, 1),
            weighted_score=round(raw * weight, 3),
            description=(
                f"Avg payroll delay {avg_days_late} days; "
                f"regular={'Yes' if is_regular else 'No'}"
            ),
            data_present=True,
        )

    def _score_trade_finance(
        self, cib: Optional[Dict]
    ) -> ScoreComponent:
        name = "trade_finance_quality"
        weight = _COMPONENT_WEIGHTS[name]

        if not cib:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No trade finance data available",
                data_present=False,
            )

        utilisation = cib.get("facility_utilisation_pct", 0.0)
        default_count = cib.get("past_due_events_12m", 0)
        active_lcs = cib.get("active_letter_of_credit_count", 0)

        # Optimal utilisation is 40–80%
        if 0.40 <= utilisation <= 0.80:
            util_score = 50
        elif utilisation < 0.40:
            util_score = utilisation * 125
        else:
            util_score = max(0, 50 - (utilisation - 0.80) * 100)

        default_penalty = min(default_count * 15, 40)
        lc_bonus = min(active_lcs * 5, 20)
        raw = min(util_score + lc_bonus - default_penalty, 100)
        raw = max(raw, 0)

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=round(raw, 1),
            weighted_score=round(raw * weight, 3),
            description=(
                f"Facility util={utilisation*100:.0f}%; "
                f"{active_lcs} active LCs; {default_count} past-due events"
            ),
            data_present=True,
        )

    def _score_geographic_coverage(
        self,
        cell: Optional[Dict],
        cib: Optional[Dict],
    ) -> ScoreComponent:
        name = "geographic_coverage"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell and not cib:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No geographic data available",
                data_present=False,
            )

        country_count = (
            (cell or {}).get("active_country_count", 1) +
            (cib or {}).get("payment_corridor_country_count", 0)
        ) // 2 or 1

        # More markets = more diversified but also more complex
        if country_count == 1:
            raw = 30
        elif country_count <= 3:
            raw = 55
        elif country_count <= 6:
            raw = 75
        elif country_count <= 10:
            raw = 85
        else:
            raw = 70  # Too many corridors = complexity risk

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=float(raw),
            weighted_score=round(raw * weight, 3),
            description=(
                f"Active in ~{country_count} African markets"
            ),
            data_present=True,
        )

    def _score_risk_management(
        self,
        forex: Optional[Dict],
        insurance: Optional[Dict],
    ) -> ScoreComponent:
        name = "risk_management"
        weight = _COMPONENT_WEIGHTS[name]

        if not forex and not insurance:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No risk management data available",
                data_present=False,
            )

        has_hedges = (forex or {}).get("has_active_forwards", False)
        hedge_ratio = (forex or {}).get("hedge_ratio", 0.0)
        has_insurance = insurance is not None and (
            insurance.get("active_policy_count", 0) > 0
        )

        hedge_score = 0.0
        if has_hedges:
            hedge_score = min(hedge_ratio * 100, 60)

        insurance_score = 30 if has_insurance else 0
        raw = min(hedge_score + insurance_score, 100)

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=round(raw, 1),
            weighted_score=round(raw * weight, 3),
            description=(
                f"Hedges={'Yes' if has_hedges else 'No'} "
                f"(ratio={hedge_ratio:.0%}); "
                f"Insurance={'Yes' if has_insurance else 'No'}"
            ),
            data_present=True,
        )

    def _score_insurance_adequacy(
        self,
        insurance: Optional[Dict],
        cib: Optional[Dict],
    ) -> ScoreComponent:
        name = "insurance_adequacy"
        weight = _COMPONENT_WEIGHTS[name]

        if not insurance:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No insurance data available",
                data_present=False,
            )

        sum_assured = insurance.get("total_sum_assured_zar", 0.0)
        facility_value = (cib or {}).get("total_facility_value_zar", 1.0)

        coverage_ratio = (
            sum_assured / facility_value if facility_value > 0 else 0.0
        )

        if coverage_ratio >= 1.0:
            raw = 90
        elif coverage_ratio >= 0.5:
            raw = 70
        elif coverage_ratio >= 0.2:
            raw = 45
        elif coverage_ratio > 0:
            raw = 25
        else:
            raw = 0

        return ScoreComponent(
            name=name, weight=weight,
            raw_score=float(raw),
            weighted_score=round(raw * weight, 3),
            description=(
                f"Sum assured R{sum_assured:,.0f} vs "
                f"facility R{facility_value:,.0f} "
                f"({coverage_ratio:.0%} coverage)"
            ),
            data_present=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _band(self, score: int) -> str:
        if score >= 750:
            return "EXCELLENT"
        elif score >= 680:
            return "STRONG"
        elif score >= 580:
            return "STABLE"
        elif score >= 450:
            return "MARGINAL"
        return "DISTRESSED"

    def _lending_params(
        self, band: str, completeness: float
    ) -> tuple:
        params = {
            "EXCELLENT": ("Approve. Preferential pricing eligible.", 4.0),
            "STRONG":    ("Approve. Standard terms.", 3.0),
            "STABLE":    ("Approve with conditions. Annual review.", 2.0),
            "MARGINAL":  ("Conditional approval. Require collateral.", 1.0),
            "DISTRESSED":("Decline or refer to turnaround team.", 0.0),
        }
        recommendation, multiple = params.get(band, ("Review manually.", 0.5))

        if completeness < 0.40:
            recommendation += " NOTE: Low data completeness — manual review required."
            multiple *= 0.5

        return recommendation, multiple
