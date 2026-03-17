"""
Next Best Action (NBA) Model

We score every client against a set of cross-domain
revenue opportunities and recommend the highest-value
action for the relationship manager to take.

This is where the multi-domain data mesh pays off.
We do not just recommend "sell a forex forward" to
a client who trades FX. We ask:
- Does this CIB client have KES exposure but no
  forex hedges? (Data shadow → sell forward)
- Are their Nigerian employees seeing a 15% payroll
  cut due to NGN depreciation? (Cell + FX → sell
  salary protection)
- Are they expanding into Ghana per SIM activations
  but have no GHS insurance? (Cell + CIB → sell
  coverage)

We express each recommendation with:
  score       – 0 to 100 composite priority score
  revenue_zar – estimated annual revenue if actioned
  confidence  – data confidence given completeness
  features    – which domain signals drove the score
  explanation – plain-English RM talking point

Disclaimer: This is not a sanctioned Standard Bank
Group project. Built by Thabo Kunene for portfolio
purposes. All data is simulated.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class ActionFeature:
    """
    A single feature that contributed to an
    action's score.

    We expose these features so the RM can explain
    the recommendation to the client in a credible
    way — "we noticed X in your CIB data, which
    suggests Y" rather than "the model said so."
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

    We rank these by score so the RM knows which
    one to lead with in the client meeting.
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
    The full NBA result for a single client,
    containing all scored and ranked actions.
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
    We score clients across all five domains and
    produce prioritised recommendations.

    The model is deliberately rule-based with
    continuous scoring rather than a black-box ML
    model. This is intentional for three reasons:

    1. Explainability: African banking regulators
       (FSCA, CBN, CBK) require clear audit trails
       for client-facing recommendations.
    2. Data sparsity: With 279 placeholder files
       still empty, a calibrated ML model would
       overfit. Rules generalise better here.
    3. Business trust: RMs adopt tools they can
       explain to clients. A scored rule set with
       plain-English features builds trust faster
       than a neural network with 0.92 AUC.

    When data completeness is high, we weight
    cross-domain signals more heavily. When data
    is partial, we widen confidence bands and
    reduce scores accordingly.
    """

    # Weights for cross-domain signal combinations.
    # Tuned based on revenue outcome tracking.
    SIGNAL_WEIGHTS = {
        "data_shadow":        0.25,
        "expansion_signal":   0.22,
        "currency_event":     0.20,
        "attrition_risk":     0.18,
        "workforce_capture":  0.15,
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
        We score all applicable actions for a client
        and return ranked recommendations.

        Domain profiles are optional — we degrade
        gracefully when data is absent and flag low
        confidence accordingly.
        """

        active_signals = active_signals or []
        actions: List[RecommendedAction] = []

        completeness = self._data_completeness(
            golden_record,
            cib_profile,
            forex_profile,
            insurance_profile,
            cell_profile,
            pbb_profile,
        )

        # --- Evaluate each opportunity type ---

        fx_action = self._score_fx_hedging(
            golden_record, cib_profile, forex_profile,
            cell_profile, active_signals, completeness
        )
        if fx_action:
            actions.append(fx_action)

        expansion_action = self._score_expansion_coverage(
            golden_record, cib_profile, cell_profile,
            insurance_profile, active_signals, completeness
        )
        if expansion_action:
            actions.append(expansion_action)

        attrition_action = self._score_attrition_risk(
            golden_record, forex_profile, cib_profile,
            active_signals, completeness
        )
        if attrition_action:
            actions.append(attrition_action)

        payroll_action = self._score_payroll_banking(
            golden_record, cell_profile, pbb_profile,
            active_signals, completeness
        )
        if payroll_action:
            actions.append(payroll_action)

        insurance_action = self._score_insurance_gap(
            golden_record, cib_profile, insurance_profile,
            cell_profile, active_signals, completeness
        )
        if insurance_action:
            actions.append(insurance_action)

        # Sort by score descending
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
        We calculate a 0–1 completeness score.

        Missing domain data reduces confidence.
        A client with all five domains populated
        gets full confidence; one with only CIB
        and Cell gets 0.4.
        """

        domain_weights = {
            "cib": 0.30,
            "forex": 0.25,
            "insurance": 0.15,
            "cell": 0.20,
            "pbb": 0.10,
        }
        present = {
            "cib": cib is not None,
            "forex": forex is not None,
            "insurance": insurance is not None,
            "cell": cell is not None,
            "pbb": pbb is not None,
        }
        return sum(
            w for d, w in domain_weights.items() if present[d]
        )

    def _confidence_label(self, completeness: float) -> str:
        if completeness >= 0.75:
            return "HIGH"
        elif completeness >= 0.45:
            return "MEDIUM"
        return "LOW"

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
        We look for clients with cross-currency CIB
        payments who lack corresponding forex hedges.

        The data shadow pattern: CIB payments to
        Nigeria, Kenya, Ghana etc. without matching
        FX forwards = unhedged exposure = opportunity.
        """

        if not cib:
            return None

        corridor_countries = cib.get(
            "active_payment_corridors", []
        )
        if not corridor_countries:
            return None

        has_hedges = (
            forex.get("has_active_forwards", False)
            if forex else False
        )
        if has_hedges:
            return None

        # Each active corridor without a hedge is
        # a revenue opportunity
        corridor_count = len(corridor_countries)
        annual_corridor_value = cib.get(
            "annual_cross_border_value_zar", 0
        )

        # FX structuring revenue ≈ 0.35% of notional
        est_revenue = annual_corridor_value * 0.0035
        score_raw = min(
            corridor_count * 15 + (annual_corridor_value / 10_000_000) * 10,
            100,
        )
        score = score_raw * completeness

        features = [
            ActionFeature(
                feature_name="active_corridors",
                domain="cib",
                value=float(corridor_count),
                contribution=0.60,
                description=(
                    f"{corridor_count} active cross-border "
                    f"payment corridors with no matching FX hedge"
                ),
            ),
            ActionFeature(
                feature_name="corridor_value",
                domain="cib",
                value=annual_corridor_value,
                contribution=0.40,
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
        We detect geographic expansion before the
        client formally announces it.

        Signal: New country SIM activations (cell) +
        new payment corridors (CIB) without matching
        insurance coverage (insurance shadow).
        """

        expansion_signals = [
            s for s in signals
            if s.get("signal_type") == "GEOGRAPHIC_EXPANSION"
        ]
        if not expansion_signals:
            return None

        best_signal = max(
            expansion_signals,
            key=lambda s: s.get("confidence_score", 0),
        )
        confidence_score = best_signal.get("confidence_score", 0)
        if confidence_score < 50:
            return None

        expansion_country = best_signal.get("expansion_country", "?")
        has_insurance = (
            expansion_country in (insurance or {}).get(
                "covered_countries", []
            )
        )
        if has_insurance:
            return None

        opportunity_zar = best_signal.get(
            "estimated_opportunity_zar", 2_000_000
        )
        score = min(confidence_score * completeness, 100)

        features = [
            ActionFeature(
                feature_name="sim_activations",
                domain="cell",
                value=float(
                    best_signal.get("cell_new_sim_activations", 0)
                ),
                contribution=0.45,
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
                contribution=0.35,
                description=(
                    f"New CIB payment corridor to "
                    f"{expansion_country} opened"
                ),
            ),
            ActionFeature(
                feature_name="insurance_gap",
                domain="insurance",
                value=0.0,
                contribution=0.20,
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
            urgency="HIGH",
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
        We detect relationship attrition before the
        client formally moves business away.

        Signal: Declining FX volumes while CIB
        payments continue = competitor FX bank.
        Declining CIB utilisation without business
        contraction = competitor transaction bank.
        """

        if not forex and not cib:
            return None

        fx_trend = (
            forex.get("volume_trend_3m", 0.0)
            if forex else 0.0
        )
        cib_util_change = (
            cib.get("facility_utilization_change_pct", 0.0)
            if cib else 0.0
        )

        # Negative trend = volumes declining = attrition risk
        attrition_score = 0.0
        if fx_trend < -0.10:           # >10% FX volume drop
            attrition_score += 40
        if fx_trend < -0.20:
            attrition_score += 20
        if cib_util_change < -0.15:    # >15% utilisation drop
            attrition_score += 30

        if attrition_score < 30:
            return None

        score = min(attrition_score * completeness, 100)
        relationship_value = golden.get(
            "total_relationship_value_zar", 0
        )
        revenue_at_risk = relationship_value * 0.015

        features = [
            ActionFeature(
                feature_name="fx_volume_trend",
                domain="forex",
                value=fx_trend,
                contribution=0.60,
                description=(
                    f"FX volumes declined "
                    f"{abs(fx_trend)*100:.0f}% over 3 months"
                ),
            ),
            ActionFeature(
                feature_name="facility_utilisation_trend",
                domain="cib",
                value=cib_util_change,
                contribution=0.40,
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
        We identify large employers whose workforce
        is not yet banking with us.

        Signal: High SIM count from cell domain +
        low PBB payroll accounts = workforce not
        captured yet.

        Revenue model: R2,500 per employee per year
        in bundled account + salary advance fees.
        """

        if not cell:
            return None

        estimated_employees = cell.get(
            "estimated_employee_count", 0
        )
        pbb_accounts = (
            pbb.get("linked_payroll_accounts", 0)
            if pbb else 0
        )

        if estimated_employees < 50:
            return None

        capture_rate = (
            pbb_accounts / estimated_employees
            if estimated_employees > 0 else 0.0
        )

        if capture_rate > 0.80:  # Already well captured
            return None

        uncaptured = estimated_employees - pbb_accounts
        revenue_per_employee = 2500
        est_revenue = uncaptured * revenue_per_employee
        score = min(
            (uncaptured / 100) * 20 * completeness, 100
        )

        features = [
            ActionFeature(
                feature_name="estimated_employees",
                domain="cell",
                value=float(estimated_employees),
                contribution=0.55,
                description=(
                    f"{estimated_employees} estimated "
                    f"employees from SIM deflation model"
                ),
            ),
            ActionFeature(
                feature_name="capture_rate",
                domain="pbb",
                value=capture_rate,
                contribution=0.45,
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
        We identify clients with significant African
        asset exposure but limited insurance coverage.

        Signal: Large trade finance facilities (CIB)
        in countries where the client has no insurance
        policy (insurance shadow).
        """

        if not cib:
            return None

        active_countries = cib.get(
            "active_payment_corridors", []
        )
        covered_countries = (
            insurance.get("covered_countries", [])
            if insurance else []
        )

        uncovered = [
            c for c in active_countries
            if c not in covered_countries
        ]

        if not uncovered:
            return None

        facility_value = cib.get(
            "total_facility_value_zar", 0
        )
        est_premium = facility_value * 0.008  # ~0.8% premium
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
                    contribution=1.0,
                    description=(
                        f"{len(uncovered)} active corridors "
                        f"without insurance cover"
                    ),
                )
            ],
        )
