"""
@file __init__.py
@description Package init for the client_lifetime_value sub-package.
             Exposes the ChurnPredictor (multi-domain attrition risk) and
             CLVCalculator (3-year NPV of a client relationship) to the
             rest of the ml_models layer.
@author Thabo Kunene
@created 2026-03-18
"""

# ChurnPredictor: uses multi-domain decay signals to estimate 90-day churn probability
from .churn_predictor import ChurnPredictor, ChurnPrediction, ChurnFeature

# CLVCalculator: discounts projected multi-domain revenues over a 3-year horizon
from .clv_calculator import CLVCalculator, CLVResult, DomainRevenue

# Public API surface for this sub-package
__all__ = [
    "ChurnPredictor",
    "ChurnPrediction",
    "ChurnFeature",
    "CLVCalculator",
    "CLVResult",
    "DomainRevenue",
]
