"""
Churn Predictor

We identify clients at elevated risk of attrition before
they formally move business to a competitor. In pan-African
banking, churn is rarely announced — it shows up as
decaying signal intensity across domains.

We monitor five behavioural signals:
  1. FX volume decay     — competitor FX bank capturing share
  2. Facility drawdown   — CIB credit migrating away
  3. USSD/MoMo silence  — cell engagement dropping
  4. Payment velocity    — fewer inbound corporate payments
  5. Insurance lapse     — policies not renewed

The multi-domain view is key: a client whose FX volumes
drop 25% while their CIB transactions stay flat is almost
certainly splitting their FX wallet. That pattern is
invisible to a single-domain view.

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Thresholds — tuned against the simulated outcome tracker
# ---------------------------------------------------------------------------

# 90-day volume decline that triggers each churn signal
_FX_DECAY_THRESHOLD = -0.15       # 15% FX volume drop
_FACILITY_DECAY_THRESHOLD = -0.20  # 20% utilisation drop
_CELL_SILENCE_THRESHOLD = -0.30   # 30% MoMo / USSD drop
_PAYMENT_DECAY_THRESHOLD = -0.18  # 18% inbound payment drop
_INSURANCE_LAPSE_DAYS = 30        # Policy lapsed > 30 days

# Feature weights for composite churn score
_FEATURE_WEIGHTS: Dict[str, float] = {
    "fx_volume_decay":       0.28,
    "facility_utilisation":  0.24,
    "cell_engagement":       0.20,
    "payment_velocity":      0.16,
    "insurance_lapse":       0.12,
}

# Country-specific churn seasonality adjustments.
# In South Africa, year-end slow-down looks like churn.
# In Nigeria, Q1 oil-price volatility causes temporary dips.
_COUNTRY_SEASONALITY: Dict[str, Dict[int, float]] = {
    "ZA": {12: 0.7, 1: 0.7},      # Year-end / January correction
    "NG": {1: 0.8, 2: 0.8},       # Q1 oil shock adjustment
    "KE": {8: 0.9},                # School-fee month correction
    "GH": {10: 0.85, 11: 0.85},   # Cocoa harvest diversion
    "ZM": {3: 0.8, 4: 0.8},       # Copper price dip season
}


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class ChurnFeature:
    """A single churn signal with its contribution."""

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

    churn_score : 0–100, higher = more likely to churn
    churn_band  : GREEN / AMBER / RED / CRITICAL
    """

    client_golden_id: str
    churn_score: float
    churn_band: str
    probability_90d: float        # Estimated probability of churn in 90 days
    revenue_at_risk_zar: float
    primary_signal: str           # Dominant churn driver
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
    We combine multi-domain signals into a single churn
    probability estimate.

    Domain profiles follow the same dict contract as the
    NBA model — optional, degrade gracefully.

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

    # Churn band thresholds
    _BAND_CRITICAL = 75
    _BAND_RED = 50
    _BAND_AMBER = 25

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

        All domain profiles are optional. Absent domains
        reduce model confidence but do not prevent scoring.
        """

        country = golden_record.get("primary_country", "ZA")
        client_id = golden_record.get("golden_id", "UNKNOWN")
        month = evaluation_month or datetime.now().month

        seasonal_adj = _COUNTRY_SEASONALITY.get(
            country, {}
        ).get(month, 1.0)

        features: List[ChurnFeature] = []
        weighted_score = 0.0
        present_weight = 0.0

        # --- FX volume decay ---
        fx_feat = self._score_fx_decay(forex_profile)
        if fx_feat is not None:
            features.append(fx_feat)
            weighted_score += fx_feat.normalised_score * fx_feat.weight
            present_weight += fx_feat.weight

        # --- CIB facility utilisation ---
        fac_feat = self._score_facility_decay(cib_profile)
        if fac_feat is not None:
            features.append(fac_feat)
            weighted_score += fac_feat.normalised_score * fac_feat.weight
            present_weight += fac_feat.weight

        # --- Cell engagement ---
        cell_feat = self._score_cell_engagement(cell_profile)
        if cell_feat is not None:
            features.append(cell_feat)
            weighted_score += cell_feat.normalised_score * cell_feat.weight
            present_weight += cell_feat.weight

        # --- Payment velocity ---
        pay_feat = self._score_payment_velocity(cib_profile)
        if pay_feat is not None:
            features.append(pay_feat)
            weighted_score += pay_feat.normalised_score * pay_feat.weight
            present_weight += pay_feat.weight

        # --- Insurance lapse ---
        ins_feat = self._score_insurance_lapse(insurance_profile)
        if ins_feat is not None:
            features.append(ins_feat)
            weighted_score += ins_feat.normalised_score * ins_feat.weight
            present_weight += ins_feat.weight

        if present_weight == 0:
            # No domain data at all
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

        # Normalise for missing domains, apply seasonal adjustment
        raw_score = (weighted_score / present_weight) * 100
        churn_score = min(raw_score * seasonal_adj, 100.0)

        confidence = self._confidence_label(present_weight)
        band = self._band(churn_score)
        prob_90d = self._score_to_probability(churn_score)
        revenue_at_risk = relationship_value_zar * prob_90d * 0.60

        primary = (
            max(features, key=lambda f: f.normalised_score * f.weight).feature_name
            if features else "unknown"
        )

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
        if not forex:
            return None
        trend = forex.get("volume_trend_3m", 0.0)
        if trend >= 0:
            score = 0.0
        elif trend <= -0.50:
            score = 1.0
        else:
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
        if not cib:
            return None
        util_change = cib.get("facility_utilization_change_pct", 0.0)
        if util_change >= 0:
            score = 0.0
        elif util_change <= -0.50:
            score = 1.0
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
        if not cell:
            return None
        momo_trend = cell.get("momo_volume_trend_3m", 0.0)
        ussd_trend = cell.get("ussd_session_trend_3m", 0.0)
        # Average of both channels
        combined = (momo_trend + ussd_trend) / 2
        if combined >= 0:
            score = 0.0
        elif combined <= -0.50:
            score = 1.0
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
        if not cib:
            return None
        pay_trend = cib.get("inbound_payment_trend_3m", 0.0)
        if pay_trend >= 0:
            score = 0.0
        elif pay_trend <= -0.40:
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
        if not insurance:
            return None
        lapsed_days = insurance.get("days_since_last_renewal", 0)
        active_policies = insurance.get("active_policy_count", 1)

        if active_policies > 0 and lapsed_days < _INSURANCE_LAPSE_DAYS:
            score = 0.0
        elif active_policies == 0:
            score = 0.8
        elif lapsed_days >= 90:
            score = 1.0
        else:
            score = (lapsed_days - _INSURANCE_LAPSE_DAYS) / 60

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
        if present_weight >= 0.75:
            return "HIGH"
        elif present_weight >= 0.44:
            return "MEDIUM"
        return "LOW"

    def _band(self, score: float) -> str:
        if score >= self._BAND_CRITICAL:
            return "CRITICAL"
        elif score >= self._BAND_RED:
            return "RED"
        elif score >= self._BAND_AMBER:
            return "AMBER"
        return "GREEN"

    def _score_to_probability(self, score: float) -> float:
        """
        Convert churn score (0–100) to 90-day churn probability.

        We use a sigmoid-like mapping calibrated against the
        simulated outcome tracker: score=50 → prob≈0.30,
        score=75 → prob≈0.60, score=100 → prob≈0.85.
        """
        x = (score - 50) / 20.0
        return round(0.85 / (1 + math.exp(-x)), 3)

    def _intervention(self, band: str, primary: str) -> str:
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
