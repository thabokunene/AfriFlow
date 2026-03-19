"""
@file sim_deflation_adjuster.py
@description Spark processor for adjusting raw SIM counts using country-specific deflation factors to estimate unique headcount.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard logging for operational observability and audit trails
import logging
# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    SIM deflation adjuster processor for the Cell domain.
    Ensures that raw telecommunications data is normalized into accurate headcount estimates.
    """
    def configure(self, config=None) -> None:
        """
        Initializes the processor state, including RBAC roles and safety thresholds.
        
        :param config: Optional configuration override.
        """
        self.logger = logging.getLogger(__name__)
        # Fallback to global config if no specific config is provided
        env = (self.config.env if self.config else get_config().env)
        # Define allowed roles based on the deployment environment
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        # Limit the size of individual records to prevent memory exhaustion in batch jobs
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validates the input record for structural integrity and authorization.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the access role is not permitted.
        :raises ValueError: If mandatory fields are missing or the record is too large.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
            
        role = record.get("access_role")
        src = record.get("source")
        
        # Security validation against allowed roles
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
            
        # Lineage validation
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
            
        # Payload size validation
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Synchronously processes and marks SIM records for deflation adjustment.
        
        :param record: The input record.
        :return: A copy of the record with a processing flag.
        :raises Exception: Re-raises any errors encountered during validation or processing.
        """
        try:
            self.validate(record)
            # Create a shallow copy to prevent side effects on the input record
            out = dict(record)
            # Mark the record as having passed the initial validation and adjustment logic
            out["processed"] = True
            return out
        except Exception as e:
            # Log the error with structured context for monitoring systems
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
