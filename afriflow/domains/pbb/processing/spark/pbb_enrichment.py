"""
@file pbb_enrichment.py
@description PBB enrichment processor with environment-aware RBAC and payload size controls
@author Thabo Kunene
@created 2026-03-17
"""
import logging
from afriflow.domains.shared.interfaces import BaseProcessor  # Base interface defining configure/validate/process contracts
from afriflow.domains.shared.config import get_config  # Global config loader to infer environment for RBAC


class Processor(BaseProcessor):
    """
    Enrichment processor for PBB records.
    Applies role-based access and size constraints before marking records as processed.
    """
    def configure(self, config=None) -> None:
        """
        Set internal logger, allowed roles by environment, and max record size.
        Staging/prod restrict to system/service roles to prevent analyst misuse.
        """
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if self.config else get_config().env)
        self._allowed_roles = {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        self._max_record_size = 100_000

    def validate(self, record) -> None:
        """
        Validate record type, access authorization, provenance source, and payload size.
        Raises:
        - TypeError for non-dict record
        - PermissionError for unauthorized role
        - ValueError for missing/invalid source or oversized record
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
        Synchronous enrichment path.
        Copies the record and flags it as processed after validation.
        """
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error("processor_error", extra={"error": str(e), "etype": e.__class__.__name__})
            raise
