"""
@file cell_enrichment.py
@description Spark-style enrichment wrapper with RBAC, input validation, and safe processing
@author Thabo Kunene
@created 2026-03-17
"""
import logging
# BaseProcessor defines the minimal processing lifecycle used across domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for RBAC and limits
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    Enrichment processor enforcing environment-aware RBAC, payload size limits,
    and structured error logging for synchronous processing paths.
    """
    def configure(self, config=None) -> None:
        """
        Set allowed roles and max payload size based on environment.
        Staging/prod environments restrict access to system/service roles.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, required fields, and role authorization.
        Raises TypeError, PermissionError, or ValueError on invalid input.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")
        role = record.get("access_role")
        src = record.get("source")
        if role not in self._allowed_roles:
            raise PermissionError("access_role not permitted")
        if not src or not isinstance(src, str):
            raise ValueError("source is required")
        if len(str(record)) > self._max_record_size:
            raise ValueError("record too large")

    def process_sync(self, record):
        """
        Process record synchronously with validation and error logging.
        Returns copy of input with 'processed' marker when successful.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
