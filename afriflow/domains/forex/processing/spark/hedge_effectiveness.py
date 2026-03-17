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
"""

import logging
from typing import Any, Dict, Optional

from afriflow.domains.shared.interfaces import BaseProcessor
from afriflow.domains.shared.config import get_config

logger = logging.getLogger(__name__)


# Hedge effectiveness thresholds (IFRS 9 / ASC 815)
EFFECTIVENESS_THRESHOLDS = {
    "highly_effective": (80.0, 125.0),  # Accounting hedge qualification
    "effective": (70.0, 140.0),          # Good risk management
    "partially_effective": (50.0, 200.0), # Some offset achieved
    "ineffective": (0.0, float("inf")),   # Poor or no offset
}


class Processor(BaseProcessor):
    """
    Processor for hedge effectiveness calculation with:
    - RBAC based on environment
    - Input validation (dict, required fields, size guard)
    - Effectiveness calculation (dollar offset method)
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
        self._max_record_size = 100_000
        self._required_fields = {
            "hedge_id", "hedge_pnl", "exposure_pnl"
        }

        self.logger.info(
            f"HedgeEffectiveness configured: env={env}, "
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
