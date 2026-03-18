"""
@file business_viability_score.py
@description Scores the operational health of African businesses using
             non-traditional, cross-domain behavioural signals as proxies
             for creditworthiness.  Designed for SMEs and informal businesses
             that have thin or no credit-bureau footprints — a widespread
             reality across sub-Saharan Africa outside South Africa.
             Output is a 300–850 viability score (mirroring credit score
             convention) plus a lending recommendation and facility multiple.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Score component weights
# ---------------------------------------------------------------------------
# Each component covers a distinct dimension of business health.
# Weights sum to 1.0 and reflect the relative predictive power of each signal
# in the African SME context (cash flow and payroll dominate because they are
# the most reliable proxies for revenue generation and workforce stability).

_COMPONENT_WEIGHTS: Dict[str, float] = {
    "cash_flow_regularity":    0.25,  # Largest weight — most direct revenue proxy
    "payroll_reliability":     0.20,  # Workforce stability; signals operational continuity
    "trade_finance_quality":   0.20,  # How well the client manages credit facilities
    "geographic_coverage":     0.15,  # Market diversification across African countries
    "risk_management":         0.10,  # Use of hedging + insurance (financial sophistication)
    "insurance_adequacy":      0.10,  # Coverage ratio vs credit facility — asset protection
}

# Score range mirrors the South African credit score convention (NCA-aligned).
# 300 = lowest possible score (no data or all signals negative)
# 850 = highest possible score (all signals excellent)
_SCORE_MIN = 300
_SCORE_MAX = 850


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class ScoreComponent:
    """
    One of six viability score components.

    :param name:           Key matching a key in _COMPONENT_WEIGHTS.
    :param weight:         Fractional weight of this component (0–1).
    :param raw_score:      Component score before weighting (0–100).
    :param weighted_score: raw_score × weight (contribution to composite).
    :param description:    Human-readable evidence summary.
    :param data_present:   False if the source domain data was unavailable.
    """

    name: str
    weight: float
    raw_score: float       # 0–100 — component score before weighting
    weighted_score: float  # raw × weight — contribution to composite 0–100
    description: str
    data_present: bool     # False → this component is excluded from the composite


@dataclass
class BusinessViabilityScore:
    """
    Final business viability assessment for one client.

    viability_score : 300–850 (higher = more viable)
    viability_band  : DISTRESSED / MARGINAL / STABLE / STRONG / EXCELLENT

    :param client_golden_id:       AfriFlow golden record identifier.
    :param viability_score:        Final scaled score (300–850).
    :param viability_band:         Human label for the score tier.
    :param component_scores:       Per-component breakdown list.
    :param data_completeness:      Fraction of maximum possible weight that
                                   was backed by real domain data (0–1).
    :param lending_recommendation: Plain-English credit decision guidance.
    :param max_facility_multiple:  Suggested max facility as a multiple of
                                   estimated annual revenue.
    :param scored_at:              ISO timestamp of scoring.
    """

    client_golden_id: str
    viability_score: int
    viability_band: str
    component_scores: List[ScoreComponent]
    data_completeness: float   # 0–1; low values flag manual review
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

    Domain profiles follow the AfriFlow profile contract (plain dicts).
    Missing domains reduce completeness but do not block scoring — the
    composite is re-normalised over present domain weights only.

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
        """
        Compute a full viability score for a client.

        :param golden_record:    Mandatory golden record dict; must contain "golden_id".
        :param cib_profile:      Corporate & Investment Banking domain profile.
        :param cell_profile:     Cell/MoMo domain profile.
        :param pbb_profile:      Personal & Business Banking domain profile.
        :param forex_profile:    Foreign exchange domain profile.
        :param insurance_profile: Insurance domain profile.
        :return:                 BusinessViabilityScore dataclass.
        """
        # Extract the client identifier for output labelling
        client_id = golden_record.get("golden_id", "UNKNOWN")

        # Build one ScoreComponent per dimension — order matches _COMPONENT_WEIGHTS
        components: List[ScoreComponent] = []

        # 1. Cash flow regularity — most predictive signal for SME viability
        components.append(
            self._score_cash_flow(cib_profile, pbb_profile)
        )

        # 2. Payroll reliability — consistency of salary payments signals workforce health
        components.append(
            self._score_payroll_reliability(pbb_profile, cell_profile)
        )

        # 3. Trade finance quality — facility usage and default history
        components.append(
            self._score_trade_finance(cib_profile)
        )

        # 4. Geographic market coverage — breadth of active African corridors
        components.append(
            self._score_geographic_coverage(cell_profile, cib_profile)
        )

        # 5. Risk management maturity — hedging presence and insurance ownership
        components.append(
            self._score_risk_management(forex_profile, insurance_profile)
        )

        # 6. Insurance adequacy — sum assured vs total facility exposure
        components.append(
            self._score_insurance_adequacy(
                insurance_profile, cib_profile
            )
        )

        # Weighted composite (0–100): only include components that have data
        present = [c for c in components if c.data_present]
        if not present:
            # No domain data at all — assign a neutral mid-point
            composite_0_100 = 50.0
            completeness = 0.0
        else:
            # Re-normalise by the sum of present component weights
            present_weight = sum(c.weight for c in present)
            completeness = present_weight  # fraction of max weight that is filled
            composite_0_100 = sum(
                c.raw_score * c.weight for c in present
            ) / present_weight

        # Scale the 0–100 composite linearly to the 300–850 credit score range
        viability_score = int(
            _SCORE_MIN + composite_0_100 / 100 * (_SCORE_MAX - _SCORE_MIN)
        )

        # Derive qualitative band from the scaled score
        band = self._band(viability_score)

        # Lending recommendation and maximum facility multiple depend on band + completeness
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
        """
        Score cash flow regularity using inbound payment frequency
        and the coefficient of variation (CV) of payment amounts.

        :param cib: CIB profile dict (may be None).
        :param pbb: PBB profile dict (may be None).
        :return:    ScoreComponent for cash_flow_regularity.
        """
        name = "cash_flow_regularity"
        weight = _COMPONENT_WEIGHTS[name]

        # Guard: return a zero-score placeholder if neither domain is available
        if not cib and not pbb:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No cash flow data available",
                data_present=False,
            )

        # Sum inbound payments from both domains (CIB corporate payments + PBB credits)
        monthly_payments = (
            (cib or {}).get("monthly_inbound_payments", 0) +
            (pbb or {}).get("monthly_credits", 0)
        )

        # CV of payment amounts — lower CV means more predictable cash flow.
        # Defaults to 1.0 (high variance) if not provided.
        payment_cv = (cib or pbb or {}).get("payment_cv", 1.0)

        # Regularity sub-score: 20 payments/month = 60 points (cap at 60)
        regularity_score = min(monthly_payments / 20 * 60, 60)

        # CV sub-score: CV=0 → 40 pts; CV=0.5 → 0 pts (linear decay)
        cv_score = max(0, 40 - payment_cv * 80)

        # Combine and cap at 100
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
        """
        Score payroll timing consistency using average days late and
        a binary regularity flag from the cell domain.

        :param pbb:  PBB profile dict.
        :param cell: Cell profile dict.
        :return:     ScoreComponent for payroll_reliability.
        """
        name = "payroll_reliability"
        weight = _COMPONENT_WEIGHTS[name]

        if not pbb and not cell:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No payroll data available",
                data_present=False,
            )

        # Average number of days the payroll is late vs scheduled date.
        # Default of 5 days is a conservative assumption when data is absent.
        avg_days_late = (pbb or {}).get("avg_payroll_days_late", 5)

        # Boolean: does the cell domain flag this employer as having regular payroll?
        is_regular = (cell or {}).get("payroll_is_regular", True)

        # Timeliness sub-score: 0 days late → 70 pts; 8+ days → 0 pts
        timeliness = max(0, 70 - avg_days_late * 8)

        # Regularity bonus: consistent monthly payroll adds 30 pts
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
        """
        Score trade finance quality using facility utilisation,
        past-due events, and active letter of credit count.

        Optimal utilisation band is 40–80%: below 40% suggests the
        client is not using the facility efficiently; above 80%
        indicates over-reliance or stress.

        :param cib: CIB profile dict.
        :return:    ScoreComponent for trade_finance_quality.
        """
        name = "trade_finance_quality"
        weight = _COMPONENT_WEIGHTS[name]

        if not cib:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No trade finance data available",
                data_present=False,
            )

        # Fraction of total credit facility currently drawn (0.0–1.0)
        utilisation = cib.get("facility_utilisation_pct", 0.0)

        # Number of past-due events in the last 12 months (payment delays / covenant breaches)
        default_count = cib.get("past_due_events_12m", 0)

        # Active letters of credit signal trade activity and bank-client trust
        active_lcs = cib.get("active_letter_of_credit_count", 0)

        # Utilisation scoring: sweet spot is 40–80% of facility
        if 0.40 <= utilisation <= 0.80:
            util_score = 50  # Ideal range — balanced use
        elif utilisation < 0.40:
            # Under-utilised: linear scale up to 50 pts at 40%
            util_score = utilisation * 125
        else:
            # Over-utilised: penalise steeply above 80%
            util_score = max(0, 50 - (utilisation - 0.80) * 100)

        # Each past-due event deducts 15 pts (capped at 40 pts total penalty)
        default_penalty = min(default_count * 15, 40)

        # Each active LC adds 5 pts (up to 20 pts bonus) — signals active trade
        lc_bonus = min(active_lcs * 5, 20)

        raw = min(util_score + lc_bonus - default_penalty, 100)
        raw = max(raw, 0)  # Floor at 0 — penalties cannot make score negative

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
        """
        Score geographic market presence using active SIM countries
        and CIB payment corridors.

        Single-market businesses score lower (concentration risk).
        Extremely wide geographic spread (>10 countries) also scores
        lower because operational complexity becomes a risk factor.

        :param cell: Cell profile dict.
        :param cib:  CIB profile dict.
        :return:     ScoreComponent for geographic_coverage.
        """
        name = "geographic_coverage"
        weight = _COMPONENT_WEIGHTS[name]

        if not cell and not cib:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No geographic data available",
                data_present=False,
            )

        # Average active country count across cell and CIB domains
        country_count = (
            (cell or {}).get("active_country_count", 1) +
            (cib or {}).get("payment_corridor_country_count", 0)
        ) // 2 or 1  # Floor at 1 to avoid division by zero

        # Tiered scoring: more corridors = more diversified, up to a complexity ceiling
        if country_count == 1:
            raw = 30   # Single-market: concentration risk
        elif country_count <= 3:
            raw = 55   # Small pan-African presence
        elif country_count <= 6:
            raw = 75   # Well-diversified across sub-regions
        elif country_count <= 10:
            raw = 85   # Strong multi-country footprint
        else:
            raw = 70   # >10 corridors introduces operational complexity risk

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
        """
        Score financial risk management sophistication using FX hedge
        ratio and presence of active insurance policies.

        Clients who hedge currency exposure and hold insurance are more
        resilient to African market volatility.

        :param forex:     Forex profile dict.
        :param insurance: Insurance profile dict.
        :return:          ScoreComponent for risk_management.
        """
        name = "risk_management"
        weight = _COMPONENT_WEIGHTS[name]

        if not forex and not insurance:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No risk management data available",
                data_present=False,
            )

        # Whether the client has any active FX forward contracts
        has_hedges = (forex or {}).get("has_active_forwards", False)

        # Fraction of FX exposure covered by forwards (0.0–1.0)
        hedge_ratio = (forex or {}).get("hedge_ratio", 0.0)

        # Whether the client holds any active insurance policies
        has_insurance = insurance is not None and (
            insurance.get("active_policy_count", 0) > 0
        )

        # Hedge sub-score: full hedge (ratio=1.0) → 60 pts
        hedge_score = 0.0
        if has_hedges:
            hedge_score = min(hedge_ratio * 100, 60)

        # Insurance bonus: any active policy adds 30 pts
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
        """
        Score insurance coverage adequacy as the ratio of total sum
        assured to total credit facility value.

        A coverage ratio >= 1.0 means assets are fully insured relative
        to credit exposure — lender has collateral protection.

        :param insurance: Insurance profile dict.
        :param cib:       CIB profile dict (for facility value baseline).
        :return:          ScoreComponent for insurance_adequacy.
        """
        name = "insurance_adequacy"
        weight = _COMPONENT_WEIGHTS[name]

        if not insurance:
            return ScoreComponent(
                name=name, weight=weight,
                raw_score=0.0, weighted_score=0.0,
                description="No insurance data available",
                data_present=False,
            )

        # Total sum assured across all active insurance policies (ZAR)
        sum_assured = insurance.get("total_sum_assured_zar", 0.0)

        # Total credit facility value from CIB — used as the denominator benchmark
        # Default to 1.0 to avoid division by zero when CIB is absent
        facility_value = (cib or {}).get("total_facility_value_zar", 1.0)

        # Coverage ratio: >1.0 means fully covered; 0.0 means uninsured
        coverage_ratio = (
            sum_assured / facility_value if facility_value > 0 else 0.0
        )

        # Tiered scoring based on coverage ratio thresholds
        if coverage_ratio >= 1.0:
            raw = 90   # Fully covered — strong protection for lender
        elif coverage_ratio >= 0.5:
            raw = 70   # More than half covered — acceptable
        elif coverage_ratio >= 0.2:
            raw = 45   # Partially covered — notable gap
        elif coverage_ratio > 0:
            raw = 25   # Minimal coverage — significant exposure
        else:
            raw = 0    # Completely uninsured

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
        """
        Map a 300–850 score to a viability band label.

        :param score: Scaled viability score.
        :return:      Band label string.
        """
        if score >= 750:
            return "EXCELLENT"
        elif score >= 680:
            return "STRONG"
        elif score >= 580:
            return "STABLE"
        elif score >= 450:
            return "MARGINAL"
        return "DISTRESSED"  # Below 450 — high credit risk

    def _lending_params(
        self, band: str, completeness: float
    ) -> tuple:
        """
        Return a (recommendation string, max_facility_multiple) tuple
        for a given viability band and data completeness level.

        Low completeness (<40% of domain weights present) triggers a
        mandatory manual review caveat regardless of band.

        :param band:         Viability band from _band().
        :param completeness: Fraction of domain weights backed by data.
        :return:             (recommendation, facility_multiple) tuple.
        """
        # Base parameters by band: (text recommendation, revenue multiple)
        params = {
            "EXCELLENT": ("Approve. Preferential pricing eligible.", 4.0),
            "STRONG":    ("Approve. Standard terms.", 3.0),
            "STABLE":    ("Approve with conditions. Annual review.", 2.0),
            "MARGINAL":  ("Conditional approval. Require collateral.", 1.0),
            "DISTRESSED":("Decline or refer to turnaround team.", 0.0),
        }
        recommendation, multiple = params.get(band, ("Review manually.", 0.5))

        # Low data completeness: halve the facility multiple and flag for human review
        if completeness < 0.40:
            recommendation += " NOTE: Low data completeness — manual review required."
            multiple *= 0.5

        return recommendation, multiple
