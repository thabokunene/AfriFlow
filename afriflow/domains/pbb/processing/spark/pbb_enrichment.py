"""
@file pbb_enrichment.py
@description Spark-based enrichment processor for the PBB domain, enforcing
    RBAC-based security controls and validating batch record integrity for retail data.
@author Thabo Kunene
@created 2026-03-19
"""

# Standard logging for operational observability and audit trails
import logging
# BaseProcessor defines the standardized processing lifecycle used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    Enrichment processor for PBB records.
    Applies role-based access and size constraints before marking records as processed.
    
    Design intent:
    - Enforce environment-aware RBAC (Role-Based Access Control) for PBB data.
    - Limit payload size to maintain Spark executor stability.
    - Provide structured error logging for batch enrichment troubleshooting.
    """

    def configure(self, config=None) -> None:
        """
        Sets internal configuration such as allowed roles and record size limits.
        Staging and production environments have more restrictive access controls.
        
        :param config: Optional configuration override.
        """
        self.logger = logging.getLogger(__name__)
        # Fallback to global config if no specific config is provided
        env = (self.config.env if self.config else get_config().env)
        # Define allowed roles based on the operational environment (system/service only in prod)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        # Prevent oversized records from causing memory issues in batch Spark jobs
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validates the input record's type, security role, and mandatory fields.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the role associated with the record is not authorized.
        :raises ValueError: If the record is missing required fields or exceeds the size limit.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
            
        role = record.get("access_role")
        src = record.get("source")
        
        # Security check: verify the caller has the necessary permissions for the environment
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
            
        # Lineage check: source must be clearly identified for audit and data provenance
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
            
        # Payload safety check for Spark executor memory stability
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Synchronously processes and marks a PBB record after validation.
        
        :param record: The input record to process.
        :return: A copy of the record with a processing flag.
        :raises Exception: Re-raises any errors encountered during validation or processing.
        """
        try:
            self.validate(record)
            # Create a shallow copy for safe transformation
            out = dict(record)
            # Mark the record as successfully processed by this module
            out["processed"] = True
            return out
        except Exception as e:
            # Log failure with structured context for easier debugging
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
