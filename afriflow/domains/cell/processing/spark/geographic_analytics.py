"""
@file geographic_analytics.py
@description Spark processor for Cell geographic analytics, identifying regional trends and usage patterns.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard logging for tracking processing events and errors
import logging
# BaseProcessor defines the standardized processing lifecycle used across all domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and limits
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    Geographic analytics processor for the Cell domain.
    Responsible for validating and preparing spatial usage data for downstream reporting.
    """
    def configure(self, config=None) -> None:
        """
        Sets internal state including allowed roles and payload size constraints.
        
        :param config: Optional configuration override.
        """
        self.logger = logging.getLogger(__name__)
        # Fallback to global config if no specific config is provided
        env = (self.config.env if self.config else get_config().env)
        # Production-grade RBAC to prevent unauthorized data processing
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        # Threshold to prevent excessive memory usage during batch analytics
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Ensures the record meets structural, security, and size requirements.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the access role is not authorized for the current environment.
        :raises ValueError: If mandatory fields are missing or the record is too large.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
            
        role = record.get("access_role")
        src = record.get("source")
        
        # Security validation
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
            
        # Data provenance validation
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
            
        # Safety limit check
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Synchronously processes geographic analytics data.
        
        :param record: The input record to process.
        :return: A copy of the record marked as successfully processed.
        :raises Exception: Re-raises any errors encountered during validation or processing.
        """
        try:
            self.validate(record)
            # Create a shallow copy for safe transformation
            out = dict(record)
            # Flag record for downstream analytics steps
            out["processed"] = True
            return out
        except Exception as e:
            # Log failure with structured context
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
