"""
Client Profitability (CIB, Spark-style).

We add a minimal, security-hardened Processor stub to support downstream
Spark jobs calculating client profitability. This focuses on validation and
safe defaults while remaining a no-op for compatibility.
"""

import logging
from typing import Any, Dict

from afriflow.domains.shared.interfaces import BaseProcessor
from afriflow.domains.shared.config import get_config


class Processor(BaseProcessor):
    """
    Minimal Processor with RBAC and input validation.
    """

    def configure(self, config=None) -> None:
        self.logger = logging.getLogger(__name__)
        env = (self.config.env if getattr(self, "config", None) else get_config().env)
        self._allowed_roles = (
            {"system", "service"} if env in {"staging", "prod"} else {"system", "service", "analyst"}
        )
        self._max_record_size = 100_000

    def validate(self, record: Any) -> None:
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

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.validate(record)
            out = dict(record)
            out["processed"] = True
            return out
        except Exception as e:
            self.logger.error(
                "processor_error",
                extra={"error": str(e), "etype": e.__class__.__name__},
            )
            raise
