"""
@file hedge_effectiveness.py
@description Spark-based processor for calculating FX hedge effectiveness metrics using dollar offset and other statistical methods.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Hedge Effectiveness (Forex, Spark-style).

We calculate hedge effectiveness metrics for accounting
and risk management purposes.

Hedge effectiveness measures how well a hedge offsets
the underlying exposure:

1. Dollar Offset Method: Hedge P&L / Exposure P&L
   - Most common for accounting (IFRS 9, ASC 815)
   - Effectiveness range: 80-125% is "highly effective"

2. Regression Method: R-squared of hedge vs exposure
   - Statistical measure of correlation
   - R² > 0.8 indicates good effectiveness

3. Variance Reduction: (1 - Var(hedged)/Var(unhedged))
   - Measures volatility reduction
   - 100% = perfect hedge

This processor implements security-hardened validation
with RBAC and structured logging.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Standard logging for operational observability and risk management auditing
import logging
# Type hinting for defining strong collection and functional contracts
from typing import Any, Dict, Optional

# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config

# Initialize module-level logger for hedge effectiveness events
logger = logging.getLogger(__name__)


# Hedge effectiveness thresholds based on international accounting standards (IFRS 9 / ASC 815).
# These ranges determine whether a hedge qualifies for hedge accounting treatment.
EFFECTIVENESS_THRESHOLDS = {
    "highly_effective": (80.0, 125.0),  # Accounting hedge qualification range
    "effective": (70.0, 140.0),          # Acceptable for internal risk management
    "partially_effective": (50.0, 200.0), # Achieves some offset but requires review
    "ineffective": (0.0, float("inf")),   # Poor offset; likely an ineffective hedge
}


class Processor(BaseProcessor):
    """
    Hedge effectiveness implementation of the BaseProcessor.
    Calculates the ratio of hedge P&L to exposure P&L to assess risk mitigation quality.
    
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
        # Prevent oversized records from causing memory issues in batch jobs
        self._max_record_size = 100_000
        # Set of mandatory fields required for valid hedge effectiveness analysis
        self._required_fields = {
            "hedge_id", "hedge_pnl", "exposure_pnl"
        }

        self.logger.info(
            f"HedgeEffectiveness configured: env={env}, "
            f"allowed_roles={self._allowed_roles}"
        )

    def validate(self, record: Any) -> None:
        """
        Validates the input record's type, security role, and mandatory fields.
        
        :param record: The record to be validated.
        :raises TypeError: If the record is not a dictionary.
        :raises PermissionError: If the access role is not authorized.
        :raises ValueError: If required fields are missing or the record is too large.
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

        if not src or not isinstance(src, str):
            raise ValueError("source is required and must be a string")

        # Check required fields
        missing = self._required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Size guard
        if len(str(record)) > self._max_record_size:
            raise ValueError(
                f"record size exceeds limit ({self._max_record_size} bytes)"
            )

        # Validate P&L fields are numeric
        hedge_pnl = record.get("hedge_pnl")
        exposure_pnl = record.get("exposure_pnl")

        if hedge_pnl is not None and not isinstance(hedge_pnl, (int, float)):
            raise ValueError("hedge_pnl must be a number")

        if exposure_pnl is not None and not isinstance(exposure_pnl, (int, float)):
            raise ValueError("exposure_pnl must be a number")

        self.logger.debug(f"Record validation passed: {record.get('hedge_id')}")

    def _calculate_effectiveness(
        self,
        hedge_pnl: float,
        exposure_pnl: float,
    ) -> Optional[float]:
        """
        Calculate hedge effectiveness using dollar offset method.

        Effectiveness = Hedge P&L / Exposure P&L * 100

        Note: Exposure P&L is typically opposite sign to Hedge P&L
        for an effective hedge (one gains while other loses).
        """
        if exposure_pnl == 0:
            # No exposure movement - can't calculate effectiveness
            return None

        # For accounting purposes, we want hedge and exposure
        # to move in opposite directions
        # If exposure loses value (negative), hedge should gain (positive)
        effectiveness = (hedge_pnl / -exposure_pnl) * 100

        return round(effectiveness, 2)

    def _get_effectiveness_level(self, effectiveness: float) -> str:
        """Classify effectiveness level based on thresholds."""
        for level, (min_eff, max_eff) in EFFECTIVENESS_THRESHOLDS.items():
            if min_eff <= effectiveness <= max_eff:
                return level

        # Handle edge cases (negative effectiveness, etc.)
        if effectiveness < 0:
            return "counterproductive"  # Hedge makes it worse
        return "ineffective"

    def _calculate_ineffectiveness(
        self,
        effectiveness: float,
    ) -> float:
        """
        Calculate hedge ineffectiveness for P&L recognition.

        Under IFRS 9, ineffectiveness is recognized in P&L.
        Ineffectiveness = |100% - effectiveness|
        """
        return round(abs(100.0 - effectiveness), 2)

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a hedge effectiveness calculation request.

        Args:
            record: Hedge record with P&L data

        Returns:
            Processed record with effectiveness metrics

        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        try:
            self.validate(record)

            out = dict(record)

            hedge_pnl = record.get("hedge_pnl", 0)
            exposure_pnl = record.get("exposure_pnl", 0)

            # Calculate effectiveness
            effectiveness = self._calculate_effectiveness(hedge_pnl, exposure_pnl)

            if effectiveness is not None:
                effectiveness_level = self._get_effectiveness_level(effectiveness)
                ineffectiveness = self._calculate_ineffectiveness(effectiveness)

                out["hedge_effectiveness_pct"] = effectiveness
                out["effectiveness_level"] = effectiveness_level
                out["ineffectiveness_pct"] = ineffectiveness

                # Accounting flag (80-125% = highly effective for hedge accounting)
                out["qualifies_for_hedge_accounting"] = (
                    80.0 <= effectiveness <= 125.0
                )

                self.logger.info(
                    f"Hedge effectiveness: {record.get('hedge_id')} "
                    f"effectiveness={effectiveness:.1f}% "
                    f"level={effectiveness_level} "
                    f"qualifies={out['qualifies_for_hedge_accounting']}"
                )
            else:
                out["hedge_effectiveness_pct"] = None
                out["effectiveness_level"] = "undefined"
                out["ineffectiveness_pct"] = None
                out["qualifies_for_hedge_accounting"] = False

                self.logger.debug(
                    f"Hedge effectiveness undefined (no exposure movement): "
                    f"{record.get('hedge_id')}"
                )

            out["processed"] = True

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
            raise RuntimeError(f"Hedge effectiveness processing failed: {e}") from e
