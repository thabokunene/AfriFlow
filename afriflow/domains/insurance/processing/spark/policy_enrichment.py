"""
@file policy_enrichment.py
@description Insurance policy enrichment processor with RBAC and safe processed flagging
@author Thabo Kunene
@created 2026-03-17
"""
import logging
from afriflow.domains.shared.interfaces import BaseProcessor  # Shared processor base used across domains
from afriflow.domains.shared.config import get_config  # Environment-aware RBAC defaults


class Processor(BaseProcessor):
    """
    Validates policy records and marks them processed; no functional logic added.
    """
    def configure(self, config=None) -> None:
        """
        Set logger, allowed roles by environment, and payload size limits.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, role authorization, source presence, and size.
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
        Synchronously flag record as processed after validation; logs errors.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
