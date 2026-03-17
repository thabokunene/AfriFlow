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


class AfriFlowError(Exception):
    """
    Base exception for all AfriFlow errors.

    All custom exceptions inherit from this base class
    to enable unified error handling across the platform.
    """

    def __init__(
        self,
        message: str,
        details: dict | None = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


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


class DataQualityError(AfriFlowError):
    """
    Data quality validation failed.

    Raised when data quality checks fail such as schema
    validation errors, completeness threshold violations,
    or consistency check failures.
    """

    pass


class ConfigurationError(AfriFlowError):
    """
    Configuration loading or validation failed.

    Raised when configuration management encounters errors
    such as missing config files, invalid config values,
    or config schema validation failures.
    """

    pass


class DataIngestionError(AfriFlowError):
    """
    Data ingestion failed.

    Raised when data ingestion encounters errors such as
    source connection failures, schema mismatches, or
    data transformation failures.
    """

    pass


class StorageError(AfriFlowError):
    """
    Data storage operation failed.

    Raised when storage operations encounter errors such
    as write failures, partition errors, or Delta Lake
    transaction failures.
    """

    pass


class APIError(AfriFlowError):
    """
    API operation failed.

    Raised when API operations encounter errors such as
    authentication failures, rate limiting, or invalid
    request/response formats.
    """

    pass


class ValidationError(AfriFlowError):
    """
    Input validation failed.

    Raised when input validation encounters errors such
    as missing required fields, invalid field values,
    or type mismatches.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        details: dict | None = None
    ):
        self.field = field
        self.value = value
        super().__init__(message, details)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging."""
        result = super().to_dict()
        result["field"] = self.field
        result["value"] = self.value
        return result
