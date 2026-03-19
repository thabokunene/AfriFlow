"""
Configuration Module

Centralized configuration loading and validation for all
AfriFlow modules. Configuration is loaded from YAML files
and validated using Pydantic models.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .loader import ConfigLoader, load_config, get_settings
from .settings import (
    Settings,
    SimDeflationConfig,
    SeasonalWeightConfig,
    SignalThresholds,
    LekgotlaConfig,
    CorridorConfig,
    ModerationPatterns,
)

__all__ = [
    "ConfigLoader",
    "load_config",
    "get_settings",
    "Settings",
    "SimDeflationConfig",
    "SeasonalWeightConfig",
    "SignalThresholds",
    "LekgotlaConfig",
    "CorridorConfig",
    "ModerationPatterns",
]
