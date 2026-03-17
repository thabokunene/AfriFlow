"""
AfriFlow - Cross-Domain Client Intelligence Platform

We unify CIB, Forex, Insurance, Cell Network, and Personal
Banking data into a single client intelligence layer across
20 African countries.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from afriflow.exceptions import (
    AfriFlowError,
    EntityResolutionError,
    SignalDetectionError,
    CurrencyPropagationError,
    SeasonalCalendarError,
    BriefingGenerationError,
    DataShadowError,
    DataQualityError,
    ConfigurationError,
    DataIngestionError,
    StorageError,
    APIError,
    ValidationError,
)
from afriflow.logging_config import (
    setup_logging,
    get_logger,
    LoggingContext,
    log_operation,
)

__version__ = "0.2.0"
__author__ = "Thabo Kunene"

__all__ = [
    # Base exception
    "AfriFlowError",
    # Domain exceptions
    "EntityResolutionError",
    "SignalDetectionError",
    "CurrencyPropagationError",
    "SeasonalCalendarError",
    "BriefingGenerationError",
    "DataShadowError",
    # Infrastructure exceptions
    "DataQualityError",
    "ConfigurationError",
    "DataIngestionError",
    "StorageError",
    "APIError",
    # Validation
    "ValidationError",
    # Logging
    "setup_logging",
    "get_logger",
    "LoggingContext",
    "log_operation",
]
