"""
@file nba_model.py
@description Next Best Action (NBA) model for relationship manager recommendations.

             Scores every client against a set of cross-domain revenue
             opportunities and recommends the highest-value action for the
             relationship manager to take.

             This is where the multi-domain data mesh pays off.
             We do not just recommend "sell a forex forward" to a client
             who trades FX. We ask:
               - Does this CIB client have KES exposure but no forex hedges?
                 (Data shadow → sell forward)
               - Are their Nigerian employees seeing a 15% payroll cut due
                 to NGN depreciation? (Cell + FX → sell salary protection)
               - Are they expanding into Ghana per SIM activations but have
                 no GHS insurance? (Cell + CIB → sell coverage)

             Each recommendation is expressed with:
               score       – 0 to 100 composite priority score
               revenue_zar – estimated annual revenue if actioned
               confidence  – data confidence given completeness
               features    – which domain signals drove the score
               explanation – plain-English RM talking point

             Disclaimer: This is not a sanctioned Standard Bank Group
             project. Built by Thabo Kunene for portfolio purposes.
             All data is simulated.
@author Thabo Kunene
@created 2026-03-18
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class ActionFeature:
    """
    A single feature that contributed to an action's score.

    Exposed so the RM can explain the recommendation to the client in a
    credible way — "we noticed X in your CIB data, which suggests Y"
    rather than "the model said so."

    :param feature_name: Descriptive name for the signal (e.g. "active_corridors").
    :param domain:       Source domain (cib / forex / cell / insurance / pbb).
    :param value:        Raw feature value observed.
    :param contribution: 0–1 share of the action's total score this feature drove.
    :param description:  Human-readable evidence string for the RM talking point.
    """

    feature_name: str
    domain: str
    value: float
    contribution: float   # 0–1 share of score
    description: str


@dataclass
class RecommendedAction:
    """
    A single prioritised action for a client.

    Ranked by score so the RM knows which one to lead with in a meeting.

    :param action_id:             Unique identifier (e.g. NBA-FX-GLD-001).
    :param client_golden_id:      AfriFlow golden record identifier.
    :param action_type:           SELL / RETAIN / PROTECT / REVIEW.
    :param product_category:      FX / CIB / INSURANCE / PBB / CELL.
    :param product_name:          Specific product being recommended.
    :param score:                 Composite priority score 0–100.
    :param confidence:            HIGH / MEDIUM / LOW based on data completeness.
    :param estimated_revenue_zar: Expected annual revenue if actioned.
    :param urgency:               IMMEDIATE / HIGH / MEDIUM / LOW.
    :param rm_talking_point:      Plain-English conversation starter for the RM.
    :param features:              List of ActionFeature instances driving the score.
    :param generated_at:          ISO timestamp of recommendation generation.
    """

    action_id: str
    client_golden_id: str
    action_type: str          # SELL, RETAIN, PROTECT, REVIEW
    product_category: str     # FX, CIB, INSURANCE, PBB, CELL
    product_name: str
    score: float              # 0–100
    confidence: str           # HIGH, MEDIUM, LOW
    estimated_revenue_zar: float
    urgency: str              # IMMEDIATE, HIGH, MEDIUM, LOW
    rm_talking_point: str
    features: List[ActionFeature] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


@dataclass
class ClientNBAResult:
    """
    The full NBA result for a single client, containing all scored and
    ranked actions.

    :param client_golden_id:       AfriFlow golden record identifier.
    :param client_name:            Canonical client name.
    :param top_action:             The single highest-scoring recommendation.
    :param all_actions:            All recommendations sorted by score descending.
    :param data_completeness_score: 0–1 coverage fraction across five domains.
    :param generated_at:           ISO timestamp.
    """

    client_golden_id: str
    client_name: str
    top_action: Optional[RecommendedAction]
    all_actions: List[RecommendedAction]
    data_completeness_score: float   # 0–1
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


class NextBestActionModel:
    """
    Score clients across all five domains and produce prioritised
    recommendations for the relationship manager.

    The model is deliberately rule-based with continuous scoring rather
    than a black-box ML model.  This is intentional for three reasons:

    1. Explainability: African banking regulators (FSCA, CBN, CBK) require
       clear audit trails for client-facing recommendations.
    2. Data sparsity: A calibrated ML model would overfit. Rules generalise
       better here.
    3. Business trust: RMs adopt tools they can explain to clients.

    When data completeness is high, cross-domain signals are weighted more
    heavily. When data is partial, confidence bands are widened and scores
    are reduced accordingly.
    """

    # Weights for cross-domain signal combinations — tuned on revenue outcomes
    SIGNAL_WEIGHTS = {
        "data_shadow":        0.25,  # Unhedged exposure / coverage gap signals
        "expansion_signal":   0.22,  # Geographic expansion detection
        "currency_event":     0.20,  # Currency devaluation / event triggers
        "attrition_risk":     0.18,  # Wallet-share decline signals
        "workforce_capture":  0.15,  # Payroll account capture opportunity
    }

    def score_client(
        self,
        golden_record: Dict,
        cib_profile: Optional[Dict] = None,
        forex_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
        cell_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
        active_signals: Optional[List[Dict]] = None,
    ) -> ClientNBAResult:
        """
        Score all applicable actions for a client and return ranked
        recommendations.

        Domain profiles are optional — the model degrades gracefully when
        data is absent and flags low confidence accordingly.

        :param golden_record:    Mandatory golden record dict; must contain "golden_id".
        :param cib_profile:      CIB domain profile dict.
        :param forex_profile:    Forex domain profile dict.
        :param insurance_profile: Insurance domain profile dict.
        :param cell_profile:     Cell/MoMo domain profile dict.
        :param pbb_profile:      PBB domain profile dict.
        :param active_signals:   List of cross-domain signal dicts from the signal layer.
        :return:                 ClientNBAResult with ranked recommendations.
        """

        active_signals = active_signals or []
        actions: List[RecommendedAction] = []

        # Compute data completeness (0–1) — drives confidence labels and score scaling
        completeness = self._data_completeness(
            golden_record,
            cib_profile,
            forex_profile,
            insurance_profile,
            cell_profile,
            pbb_profile,
        )

        # --- Evaluate each opportunity type ---

        # Opportunity 1: FX hedging — unhedged cross-border CIB corridors
        fx_action = self._score_fx_hedging(
            golden_record, cib_profile, forex_profile,
            cell_profile, active_signals, completeness
        )
        if fx_action:
            actions.append(fx_action)

        # Opportunity 2: Expansion coverage — insurance gap in new markets
        expansion_action = self._score_expansion_coverage(
            golden_record, cib_profile, cell_profile,
            insurance_profile, active_signals, completeness
        )
        if expansion_action:
            actions.append(expansion_action)

        # Opportunity 3: Attrition risk — FX / CIB wallet-share declining
        attrition_action = self._score_attrition_risk(
            golden_record, forex_profile, cib_profile,
            active_signals, completeness
        )
        if attrition_action:
            actions.append(attrition_action)

        # Opportunity 4: Payroll banking — uncaptured workforce employees
        payroll_action = self._score_payroll_banking(
            golden_record, cell_profile, pbb_profile,
            active_signals, completeness
        )
        if payroll_action:
            actions.append(payroll_action)

        # Opportunity 5: Insurance gap — active CIB corridors without cover
        insurance_action = self._score_insurance_gap(
            golden_record, cib_profile, insurance_profile,
            cell_profile, active_signals, completeness
        )
        if insurance_action:
            actions.append(insurance_action)

        # Sort by score descending — highest-value action first
        actions.sort(key=lambda a: a.score, reverse=True)

        top = actions[0] if actions else None

        return ClientNBAResult(
            client_golden_id=golden_record.get(
                "golden_id", "UNKNOWN"
            ),
            client_name=golden_record.get(
                "canonical_name", "Unknown Client"
            ),
            top_action=top,
            all_actions=actions,
            data_completeness_score=completeness,
        )

    def _data_completeness(
        self,
        golden_record: Dict,
        cib: Optional[Dict],
        forex: Optional[Dict],
        insurance: Optional[Dict],
        cell: Optional[Dict],
        pbb: Optional[Dict],
    ) -> float:
        """
        Compute a 0–1 completeness score based on which domain profiles
        are present.

        Domain weights reflect their relative importance to the NBA model:
        CIB and Forex carry the most weight as they are the primary
        signal sources for cross-domain opportunities.

        :param golden_record: Golden record dict (not used directly; included for future).
        :param cib:           CIB profile dict.
        :param forex:         Forex profile dict.
        :param insurance:     Insurance profile dict.
        :param cell:          Cell profile dict.
        :param pbb:           PBB profile dict.
        :return:              Completeness score (0–1).
        """

        # Domain weights for completeness calculation — must sum to 1.0
        domain_weights = {
            "cib":       0.30,  # CIB is the primary deal-flow signal
            "forex":     0.25,  # FX is the primary wallet-share signal
            "insurance": 0.15,  # Insurance coverage gap is a key opportunity
            "cell":      0.20,  # Cell data drives workforce + expansion signals
            "pbb":       0.10,  # PBB adds payroll and deposit signals
        }

        # Map presence of each domain profile to its weight contribution
        present = {
            "cib":       cib is not None,
            "forex":     forex is not None,
            "insurance": insurance is not None,
            "cell":      cell is not None,
            "pbb":       pbb is not None,
        }
        return sum(
            w for d, w in domain_weights.items() if present[d]
        )

    def _confidence_label(self, completeness: float) -> str:
        """
        Map a completeness fraction to a model confidence label.

        :param completeness: 0–1 data completeness score.
        :return:             Confidence label string (HIGH / MEDIUM / LOW).
        """
        if completeness >= 0.75:
            return "HIGH"    # Most domains present — high confidence
        elif completeness >= 0.45:
            return "MEDIUM"  # Core domains present — moderate confidence
        return "LOW"         # Partial data — indicative only

    def _score_fx_hedging(
        self,
        golden: Dict,
        cib: Optional[Dict],
        forex: Optional[Dict],
        cell: Optional[Dict],
        signals: List[Dict],
        completeness: float,
    ) -> Optional[RecommendedAction]:
        """
        Score FX hedging opportunity.

        Identifies clients with active cross-border CIB payment corridors
        who lack corresponding FX forward hedges — unhedged currency exposure.

        Data shadow pattern: CIB payments to Nigeria, Kenya, Ghana etc.
        without matching FX forwards = unhedged exposure = opportunity.

        :param golden:       Golden record dict.
        :param cib:          CIB profile dict.
        :param forex:        Forex profile dict.
        :param cell:         Cell profile dict.
        :param signals:      Cross-domain signal list.
        :param completeness: Data completeness fraction for confidence scaling.
        :return:             RecommendedAction or None if condition not met.
        """

        if not cib:
            return None

        # List of active payment corridor country codes (e.g. ["NG", "KE", "GH"])
        corridor_countries = cib.get(
            "active_payment_corridors", []
        )
        if not corridor_countries:
            return None

        # Check if the client already has FX hedges in place
        has_hedges = (
            forex.get("has_active_forwards", False)
            if forex else False
        )
        if has_hedges:
            return None  # Already hedged — no opportunity

        # Each active corridor without a hedge is a revenue opportunity
        corridor_count = len(corridor_countries)
        annual_corridor_value = cib.get(
            "annual_cross_border_value_zar", 0
        )

        # FX structuring revenue ≈ 0.35% of notional
        est_revenue = annual_corridor_value * 0.0035

        # Raw score: corridor count × 15 pts + value contribution (up to 100)
        score_raw = min(
            corridor_count * 15 + (annual_corridor_value / 10_000_000) * 10,
            100,
        )
        # Scale by completeness — low data quality reduces confidence and score
        score = score_raw * completeness

        # Build feature breakdown for RM explainability
        features = [
            ActionFeature(
                feature_name="active_corridors",
                domain="cib",
                value=float(corridor_count),
                contribution=0.60,  # Corridor count drives 60% of score
                description=(
                    f"{corridor_count} active cross-border "
                    f"payment corridors with no matching FX hedge"
                ),
            ),
            ActionFeature(
                feature_name="corridor_value",
                domain="cib",
                value=annual_corridor_value,
                contribution=0.40,  # Value at risk drives 40% of score
                description=(
                    f"R{annual_corridor_value:,.0f} annual "
                    f"cross-border flow at risk"
                ),
            ),
        ]

        return RecommendedAction(
            action_id=(
                f"NBA-FX-{golden.get('golden_id', 'UNK')}"
            ),
            client_golden_id=golden.get("golden_id", ""),
            action_type="SELL",
            product_category="FX",
            product_name="FX Forward / Hedging Programme",
            score=round(score, 1),
            confidence=self._confidence_label(completeness),
            estimated_revenue_zar=round(est_revenue, 0),
            urgency=(
                "HIGH" if corridor_count >= 3 else "MEDIUM"
            ),
            rm_talking_point=(
                f"Your client is making cross-border payments "
                f"to {', '.join(corridor_countries[:3])} "
                f"totalling R{annual_corridor_value:,.0f}/year "
                f"with zero FX hedging in place. A single "
                f"currency move in NGN or KES could wipe out "
                f"a quarter's profit on that corridor."
            ),
            features=features,
        )

    def _score_expansion_coverage(
        self,
        golden: Dict,
        cib: Optional[Dict],
        cell: Optional[Dict],
        insurance: Optional[Dict],
        signals: List[Dict],
        completeness: float,
    ) -> Optional[RecommendedAction]:
        """
        Score geographic expansion insurance coverage opportunity.

        Detects geographic expansion before the client formally announces
        it, by looking for new SIM activations in a country (cell) plus
        new CIB payment corridors, without matching insurance coverage.

        :param golden:       Golden record dict.
        :param cib:          CIB profile dict.
        :param cell:         Cell profile dict.
        :param insurance:    Insurance profile dict.
        :param signals:      Cross-domain signal list (expansion signals used here).
        :param completeness: Data completeness fraction for confidence scaling.
        :return:             RecommendedAction or None if condition not met.
        """

        # Filter signals to only geographic expansion type
        expansion_signals = [
            s for s in signals
            if s.get("signal_type") == "GEOGRAPHIC_EXPANSION"
        ]
        if not expansion_signals:
            return None

        # Use the expansion signal with highest confidence
        best_signal = max(
            expansion_signals,
            key=lambda s: s.get("confidence_score", 0),
        )
        confidence_score = best_signal.get("confidence_score", 0)
        if confidence_score < 50:
            return None  # Low-confidence expansion signal — do not act

        expansion_country = best_signal.get("expansion_country", "?")

        # Check if insurance already covers this country
        has_insurance = (
            expansion_country in (insurance or {}).get(
                "covered_countries", []
            )
        )
        if has_insurance:
            return None  # Already insured — no gap to close

        opportunity_zar = best_signal.get(
            "estimated_opportunity_zar", 2_000_000
        )
        # Scale raw confidence score by data completeness
        score = min(confidence_score * completeness, 100)

        features = [
            ActionFeature(
                feature_name="sim_activations",
                domain="cell",
                value=float(
                    best_signal.get("cell_new_sim_activations", 0)
                ),
                contribution=0.45,  # SIM activations are the primary expansion signal
                description=(
                    f"New SIM activations detected in "
                    f"{expansion_country}"
                ),
            ),
            ActionFeature(
                feature_name="new_corridors",
                domain="cib",
                value=float(
                    best_signal.get("cib_new_corridor_payments", 0)
                ),
                contribution=0.35,  # New CIB corridor confirms commercial activity
                description=(
                    f"New CIB payment corridor to "
                    f"{expansion_country} opened"
                ),
            ),
            ActionFeature(
                feature_name="insurance_gap",
                domain="insurance",
                value=0.0,
                contribution=0.20,  # Absence of insurance is the gap we are closing
                description=(
                    f"No insurance coverage in "
                    f"{expansion_country}"
                ),
            ),
        ]

        return RecommendedAction(
            action_id=(
                f"NBA-EXP-{golden.get('golden_id', 'UNK')}"
            ),
            client_golden_id=golden.get("golden_id", ""),
            action_type="SELL",
            product_category="INSURANCE",
            product_name=(
                f"Trade Credit + Property Cover "
                f"({expansion_country})"
            ),
            score=round(score, 1),
            confidence=self._confidence_label(completeness),
            estimated_revenue_zar=round(opportunity_zar, 0),
            urgency="HIGH",  # Expansion windows are time-sensitive
            rm_talking_point=(
                f"We are seeing new SIM activations and "
                f"payment flows to {expansion_country}. "
                f"Your client appears to be expanding there "
                f"but has no insurance coverage in place. "
                f"This is the window to position before a "
                f"competitor does."
            ),
            features=features,
        )

    def _score_attrition_risk(
        self,
        golden: Dict,
        forex: Optional[Dict],
        cib: Optional[Dict],
        signals: List[Dict],
        completeness: float,
    ) -> Optional[RecommendedAction]:
        """
        Score relationship attrition risk and retention action.

        Detects declining FX volumes while CIB payments continue
        (competitor FX bank), or declining CIB utilisation without
        business contraction (competitor transaction bank).

        :param golden:       Golden record dict.
        :param forex:        Forex profile dict.
        :param cib:          CIB profile dict.
        :param signals:      Cross-domain signal list (not used directly here).
        :param completeness: Data completeness fraction for confidence scaling.
        :return:             RecommendedAction or None if no attrition signal.
        """

        if not forex and not cib:
            return None

        # 3-month FX volume trend; 0.0 default if forex data absent
        fx_trend = (
            forex.get("volume_trend_3m", 0.0)
            if forex else 0.0
        )
        # Change in CIB facility utilisation; 0.0 default if CIB absent
        cib_util_change = (
            cib.get("facility_utilization_change_pct", 0.0)
            if cib else 0.0
        )

        # Accumulate attrition score based on decline thresholds
        attrition_score = 0.0
        if fx_trend < -0.10:           # >10% FX volume drop — early warning
            attrition_score += 40
        if fx_trend < -0.20:           # >20% — confirmation of competitor capture
            attrition_score += 20
        if cib_util_change < -0.15:    # >15% utilisation drop — facility migrating
            attrition_score += 30

        # Only flag if attrition score crosses the minimum threshold
        if attrition_score < 30:
            return None

        # Scale by completeness
        score = min(attrition_score * completeness, 100)

        # Estimate revenue at risk: 1.5% of total relationship value
        relationship_value = golden.get(
            "total_relationship_value_zar", 0
        )
        revenue_at_risk = relationship_value * 0.015

        features = [
            ActionFeature(
                feature_name="fx_volume_trend",
                domain="forex",
                value=fx_trend,
                contribution=0.60,  # FX trend is the primary attrition signal
                description=(
                    f"FX volumes declined "
                    f"{abs(fx_trend)*100:.0f}% over 3 months"
                ),
            ),
            ActionFeature(
                feature_name="facility_utilisation_trend",
                domain="cib",
                value=cib_util_change,
                contribution=0.40,  # Utilisation drop confirms relationship erosion
                description=(
                    f"Facility utilisation dropped "
                    f"{abs(cib_util_change)*100:.0f}%"
                ),
            ),
        ]

        return RecommendedAction(
            action_id=(
                f"NBA-ATR-{golden.get('golden_id', 'UNK')}"
            ),
            client_golden_id=golden.get("golden_id", ""),
            action_type="RETAIN",
            product_category="CIB",
            product_name="Relationship Retention Review",
            score=round(score, 1),
            confidence=self._confidence_label(completeness),
            estimated_revenue_zar=round(revenue_at_risk, 0),
            urgency=(
                "IMMEDIATE" if score > 70 else "HIGH"
            ),
            rm_talking_point=(
                f"FX volumes have declined "
                f"{abs(fx_trend)*100:.0f}% over 3 months "
                f"while the client's underlying business "
                f"has not contracted. This pattern is "
                f"consistent with competitor FX capture. "
                f"Recommend proactive relationship meeting."
            ),
            features=features,
        )

    def _score_payroll_banking(
        self,
        golden: Dict,
        cell: Optional[Dict],
        pbb: Optional[Dict],
        signals: List[Dict],
        completeness: float,
    ) -> Optional[RecommendedAction]:
        """
        Score payroll banking opportunity.

        Identifies large employers whose workforce is not yet banking with
        the institution. Signal: high SIM count from cell domain + low PBB
        payroll accounts = workforce not yet captured.

        Revenue model: R2,500 per employee per year in bundled account
        + salary advance fees.

        :param golden:       Golden record dict.
        :param cell:         Cell profile dict.
        :param pbb:          PBB profile dict.
        :param signals:      Cross-domain signal list.
        :param completeness: Data completeness fraction.
        :return:             RecommendedAction or None if workforce too small
                             or already well captured.
        """

        if not cell:
            return None

        # SIM deflation model employee count estimate from cell domain
        estimated_employees = cell.get(
            "estimated_employee_count", 0
        )

        # Number of employees with linked PBB payroll accounts
        pbb_accounts = (
            pbb.get("linked_payroll_accounts", 0)
            if pbb else 0
        )

        # Minimum threshold: ignore micro-employers (< 50 staff)
        if estimated_employees < 50:
            return None

        # Capture rate: fraction of workforce already banking with us
        capture_rate = (
            pbb_accounts / estimated_employees
            if estimated_employees > 0 else 0.0
        )

        if capture_rate > 0.80:
            return None  # Already well captured — diminishing returns

        # Uncaptured workforce = opportunity mass
        uncaptured = estimated_employees - pbb_accounts
        revenue_per_employee = 2500  # ZAR per employee per year (conservative)
        est_revenue = uncaptured * revenue_per_employee

        # Score: every 100 uncaptured employees adds 20 pts, scaled by completeness
        score = min(
            (uncaptured / 100) * 20 * completeness, 100
        )

        features = [
            ActionFeature(
                feature_name="estimated_employees",
                domain="cell",
                value=float(estimated_employees),
                contribution=0.55,  # Headcount size drives most of the opportunity
                description=(
                    f"{estimated_employees} estimated "
                    f"employees from SIM deflation model"
                ),
            ),
            ActionFeature(
                feature_name="capture_rate",
                domain="pbb",
                value=capture_rate,
                contribution=0.45,  # Capture gap drives urgency
                description=(
                    f"Only {capture_rate*100:.0f}% of "
                    f"workforce banking with us"
                ),
            ),
        ]

        return RecommendedAction(
            action_id=(
                f"NBA-PBB-{golden.get('golden_id', 'UNK')}"
            ),
            client_golden_id=golden.get("golden_id", ""),
            action_type="SELL",
            product_category="PBB",
            product_name="Corporate Payroll Banking Package",
            score=round(score, 1),
            confidence=self._confidence_label(completeness),
            estimated_revenue_zar=round(est_revenue, 0),
            urgency="MEDIUM",
            rm_talking_point=(
                f"Our cell network data estimates "
                f"{estimated_employees} employees at this "
                f"client but only {pbb_accounts} payroll "
                f"accounts linked. That is "
                f"{uncaptured} employees banking elsewhere, "
                f"representing R{est_revenue:,.0f}/year in "
                f"untapped PBB revenue."
            ),
            features=features,
        )

    def _score_insurance_gap(
        self,
        golden: Dict,
        cib: Optional[Dict],
        insurance: Optional[Dict],
        cell: Optional[Dict],
        signals: List[Dict],
        completeness: float,
    ) -> Optional[RecommendedAction]:
        """
        Score insurance coverage gap opportunity.

        Identifies clients with significant African asset exposure (active
        CIB corridors) but no insurance coverage in those countries.

        :param golden:       Golden record dict.
        :param cib:          CIB profile dict.
        :param insurance:    Insurance profile dict.
        :param cell:         Cell profile dict (reserved for future corridor signals).
        :param signals:      Cross-domain signal list.
        :param completeness: Data completeness fraction.
        :return:             RecommendedAction or None if all corridors are covered.
        """

        if not cib:
            return None

        # Active cross-border payment corridor countries from CIB
        active_countries = cib.get(
            "active_payment_corridors", []
        )

        # Countries where the client already has insurance coverage
        covered_countries = (
            insurance.get("covered_countries", [])
            if insurance else []
        )

        # Uncovered = corridors with CIB exposure but no insurance
        uncovered = [
            c for c in active_countries
            if c not in covered_countries
        ]

        if not uncovered:
            return None  # All corridors are covered — no gap

        # Estimated annual premium: ~0.8% of total facility value
        facility_value = cib.get(
            "total_facility_value_zar", 0
        )
        est_premium = facility_value * 0.008  # 0.8% trade credit premium

        # Score: each uncovered corridor adds 20 pts, scaled by completeness
        score = min(
            len(uncovered) * 20 * completeness, 100
        )

        return RecommendedAction(
            action_id=(
                f"NBA-INS-{golden.get('golden_id', 'UNK')}"
            ),
            client_golden_id=golden.get("golden_id", ""),
            action_type="SELL",
            product_category="INSURANCE",
            product_name="Trade Credit Insurance",
            score=round(score, 1),
            confidence=self._confidence_label(completeness),
            estimated_revenue_zar=round(est_premium, 0),
            urgency="MEDIUM",
            rm_talking_point=(
                f"Client has CIB exposure in "
                f"{', '.join(uncovered)} but no trade "
                f"credit insurance covering those markets. "
                f"A supplier default or political risk event "
                f"in any of those countries is unhedged."
            ),
            features=[
                ActionFeature(
                    feature_name="uncovered_countries",
                    domain="cib",
                    value=float(len(uncovered)),
                    contribution=1.0,  # Single feature — full contribution
                    description=(
                        f"{len(uncovered)} active corridors "
                        f"without insurance cover"
                    ),
                )
            ],
        )
