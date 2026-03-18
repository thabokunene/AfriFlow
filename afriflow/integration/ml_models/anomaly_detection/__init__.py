"""
@file __init__.py
@description Package init for the anomaly_detection sub-package.
             Exposes cross-domain anomaly detection and multi-domain fraud
             signal correlation classes to the rest of the ml_models layer.
@author Thabo Kunene
@created 2026-03-18
"""

# Cross-domain anomaly detector: flags structured transactions, competitor entry,
# fraud rings, salary diversion, and all-domain silence patterns
from .cross_domain_anomaly import (
    CrossDomainAnomalyDetector,  # Main detector class
    CrossDomainAnomaly,          # Anomaly result dataclass
    DomainDeviation,             # Per-domain z-score deviation
)

# Fraud signal correlator: combines Dempster-Shafer belief masses from each
# domain to produce a composite fraud risk score
from .fraud_signal_correlator import (
    FraudSignalCorrelator,  # Main correlator class
    FraudCorrelation,       # Composite fraud assessment result
    FraudSignal,            # Single-domain fraud indicator
)

# Public API surface for this sub-package
__all__ = [
    "CrossDomainAnomalyDetector",
    "CrossDomainAnomaly",
    "DomainDeviation",
    "FraudSignalCorrelator",
    "FraudCorrelation",
    "FraudSignal",
]
