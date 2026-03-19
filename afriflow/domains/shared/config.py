"""
@file config.py
@description Centralized environment-driven configuration loader for AfriFlow domains, ensuring consistency across environments.
@author Thabo Kunene
@created 2026-03-19
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

# Access to system environment variables for runtime configuration
import os
# Dataclasses for structured, immutable-ish configuration containers
from dataclasses import dataclass
# Type hinting for better IDE support and static analysis
from typing import Optional
# Standard logging for operational observability during startup
import logging

# Initialize module-level logger for configuration lifecycle events
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """
    Application configuration container.
    Stores connectivity strings and environment settings used across all domains.

    Attributes:
        env: Environment name (dev, staging, prod)
        kafka_broker: Kafka broker connection string for message ingestion
        schema_registry_url: URL for Avro schema management
        db_url: Database connection string for persistence
    """

    env: str
    kafka_broker: str
    schema_registry_url: str
    db_url: str

    @classmethod
    def load(cls) -> "AppConfig":
        """
        Loads configuration from environment variables with sensible defaults.
        Supports both modern and legacy environment variable names for compatibility.

        :return: An initialized AppConfig instance.
        """
        # Accept both SCHEMA_REGISTRY_URL (preferred) and SCHEMA_REGISTRY (legacy)
        # fallback to localhost for developer convenience.
        schema_registry = os.getenv("SCHEMA_REGISTRY_URL") or os.getenv(
            "SCHEMA_REGISTRY", "http://localhost:8081"
        )

        # Environment name, defaults to 'dev' for local testing
        env = os.getenv("APP_ENV", "dev")
        # Kafka broker list, typically comma-separated in production
        kafka_broker = os.getenv("KAFKA_BROKER", "localhost:9092")
        # Primary database URL for domain-specific storage
        db_url = os.getenv("DATABASE_URL", "sqlite:///afriflow.db")

        # Validate environment to prevent misconfiguration in critical pipelines
        if env not in ("dev", "staging", "prod", "test"):
            logger.warning(
                f"Unknown APP_ENV '{env}', using 'dev' settings"
            )

        # Log essential configuration state (excluding sensitive credentials if any)
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
        Validates that critical configuration values are present.
        
        :raises ValueError: If any mandatory configuration is missing.
        """
        # Ensure Kafka connectivity is defined
        if not self.kafka_broker:
            raise ValueError("KAFKA_BROKER is required")

        # Ensure Schema Registry is defined for Avro processing
        if not self.schema_registry_url:
            raise ValueError("SCHEMA_REGISTRY_URL is required")

        # Ensure Database URL is defined for state persistence
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
