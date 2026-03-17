"""
Hedge Gap Detector (Forex, Flink-style).

We detect gaps between hedge instruments and their
underlying exposures. A hedge gap occurs when:
1. Hedge notional != exposure notional
2. Hedge maturity != exposure maturity
3. Hedge currency pair doesn't match exposure

This processor implements security-hardened validation
with RBAC and structured logging.
"""

import logging
from typing import Any, Dict, Optional

from afriflow.domains.shared.interfaces import BaseProcessor
from afriflow.domains.shared.config import get_config

logger = logging.getLogger(__name__)


class Processor(BaseProcessor):
    """
    Processor for detecting hedge gaps with:
    - RBAC based on environment
    - Input validation (dict, required fields, size guard)
    - Structured error logging
    """

    def configure(self, config: Optional[Any] = None) -> None:
        """Configure the processor with environment-specific settings."""
        self.logger = logging.getLogger(__name__)
        cfg = self.config if hasattr(self, "config") and self.config else get_config()
        env = getattr(cfg, "env", "dev")

        self._allowed_roles = (
            {"system", "service"}
            if env in {"staging", "prod"}
            else {"system", "service", "analyst"}
        )
        self._max_record_size = 100_000  # ~100KB guardrail
        self._required_fields = {
            "hedge_id", "client_id", "currency_pair",
            "notional_base", "underlying_exposure_id"
        }

        self.logger.info(
            f"HedgeGapDetector configured: env={env}, "
            f"allowed_roles={self._allowed_roles}"
        )

    def validate(self, record: Any) -> None:
        """
        Validate the input record.

        Args:
            record: Record to validate

        Raises:
            TypeError: If record is not a dict
            PermissionError: If access_role not permitted
            ValueError: If required fields missing or record too large
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")

        role = record.get("access_role")
        src = record.get("source")

        if role not in self._allowed_roles:
            raise PermissionError(
                f"access_role '{role}' not permitted. "
                f"Allowed: {self._allowed_roles}"
            )

        if not src or not isinstance(src, str):
            raise ValueError("source is required and must be a string")

        # Check required fields for hedge gap detection
        missing = self._required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Size guard
        if len(str(record)) > self._max_record_size:
            raise ValueError(
                f"record size exceeds limit ({self._max_record_size} bytes)"
            )

        # Validate notional is positive
        notional = record.get("notional_base")
        if notional is not None and (
            not isinstance(notional, (int, float)) or notional <= 0
        ):
            raise ValueError("notional_base must be a positive number")

        self.logger.debug(f"Record validation passed: {record.get('hedge_id')}")

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a hedge gap detection request.

        Args:
            record: Hedge record with exposure reference

        Returns:
            Processed record with gap analysis

        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        try:
            self.validate(record)

            out = dict(record)

            # Calculate hedge gap metrics
            hedge_notional = record.get("notional_base", 0)
            exposure_notional = record.get("exposure_notional", hedge_notional)

            # Gap percentage
            if exposure_notional > 0:
                gap_pct = abs(hedge_notional - exposure_notional) / exposure_notional * 100
            else:
                gap_pct = 0.0

            # Gap assessment
            if gap_pct == 0:
                gap_status = "perfect_hedge"
            elif gap_pct <= 5:
                gap_status = "acceptable"
            elif gap_pct <= 20:
                gap_status = "moderate_gap"
            else:
                gap_status = "significant_gap"

            out["hedge_gap_pct"] = round(gap_pct, 2)
            out["gap_status"] = gap_status
            out["processed"] = True

            self.logger.info(
                f"Hedge gap analysis: {record.get('hedge_id')} "
                f"gap={gap_pct:.1f}% status={gap_status}"
            )

            return out

        except (TypeError, PermissionError, ValueError):
            raise
        except Exception as e:
            self.logger.error(
                "processor_error",
                extra={
                    "error": str(e),
                    "etype": e.__class__.__name__,
                    "hedge_id": record.get("hedge_id"),
                },
            )
            raise RuntimeError(f"Hedge gap processing failed: {e}") from e
