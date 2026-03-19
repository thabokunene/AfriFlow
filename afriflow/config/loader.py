"""
Configuration Loader

We load and validate configuration from YAML files.
Configuration is loaded once at startup and passed via
dependency injection (not global state).

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from afriflow.config.settings import (
    Settings,
    SimDeflationConfig,
    SeasonalWeightConfig,
    SignalThresholds,
    LekgotlaConfig,
    CorridorConfig,
    ModerationPatterns,
)
from afriflow.exceptions import ConfigurationError, MissingConfigError, InvalidConfigError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("config.loader")

# Default configuration paths
DEFAULT_CONFIG_DIR = Path(__file__).parent


class ConfigLoader:
    """
    Loads and validates configuration from YAML files.

    Configuration is loaded once at startup and cached.
    All configuration access should go through this loader
    to ensure consistency and validation.

    Attributes:
        config_dir: Directory containing config files
        _settings: Cached Settings object
        _raw_config: Raw configuration dictionary
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """
        Initialize the configuration loader.

        Args:
            config_dir: Directory containing config files.
                       Defaults to afriflow/config/
        """
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self._settings: Optional[Settings] = None
        self._raw_config: Dict[str, Any] = {}

        logger.info(
            f"ConfigLoader initialized with config_dir: "
            f"{self.config_dir}"
        )

    def load(self) -> Settings:
        """
        Load and validate all configuration files.

        Returns:
            Validated Settings object

        Raises:
            ConfigurationError: If config files are invalid
        """
        if self._settings is not None:
            logger.debug("Returning cached settings")
            return self._settings

        logger.info("Loading configuration files...")

        try:
            # Load SIM deflation factors
            sim_deflation = self._load_sim_deflation(
                "sim_deflation.yml"
            )

            # Load seasonal weights
            seasonal_weights = self._load_seasonal_weights(
                "seasonal_weights.yml"
            )

            # Load signal thresholds
            signal_thresholds = self._load_signal_thresholds(
                "signal_thresholds.yml"
            )

            # Load Lekgotla config
            lekgotla = self._load_lekgotla_config(
                "lekgotla_config.yml"
            )

            # Load corridor config
            corridor = self._load_corridor_config(
                "corridor_config.yml"
            )

            # Load moderation patterns
            moderation = self._load_moderation_patterns(
                "moderation_patterns.yml"
            )

            self._settings = Settings(
                sim_deflation=sim_deflation,
                seasonal_weights=seasonal_weights,
                signal_thresholds=signal_thresholds,
                lekgotla=lekgotla,
                corridor=corridor,
                moderation=moderation,
            )

            logger.info(
                f"Configuration loaded successfully: "
                f"{len(sim_deflation)} countries, "
                f"{len(seasonal_weights)} seasonal patterns"
            )

            return self._settings

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}"
            )
        except Exception as e:
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

        Args:
            filename: Name of the file to load

        Returns:
            Parsed YAML content as dictionary

        Raises:
            ConfigurationError: If file cannot be loaded
        """
        filepath = self.config_dir / filename

        if not filepath.exists():
            logger.warning(
                f"Configuration file not found: {filepath}, "
                f"using defaults"
            )
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            logger.debug(f"Loaded config file: {filepath}")
            return content or {}

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in {filepath}: {e}"
            )
        except IOError as e:
            raise ConfigurationError(
                f"Cannot read {filepath}: {e}"
            )

    def _load_sim_deflation(
        self,
        filename: str
    ) -> Dict[str, SimDeflationConfig]:
        """Load SIM deflation factors from config file."""
        data = self._load_yaml_file(filename)
        country_factors = data.get("country_factors", {})

        result = {}
        for country_code, factors in country_factors.items():
            try:
                result[country_code.upper()] = SimDeflationConfig(
                    country_code=country_code.upper(),
                    deflation_factor=factors.get(
                        "deflation_factor", 0.5
                    ),
                    avg_sims_per_person=factors.get(
                        "avg_sims_per_person", 2.0
                    ),
                    confidence=factors.get(
                        "confidence", "low"
                    ),
                    source=factors.get(
                        "source", "Default"
                    ),
                )
            except Exception as e:
                logger.warning(
                    f"Invalid SIM deflation config for "
                    f"{country_code}: {e}"
                )

        logger.info(
            f"Loaded {len(result)} SIM deflation factors"
        )
        return result

    def _load_seasonal_weights(
        self,
        filename: str
    ) -> Dict[str, SeasonalWeightConfig]:
        """Load seasonal weights from config file."""
        data = self._load_yaml_file(filename)
        seasons = data.get("seasons", {})

        result = {}
        for commodity, countries in seasons.items():
            for country_code, patterns in countries.items():
                for pattern in patterns:
                    key = f"{commodity}_{country_code}"
                    try:
                        result[key] = SeasonalWeightConfig(
                            commodity=commodity,
                            country_code=country_code.upper(),
                            peak_months=pattern.get(
                                "peak_months", []
                            ),
                            trough_months=pattern.get(
                                "trough_months", []
                            ),
                            flow_type=pattern.get(
                                "flow_type", "export"
                            ),
                            expected_peak_multiplier=pattern.get(
                                "expected_peak_multiplier", 1.5
                            ),
                            expected_trough_multiplier=pattern.get(
                                "expected_trough_multiplier", 0.5
                            ),
                        )
                    except Exception as e:
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
        """Load signal thresholds from config file."""
        data = self._load_yaml_file(filename)

        try:
            expansion = data.get("expansion", {})
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
            logger.warning(
                f"Using default signal thresholds: {e}"
            )
            return SignalThresholds()

    def _load_lekgotla_config(
        self,
        filename: str
    ) -> LekgotlaConfig:
        """Load Lekgotla configuration from config file."""
        data = self._load_yaml_file(filename)

        try:
            points = data.get("points", {})
            graduation = data.get("graduation", {})
            notification = data.get("notification", {})

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
            logger.warning(
                f"Using default Lekgotla config: {e}"
            )
            return LekgotlaConfig()

    def _load_corridor_config(
        self,
        filename: str
    ) -> CorridorConfig:
        """Load corridor configuration from config file."""
        data = self._load_yaml_file(filename)

        try:
            leakage = data.get("leakage_detection", {})
            capture = data.get("capture_expectations", {})
            informal = data.get("informal_detection", {})

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
            logger.warning(
                f"Using default corridor config: {e}"
            )
            return CorridorConfig()

    def _load_moderation_patterns(
        self,
        filename: str
    ) -> ModerationPatterns:
        """Load moderation patterns from config file."""
        data = self._load_yaml_file(filename)

        try:
            patterns = data.get("patterns", {})
            auto_flag = data.get("auto_flag", {})
            review = data.get("review", {})

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
            logger.warning(
                f"Using default moderation patterns: {e}"
            )
            return ModerationPatterns()

    def reload(self) -> Settings:
        """
        Force reload of configuration (for testing).

        Returns:
            Reloaded Settings object
        """
        logger.info("Forcing configuration reload...")
        self._settings = None
        self._raw_config = {}
        return self.load()


# Global settings instance (loaded lazily)
_settings_instance: Optional[Settings] = None
_config_loader: Optional[ConfigLoader] = None


def get_settings(
    config_dir: Optional[Path] = None
) -> Settings:
    """
    Get the global settings instance.

    This function loads configuration on first call and
    caches it for subsequent calls. Use ConfigLoader
    directly if you need to reload configuration.

    Args:
        config_dir: Optional custom config directory

    Returns:
        Global Settings object
    """
    global _settings_instance, _config_loader

    if _settings_instance is None:
        _config_loader = ConfigLoader(config_dir)
        _settings_instance = _config_loader.load()

    return _settings_instance


def load_config(
    config_dir: Optional[Path] = None
) -> Settings:
    """
    Load configuration from files.

    This is a convenience function that creates a ConfigLoader
    and loads settings. Use get_settings() for the cached
    global instance.

    Args:
        config_dir: Optional custom config directory

    Returns:
        Loaded Settings object
    """
    loader = ConfigLoader(config_dir)
    return loader.load()


__all__ = [
    "ConfigLoader",
    "load_config",
    "get_settings",
]
