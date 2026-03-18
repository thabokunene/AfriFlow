"""
@file geographic_analytics.py
@description Cell geographic analytics processor with RBAC validation and safe processing flag
@author Thabo Kunene
@created 2026-03-17
"""
import logging
from afriflow.domains.shared.interfaces import BaseProcessor  # Base processor contract for configure/validate/process
from afriflow.domains.shared.config import get_config  # Environment-sensitive RBAC defaults


class Processor(BaseProcessor):
    """
    Validates cell usage/geo inputs and marks records processed after checks.
    """
    def configure(self, config=None) -> None:
        """
        Initialize logger, allowed roles by environment, and size guardrail.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, role authorization, source provenance, and payload size.
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
        Synchronously flag record as processed after validation, with error logging.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
