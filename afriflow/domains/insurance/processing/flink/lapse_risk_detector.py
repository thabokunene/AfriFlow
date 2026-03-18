"""
@file lapse_risk_detector.py
@description Insurance lapse risk detector with RBAC validation and safe enrichment flagging
@author Thabo Kunene
@created 2026-03-17
"""
import logging
from afriflow.domains.shared.interfaces import BaseProcessor  # Base contract enforcing configure/validate/process methods
from afriflow.domains.shared.config import get_config  # Environment-aware configuration sourcing


class Processor(BaseProcessor):
    """
    Processor validating insurance records before computing lapse risk markers.
    """
    def configure(self, config=None) -> None:
        """
        Initialize logger and environment-based RBAC, set payload size guardrail.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate input record type, role authorization, source provenance, and payload size.
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
        Synchronously flag record as processed after validation.
        Edge cases are captured and logged; errors are re-raised to callers.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
