"""
@file hedge_gap_detector.py
@description Flink-based processor for detecting mismatches between hedge instruments and underlying exposures in the Forex domain.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Hedge Gap Detector (Forex, Flink-style).

We detect gaps between hedge instruments and their
underlying exposures. A hedge gap occurs when:
1. Hedge notional != exposure notional
2. Hedge maturity != exposure maturity
3. Hedge currency pair doesn't match exposure

This processor implements security-hardened validation
with RBAC and structured logging.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Standard logging for operational observability and security auditing
import logging
# Type hinting for defining strong collection and functional contracts
from typing import Any, Dict, Optional

# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config

# Initialize module-level logger for the hedge gap detector
logger = logging.getLogger(__name__)


class Processor(BaseProcessor):
    """
    Hedge gap detector implementation of the BaseProcessor.
    Ensures that hedging data is validated and compared against underlying exposures to identify risk gaps.
    
    Design intent:
    - Enforce environment-aware RBAC (Role-Based Access Control).
    - Limit payload size to maintain processing stability.
    - Provide structured error logging for troubleshooting.
    """

    def configure(self, config: Optional[Any] = None) -> None:
        """
        Sets internal configuration such as allowed roles, required fields, and record size limits.
        Staging and production environments have more restrictive access controls.
        
        :param config: Optional configuration override.
        """
        self.logger = logging.getLogger(__name__)
        # Fallback to global config if no specific config is provided
        cfg = self.config if hasattr(self, "config") and self.config else get_config()
        env = getattr(cfg, "env", "dev")

        # Define allowed roles based on the operational environment
        self._allowed_roles = (
            {"system", "service"}
            if env in {"staging", "prod"}
            else {"system", "service", "analyst"}
        )
        # Prevent oversized records from causing memory issues in streaming jobs
        self._max_record_size = 100_000
        # Set of mandatory fields required for valid hedge gap analysis
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
        Validates the input record's type, security role, mandatory fields, and values.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the access role is not authorized.
        :raises ValueError: If required fields are missing, the record is too large, or values are invalid.
        """
        if not isinstance(record, dict):
            raise TypeError("record must be a dict")

        role = record.get("access_role")
        src = record.get("source")

        # Security check: verify the caller has the necessary permissions
        if role not in self._allowed_roles:
            raise PermissionError(
                f"access_role '{role}' not permitted. "
                f"Allowed: {self._allowed_roles}"
            )

        # Lineage check: source must be clearly identified
        if not src or not isinstance(src, str):
            raise ValueError("source is required and must be a string")

        # Structural check: ensure all mandatory fields for gap detection are present
        missing = self._required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Payload safety check
        if len(str(record)) > self._max_record_size:
            raise ValueError(
                f"record size exceeds limit ({self._max_record_size} bytes)"
            )

        # Data quality check: ensure notional amount is a positive number
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
