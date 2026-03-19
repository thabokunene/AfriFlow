"""
Logging Configuration

We provide centralized logging setup for all AfriFlow modules.
All logging uses structured JSON format for production
observability and log aggregation systems.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

import logging
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Each log entry is formatted as a JSON line with:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name
    - message: Log message
    - module: Module name
    - function: Function name
    - line: Line number
    - extra: Additional fields from log record
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class ContextFilter(logging.Filter):
    """
    Adds contextual information to log records.

    This filter adds:
    - correlation_id: For tracing requests across modules
    - user_id: User identifier if available
    - session_id: Session identifier if available
    - country: Country code for federated operations
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id
        self.country = country

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        record.extra_fields = {}

        if self.correlation_id:
            record.extra_fields["correlation_id"] = self.correlation_id
        if self.user_id:
            record.extra_fields["user_id"] = self.user_id
        if self.session_id:
            record.extra_fields["session_id"] = self.session_id
        if self.country:
            record.extra_fields["country"] = self.country

        return True


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    include_context: bool = True,
) -> None:
    """
    Configure structured logging for AfriFlow.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output JSON lines. If False, plain text.
        log_file: Optional file path to write logs to.
        log_to_console: If True, log to stdout.
        include_context: If True, add correlation/user/session context.

    Example:
        >>> setup_logging(level="DEBUG", json_format=True)
        >>> logger = logging.getLogger("afriflow.data_shadow")
        >>> logger.info("Processing client", extra={
        ...     "client_id": "GLD-001",
        ...     "country": "NG"
        ... })
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    root_logger.handlers = []

    # Create formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Add context filter
    if include_context:
        context_filter = ContextFilter()
        for handler in root_logger.handlers:
            handler.addFilter(context_filter)

    # Log startup message
    logger = logging.getLogger("afriflow")
    logger.info(
        f"AfriFlow logging initialized: level={level}, "
        f"json={json_format}, file={log_file}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This is a convenience function that returns a logger
    prefixed with 'afriflow' for consistent naming.

    Args:
        name: Logger name (will be prefixed with 'afriflow')

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger("data_shadow")
        >>> logger.info("Processing started")
    """
    return logging.getLogger(f"afriflow.{name}")


class LoggingContext:
    """
    Context manager for adding temporary context to logs.

    Use this to add correlation IDs, user IDs, or other
    context for a specific code block.

    Example:
        >>> with LoggingContext(correlation_id="req-123"):
        ...     logger.info("Processing request")
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.session_id = session_id
        self.country = country
        self._old_filters: list = []

    def __enter__(self) -> LoggingContext:
        """Add context filters to all handlers."""
        root_logger = logging.getLogger()
        context_filter = ContextFilter(
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            session_id=self.session_id,
            country=self.country,
        )

        for handler in root_logger.handlers:
            self._old_filters.append(handler.filters[:])
            handler.addFilter(context_filter)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Remove context filters from all handlers."""
        root_logger = logging.getLogger()
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
    all modules.

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "shadow_calculation")
        status: Operation status (started, completed, failed)
        **kwargs: Additional fields to log

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
    extra = {
        "operation": operation,
        "status": status,
        **kwargs
    }

    if status == "failed":
        logger.error(f"Operation {operation} failed", extra=extra)
    elif status == "completed":
        logger.info(f"Operation {operation} completed", extra=extra)
    else:
        logger.debug(f"Operation {operation} started", extra=extra)


__all__ = [
    "JSONFormatter",
    "ContextFilter",
    "setup_logging",
    "get_logger",
    "LoggingContext",
    "log_operation",
]
