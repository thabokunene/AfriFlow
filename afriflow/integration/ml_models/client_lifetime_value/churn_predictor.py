"""
@file churn_predictor.py
@description Identifies clients at elevated risk of attrition before they
             formally move business to a competitor.  Pan-African banking
             churn rarely announces itself — it shows up as decaying signal
             intensity across multiple domains simultaneously.
             Five behavioural features are monitored: FX volume decay,
             facility utilisation drop, cell engagement decline, inbound
             payment velocity fall, and insurance lapse.  The multi-domain
             view is critical — a 25% FX volume drop alongside flat CIB
             transactions almost certainly indicates a split FX wallet.
             Output: churn score 0–100, probability of 90-day churn,
             revenue at risk, and a prioritised intervention recommendation.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

import math  # Used for sigmoid-like score-to-probability conversion
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Thresholds — tuned against the simulated outcome tracker
# ---------------------------------------------------------------------------
# These thresholds represent the minimum negative trend that triggers each
# churn feature.  Values are 3-month percentage changes (negative = decline).

_FX_DECAY_THRESHOLD       = -0.15   # 15% FX volume drop triggers fx_volume_decay
_FACILITY_DECAY_THRESHOLD = -0.20   # 20% utilisation drop triggers facility signal
_CELL_SILENCE_THRESHOLD   = -0.30   # 30% MoMo/USSD drop triggers cell_engagement
_PAYMENT_DECAY_THRESHOLD  = -0.18   # 18% inbound payment drop triggers payment_velocity
_INSURANCE_LAPSE_DAYS     = 30      # Policy lapsed > 30 days triggers insurance_lapse

# Feature weights for the composite churn score.
# FX volume decay is weighted highest (0.28) because it is the most reliable
# early-warning signal for CIB client wallet-splitting.
_FEATURE_WEIGHTS: Dict[str, float] = {
    "fx_volume_decay":       0.28,  # FX volume decline — competitor FX bank capture
    "facility_utilisation":  0.24,  # Credit facility drop — competitor transaction bank
    "cell_engagement":       0.20,  # MoMo/USSD decline — digital channel abandonment
    "payment_velocity":      0.16,  # Inbound payment drop — revenue declining
    "insurance_lapse":       0.12,  # Policy not renewed — engagement dropping
}

# Country-specific seasonal correction factors.
# Without these, year-end slowdowns in South Africa would trigger false CRITICAL alerts.
# The factor is multiplied into the raw churn score — values < 1.0 reduce sensitivity.
_COUNTRY_SEASONALITY: Dict[str, Dict[int, float]] = {
    "ZA": {12: 0.7, 1: 0.7},     # SA December/January: year-end accounting slowdown
    "NG": {1: 0.8, 2: 0.8},      # Nigeria Q1: oil price and FX volatility correction
    "KE": {8: 0.9},               # Kenya August: school-fee month cash diversion
    "GH": {10: 0.85, 11: 0.85},  # Ghana Oct/Nov: cocoa harvest cash diversion
    "ZM": {3: 0.8, 4: 0.8},      # Zambia Mar/Apr: copper price dip season
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class ChurnFeature:
    """
    A single churn signal with its normalised contribution.

    :param feature_name:      Key matching _FEATURE_WEIGHTS.
    :param domain:            Source domain (forex / cib / cell / insurance).
    :param raw_value:         Actual metric observed (trend, ratio, etc.).
    :param normalised_score:  0–1 score for this feature (1 = strong churn signal).
    :param weight:            This feature's weight in the composite model.
    :param description:       Human-readable evidence summary.
    """

    feature_name: str
    domain: str
    raw_value: float          # The actual metric (trend, ratio, etc.)
    normalised_score: float   # 0–1 score for this feature
    weight: float             # Weight in composite model
    description: str


@dataclass
class ChurnPrediction:
    """
    Churn prediction for a single client.

    churn_score : 0–100 (higher = more likely to churn)
    churn_band  : GREEN / AMBER / RED / CRITICAL

    :param client_golden_id:          AfriFlow golden record identifier.
    :param churn_score:               Composite churn score 0–100.
    :param churn_band:                Tier label for prioritisation.
    :param probability_90d:           Estimated 90-day churn probability (0–1).
    :param revenue_at_risk_zar:       Expected revenue loss if client churns.
    :param primary_signal:            Feature name of the dominant churn driver.
    :param recommended_intervention:  Plain-English RM action guidance.
    :param features:                  All scored ChurnFeature instances.
    :param confidence:                LOW / MEDIUM / HIGH based on data completeness.
    :param evaluated_at:              ISO timestamp.
    """

    client_golden_id: str
    churn_score: float
    churn_band: str
    probability_90d: float        # Estimated probability of churn in next 90 days
    revenue_at_risk_zar: float    # churn_prob × relationship_value × 60% capture rate
    primary_signal: str           # Dominant churn driver feature name
    recommended_intervention: str
    features: List[ChurnFeature] = field(default_factory=list)
    confidence: str = "MEDIUM"    # LOW / MEDIUM / HIGH
    evaluated_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------

class ChurnPredictor:
    """
    Combine multi-domain signals into a single churn probability estimate.

    Domain profiles follow the same dict contract as the NBA model —
    all are optional and the model degrades gracefully when absent.

    Usage::

        predictor = ChurnPredictor()
        result = predictor.predict(
            golden_record=golden,
            forex_profile=fx,
            cib_profile=cib,
            cell_profile=cell,
            insurance_profile=ins,
            relationship_value_zar=45_000_000,
        )
    """

    # Churn band thresholds (inclusive lower bound)
    _BAND_CRITICAL = 75   # CRITICAL: urgent RM intervention within 48h
    _BAND_RED      = 50   # RED: RM meeting within 2 weeks
    _BAND_AMBER    = 25   # AMBER: flag for quarterly review

    def predict(
        self,
        golden_record: Dict,
        forex_profile: Optional[Dict] = None,
        cib_profile: Optional[Dict] = None,
        cell_profile: Optional[Dict] = None,
        insurance_profile: Optional[Dict] = None,
        pbb_profile: Optional[Dict] = None,
        relationship_value_zar: float = 0.0,
        evaluation_month: Optional[int] = None,
    ) -> ChurnPrediction:
        """
        Predict churn risk for a client.

        All domain profiles are optional. Absent domains reduce model
        confidence but do not prevent scoring.  Seasonal adjustments are
        applied per country and month.

        :param golden_record:          Client golden record dict.
        :param forex_profile:          Forex domain profile.
        :param cib_profile:            CIB domain profile.
        :param cell_profile:           Cell domain profile.
        :param insurance_profile:      Insurance domain profile.
        :param pbb_profile:            PBB domain profile.
        :param relationship_value_zar: Total annual relationship value in ZAR.
        :param evaluation_month:       Month number (1–12) for seasonal adjustment.
        :return:                       ChurnPrediction dataclass.
        """

        # Extract client context from the golden record
        country = golden_record.get("primary_country", "ZA")
        client_id = golden_record.get("golden_id", "UNKNOWN")

        # Determine evaluation month (default to current calendar month)
        month = evaluation_month or datetime.now().month

        # Look up seasonal correction factor for this country and month
        # Defaults to 1.0 (no adjustment) if not in the table
        seasonal_adj = _COUNTRY_SEASONALITY.get(
            country, {}
        ).get(month, 1.0)

        features: List[ChurnFeature] = []
        weighted_score = 0.0    # Sum of (normalised_score × weight) for present features
        present_weight = 0.0    # Sum of weights for domains that have data

        # --- FX volume decay: competitor FX bank capturing wallet share ---
        fx_feat = self._score_fx_decay(forex_profile)
        if fx_feat is not None:
            features.append(fx_feat)
            weighted_score += fx_feat.normalised_score * fx_feat.weight
            present_weight += fx_feat.weight

        # --- CIB facility utilisation drop: credit migrating to competitor ---
        fac_feat = self._score_facility_decay(cib_profile)
        if fac_feat is not None:
            features.append(fac_feat)
            weighted_score += fac_feat.normalised_score * fac_feat.weight
            present_weight += fac_feat.weight

        # --- Cell engagement decline: digital channel abandonment ---
        cell_feat = self._score_cell_engagement(cell_profile)
        if cell_feat is not None:
            features.append(cell_feat)
            weighted_score += cell_feat.normalised_score * cell_feat.weight
            present_weight += cell_feat.weight

        # --- Payment velocity drop: fewer inbound corporate payments ---
        pay_feat = self._score_payment_velocity(cib_profile)
        if pay_feat is not None:
            features.append(pay_feat)
            weighted_score += pay_feat.normalised_score * pay_feat.weight
            present_weight += pay_feat.weight

        # --- Insurance lapse: policy not renewed — engagement breaking down ---
        ins_feat = self._score_insurance_lapse(insurance_profile)
        if ins_feat is not None:
            features.append(ins_feat)
            weighted_score += ins_feat.normalised_score * ins_feat.weight
            present_weight += ins_feat.weight

        # Edge case: no domain data at all
        if present_weight == 0:
            return ChurnPrediction(
                client_golden_id=client_id,
                churn_score=0.0,
                churn_band="GREEN",
                probability_90d=0.0,
                revenue_at_risk_zar=0.0,
                primary_signal="no_data",
                recommended_intervention=(
                    "Insufficient data for churn assessment. "
                    "Enrich with at least one domain profile."
                ),
                features=[],
                confidence="LOW",
            )

        # Normalise weighted score over present domains, then apply seasonal correction
        raw_score = (weighted_score / present_weight) * 100

        # Seasonal adjustment dampens the score in known low-activity periods
        churn_score = min(raw_score * seasonal_adj, 100.0)

        # Determine model confidence from domain coverage
        confidence = self._confidence_label(present_weight)

        # Derive band from thresholded score
        band = self._band(churn_score)

        # Convert score to 90-day churn probability via sigmoid mapping
        prob_90d = self._score_to_probability(churn_score)

        # Revenue at risk: expected loss = prob × relationship_value × 60% capture
        # (60% capture rate accounts for partial wallet migration, not full exit)
        revenue_at_risk = relationship_value_zar * prob_90d * 0.60

        # Identify the feature with the highest weighted contribution
        primary = (
            max(features, key=lambda f: f.normalised_score * f.weight).feature_name
            if features else "unknown"
        )

        # Generate intervention text based on band and primary driver
        intervention = self._intervention(band, primary)

        return ChurnPrediction(
            client_golden_id=client_id,
            churn_score=round(churn_score, 1),
            churn_band=band,
            probability_90d=round(prob_90d, 3),
            revenue_at_risk_zar=round(revenue_at_risk, 0),
            primary_signal=primary,
            recommended_intervention=intervention,
            features=features,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Feature scorers
    # ------------------------------------------------------------------

    def _score_fx_decay(
        self, forex: Optional[Dict]
    ) -> Optional[ChurnFeature]:
        """
        Score FX volume decay as a churn signal.

        A declining FX volume trend while the client's business continues
        is the clearest indicator of wallet-splitting to a competitor FX bank.

        Scoring: 0% change → 0.0; -50% or more → 1.0 (linear interpolation).

        :param forex: Forex profile dict.
        :return:      ChurnFeature or None if forex data absent.
        """
        if not forex:
            return None

        # 3-month volume trend (negative = declining)
        trend = forex.get("volume_trend_3m", 0.0)

        if trend >= 0:
            score = 0.0  # Growing or flat: no churn signal
        elif trend <= -0.50:
            score = 1.0  # >= 50% drop: maximum churn signal
        else:
            # Linear interpolation between 0% and -50% decline
            score = abs(trend) / 0.50

        return ChurnFeature(
            feature_name="fx_volume_decay",
            domain="forex",
            raw_value=trend,
            normalised_score=round(score, 3),
            weight=_FEATURE_WEIGHTS["fx_volume_decay"],
            description=(
                f"FX volumes {'grew' if trend >= 0 else 'declined'} "
                f"{abs(trend)*100:.1f}% over 3 months"
            ),
        )

    def _score_facility_decay(
        self, cib: Optional[Dict]
    ) -> Optional[ChurnFeature]:
        """
        Score credit facility utilisation decline as a churn signal.

        A client drawing less on their facility without a corresponding
        business contraction is likely migrating to a competitor's facility.

        Scoring: linear from 0% (no change) to -50% (max signal).

        :param cib: CIB profile dict.
        :return:    ChurnFeature or None.
        """
        if not cib:
            return None

        # Change in facility utilisation over the measurement period
        util_change = cib.get("facility_utilization_change_pct", 0.0)

        if util_change >= 0:
            score = 0.0  # Utilisation grew or held: no signal
        elif util_change <= -0.50:
            score = 1.0  # 50%+ drop: maximum signal
        else:
            score = abs(util_change) / 0.50

        return ChurnFeature(
            feature_name="facility_utilisation",
            domain="cib",
            raw_value=util_change,
            normalised_score=round(score, 3),
            weight=_FEATURE_WEIGHTS["facility_utilisation"],
            description=(
                f"Credit facility utilisation "
                f"{'increased' if util_change >= 0 else 'dropped'} "
                f"{abs(util_change)*100:.1f}%"
            ),
        )

    def _score_cell_engagement(
        self, cell: Optional[Dict]
    ) -> Optional[ChurnFeature]:
        """
        Score cell/MoMo engagement decline as a churn signal.

        Both MoMo volume and USSD session trends are averaged to produce
        a blended cell engagement trend.  Declining digital engagement
        predicts reduced product adoption and eventual relationship attrition.

        :param cell: Cell profile dict.
        :return:     ChurnFeature or None.
        """
        if not cell:
            return None

        # 3-month trend for MoMo transaction volume
        momo_trend = cell.get("momo_volume_trend_3m", 0.0)

        # 3-month trend for USSD session count
        ussd_trend = cell.get("ussd_session_trend_3m", 0.0)

        # Average both channels — decay in either channel is a signal
        combined = (momo_trend + ussd_trend) / 2

        if combined >= 0:
            score = 0.0  # Growing engagement: no signal
        elif combined <= -0.50:
            score = 1.0  # >= 50% blended decline: max signal
        else:
            score = abs(combined) / 0.50

        return ChurnFeature(
            feature_name="cell_engagement",
            domain="cell",
            raw_value=combined,
            normalised_score=round(score, 3),
            weight=_FEATURE_WEIGHTS["cell_engagement"],
            description=(
                f"MoMo + USSD engagement "
                f"{'growing' if combined >= 0 else 'declining'} "
                f"{abs(combined)*100:.1f}% (3-month avg)"
            ),
        )

    def _score_payment_velocity(
        self, cib: Optional[Dict]
    ) -> Optional[ChurnFeature]:
        """
        Score inbound payment velocity decline as a churn signal.

        Fewer inbound corporate payments suggests the client's customers
        are paying via a different bank — payment stream migration.

        Scoring: linear from 0% to -40% (steeper curve than FX — payment
        migration happens faster than FX wallet migration).

        :param cib: CIB profile dict.
        :return:    ChurnFeature or None.
        """
        if not cib:
            return None

        # 3-month change in inbound payment count or volume
        pay_trend = cib.get("inbound_payment_trend_3m", 0.0)

        if pay_trend >= 0:
            score = 0.0
        elif pay_trend <= -0.40:
            # Full signal at -40% (steeper than FX — 40% not 50%)
            score = 1.0
        else:
            score = abs(pay_trend) / 0.40

        return ChurnFeature(
            feature_name="payment_velocity",
            domain="cib",
            raw_value=pay_trend,
            normalised_score=round(score, 3),
            weight=_FEATURE_WEIGHTS["payment_velocity"],
            description=(
                f"Inbound CIB payments "
                f"{'growing' if pay_trend >= 0 else 'falling'} "
                f"{abs(pay_trend)*100:.1f}%"
            ),
        )

    def _score_insurance_lapse(
        self, insurance: Optional[Dict]
    ) -> Optional[ChurnFeature]:
        """
        Score insurance lapse as a churn signal.

        A client who stops renewing insurance policies is disengaging from
        the cross-product relationship — often the first product abandoned
        before FX and CIB products migrate.

        Scoring:
          - Active policy, renewal recent: score = 0
          - No policies at all: score = 0.8 (not full signal — could be new client)
          - Lapsed >= 90 days: score = 1.0

        :param insurance: Insurance profile dict.
        :return:          ChurnFeature or None.
        """
        if not insurance:
            return None

        # Days since the most recent policy renewal
        lapsed_days = insurance.get("days_since_last_renewal", 0)

        # Number of currently active policies
        active_policies = insurance.get("active_policy_count", 1)

        if active_policies > 0 and lapsed_days < _INSURANCE_LAPSE_DAYS:
            score = 0.0  # Policy is active and recently renewed — healthy

        elif active_policies == 0:
            # No active policies at all — high churn signal but not absolute
            score = 0.8

        elif lapsed_days >= 90:
            score = 1.0  # Policy lapsed >= 90 days — strong churn indicator

        else:
            # Linear interpolation between 30 and 90 days lapsed
            score = (lapsed_days - _INSURANCE_LAPSE_DAYS) / 60

        # Clamp to [0.0, 1.0] to handle edge cases
        score = max(0.0, min(score, 1.0))

        return ChurnFeature(
            feature_name="insurance_lapse",
            domain="insurance",
            raw_value=float(lapsed_days),
            normalised_score=round(score, 3),
            weight=_FEATURE_WEIGHTS["insurance_lapse"],
            description=(
                f"{active_policies} active policies; "
                f"last renewal {lapsed_days} days ago"
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confidence_label(self, present_weight: float) -> str:
        """
        Assign model confidence based on the fraction of total possible
        feature weight that is backed by real domain data.

        :param present_weight: Sum of weights for present features.
        :return:               Confidence label string.
        """
        if present_weight >= 0.75:
            return "HIGH"    # Most domain signals available
        elif present_weight >= 0.44:
            return "MEDIUM"  # At least FX + CIB (two highest-weight features)
        return "LOW"         # Only one or two minor domains present

    def _band(self, score: float) -> str:
        """
        Map churn score to a risk band label.

        :param score: Churn score 0–100.
        :return:      Band label string.
        """
        if score >= self._BAND_CRITICAL:
            return "CRITICAL"  # Immediate intervention
        elif score >= self._BAND_RED:
            return "RED"       # Urgent intervention
        elif score >= self._BAND_AMBER:
            return "AMBER"     # Monitor and prepare
        return "GREEN"         # No immediate action required

    def _score_to_probability(self, score: float) -> float:
        """
        Convert churn score (0–100) to 90-day churn probability using a
        sigmoid-like mapping calibrated against the simulated outcome tracker:
          score=50  → prob ≈ 0.30
          score=75  → prob ≈ 0.60
          score=100 → prob ≈ 0.85

        Formula: 0.85 / (1 + exp(-(score - 50) / 20))

        :param score: Churn score 0–100.
        :return:      Estimated 90-day churn probability (0–1).
        """
        x = (score - 50) / 20.0  # Centre on 50 with a 20-point scale factor
        return round(0.85 / (1 + math.exp(-x)), 3)

    def _intervention(self, band: str, primary: str) -> str:
        """
        Return a targeted RM intervention text based on churn band
        and primary driving signal.

        :param band:    Churn band (CRITICAL / RED / AMBER / GREEN).
        :param primary: Primary churn feature name.
        :return:        Intervention recommendation string.
        """
        # Specific interventions for high-impact (band, signal) combinations
        interventions: Dict[Tuple[str, str], str] = {
            ("CRITICAL", "fx_volume_decay"): (
                "Urgent RM call within 48 hours. Lead with competitive "
                "FX pricing review. Bring FX pricing head."
            ),
            ("CRITICAL", "facility_utilisation"): (
                "Urgent credit review. Assess if competitor has offered "
                "better facility terms. Bring credit head."
            ),
            ("RED", "fx_volume_decay"): (
                "Schedule FX utilisation review within 2 weeks. "
                "Present consolidated corridor pricing."
            ),
            ("RED", "cell_engagement"): (
                "Digital channel re-engagement campaign. "
                "Offer MoMo pricing incentive."
            ),
            ("RED", "insurance_lapse"): (
                "Insurance renewal call. Cross-sell bundled cover. "
                "Leverage CIB corridor exposure data."
            ),
            ("AMBER", "payment_velocity"): (
                "Quarterly relationship review. Explore payment "
                "volume decline with client."
            ),
        }

        key = (band, primary)
        if key in interventions:
            return interventions[key]

        # Generic fallbacks for bands without a specific script
        if band == "CRITICAL":
            return (
                "Immediate RM intervention required. "
                f"Primary churn driver: {primary.replace('_', ' ')}."
            )
        if band == "RED":
            return (
                f"Schedule client meeting within 2 weeks. "
                f"Address {primary.replace('_', ' ')} trend."
            )
        if band == "AMBER":
            return (
                f"Flag for next quarterly review. Monitor "
                f"{primary.replace('_', ' ')} closely."
            )
        return "No intervention required. Monitor regularly."
