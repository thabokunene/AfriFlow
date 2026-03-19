"""
AfriFlow Custom Exception Hierarchy

We define a structured exception hierarchy for all AfriFlow
errors. This enables precise error handling, clear error
messages, and proper logging throughout the platform.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, Any, Optional


class AfriFlowError(Exception):
    """
    Base exception for all AfriFlow errors.

    All custom exceptions inherit from this base class
    to enable unified error handling across the platform.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional context
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


# ============================================
# DOMAIN ERRORS
# ============================================

class EntityResolutionError(AfriFlowError):
    """
    Entity resolution failed.

    Raised when client entity matching encounters errors
    such as invalid input data, matching algorithm failures,
    or golden ID generation failures.
    """
    pass


class SignalDetectionError(AfriFlowError):
    """
    Signal detection failed.

    Raised when cross-domain signal detection encounters
    errors such as invalid signal configuration, missing
    domain data, or signal calculation failures.
    """
    pass


class CurrencyPropagationError(AfriFlowError):
    """
    Currency event propagation failed.

    Raised when FX event cascade calculation encounters
    errors such as invalid event data, missing client
    exposures, or impact calculation failures.
    """
    pass


class SeasonalCalendarError(AfriFlowError):
    """
    Seasonal calendar lookup failed.

    Raised when seasonal adjustment encounters errors
    such as invalid calendar data, missing country/sector
    patterns, or adjustment calculation failures.
    """
    pass


class BriefingGenerationError(AfriFlowError):
    """
    Briefing generation failed.

    Raised when RM briefing generation encounters errors
    such as missing client data, template rendering failures,
    or data aggregation failures.
    """
    pass


class DataShadowError(AfriFlowError):
    """
    Data shadow calculation failed.

    Raised when data shadow gap detection encounters errors
    such as invalid expectation rules, missing domain data,
    or gap calculation failures.
    """
    pass


class CorridorError(AfriFlowError):
    """
    Corridor operation failed.

    Raised when corridor identification, revenue attribution,
    or leakage detection encounters errors.
    """
    pass


class LekgotlaError(AfriFlowError):
    """
    Lekgotla operation failed.

    Raised when thread management, knowledge card operations,
    or notification delivery encounters errors.
    """
    pass


# ============================================
# DATA QUALITY ERRORS
# ============================================

class DataQualityError(AfriFlowError):
    """
    Data quality validation failed.

    Raised when data quality checks fail such as schema
    validation errors, completeness threshold violations,
    or consistency check failures.
    """
    pass


class FreshnessError(AfriFlowError):
    """
    Data freshness check failed.

    Raised when data is stale beyond acceptable SLA
    thresholds.
    """
    pass


class ContractViolationError(AfriFlowError):
    """
    Data contract violation detected.

    Raised when incoming data does not conform to the
    expected domain contract schema.
    """
    pass


# ============================================
# CONFIGURATION ERRORS
# ============================================

class ConfigurationError(AfriFlowError):
    """
    Configuration loading or validation failed.

    Raised when configuration management encounters errors
    such as missing config files, invalid config values,
    or config schema validation failures.
    """
    pass


class MissingConfigError(ConfigurationError):
    """
    Required configuration is missing.

    Raised when a required configuration key is not found.
    """
    pass


class InvalidConfigError(ConfigurationError):
    """
    Configuration value is invalid.

    Raised when a configuration value fails validation.
    """
    pass


# ============================================
# DATA INGESTION ERRORS
# ============================================

class DataIngestionError(AfriFlowError):
    """
    Data ingestion failed.

    Raised when data ingestion encounters errors such as
    source connection failures, schema mismatches, or
    data transformation failures.
    """
    pass


class SchemaEvolutionError(AfriFlowError):
    """
    Schema evolution detected.

    Raised when incoming data schema does not match
    expected schema and cannot be automatically migrated.
    """
    pass


# ============================================
# STORAGE ERRORS
# ============================================

class StorageError(AfriFlowError):
    """
    Data storage operation failed.

    Raised when storage operations encounter errors such
    as write failures, partition errors, or Delta Lake
    transaction failures.
    """
    pass


class ConnectionError(AfriFlowError):
    """
    Database connection failed.

    Raised when database connectivity is lost or cannot
    be established.
    """
    pass


# ============================================
# API ERRORS
# ============================================

class APIError(AfriFlowError):
    """
    API operation failed.

    Raised when API operations encounter errors such as
    authentication failures, rate limiting, or invalid
    request/response formats.
    """
    pass


class AuthenticationError(APIError):
    """
    Authentication failed.

    Raised when API authentication fails.
    """
    pass


class AuthorizationError(APIError):
    """
    Authorization failed.

    Raised when user lacks permission for the requested
    operation.
    """
    pass


class RateLimitError(APIError):
    """
    Rate limit exceeded.

    Raised when API rate limit is exceeded.
    """
    pass


# ============================================
# VALIDATION ERRORS
# ============================================

class ValidationError(AfriFlowError):
    """
    Input validation failed.

    Raised when input validation encounters errors such
    as missing required fields, invalid field values,
    or type mismatches.

    Attributes:
        field: The field that failed validation
        value: The invalid value
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.field = field
        self.value = value
        super().__init__(message, details)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        result = super().to_dict()
        result["field"] = self.field
        result["value"] = self.value
        return result


# ============================================
# POD AND INFRASTRUCTURE ERRORS
# ============================================

class PodError(AfriFlowError):
    """
    Country pod operation failed.

    Raised when country pod operations encounter errors.
    """
    pass


class PodOfflineError(PodError):
    """
    Country pod is offline.

    Raised when a country pod is unreachable.
    """
    pass


class SyncError(PodError):
    """
    Pod synchronization failed.

    Raised when pod sync operations fail.
    """
    pass


# ============================================
# OUTCOME TRACKING ERRORS
# ============================================

class OutcomeTrackingError(AfriFlowError):
    """
    Outcome tracking operation failed.

    Raised when outcome recording or feedback loop
    operations encounter errors.
    """
    pass


# ============================================
# NOTIFICATION ERRORS
# ============================================

class NotificationError(AfriFlowError):
    """
    Notification delivery failed.

    Raised when notification delivery encounters errors.
    """
    pass


class DeliveryChannelError(NotificationError):
    """
    Notification delivery channel failed.

    Raised when a specific delivery channel (email,
    push, WhatsApp) fails.
    """
    pass


# ============================================
# EXCEPTION FACTORY
# ============================================

def create_error_from_code(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> AfriFlowError:
    """
    Create an exception from an error code.

    Args:
        error_code: Error code string (e.g., "ENTITY_RESOLUTION_FAILED")
        message: Human-readable message
        details: Optional additional context

    Returns:
        Appropriate AfriFlowError subclass instance
    """
    error_map = {
        "ENTITY_RESOLUTION_FAILED": EntityResolutionError,
        "SIGNAL_DETECTION_FAILED": SignalDetectionError,
        "CURRENCY_PROPAGATION_FAILED": CurrencyPropagationError,
        "SEASONAL_CALENDAR_FAILED": SeasonalCalendarError,
        "BRIEFING_GENERATION_FAILED": BriefingGenerationError,
        "DATA_SHADOW_FAILED": DataShadowError,
        "CORRIDOR_FAILED": CorridorError,
        "LEKGOTLA_FAILED": LekgotlaError,
        "DATA_QUALITY_FAILED": DataQualityError,
        "FRESHNESS_FAILED": FreshnessError,
        "CONTRACT_VIOLATION": ContractViolationError,
        "CONFIG_MISSING": MissingConfigError,
        "CONFIG_INVALID": InvalidConfigError,
        "DATA_INGESTION_FAILED": DataIngestionError,
        "SCHEMA_EVOLUTION_FAILED": SchemaEvolutionError,
        "STORAGE_FAILED": StorageError,
        "CONNECTION_FAILED": ConnectionError,
        "API_ERROR": APIError,
        "AUTHENTICATION_FAILED": AuthenticationError,
        "AUTHORIZATION_FAILED": AuthorizationError,
        "RATE_LIMIT_EXCEEDED": RateLimitError,
        "VALIDATION_FAILED": ValidationError,
        "POD_OFFLINE": PodOfflineError,
        "SYNC_FAILED": SyncError,
        "OUTCOME_TRACKING_FAILED": OutcomeTrackingError,
        "NOTIFICATION_FAILED": NotificationError,
        "DELIVERY_CHANNEL_FAILED": DeliveryChannelError,
    }

    error_class = error_map.get(error_code, AfriFlowError)
    return error_class(message, details)


__all__ = [
    # Base
    "AfriFlowError",
    # Domain
    "EntityResolutionError",
    "SignalDetectionError",
    "CurrencyPropagationError",
    "SeasonalCalendarError",
    "BriefingGenerationError",
    "DataShadowError",
    "CorridorError",
    "LekgotlaError",
    # Data Quality
    "DataQualityError",
    "FreshnessError",
    "ContractViolationError",
    # Configuration
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
    # Ingestion
    "DataIngestionError",
    "SchemaEvolutionError",
    # Storage
    "StorageError",
    "ConnectionError",
    # API
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    # Validation
    "ValidationError",
    # Pod
    "PodError",
    "PodOfflineError",
    "SyncError",
    # Outcome
    "OutcomeTrackingError",
    # Notification
    "NotificationError",
    "DeliveryChannelError",
    # Factory
    "create_error_from_code",
]
