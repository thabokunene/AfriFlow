"""
@file __init__.py
@description Configuration Module - Centralized configuration loading and validation
@author Thabo Kunene
@created 2026-03-19

This module provides centralized configuration loading for all AfriFlow modules.
Configuration is loaded from YAML files and validated using Pydantic models.

Key Components:
- ConfigLoader: Loads and validates YAML configuration files
- Settings: Master settings container with all configuration sections
- get_settings(): Lazy-loaded global settings instance
- load_config(): Direct configuration loading function

Configuration Files:
- defaults.yml: Base application defaults
- sim_deflation.yml: SIM to employee deflation factors per country
- seasonal_weights.yml: Seasonal adjustment weights per commodity
- signal_thresholds.yml: Signal detection thresholds
- lekgotla_config.yml: Lekgotla points, levels, graduation settings
- corridor_config.yml: Corridor leakage detection settings
- moderation_patterns.yml: Content moderation regex patterns

Usage:
    >>> from afriflow.config import get_settings
    >>> settings = get_settings()
    >>> sim_factor = settings.get_sim_deflation("NG")  # Returns 0.36 for Nigeria
"""

# Import configuration loader and convenience functions
# These enable loading YAML configuration files with validation
from .loader import ConfigLoader, load_config, get_settings

# Import Pydantic models for configuration validation
# Each model validates a specific configuration section
from .settings import (
    Settings,  # Master settings container
    SimDeflationConfig,  # SIM deflation factor configuration
    SeasonalWeightConfig,  # Seasonal adjustment weight configuration
    SignalThresholds,  # Signal detection threshold configuration
    LekgotlaConfig,  # Lekgotla platform configuration
    CorridorConfig,  # Corridor intelligence configuration
    ModerationPatterns,  # Content moderation pattern configuration
)

# Public API - defines what's exported for 'from afriflow.config import *'
__all__ = [
    # Configuration loader class and convenience functions
    "ConfigLoader",
    "load_config",
    "get_settings",
    # Pydantic models for each configuration section
    "Settings",
    "SimDeflationConfig",
    "SeasonalWeightConfig",
    "SignalThresholds",
    "LekgotlaConfig",
    "CorridorConfig",
    "ModerationPatterns",
]
