"""
Configuration Module

We provide centralized configuration loading and validation
for all AfriFlow settings. All magic numbers and thresholds
are loaded from YAML configuration files.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from afriflow.config.settings import (
    Settings,
    RevenueEstimates,
    ExpansionThresholds,
    SimDeflationConfig,
    CurrencyThreshold,
    SeasonalPattern,
)
from afriflow.config.loader import (
    ConfigLoader,
    load_config,
    get_settings,
)

__all__ = [
    "Settings",
    "RevenueEstimates",
    "ExpansionThresholds",
    "SimDeflationConfig",
    "CurrencyThreshold",
    "SeasonalPattern",
    "ConfigLoader",
    "load_config",
    "get_settings",
]
