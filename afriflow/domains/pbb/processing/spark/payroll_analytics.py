"""
@file payroll_analytics.py
@description Payroll analytics processor enforcing RBAC validation and safe synchronous processing
@author Thabo Kunene
@created 2026-03-17
"""
import logging
from afriflow.domains.shared.interfaces import BaseProcessor  # Shared processor base with configure/validate/process methods
from afriflow.domains.shared.config import get_config  # Global config for environment-aware RBAC


class Processor(BaseProcessor):
    """
    Validates payroll analytics inputs and marks records processed after checks.
    """
    def configure(self, config=None) -> None:
        """
        Configure logger, allowed roles based on environment, and payload size limit.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, role-based access, source attribution, and size constraints.
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
        Synchronously process validated records and add a processed flag.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
