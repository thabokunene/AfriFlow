"""
@file exceptions.py
@description AfriFlow Custom Exception Hierarchy - Structured error handling for all modules
@author Thabo Kunene
@created 2026-03-19

This module defines a comprehensive exception hierarchy for all AfriFlow errors.
All custom exceptions inherit from AfriFlowError to enable:
- Unified error handling across the platform
- Consistent error logging with structured data
- Clear error messages for debugging and monitoring

Exception Categories:
1. Domain Errors - Business logic failures (entity resolution, signals, etc.)
2. Data Quality Errors - Validation and freshness failures
3. Configuration Errors - Config loading and validation failures
4. Data Ingestion Errors - Pipeline and schema failures
5. Storage Errors - Database and connection failures
6. API Errors - Authentication, authorization, and rate limiting
7. Validation Errors - Input validation failures
8. Pod Errors - Country pod connectivity and sync failures
9. Outcome Tracking Errors - Signal outcome recording failures
10. Notification Errors - Alert delivery failures

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

from typing import Dict, Any, Optional  # Type hints for dictionary, any type, and optional types


class AfriFlowError(Exception):
    """
    Base exception for all AfriFlow errors.

    All custom exceptions inherit from this base class
    to enable unified error handling across the platform.

    Attributes:
        message (str): Human-readable error message
        details (Optional[Dict[str, Any]]): Optional dictionary with additional context

    Example:
        >>> try:
        ...     raise AfriFlowError("Something went wrong", {"key": "value"})
        ... except AfriFlowError as e:
        ...     print(e.to_dict())  # {'error_type': 'AfriFlowError', 'message': '...', 'details': {...}}
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize the base AfriFlow error.

        Args:
            message: Human-readable error message describing what went wrong
            details: Optional dictionary with additional context (e.g., failed field names, values)
        """
        self.message = message  # Store the error message for display
        self.details = details or {}  # Store additional context, default to empty dict
        super().__init__(self.message)  # Call parent Exception constructor with message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for structured logging.

        This enables consistent error logging across all modules
        and integration with log aggregation systems.

        Returns:
            Dictionary with error_type, message, and details fields
        """
        return {
            "error_type": self.__class__.__name__,  # Exception class name (e.g., "EntityResolutionError")
            "message": self.message,  # Human-readable error message
            "details": self.details,  # Additional context dictionary
        }

    def __str__(self) -> str:
        """
        Return string representation of the exception.

        Includes details dictionary if present for more informative error messages.

        Returns:
            Formatted error string with message and optional details
        """
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


# ============================================
# DOMAIN ERRORS
# ============================================
# These exceptions are raised by business logic modules
# when domain-specific operations fail

class EntityResolutionError(AfriFlowError):
    """
    Entity resolution failed.

    Raised when client entity matching encounters errors
    such as:
    - Invalid input data (missing required fields)
    - Matching algorithm failures (fuzzy matching errors)
    - Golden ID generation failures (duplicate ID creation)

    Example:
        >>> if not golden_id:
        ...     raise EntityResolutionError(
        ...         "Failed to generate golden ID",
        ...         {"client_name": "Acme Corp"}
        ...     )
    """
    pass


class SignalDetectionError(AfriFlowError):
    """
    Signal detection failed.

    Raised when cross-domain signal detection encounters
    errors such as:
    - Invalid signal configuration (missing thresholds)
    - Missing domain data (required domain not available)
    - Signal calculation failures (mathematical errors)

    Example:
        >>> if confidence < threshold:
        ...     raise SignalDetectionError(
        ...         "Confidence below threshold",
        ...         {"confidence": 0.45, "threshold": 0.70}
        ...     )
    """
    pass


class CurrencyPropagationError(AfriFlowError):
    """
    Currency event propagation failed.

    Raised when FX event cascade calculation encounters
    errors such as:
    - Invalid event data (malformed currency event)
    - Missing client exposures (client not found in exposure table)
    - Impact calculation failures (division by zero, overflow)

    Example:
        >>> try:
        ...     impact = exposure / rate
        ... except ZeroDivisionError as e:
        ...     raise CurrencyPropagationError("Rate is zero", {"currency": currency})
    """
    pass


class SeasonalCalendarError(AfriFlowError):
    """
    Seasonal calendar lookup failed.

    Raised when seasonal adjustment encounters errors
    such as:
    - Invalid calendar data (malformed seasonal patterns)
    - Missing country/sector patterns (no data for country)
    - Adjustment calculation failures (invalid multipliers)

    Example:
        >>> if country not in calendar:
        ...     raise SeasonalCalendarError(
        ...         "No seasonal pattern for country",
        ...         {"country": country_code}
        ...     )
    """
    pass


class BriefingGenerationError(AfriFlowError):
    """
    Briefing generation failed.

    Raised when RM briefing generation encounters errors
    such as:
    - Missing client data (client not found in golden record)
    - Template rendering failures (Jinja2 template errors)
    - Data aggregation failures (SQL query errors)

    Example:
        >>> if not client_data:
        ...     raise BriefingGenerationError(
        ...         "Client data not found",
        ...         {"client_id": client_id}
        ...     )
    """
    pass


class DataShadowError(AfriFlowError):
    """
    Data shadow calculation failed.

    Raised when data shadow gap detection encounters errors
    such as:
    - Invalid expectation rules (malformed rule definitions)
    - Missing domain data (domain not returning data)
    - Gap calculation failures (mathematical errors)

    Example:
        >>> if expected > 0 and actual == 0:
        ...     raise DataShadowError(
        ...         "Data gap detected",
        ...         {"expected": expected, "actual": actual}
        ...     )
    """
    pass


class CorridorError(AfriFlowError):
    """
    Corridor operation failed.

    Raised when corridor identification, revenue attribution,
    or leakage detection encounters errors.

    Common scenarios:
    - Corridor identification failures (missing payment data)
    - Revenue attribution errors (no revenue records found)
    - Leakage detection failures (insufficient data for comparison)

    Example:
        >>> if not corridor_data:
        ...     raise CorridorError(
        ...         "Corridor data not found",
        ...         {"corridor_id": corridor_id}
        ...     )
    """
    pass


class LekgotlaError(AfriFlowError):
    """
    Lekgotla operation failed.

    Raised when thread management, knowledge card operations,
    or notification delivery encounters errors.

    Common scenarios:
    - Thread creation failures (database errors)
    - Knowledge card graduation errors (validation failures)
    - Notification delivery failures (channel unavailable)

    Example:
        >>> if not thread_created:
        ...     raise LekgotlaError(
        ...         "Failed to create thread",
        ...         {"title": thread_title}
        ...     )
    """
    pass


# ============================================
# DATA QUALITY ERRORS
# ============================================
# These exceptions are raised when data quality checks fail
# or data does not meet expected standards

class DataQualityError(AfriFlowError):
    """
    Data quality validation failed.

    Raised when data quality checks fail such as:
    - Schema validation errors (field type mismatches)
    - Completeness threshold violations (too many nulls)
    - Consistency check failures (cross-field validation)

    Example:
        >>> if null_count > threshold:
        ...     raise DataQualityError(
        ...         "Too many null values",
        ...         {"null_count": null_count, "threshold": threshold}
        ...     )
    """
    pass


class FreshnessError(AfriFlowError):
    """
    Data freshness check failed.

    Raised when data is stale beyond acceptable SLA
    thresholds. This indicates that data has not been
    refreshed within the expected time window.

    Common scenarios:
    - Pod offline (country pod not syncing)
    - Pipeline failure (ETL job failed)
    - Source system unavailable (upstream system down)

    Example:
        >>> if hours_since_refresh > sla_hours:
        ...     raise FreshnessError(
        ...         "Data stale beyond SLA",
        ...         {"hours_stale": hours_since_refresh, "sla_hours": sla_hours}
        ...     )
    """
    pass


class ContractViolationError(AfriFlowError):
    """
    Data contract violation detected.

    Raised when incoming data does not conform to the
    expected domain contract schema. This indicates that
    a domain is sending data that doesn't match the
    agreed-upon contract.

    Common scenarios:
    - Missing required fields
    - Invalid field types
    - Unexpected field values

    Example:
        >>> if "client_id" not in record:
        ...     raise ContractViolationError(
        ...         "Missing required field",
        ...         {"field": "client_id", "domain": domain}
        ...     )
    """
    pass


# ============================================
# CONFIGURATION ERRORS
# ============================================
# These exceptions are raised when configuration loading
# or validation fails

class ConfigurationError(AfriFlowError):
    """
    Configuration loading or validation failed.

    Raised when configuration management encounters errors
    such as:
    - Missing config files (YAML file not found)
    - Invalid config values (type validation failures)
    - Config schema validation failures (missing required keys)

    Example:
        >>> if not config_file.exists():
        ...     raise ConfigurationError(
        ...         "Config file not found",
        ...         {"path": str(config_file)}
        ...     )
    """
    pass


class MissingConfigError(ConfigurationError):
    """
    Required configuration is missing.

    Raised when a required configuration key is not found
    in the loaded configuration. This is more specific than
    ConfigurationError and indicates a missing key rather
    than a file loading issue.

    Example:
        >>> if "database_url" not in config:
        ...     raise MissingConfigError(
        ...         "Required config key missing",
        ...         {"key": "database_url"}
        ...     )
    """
    pass


class InvalidConfigError(ConfigurationError):
    """
    Configuration value is invalid.

    Raised when a configuration value fails validation.
    This indicates the key exists but the value is not
    acceptable (wrong type, out of range, invalid format).

    Example:
        >>> if not isinstance(port, int) or port < 1 or port > 65535:
        ...     raise InvalidConfigError(
        ...         "Invalid port number",
        ...         {"key": "database.port", "value": port}
        ...     )
    """
    pass


# ============================================
# DATA INGESTION ERRORS
# ============================================
# These exceptions are raised during data ingestion
# when data cannot be properly consumed or transformed

class DataIngestionError(AfriFlowError):
    """
    Data ingestion failed.

    Raised when data ingestion encounters errors such as:
    - Source connection failures (Kafka broker unreachable)
    - Schema mismatches (Avro schema evolution issues)
    - Data transformation failures (ETL transformation errors)

    Example:
        >>> if not kafka_connected:
        ...     raise DataIngestionError(
        ...         "Cannot connect to Kafka",
        ...         {"bootstrap_servers": servers}
        ...     )
    """
    pass


class SchemaEvolutionError(AfriFlowError):
    """
    Schema evolution detected.

    Raised when incoming data schema does not match
    expected schema and cannot be automatically migrated.
    This indicates a breaking schema change that requires
    manual intervention.

    Common scenarios:
    - Field removed without backward compatibility
    - Field type changed (string to int)
    - Required field added without default value

    Example:
        >>> if schema_version > supported_version:
        ...     raise SchemaEvolutionError(
        ...         "Unsupported schema version",
        ...         {"current": schema_version, "supported": supported_version}
        ...     )
    """
    pass


# ============================================
# STORAGE ERRORS
# ============================================
# These exceptions are raised when data storage
# operations fail

class StorageError(AfriFlowError):
    """
    Data storage operation failed.

    Raised when storage operations encounter errors such as:
    - Write failures (disk full, permission denied)
    - Partition errors (partition key issues)
    - Delta Lake transaction failures (concurrent write conflicts)

    Example:
        >>> try:
        ...     delta_table.write(data)
        ... except Exception as e:
        ...     raise StorageError("Delta write failed", {"error": str(e)})
    """
    pass


class ConnectionError(AfriFlowError):
    """
    Database connection failed.

    Raised when database connectivity is lost or cannot
    be established. This indicates infrastructure issues
    rather than application logic problems.

    Common scenarios:
    - Database server unreachable
    - Connection pool exhausted
    - Network connectivity issues

    Example:
        >>> if not connection.ping():
        ...     raise ConnectionError(
        ...         "Database connection lost",
        ...         {"host": db_host, "port": db_port}
        ...     )
    """
    pass


# ============================================
# API ERRORS
# ============================================
# These exceptions are raised by the API layer
# when HTTP operations fail

class APIError(AfriFlowError):
    """
    API operation failed.

    Raised when API operations encounter errors such as:
    - Authentication failures (invalid token)
    - Rate limiting (too many requests)
    - Invalid request/response formats (malformed JSON)

    Example:
        >>> if response.status_code == 500:
        ...     raise APIError(
        ...         "Internal server error",
        ...         {"endpoint": endpoint, "status": response.status_code}
        ...     )
    """
    pass


class AuthenticationError(APIError):
    """
    Authentication failed.

    Raised when API authentication fails. This indicates
    the client is not properly authenticated.

    Common scenarios:
    - Missing authentication token
    - Expired authentication token
    - Invalid authentication credentials

    Example:
        >>> if not token or not validate_token(token):
        ...     raise AuthenticationError(
        ...         "Authentication failed",
        ...         {"token_provided": token is not None}
        ...     )
    """
    pass


class AuthorizationError(APIError):
    """
    Authorization failed.

    Raised when user lacks permission for the requested
    operation. This indicates the user is authenticated
    but not authorized for the specific action.

    Common scenarios:
    - User lacks required role
    - User accessing another user's data
    - Country-level access restrictions

    Example:
        >>> if user.country != requested_country:
        ...     raise AuthorizationError(
        ...         "Access denied for country",
        ...         {"user_country": user.country, "requested": requested_country}
        ...     )
    """
    pass


class RateLimitError(APIError):
    """
    Rate limit exceeded.

    Raised when API rate limit is exceeded. This indicates
    the client is making too many requests too quickly.

    Common scenarios:
    - Too many requests per second
    - Too many requests per minute
    - Quota exceeded for the billing tier

    Example:
        >>> if requests_per_second > limit:
        ...     raise RateLimitError(
        ...         "Rate limit exceeded",
        ...         {"current": requests_per_second, "limit": limit}
        ...     )
    """
    pass


# ============================================
# VALIDATION ERRORS
# ============================================
# These exceptions are raised when input validation fails

class ValidationError(AfriFlowError):
    """
    Input validation failed.

    Raised when input validation encounters errors such as:
    - Missing required fields (null where not allowed)
    - Invalid field values (out of range, wrong format)
    - Type mismatches (string where int expected)

    Attributes:
        field (Optional[str]): The field that failed validation
        value (Optional[Any]): The invalid value that was provided

    Example:
        >>> if not email or "@" not in email:
        ...     raise ValidationError(
        ...         "Invalid email format",
        ...         field="email",
        ...         value=email
        ...     )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize validation error with field context.

        Args:
            message: Human-readable error message
            field: The specific field that failed validation
            value: The invalid value that was provided
            details: Optional additional context dictionary
        """
        self.field = field  # Store the field name for error reporting
        self.value = value  # Store the invalid value for debugging
        super().__init__(message, details)  # Call parent constructor

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging.

        Extends parent to_dict() to include field and value
        for more detailed error reporting.

        Returns:
            Dictionary with error_type, message, details, field, and value
        """
        result = super().to_dict()  # Get base dictionary from parent
        result["field"] = self.field  # Add the field that failed validation
        result["value"] = self.value  # Add the invalid value
        return result


# ============================================
# POD AND INFRASTRUCTURE ERRORS
# ============================================
# These exceptions are raised by country pod operations
# when infrastructure issues occur

class PodError(AfriFlowError):
    """
    Country pod operation failed.

    Raised when country pod operations encounter errors.
    Country pods are federated deployments in each country
    that process data locally before syncing to the central hub.

    Common scenarios:
    - Pod initialization failures
    - Pod configuration errors
    - Pod communication failures

    Example:
        >>> if not pod_initialized:
        ...     raise PodError(
        ...         "Pod not initialized",
        ...         {"pod_id": pod_id}
        ...     )
    """
    pass


class PodOfflineError(PodError):
    """
    Country pod is offline.

    Raised when a country pod is unreachable. This indicates
    the pod is not responding to health checks or connection
    attempts.

    Common scenarios:
    - Network connectivity lost
    - Pod process crashed
    - Server hardware failure

    Example:
        >>> if not health_check_response:
        ...     raise PodOfflineError(
        ...         "Pod not responding",
        ...         {"pod_id": pod_id, "last_seen": last_seen}
        ...     )
    """
    pass


class SyncError(PodError):
    """
    Pod synchronization failed.

    Raised when pod sync operations fail. This indicates
    data cannot be synchronized between the country pod
    and the central hub.

    Common scenarios:
    - Sync conflict (concurrent modifications)
    - Data corruption during sync
    - Network timeout during large transfer

    Example:
        >>> if sync_status != "success":
        ...     raise SyncError(
        ...         "Sync failed",
        ...         {"pod_id": pod_id, "status": sync_status}
        ...     )
    """
    pass


# ============================================
# OUTCOME TRACKING ERRORS
# ============================================
# These exceptions are raised when outcome recording
# or feedback loop operations fail

class OutcomeTrackingError(AfriFlowError):
    """
    Outcome tracking operation failed.

    Raised when outcome recording or feedback loop
    operations encounter errors.

    Common scenarios:
    - Outcome recording failures (database errors)
    - Feedback loop processing errors
    - Signal lifecycle state transition failures

    Example:
        >>> if not outcome_recorded:
        ...     raise OutcomeTrackingError(
        ...         "Failed to record outcome",
        ...         {"signal_id": signal_id}
        ...     )
    """
    pass


# ============================================
# NOTIFICATION ERRORS
# ============================================
# These exceptions are raised when notification
# delivery fails

class NotificationError(AfriFlowError):
    """
    Notification delivery failed.

    Raised when notification delivery encounters errors.
    This is the base class for all notification-related
    errors.

    Common scenarios:
    - Notification queue full
    - Template rendering failures
    - Recipient lookup failures

    Example:
        >>> if not notification_sent:
        ...     raise NotificationError(
        ...         "Failed to send notification",
        ...         {"notification_id": notification_id}
        ...     )
    """
    pass


class DeliveryChannelError(NotificationError):
    """
    Notification delivery channel failed.

    Raised when a specific delivery channel (email,
    push, WhatsApp) fails. This provides more specific
    error information than the base NotificationError.

    Common scenarios:
    - Email server unreachable
    - Push notification service unavailable
    - WhatsApp API rate limited

    Example:
        >>> if not email_sent:
        ...     raise DeliveryChannelError(
        ...         "Email delivery failed",
        ...         {"channel": "email", "recipient": recipient}
        ...     )
    """
    pass


# ============================================
# EXCEPTION FACTORY
# ============================================
# This factory function enables creating exceptions
# from error codes (useful for API responses and
# centralized error handling)

def create_error_from_code(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> AfriFlowError:
    """
    Create an exception from an error code.

    This factory function maps error codes to their corresponding
    exception classes. Useful for API responses, centralized
    error handling, and converting string error codes to
    proper exception objects.

    Args:
        error_code: Error code string (e.g., "ENTITY_RESOLUTION_FAILED")
        message: Human-readable error message
        details: Optional additional context dictionary

    Returns:
        Appropriate AfriFlowError subclass instance

    Example:
        >>> error = create_error_from_code(
        ...     "VALIDATION_FAILED",
        ...     "Email format invalid",
        ...     {"field": "email", "value": "invalid"}
        ... )
        >>> raise error
    """
    # Map error codes to their corresponding exception classes
    # This enables centralized error handling and API error responses
    error_map = {
        # Domain errors
        "ENTITY_RESOLUTION_FAILED": EntityResolutionError,
        "SIGNAL_DETECTION_FAILED": SignalDetectionError,
        "CURRENCY_PROPAGATION_FAILED": CurrencyPropagationError,
        "SEASONAL_CALENDAR_FAILED": SeasonalCalendarError,
        "BRIEFING_GENERATION_FAILED": BriefingGenerationError,
        "DATA_SHADOW_FAILED": DataShadowError,
        "CORRIDOR_FAILED": CorridorError,
        "LEKGOTLA_FAILED": LekgotlaError,
        # Data quality errors
        "DATA_QUALITY_FAILED": DataQualityError,
        "FRESHNESS_FAILED": FreshnessError,
        "CONTRACT_VIOLATION": ContractViolationError,
        # Configuration errors
        "CONFIG_MISSING": MissingConfigError,
        "CONFIG_INVALID": InvalidConfigError,
        # Ingestion errors
        "DATA_INGESTION_FAILED": DataIngestionError,
        "SCHEMA_EVOLUTION_FAILED": SchemaEvolutionError,
        # Storage errors
        "STORAGE_FAILED": StorageError,
        "CONNECTION_FAILED": ConnectionError,
        # API errors
        "API_ERROR": APIError,
        "AUTHENTICATION_FAILED": AuthenticationError,
        "AUTHORIZATION_FAILED": AuthorizationError,
        "RATE_LIMIT_EXCEEDED": RateLimitError,
        # Validation errors
        "VALIDATION_FAILED": ValidationError,
        # Pod errors
        "POD_OFFLINE": PodOfflineError,
        "SYNC_FAILED": SyncError,
        # Outcome tracking errors
        "OUTCOME_TRACKING_FAILED": OutcomeTrackingError,
        # Notification errors
        "NOTIFICATION_FAILED": NotificationError,
        "DELIVERY_CHANNEL_FAILED": DeliveryChannelError,
    }

    # Get the exception class from the map, default to base AfriFlowError
    # if error code is not recognized
    error_class = error_map.get(error_code, AfriFlowError)
    return error_class(message, details)


# ============================================
# PUBLIC API
# ============================================
# Define what's exported when using 'from afriflow.exceptions import *'

__all__ = [
    # Base exception - parent of all custom exceptions
    "AfriFlowError",
    # Domain exceptions - business logic failures
    "EntityResolutionError",
    "SignalDetectionError",
    "CurrencyPropagationError",
    "SeasonalCalendarError",
    "BriefingGenerationError",
    "DataShadowError",
    "CorridorError",
    "LekgotlaError",
    # Data quality exceptions - validation and freshness failures
    "DataQualityError",
    "FreshnessError",
    "ContractViolationError",
    # Configuration exceptions - config loading failures
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
    # Ingestion exceptions - data pipeline failures
    "DataIngestionError",
    "SchemaEvolutionError",
    # Storage exceptions - database operation failures
    "StorageError",
    "ConnectionError",
    # API exceptions - HTTP operation failures
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    # Validation exceptions - input validation failures
    "ValidationError",
    # Pod exceptions - country pod infrastructure failures
    "PodError",
    "PodOfflineError",
    "SyncError",
    # Outcome tracking exceptions - signal outcome recording failures
    "OutcomeTrackingError",
    # Notification exceptions - alert delivery failures
    "NotificationError",
    "DeliveryChannelError",
    # Factory function - create exceptions from error codes
    "create_error_from_code",
]
