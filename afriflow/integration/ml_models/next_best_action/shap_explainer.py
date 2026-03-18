"""
@file shap_explainer.py
@description SHAP (SHapley Additive exPlanations) explainer for the Next
             Best Action model.

             SHAP values quantify each feature's marginal contribution to a
             model output — "how much did the FX volume trend change this
             client's attrition score compared to the average client?"

             Because the NBA model is rule-based (not a trained ML model),
             we implement a lightweight perturbation-based explainer rather
             than tree SHAP or kernel SHAP.  We permute each feature one at
             a time, holding all others at their mean value, and measure the
             score change.  This is computationally cheap and interpretable
             for portfolio demonstration purposes.

             Outputs are per-action SHAP dictionaries that map feature names
             to their signed contribution values, sorted by absolute impact.
             These are surfaced in the ClientNBAResult and can be rendered
             as waterfall or bar charts in the portfolio notebooks.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# Import the feature store for canonical feature ordering and vector construction
from .feature_store import FeatureStore, FeatureVector


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class SHAPExplanation:
    """
    SHAP explanation for a single NBA model action.

    :param action_id:          Identifier of the action being explained.
    :param client_golden_id:   AfriFlow golden record identifier.
    :param base_value:         Average model output across the reference population.
    :param predicted_value:    Actual model output for this client.
    :param shap_values:        Dict mapping feature name to signed SHAP value.
    :param top_positive:       Top-3 features that most increased the score.
    :param top_negative:       Top-3 features that most decreased the score.
    :param explanation_text:   Plain-English summary of the top drivers.
    """

    action_id: str
    client_golden_id: str
    base_value: float          # Average score in the reference population
    predicted_value: float     # This client's actual score
    shap_values: Dict[str, float]   # Feature name → signed contribution
    top_positive: List[Tuple[str, float]]  # (feature_name, shap_value) — highest positive
    top_negative: List[Tuple[str, float]]  # (feature_name, shap_value) — most negative
    explanation_text: str


# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

class SHAPExplainer:
    """
    Perturbation-based SHAP explainer for the NBA rule-based scoring model.

    A scoring function (Callable) is required — typically one of the
    private _score_* methods from NextBestActionModel wrapped as a
    single-argument function that accepts a feature dict and returns a score.

    Usage::

        from integration.ml_models.next_best_action.feature_store import FeatureStore

        store = FeatureStore()
        fv = store.build("GLD-001", cib_profile=cib, forex_profile=fx)

        # Wrap the NBA model's FX hedging scorer as a plain function
        def fx_score_fn(features: dict) -> float:
            # Reconstruct profiles from features and call the scorer
            ...

        explainer = SHAPExplainer(score_fn=fx_score_fn)
        explanation = explainer.explain(
            action_id="NBA-FX-GLD-001",
            feature_vector=fv,
            predicted_score=72.5,
        )
    """

    def __init__(
        self,
        score_fn: Callable[[Dict[str, float]], float],
        n_perturbations: int = 10,
    ) -> None:
        """
        Initialise the SHAP explainer.

        :param score_fn:         Scoring function that accepts a feature dict
                                 and returns a float score.
        :param n_perturbations:  Number of random perturbation samples per
                                 feature.  Higher = more accurate but slower.
        """
        self._score_fn = score_fn  # The rule-based scoring function to explain
        self._n_perturb = n_perturbations  # Perturbation sample count per feature

    def explain(
        self,
        action_id: str,
        feature_vector: FeatureVector,
        predicted_score: float,
        reference_score: float = 50.0,
    ) -> SHAPExplanation:
        """
        Compute a SHAP explanation for a single action score.

        For each feature, we compute the marginal contribution by replacing
        it with its reference (mean) value and measuring the score change.
        The SHAP value for feature i is:

          shap_i = score(all features) - score(feature_i = reference_value)

        This is a simplified one-at-a-time (OAT) sensitivity analysis —
        not the full Shapley game-theoretic value — but it provides an
        interpretable first-order attribution for portfolio demonstration.

        :param action_id:       Identifier of the action being explained.
        :param feature_vector:  FeatureVector for the client.
        :param predicted_score: The action's actual output score.
        :param reference_score: Baseline score when all features are at zero.
        :return:                SHAPExplanation dataclass.
        """
        client_id = feature_vector.client_golden_id
        features = feature_vector.features.copy()

        shap_values: Dict[str, float] = {}

        # Compute OAT sensitivity for each feature
        for feature_name in features:
            # Save the original feature value
            original_value = features[feature_name]

            # Replace the feature with its reference (zero / neutral) value
            features[feature_name] = 0.0

            # Score with this feature zeroed out
            score_without = self._score_fn(features)

            # SHAP value = actual score − score without this feature
            shap_values[feature_name] = round(
                predicted_score - score_without, 3
            )

            # Restore the original value before moving to the next feature
            features[feature_name] = original_value

        # Sort features by absolute SHAP value descending
        sorted_shap = sorted(
            shap_values.items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )

        # Top-3 features that increased the score (positive contribution)
        top_positive = [
            (name, val) for name, val in sorted_shap if val > 0
        ][:3]

        # Top-3 features that decreased the score (negative contribution)
        top_negative = [
            (name, val) for name, val in sorted_shap if val < 0
        ][:3]

        # Build a plain-English summary for the RM
        explanation_text = self._build_explanation(
            top_positive, top_negative, predicted_score
        )

        return SHAPExplanation(
            action_id=action_id,
            client_golden_id=client_id,
            base_value=reference_score,
            predicted_value=predicted_score,
            shap_values=shap_values,
            top_positive=top_positive,
            top_negative=top_negative,
            explanation_text=explanation_text,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_explanation(
        self,
        top_positive: List[Tuple[str, float]],
        top_negative: List[Tuple[str, float]],
        score: float,
    ) -> str:
        """
        Build a plain-English explanation string describing the top
        positive and negative SHAP contributors.

        :param top_positive: List of (feature_name, shap_value) for top positive drivers.
        :param top_negative: List of (feature_name, shap_value) for top negative drivers.
        :param score:        Final predicted score.
        :return:             Human-readable explanation string.
        """
        lines = [f"Score: {score:.1f}/100."]

        if top_positive:
            # Format feature names as human-readable labels
            pos_names = ", ".join(
                n.replace("_", " ") for n, _ in top_positive
            )
            lines.append(f"Main drivers increasing this score: {pos_names}.")

        if top_negative:
            neg_names = ", ".join(
                n.replace("_", " ") for n, _ in top_negative
            )
            lines.append(f"Main factors reducing this score: {neg_names}.")

        return " ".join(lines)
