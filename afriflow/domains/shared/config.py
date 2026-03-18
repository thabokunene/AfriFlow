"""
@file config.py
@description Centralized environment-driven configuration loader for AfriFlow domains
@author Thabo Kunene
@created 2026-03-17
"""

"""
AfriFlow Shared Configuration.

We provide centralized configuration management for all
AfriFlow domains. Configuration is loaded from environment
variables with sensible defaults for development.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import os  # Environment variable access for deployment-specific configuration
from dataclasses import dataclass
from typing import Optional
import logging  # Operational logs for configuration loading and validation behavior

logger = logging.getLogger(__name__)  # Module-level logger for config lifecycle events


@dataclass
class AppConfig:
    """
    Application configuration container.

    Attributes:
        env: Environment name (dev, staging, prod)
        kafka_broker: Kafka broker connection string
        schema_registry_url: Schema Registry URL
        db_url: Database connection URL
    """

    env: str
    kafka_broker: str
    schema_registry_url: str
    db_url: str

    @classmethod
    def load(cls) -> "AppConfig":
        """
        Load configuration from environment variables.

        We accept both SCHEMA_REGISTRY_URL (preferred) and
        SCHEMA_REGISTRY (legacy) for backward compatibility.

        Returns:
            AppConfig instance with loaded configuration

        Raises:
            ValueError: If required configuration is invalid
        """
        # Accept both SCHEMA_REGISTRY_URL (preferred) and SCHEMA_REGISTRY (legacy)
        schema_registry = os.getenv("SCHEMA_REGISTRY_URL") or os.getenv(
            "SCHEMA_REGISTRY", "http://localhost:8081"
        )

        env = os.getenv("APP_ENV", "dev")
        kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")
        db_url = os.getenv("DATABASE_URL", "sqlite:///afriflow.db")

        # Validate environment
        if env not in ("dev", "staging", "prod", "test"):
            logger.warning(
                f"Unknown APP_ENV '{env}', using 'dev' settings"
            )

        logger.info(
            f"Configuration loaded: env={env}, "
            f"kafka={kafka_broker}"
        )

        return cls(
            env=env,
            kafka_broker=kafka_broker,
            schema_registry_url=schema_registry,
            db_url=db_url,
        )

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.kafka_broker:
            raise ValueError("KAFKA_BROKER is required")

        if not self.schema_registry_url:
            raise ValueError("SCHEMA_REGISTRY_URL is required")

        if not self.db_url:
            raise ValueError("DATABASE_URL is required")

        logger.debug("Configuration validation passed")


# Global configuration instance
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get the global configuration instance.

    Returns:
        AppConfig instance

    Raises:
        RuntimeError: If configuration not loaded
    """
    global config
    if config is None:
        # Lazy-load configuration so libraries can import safely without requiring env at import time
        config = AppConfig.load()
    return config


def reset_config() -> None:
    """Reset configuration (for testing)."""
    global config
    config = None
    logger.debug("Configuration reset")
