"""
@file loader.py
@description Configuration Loader - YAML configuration loading and validation
@author Thabo Kunene
@created 2026-03-19

This module loads and validates configuration from YAML files.
Configuration is loaded once at startup and passed via
dependency injection (not global state).

Key Components:
- ConfigLoader: Main class for loading and validating YAML configs
- get_settings(): Lazy-loaded global settings instance
- load_config(): Direct configuration loading function

Configuration Files Loaded:
- sim_deflation.yml: SIM to employee conversion factors
- seasonal_weights.yml: Seasonal adjustment weights
- signal_thresholds.yml: Signal detection thresholds
- lekgotla_config.yml: Lekgotla platform settings
- corridor_config.yml: Corridor intelligence settings
- moderation_patterns.yml: Content moderation patterns

Usage:
    >>> from afriflow.config.loader import get_settings
    >>> settings = get_settings()
    >>> sim_factor = settings.get_sim_deflation("NG")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Standard library imports
import os  # For environment variable access (future use)
import yaml  # YAML parser for configuration files
from pathlib import Path  # Cross-platform file path handling
from typing import Optional, Dict, Any  # Type hints for optional, dict, and any types
import logging  # Python's built-in logging module

# Import Pydantic models for configuration validation
from afriflow.config.settings import (
    Settings,  # Master settings container
    SimDeflationConfig,  # SIM deflation factor model
    SeasonalWeightConfig,  # Seasonal weight model
    SignalThresholds,  # Signal threshold model
    LekgotlaConfig,  # Lekgotla platform model
    CorridorConfig,  # Corridor intelligence model
    ModerationPatterns,  # Moderation patterns model
)

# Import custom exceptions for error handling
from afriflow.exceptions import ConfigurationError, MissingConfigError, InvalidConfigError

# Import logging utilities for structured logging
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("config.loader")  # Get logger instance for this module

# Default configuration directory path
# This is afriflow/config/ relative to this file
DEFAULT_CONFIG_DIR = Path(__file__).parent


class ConfigLoader:
    """
    Loads and validates configuration from YAML files.

    Configuration is loaded once at startup and cached.
    All configuration access should go through this loader
    to ensure consistency and validation.

    This class implements the Singleton pattern via caching
    to ensure configuration is only loaded once per process.

    Attributes:
        config_dir: Directory containing config files
        _settings: Cached Settings object (lazy-loaded)
        _raw_config: Raw configuration dictionary (for debugging)

    Example:
        >>> loader = ConfigLoader()
        >>> settings = loader.load()
        >>> print(settings.signal_thresholds.expansion_min_cib_payments)
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_dir: Directory containing config files.
                       Defaults to afriflow/config/
        """
        # Set configuration directory (use default if not specified)
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        # Cached Settings object (None until load() is called)
        self._settings: Optional[Settings] = None
        # Raw configuration dictionary (for debugging/inspection)
        self._raw_config: Dict[str, Any] = {}

        # Log initialization for observability
        logger.info(
            f"ConfigLoader initialized with config_dir: "
            f"{self.config_dir}"
        )

    def load(self) -> Settings:
        """
        Load and validate all configuration files.

        This method loads all YAML configuration files,
        validates them using Pydantic models, and returns
        a Settings object with all configuration sections.

        Configuration is cached after first load. Subsequent
        calls return the cached Settings object.

        Returns:
            Validated Settings object with all configuration

        Raises:
            ConfigurationError: If config files are invalid
            yaml.YAMLError: If YAML parsing fails

        Example:
            >>> loader = ConfigLoader()
            >>> settings = loader.load()
            >>> print(settings.lekgotla.thread_points)  # 10
        """
        # Return cached settings if already loaded
        # This avoids reloading configuration on every call
        if self._settings is not None:
            logger.debug("Returning cached settings")
            return self._settings

        # Log configuration loading start
        logger.info("Loading configuration files...")

        try:
            # Load SIM deflation factors from YAML
            sim_deflation = self._load_sim_deflation(
                "sim_deflation.yml"
            )

            # Load seasonal weights from YAML
            seasonal_weights = self._load_seasonal_weights(
                "seasonal_weights.yml"
            )

            # Load signal thresholds from YAML
            signal_thresholds = self._load_signal_thresholds(
                "signal_thresholds.yml"
            )

            # Load Lekgotla configuration from YAML
            lekgotla = self._load_lekgotla_config(
                "lekgotla_config.yml"
            )

            # Load corridor configuration from YAML
            corridor = self._load_corridor_config(
                "corridor_config.yml"
            )

            # Load moderation patterns from YAML
            moderation = self._load_moderation_patterns(
                "moderation_patterns.yml"
            )

            # Create Settings object with all loaded configuration
            self._settings = Settings(
                sim_deflation=sim_deflation,
                seasonal_weights=seasonal_weights,
                signal_thresholds=signal_thresholds,
                lekgotla=lekgotla,
                corridor=corridor,
                moderation=moderation,
            )

            # Log successful configuration load with summary stats
            logger.info(
                f"Configuration loaded successfully: "
                f"{len(sim_deflation)} countries, "
                f"{len(seasonal_weights)} seasonal patterns"
            )

            return self._settings

        except yaml.YAMLError as e:
            # Handle YAML parsing errors
            logger.error(f"YAML parsing error: {e}")
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}"
            )
        except Exception as e:
            # Handle any other errors during configuration loading
            logger.error(f"Configuration load error: {e}")
            raise ConfigurationError(
                f"Failed to load configuration: {e}"
            )

    def _load_yaml_file(
        self,
        filename: str
    ) -> Dict[str, Any]:
        """
        Load a YAML configuration file.

        This is a helper method that reads and parses a single
        YAML file. It handles file not found gracefully by
        returning an empty dictionary.

        Args:
            filename: Name of the file to load (relative to config_dir)

        Returns:
            Parsed YAML content as dictionary
            Empty dict if file not found

        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        # Build full file path from config directory and filename
        filepath = self.config_dir / filename

        # Check if file exists before attempting to read
        if not filepath.exists():
            # Log warning but don't fail - use defaults instead
            logger.warning(
                f"Configuration file not found: {filepath}, "
                f"using defaults"
            )
            return {}

        try:
            # Open and parse YAML file
            with open(filepath, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            # Log successful file load for observability
            logger.debug(f"Loaded config file: {filepath}")

            # Return parsed content or empty dict if file was empty
            return content or {}

        except yaml.YAMLError as e:
            # Handle YAML parsing errors with descriptive message
            raise ConfigurationError(
                f"Invalid YAML in {filepath}: {e}"
            )
        except IOError as e:
            # Handle file I/O errors (permissions, etc.)
            raise ConfigurationError(
                f"Cannot read {filepath}: {e}"
            )

    def _load_sim_deflation(
        self,
        filename: str
    ) -> Dict[str, SimDeflationConfig]:
        """
        Load SIM deflation factors from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            Dictionary mapping country codes to SimDeflationConfig objects

        Example:
            {"ZA": SimDeflationConfig(country_code="ZA", deflation_factor=0.77, ...)}
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)
        # Extract country_factors section from YAML
        country_factors = data.get("country_factors", {})

        # Build result dictionary
        result = {}
        for country_code, factors in country_factors.items():
            try:
                # Create SimDeflationConfig object for each country
                result[country_code.upper()] = SimDeflationConfig(
                    country_code=country_code.upper(),  # Ensure uppercase
                    deflation_factor=factors.get(  # Get deflation factor with default
                        "deflation_factor", 0.5
                    ),
                    avg_sims_per_person=factors.get(  # Get average SIMs with default
                        "avg_sims_per_person", 2.0
                    ),
                    confidence=factors.get(  # Get confidence level with default
                        "confidence", "low"
                    ),
                    source=factors.get(  # Get data source with default
                        "source", "Default"
                    ),
                )
            except Exception as e:
                # Log warning for invalid config but continue loading others
                logger.warning(
                    f"Invalid SIM deflation config for "
                    f"{country_code}: {e}"
                )

        # Log count of loaded SIM deflation factors
        logger.info(
            f"Loaded {len(result)} SIM deflation factors"
        )
        return result

    def _load_seasonal_weights(
        self,
        filename: str
    ) -> Dict[str, SeasonalWeightConfig]:
        """
        Load seasonal weights from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            Dictionary mapping commodity_country keys to SeasonalWeightConfig
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)
        # Extract seasons section from YAML
        seasons = data.get("seasons", {})

        # Build result dictionary
        result = {}
        for commodity, countries in seasons.items():
            for country_code, patterns in countries.items():
                for pattern in patterns:
                    # Create unique key from commodity and country
                    key = f"{commodity}_{country_code}"
                    try:
                        # Create SeasonalWeightConfig object
                        result[key] = SeasonalWeightConfig(
                            commodity=commodity,
                            country_code=country_code.upper(),
                            peak_months=pattern.get("peak_months", []),
                            trough_months=pattern.get("trough_months", []),
                            flow_type=pattern.get("flow_type", "export"),
                            expected_peak_multiplier=pattern.get(
                                "expected_peak_multiplier", 1.5
                            ),
                            expected_trough_multiplier=pattern.get(
                                "expected_trough_multiplier", 0.5
                            ),
                        )
                    except Exception as e:
                        # Log warning but continue loading
                        logger.warning(
                            f"Invalid seasonal pattern for "
                            f"{commodity}/{country_code}: {e}"
                        )

        logger.info(
            f"Loaded {len(result)} seasonal patterns"
        )
        return result

    def _load_signal_thresholds(
        self,
        filename: str
    ) -> SignalThresholds:
        """
        Load signal thresholds from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            SignalThresholds object with loaded or default values
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)

        try:
            # Extract expansion section from YAML
            expansion = data.get("expansion", {})

            # Create SignalThresholds object with values from config
            # Use defaults for any missing values
            return SignalThresholds(
                expansion_min_cib_payments=expansion.get(
                    "min_cib_payments",
                    SignalThresholds.model_fields[
                        "expansion_min_cib_payments"
                    ].default
                ),
                expansion_min_cib_value=expansion.get(
                    "min_cib_value_zar",
                    SignalThresholds.model_fields[
                        "expansion_min_cib_value"
                    ].default
                ),
                expansion_min_sim_activations=expansion.get(
                    "min_sim_activations",
                    SignalThresholds.model_fields[
                        "expansion_min_sim_activations"
                    ].default
                ),
            )
        except Exception as e:
            # Log warning and return defaults on error
            logger.warning(
                f"Using default signal thresholds: {e}"
            )
            return SignalThresholds()

    def _load_lekgotla_config(
        self,
        filename: str
    ) -> LekgotlaConfig:
        """
        Load Lekgotla configuration from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            LekgotlaConfig object with loaded or default values
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)

        try:
            # Extract configuration sections from YAML
            points = data.get("points", {})
            graduation = data.get("graduation", {})
            notification = data.get("notification", {})

            # Create LekgotlaConfig object with values from config
            return LekgotlaConfig(
                thread_points=points.get("thread_created", 10),
                reply_points=points.get("reply_posted", 5),
                solution_points=points.get("solution_marked", 25),
                card_contribution_points=points.get(
                    "card_contributed", 50
                ),
                card_publication_points=points.get(
                    "card_published", 100
                ),
                upvote_received_points=points.get(
                    "upvote_received", 2
                ),
                graduation_min_upvotes=graduation.get(
                    "min_upvotes", 10
                ),
                graduation_min_contributors=graduation.get(
                    "min_contributors", 3
                ),
                notification_batch_size=notification.get(
                    "batch_size", 100
                ),
                notification_delay_seconds=notification.get(
                    "delay_seconds", 300
                ),
            )
        except Exception as e:
            # Log warning and return defaults on error
            logger.warning(
                f"Using default Lekgotla config: {e}"
            )
            return LekgotlaConfig()

    def _load_corridor_config(
        self,
        filename: str
    ) -> CorridorConfig:
        """
        Load corridor configuration from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            CorridorConfig object with loaded or default values
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)

        try:
            # Extract configuration sections from YAML
            leakage = data.get("leakage_detection", {})
            capture = data.get("capture_expectations", {})
            informal = data.get("informal_detection", {})

            # Create CorridorConfig object with values from config
            return CorridorConfig(
                leakage_detection_threshold=leakage.get(
                    "threshold", 0.10
                ),
                fx_capture_expected_pct=capture.get(
                    "fx_pct", 0.60
                ),
                insurance_capture_expected_pct=capture.get(
                    "insurance_pct", 0.30
                ),
                payroll_capture_expected_pct=capture.get(
                    "payroll_pct", 0.40
                ),
                informal_ratio_alert_threshold=informal.get(
                    "momo_cib_ratio_threshold", 1.0
                ),
            )
        except Exception as e:
            # Log warning and return defaults on error
            logger.warning(
                f"Using default corridor config: {e}"
            )
            return CorridorConfig()

    def _load_moderation_patterns(
        self,
        filename: str
    ) -> ModerationPatterns:
        """
        Load moderation patterns from config file.

        Args:
            filename: Name of the YAML file to load

        Returns:
            ModerationPatterns object with loaded or default values
        """
        # Load raw YAML data from file
        data = self._load_yaml_file(filename)

        try:
            # Extract configuration sections from YAML
            patterns = data.get("patterns", {})
            auto_flag = data.get("auto_flag", {})
            review = data.get("review", {})

            # Create ModerationPatterns object with values from config
            return ModerationPatterns(
                confidential_patterns=patterns.get(
                    "confidential", []
                ),
                spam_patterns=patterns.get("spam", []),
                inappropriate_patterns=patterns.get(
                    "inappropriate", []
                ),
                auto_flag_enabled=auto_flag.get("enabled", True),
                require_review_before_publish=review.get(
                    "require_before_publish", False
                ),
            )
        except Exception as e:
            # Log warning and return defaults on error
            logger.warning(
                f"Using default moderation patterns: {e}"
            )
            return ModerationPatterns()

    def reload(self) -> Settings:
        """
        Force reload of configuration (for testing).

        This method clears the cached Settings object and
        reloads all configuration from YAML files. Use this
        in tests or when configuration changes at runtime.

        Returns:
            Reloaded Settings object
        """
        # Log configuration reload for observability
        logger.info("Forcing configuration reload...")

        # Clear cached settings
        self._settings = None
        # Clear raw config cache
        self._raw_config = {}

        # Reload configuration from files
        return self.load()


# ============================================
# GLOBAL SETTINGS INSTANCE
# ============================================
# Lazy-loaded global settings for convenience access
# This implements the Singleton pattern for configuration

# Global settings instance (loaded lazily on first call)
_settings_instance: Optional[Settings] = None
# Global config loader instance (used for loading)
_config_loader: Optional[ConfigLoader] = None


def get_settings(
    config_dir: Optional[Path] = None
) -> Settings:
    """
    Get the global settings instance.

    This function loads configuration on first call and
    caches it for subsequent calls. Use ConfigLoader
    directly if you need to reload configuration.

    This is the recommended way to access configuration
    throughout the application.

    Args:
        config_dir: Optional custom config directory
                   (useful for testing with test configs)

    Returns:
        Global Settings object (cached after first load)

    Example:
        >>> settings = get_settings()
        >>> factor = settings.get_sim_deflation("NG")
    """
    # Access global variables for caching
    global _settings_instance, _config_loader

    # Load configuration on first call (lazy loading)
    if _settings_instance is None:
        # Create config loader with optional custom directory
        _config_loader = ConfigLoader(config_dir)
        # Load and cache settings
        _settings_instance = _config_loader.load()

    # Return cached settings instance
    return _settings_instance


def load_config(
    config_dir: Optional[Path] = None
) -> Settings:
    """
    Load configuration from files.

    This is a convenience function that creates a ConfigLoader
    and loads settings. Use get_settings() for the cached
    global instance.

    Use this function when you need to:
    - Load configuration with a custom directory
    - Force reload of configuration
    - Access configuration in tests

    Args:
        config_dir: Optional custom config directory

    Returns:
        Loaded Settings object (not cached)
    """
    # Create new ConfigLoader instance
    loader = ConfigLoader(config_dir)
    # Load and return configuration
    return loader.load()


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.config.loader import *'

__all__ = [
    # Main configuration loader class
    "ConfigLoader",
    # Convenience function for loading configuration
    "load_config",
    # Function for getting cached global settings
    "get_settings",
]
