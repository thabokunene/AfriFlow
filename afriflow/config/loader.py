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

import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from afriflow.config.settings import (
    Settings,
    RevenueEstimates,
    ExpansionThresholds,
    SimDeflationConfig,
    CurrencyThreshold,
    SeasonalPattern,
)
from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger

logger = get_logger("config.loader")

# Default configuration paths
DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config"


class ConfigLoader:
    """
    Loads and validates configuration from YAML files.

    Configuration is loaded once at startup and cached.
    All configuration access should go through this loader
    to ensure consistency and validation.
    """

    def __init__(self, config_dir: Optional[Path] = None):
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
            # Load revenue estimates
            revenue_data = self._load_yaml_file(
                "sim_deflation_factors.yml"
            )
            revenue_estimates = self._parse_revenue_estimates(
                revenue_data
            )

            # Load expansion thresholds
            expansion_data = self._load_yaml_file(
                "expansion_thresholds.yml"
            )
            expansion_thresholds = self._parse_expansion_thresholds(
                expansion_data
            )

            # Load SIM deflation factors
            sim_deflation = self._load_sim_deflation(
                "sim_deflation_factors.yml"
            )

            # Load currency thresholds
            currency_thresholds = self._load_currency_thresholds(
                "currency_thresholds.yml"
            )

            # Load seasonal patterns
            seasonal_patterns = self._load_seasonal_patterns(
                "seasonal_calendars/southern_africa_agriculture.yml"
            )

            self._settings = Settings(
                revenue_estimates=revenue_estimates,
                expansion_thresholds=expansion_thresholds,
                sim_deflation=sim_deflation,
                currency_thresholds=currency_thresholds,
                seasonal_patterns=seasonal_patterns,
            )

            logger.info(
                f"Configuration loaded successfully: "
                f"{len(sim_deflation)} countries, "
                f"{len(currency_thresholds)} currencies, "
                f"{len(seasonal_patterns)} seasonal patterns"
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

    def _parse_revenue_estimates(
        self,
        data: Dict[str, Any]
    ) -> RevenueEstimates:
        """Parse revenue estimates from config data."""
        try:
            return RevenueEstimates()
        except Exception as e:
            logger.warning(
                f"Using default revenue estimates: {e}"
            )
            return RevenueEstimates()

    def _parse_expansion_thresholds(
        self,
        data: Dict[str, Any]
    ) -> ExpansionThresholds:
        """
        Parse expansion thresholds from config data.

        Args:
            data: Raw configuration data from YAML file

        Returns:
            Validated ExpansionThresholds object
        """
        try:
            min_evidence = data.get("min_evidence", {})
            
            return ExpansionThresholds(
                min_cib_payments_for_signal=min_evidence.get(
                    "cib_payments_count",
                    ExpansionThresholds.model_fields["min_cib_payments_for_signal"].default
                ),
                min_cib_value_for_signal=min_evidence.get(
                    "cib_value_zar",
                    ExpansionThresholds.model_fields["min_cib_value_for_signal"].default
                ),
                min_sim_activations_for_signal=min_evidence.get(
                    "sim_activations_count",
                    ExpansionThresholds.model_fields["min_sim_activations_for_signal"].default
                ),
                min_forex_trades_for_signal=min_evidence.get(
                    "forex_trades_count",
                    ExpansionThresholds.model_fields["min_forex_trades_for_signal"].default
                ),
                min_pbb_accounts_for_signal=min_evidence.get(
                    "pbb_accounts_count",
                    ExpansionThresholds.model_fields["min_pbb_accounts_for_signal"].default
                ),
            )
        except Exception as e:
            logger.warning(
                f"Using default expansion thresholds: {e}"
            )
            return ExpansionThresholds()

    def _load_sim_deflation(
        self,
        filename: str
    ) -> Dict[str, SimDeflationConfig]:
        """
        Load SIM deflation factors from config file.

        Args:
            filename: Name of the config file

        Returns:
            Dictionary mapping country codes to configs
        """
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

    def _load_currency_thresholds(
        self,
        filename: str
    ) -> Dict[str, CurrencyThreshold]:
        """
        Load currency thresholds from config file.

        Args:
            filename: Name of the config file

        Returns:
            Dictionary mapping currency codes to thresholds
        """
        data = self._load_yaml_file(filename)
        thresholds = data.get("thresholds", {})

        result = {}
        for currency, values in thresholds.items():
            try:
                result[currency.upper()] = CurrencyThreshold(
                    devaluation_pct=values.get(
                        "devaluation_pct", 10.0
                    ),
                    rapid_depreciation_pct=values.get(
                        "rapid_depreciation_pct", 5.0
                    ),
                    parallel_divergence_pct=values.get(
                        "parallel_divergence_pct", 20.0
                    ),
                    notes=values.get("notes"),
                )
            except Exception as e:
                logger.warning(
                    f"Invalid currency threshold for "
                    f"{currency}: {e}"
                )

        logger.info(
            f"Loaded {len(result)} currency thresholds"
        )
        return result

    def _load_seasonal_patterns(
        self,
        filename: str
    ) -> list[SeasonalPattern]:
        """
        Load seasonal patterns from config file.

        Args:
            filename: Name of the config file

        Returns:
            List of SeasonalPattern objects
        """
        data = self._load_yaml_file(filename)
        seasons = data.get("seasons", {})

        result = []
        for commodity, countries in seasons.items():
            for country_code, patterns in countries.items():
                for pattern in patterns:
                    try:
                        result.append(SeasonalPattern(
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
                            expected_peak_multiplier=(
                                pattern.get(
                                    "expected_peak_multiplier",
                                    1.5
                                )
                            ),
                            expected_trough_multiplier=(
                                pattern.get(
                                    "expected_trough_multiplier",
                                    0.5
                                )
                            ),
                        ))
                    except Exception as e:
                        logger.warning(
                            f"Invalid seasonal pattern for "
                            f"{commodity}/{country_code}: {e}"
                        )

        logger.info(
            f"Loaded {len(result)} seasonal patterns"
        )
        return result

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
