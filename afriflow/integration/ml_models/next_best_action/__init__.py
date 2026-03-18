"""
@file __init__.py
@description Package init for the next_best_action sub-package.
             Exposes the rule-based NBA model, its result dataclasses, and
             the SHAP explainer to the rest of the ml_models layer.
             Also re-exports the FeatureStore for callers that need direct
             feature-vector access without going through the full model.
@author Thabo Kunene
@created 2026-03-18
"""

# NBA model: rule-scored cross-domain opportunity recommendations
from .nba_model import (
    NextBestActionModel,  # Main scoring class
    ClientNBAResult,      # Full result for one client
    RecommendedAction,    # A single ranked recommendation
    ActionFeature,        # A feature that drove a recommendation score
)

# Public API surface for this sub-package
__all__ = [
    "NextBestActionModel",
    "ClientNBAResult",
    "RecommendedAction",
    "ActionFeature",
]
