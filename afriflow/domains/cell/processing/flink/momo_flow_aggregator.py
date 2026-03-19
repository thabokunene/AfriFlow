"""
@file momo_flow_aggregator.py
@description Flink-based processor for aggregating Mobile Money (MoMo) transaction flows.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard logging for operational observability
import logging
# BaseProcessor defines the minimal processing interface used across domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config loads environment-aware settings to enforce RBAC and limits
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    MoMo flow aggregator implementation of the BaseProcessor.
    Handles validation and enrichment of mobile money flow records.
    """
    def configure(self, config=None) -> None:
        """
        Sets internal limits and roles based on the environment.
        
        :param config: Optional configuration override.
        """
        self.logger = logging.getLogger(__name__)
        # Determine current environment to set security posture
        env = (self.config.env if self.config else get_config().env)
        # Stricter roles in production environments
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        # Limit record size to prevent OOM in stream processing
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Enforces structural and security constraints on input records.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the access role is not authorized.
        :raises ValueError: If mandatory fields are missing or the record is too large.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
        
        role = record.get("access_role")
        src = record.get("source")
        
        # Verify that the providing service has the correct permissions
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
        
        # Source must be present for lineage tracking
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
            
        # Security check to prevent memory overflow attacks
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Synchronously processes and enriches a MoMo record.
        
        :param record: The input record.
        :return: The enriched record with a 'processed' flag.
        :raises Exception: Re-raises any validation or processing errors.
        """
        try:
            self.validate(record)
            # Create a shallow copy to avoid mutating the original input
            out = dict(record)
            # Mark the record as successfully processed by this module
            out["processed"] = True
            return out
        except Exception as e:
            # Log failure with structured context for easier debugging
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
