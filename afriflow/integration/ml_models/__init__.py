"""
@file __init__.py
@description Top-level package init for the AfriFlow ML models layer.
             Exposes the primary classes from all four sub-packages so
             callers can import directly from `integration.ml_models`
             without knowing the internal module layout.
@author Thabo Kunene
@created 2026-03-18
"""

# Sub-package: NBA — rule-scored recommendations for relationship managers
from .next_best_action import NextBestActionModel, ClientNBAResult, RecommendedAction

# Sub-package: CLV — churn prediction and client lifetime value estimation
from .client_lifetime_value import ChurnPredictor, CLVCalculator

# Sub-package: Anomaly — cross-domain behaviour anomalies and fraud correlation
from .anomaly_detection import CrossDomainAnomalyDetector, FraudSignalCorrelator

# Sub-package: Alternative scoring — viability, digital maturity, IEHI
from .alternative_scoring import (
    BusinessViabilityScorer,       # SME viability from cross-domain behaviour
    DigitalMaturityScorer,         # How digitally engaged is the client
    InformalEconomyHealthIndexer,  # Health of informal economy cluster
)

# Public API — controls what `from integration.ml_models import *` exposes
__all__ = [
    # Next Best Action
    "NextBestActionModel",
    "ClientNBAResult",
    "RecommendedAction",
    # Client Lifetime Value
    "ChurnPredictor",
    "CLVCalculator",
    # Anomaly Detection
    "CrossDomainAnomalyDetector",
    "FraudSignalCorrelator",
    # Alternative Scoring
    "BusinessViabilityScorer",
    "DigitalMaturityScorer",
    "InformalEconomyHealthIndexer",
]
