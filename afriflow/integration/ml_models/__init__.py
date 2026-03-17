"""
AfriFlow ML Models

Cross-domain machine learning for pan-African financial services.

Packages:
  next_best_action    — Prioritised revenue actions for RMs
  client_lifetime_value — Churn prediction and CLV
  anomaly_detection   — Cross-domain anomaly and fraud correlation
  alternative_scoring — Business viability, digital maturity, IEHI
"""

from .next_best_action import NextBestActionModel, ClientNBAResult, RecommendedAction
from .client_lifetime_value import ChurnPredictor, CLVCalculator
from .anomaly_detection import CrossDomainAnomalyDetector, FraudSignalCorrelator
from .alternative_scoring import (
    BusinessViabilityScorer,
    DigitalMaturityScorer,
    InformalEconomyHealthIndexer,
)

__all__ = [
    "NextBestActionModel",
    "ClientNBAResult",
    "RecommendedAction",
    "ChurnPredictor",
    "CLVCalculator",
    "CrossDomainAnomalyDetector",
    "FraudSignalCorrelator",
    "BusinessViabilityScorer",
    "DigitalMaturityScorer",
    "InformalEconomyHealthIndexer",
]
