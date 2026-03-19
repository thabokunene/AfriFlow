"""
@file logging_config.py
@description Logging Configuration - Structured JSON logging for all AfriFlow modules
@author Thabo Kunene
@created 2026-03-19

This module provides centralized logging setup for all AfriFlow modules.
All logging uses structured JSON format for production observability
and log aggregation systems (e.g., ELK stack, Splunk, Datadog).

Key Features:
- JSONFormatter: Outputs logs as JSON lines for easy parsing
- ContextFilter: Adds correlation IDs, user IDs, session IDs, country codes
- setup_logging: Configures root logger with handlers and formatters
- get_logger: Convenience function for getting named loggers
- LoggingContext: Context manager for scoped logging context
- log_operation: Helper for consistent operation status logging

Usage:
    >>> from afriflow.logging_config import setup_logging, get_logger
    >>> setup_logging(level="DEBUG", json_format=True)
    >>> logger = get_logger("data_shadow")
    >>> logger.info("Processing client", extra={"client_id": "GLD-001"})

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

import logging  # Python's built-in logging module
import sys  # For stdout handler (console logging)
import json  # For JSON formatting of log entries
from typing import Optional, Dict, Any  # Type hints for optional, dict, and any types
from datetime import datetime  # For ISO 8601 timestamps
from pathlib import Path  # For cross-platform file path handling


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Each log entry is formatted as a JSON line with:
    - timestamp: ISO 8601 timestamp in UTC
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name (e.g., "afriflow.data_shadow")
    - message: Log message
    - module: Module name where log was called
    - function: Function name where log was called
    - line: Line number where log was called
    - extra: Additional fields from log record (e.g., client_id, country)

    This format is compatible with log aggregation systems like:
    - Elasticsearch/Logstash/Kibana (ELK)
    - Splunk
    - Datadog
    - Google Cloud Logging

    Example output:
        {"timestamp": "2026-03-19T10:30:00.000Z", "level": "INFO", "logger": "afriflow.data_shadow", "message": "Processing client", "module": "shadow_monitor", "function": "calculate", "line": 42, "client_id": "GLD-001"}
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: LogRecord object containing log event data

        Returns:
            JSON string representation of the log entry
        """
        # Build base log entry with standard fields
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC timestamp in ISO 8601 format
            "level": record.levelname,  # Log level name (INFO, ERROR, etc.)
            "logger": record.name,  # Logger name (e.g., "afriflow.data_shadow")
            "message": record.getMessage(),  # Formatted log message
            "module": record.module,  # Module name where log was called
            "function": record.funcName,  # Function name where log was called
            "line": record.lineno,  # Line number where log was called
        }

        # Add extra fields if present (e.g., client_id, country from extra={})
        # These are passed via logger.info("msg", extra={"key": "value"})
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Add exception info if present (for error logs with exc_info=True)
        # This includes full stack trace for debugging
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Convert to JSON string (single line for easy parsing)
        return json.dumps(log_entry)


class ContextFilter(logging.Filter):
    """
    Adds contextual information to log records.

    This filter adds:
    - correlation_id: For tracing requests across modules (e.g., "req-123")
    - user_id: User identifier if available (e.g., "user-456")
    - session_id: Session identifier if available (e.g., "sess-789")
    - country: Country code for federated operations (e.g., "ZA", "NG")

    These fields enable:
    - Request tracing across distributed systems
    - User-specific log filtering
    - Country-level log segmentation

    Usage:
        >>> with LoggingContext(correlation_id="req-123", country="ZA"):
        ...     logger.info("Processing request")
        # Output includes: {"correlation_id": "req-123", "country": "ZA"}
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """
        Initialize context filter with optional context values.

        Args:
            correlation_id: Unique ID for tracing requests across modules
            user_id: User identifier for user-specific logging
            session_id: Session identifier for session tracking
            country: Country code for federated operations (ISO 3166-1 alpha-2)
        """
        self.correlation_id = correlation_id  # Store correlation ID for request tracing
        self.user_id = user_id  # Store user ID for user-specific logging
        self.session_id = session_id  # Store session ID for session tracking
        self.country = country  # Store country code for federated logging

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context to log record.

        This method is called by the logging system for each log record.
        It adds context fields to the record's extra_fields attribute.

        Args:
            record: LogRecord object to add context to

        Returns:
            True to indicate the record should be logged
        """
        # Initialize extra_fields dictionary for context data
        record.extra_fields = {}

        # Add each context field if it has a value
        # These will be included in the JSON output by JSONFormatter
        if self.correlation_id:
            record.extra_fields["correlation_id"] = self.correlation_id
        if self.user_id:
            record.extra_fields["user_id"] = self.user_id
        if self.session_id:
            record.extra_fields["session_id"] = self.session_id
        if self.country:
            record.extra_fields["country"] = self.country

        return True  # Always allow the record to be logged


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    include_context: bool = True,
) -> None:
    """
    Configure structured logging for AfriFlow.

    This function sets up the root logger with:
    - Configured log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - JSON or plain text formatter
    - Console handler (stdout)
    - Optional file handler
    - Optional context filter

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               DEBUG shows all logs, INFO shows info and above, etc.
        json_format: If True, output JSON lines. If False, plain text.
                     JSON format is recommended for production.
        log_file: Optional file path to write logs to.
                  If None, logs only go to console.
        log_to_console: If True, log to stdout. Set to False for file-only logging.
        include_context: If True, add correlation/user/session context.
                        Enable for distributed tracing.

    Example:
        >>> setup_logging(level="DEBUG", json_format=True, log_file="logs/app.log")
        >>> logger = logging.getLogger("afriflow.data_shadow")
        >>> logger.info("Processing client", extra={
        ...     "client_id": "GLD-001",
        ...     "country": "NG"
        ... })
    """
    # Get root logger (applies to all loggers in the application)
    root_logger = logging.getLogger()
    # Set the logging level (controls which messages are processed)
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers to avoid duplicate log output
    # This is important if setup_logging is called multiple times
    root_logger.handlers = []

    # Create formatter based on json_format flag
    # JSON format for production, plain text for development/debugging
    if json_format:
        formatter = JSONFormatter()  # Use our custom JSON formatter
    else:
        # Use standard Python logging format for plain text output
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"  # Custom date format for readability
        )

    # Console handler - outputs logs to stdout
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler - outputs logs to a file
    if log_file:
        # Ensure directory exists before creating file handler
        # This prevents errors if log directory doesn't exist yet
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Add context filter to all handlers
    # This enables correlation IDs and other context to be added to logs
    if include_context:
        context_filter = ContextFilter()
        for handler in root_logger.handlers:
            handler.addFilter(context_filter)

    # Log startup message to confirm logging is configured
    # This helps verify the configuration in logs
    logger = logging.getLogger("afriflow")
    logger.info(
        f"AfriFlow logging initialized: level={level}, "
        f"json={json_format}, file={log_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This is a convenience function that returns a logger
    prefixed with 'afriflow' for consistent naming across
    all modules.

    Args:
        name: Logger name (will be prefixed with 'afriflow')
              Use module name for clarity (e.g., "data_shadow")

    Returns:
        Configured logger instance with afriflow prefix

    Example:
        >>> logger = get_logger("data_shadow")
        >>> logger.info("Processing started")
        # Logger name will be "afriflow.data_shadow"
    """
    # Prefix with 'afriflow.' for consistent naming
    # This makes it easy to filter logs by application
    return logging.getLogger(f"afriflow.{name}")


class LoggingContext:
    """
    Context manager for adding temporary context to logs.

    Use this to add correlation IDs, user IDs, or other
    context for a specific code block. The context is
    automatically removed when exiting the block.

    This is useful for:
    - Request tracing (add correlation_id for the request duration)
    - User session logging (add user_id for session duration)
    - Country-specific operations (add country for federated ops)

    Example:
        >>> with LoggingContext(correlation_id="req-123"):
        ...     logger.info("Processing request")
        # All logs in this block include correlation_id="req-123"
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """
        Initialize logging context with optional context values.

        Args:
            correlation_id: Unique ID for tracing requests across modules
            user_id: User identifier for user-specific logging
            session_id: Session identifier for session tracking
            country: Country code for federated operations
        """
        self.correlation_id = correlation_id  # Store correlation ID
        self.user_id = user_id  # Store user ID
        self.session_id = session_id  # Store session ID
        self.country = country  # Store country code
        self._old_filters: list = []  # Store old filters for restoration

    def __enter__(self) -> LoggingContext:
        """
        Add context filters to all handlers.

        This method is called when entering the 'with' block.
        It saves the current filters and adds the new context filter.

        Returns:
            Self (the context manager instance)
        """
        # Get root logger to access all handlers
        root_logger = logging.getLogger()
        # Create context filter with the provided context values
        context_filter = ContextFilter(
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            session_id=self.session_id,
            country=self.country,
        )

        # Save current filters for each handler (for restoration on exit)
        # Then add the new context filter to each handler
        for handler in root_logger.handlers:
            self._old_filters.append(handler.filters[:])  # Copy current filters
            handler.addFilter(context_filter)  # Add new context filter

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Remove context filters from all handlers.

        This method is called when exiting the 'with' block,
        even if an exception occurred. It restores the original
        filters to avoid context leakage between requests.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        # Get root logger to access all handlers
        root_logger = logging.getLogger()
        # Restore original filters for each handler
        # This removes the context filter we added in __enter__
        for i, handler in enumerate(root_logger.handlers):
            handler.filters = self._old_filters[i]


def log_operation(
    logger: logging.Logger,
    operation: str,
    status: str = "started",
    **kwargs: Any
) -> None:
    """
    Log an operation with standard fields.

    This provides consistent logging for operations across
    all modules. It logs operation name, status, and any
    additional context fields.

    Args:
        logger: Logger instance (from get_logger())
        operation: Operation name (e.g., "shadow_calculation")
        status: Operation status (started, completed, failed)
        **kwargs: Additional fields to log (e.g., client_id, country)

    Example:
        >>> logger = get_logger("data_shadow")
        >>> log_operation(logger, "shadow_calculation", "started",
        ...               client_id="GLD-001")
        >>> try:
        ...     # Do work
        ...     log_operation(logger, "shadow_calculation", "completed",
        ...                   client_id="GLD-001", gaps=3)
        ... except Exception as e:
        ...     log_operation(logger, "shadow_calculation", "failed",
        ...                   client_id="GLD-001", error=str(e))
    """
    # Build extra dictionary with operation metadata and additional fields
    extra = {
        "operation": operation,  # Name of the operation being logged
        "status": status,  # Current status (started/completed/failed)
        **kwargs  # Additional context fields (client_id, country, etc.)
    }

    # Log at appropriate level based on status
    # Failed operations log as ERROR, completed as INFO, started as DEBUG
    if status == "failed":
        logger.error(f"Operation {operation} failed", extra=extra)
    elif status == "completed":
        logger.info(f"Operation {operation} completed", extra=extra)
    else:
        logger.debug(f"Operation {operation} started", extra=extra)


# ============================================
# PUBLIC API
# ============================================
# Define what's exported when using 'from afriflow.logging_config import *'

__all__ = [
    # JSON formatter for structured logging
    "JSONFormatter",
    # Context filter for adding correlation IDs, user IDs, etc.
    "ContextFilter",
    # Main setup function for configuring logging
    "setup_logging",
    # Convenience function for getting named loggers
    "get_logger",
    # Context manager for scoped logging context
    "LoggingContext",
    # Helper for consistent operation logging
    "log_operation",
]
