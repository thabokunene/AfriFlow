"""
@file __init__.py
@description AfriFlow - Cross-Domain Client Intelligence Platform main package initialization
@author Thabo Kunene
@created 2026-03-19

AfriFlow unifies CIB, Forex, Insurance, Cell Network, and Personal
Banking data into a single client intelligence layer across
20 African countries.

This package provides:
- Exception hierarchy for all AfriFlow errors
- Structured logging configuration
- Version and author metadata

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Import custom exceptions for re-export at package level
# These provide unified error handling across all modules
from afriflow.exceptions import (
    AfriFlowError,  # Base exception class for all AfriFlow errors
    EntityResolutionError,  # Entity matching failures
    SignalDetectionError,  # Signal detection failures
    CurrencyPropagationError,  # Currency event propagation failures
    SeasonalCalendarError,  # Seasonal adjustment failures
    BriefingGenerationError,  # RM briefing generation failures
    DataShadowError,  # Data shadow calculation failures
    CorridorError,  # Corridor operation failures
    LekgotlaError,  # Lekgotla operation failures
    DataQualityError,  # Data quality validation failures
    ConfigurationError,  # Configuration loading failures
    DataIngestionError,  # Data ingestion failures
    StorageError,  # Data storage operation failures
    APIError,  # API operation failures
    ValidationError,  # Input validation failures
)

# Import logging utilities for structured logging
# All modules should use these for consistent log formatting
from afriflow.logging_config import (
    setup_logging,  # Initialize logging with JSON formatting
    get_logger,  # Get a logger instance with afriflow prefix
    LoggingContext,  # Context manager for adding correlation IDs
    log_operation,  # Helper for logging operation status
)

# Package metadata
__version__ = "0.2.0"  # Current package version (semantic versioning)
__author__ = "Thabo Kunene"  # Package author

# Public API - defines what's exported when using 'from afriflow import *'
__all__ = [
    # Base exception - parent of all custom exceptions
    "AfriFlowError",
    # Domain exceptions - specific to business logic
    "EntityResolutionError",
    "SignalDetectionError",
    "CurrencyPropagationError",
    "SeasonalCalendarError",
    "BriefingGenerationError",
    "DataShadowError",
    "CorridorError",
    "LekgotlaError",
    # Infrastructure exceptions - technical/operational errors
    "DataQualityError",
    "ConfigurationError",
    "DataIngestionError",
    "StorageError",
    "APIError",
    # Validation - input validation failures
    "ValidationError",
    # Logging utilities - structured logging setup and helpers
    "setup_logging",
    "get_logger",
    "LoggingContext",
    "log_operation",
]
