"""
@file parallel_market_monitor.py
@description Flink-based processor for monitoring divergence between official and parallel FX rates in African markets.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Parallel Market Monitor (Forex, Flink-style).

We monitor divergence between official and parallel
(street) FX rates for currencies with capital controls.

Parallel market premiums are key intelligence for:
1. NGN (Nigeria): Official vs black market Naira
2. AOA (Angola): Official vs rua rate
3. ETB (Ethiopia): Official vs street Birr
4. ZWL (Zimbabwe): Official vs USD cash rate

A widening premium signals:
- FX shortage in official market
- Anticipation of devaluation
- Capital flight pressure

This processor implements security-hardened validation
with RBAC and structured logging.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Standard logging for operational observability and economic anomaly detection
import logging
# Type hinting for defining strong collection and functional contracts
from typing import Any, Dict, Optional

# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config

# Initialize module-level logger for parallel market monitoring events
logger = logging.getLogger(__name__)


# List of ISO currency codes where parallel market activity is significant and monitored.
PARALLEL_MARKET_CURRENCIES = {"NGN", "AOA", "ETB", "ZWL", "CDF", "SSP"}

# Percentage thresholds used to classify the severity of parallel market premiums.
# A higher premium indicates greater economic stress or impending devaluation.
PREMIUM_THRESHOLDS = {
    "low": 5.0,
    "moderate": 15.0,
    "high": 30.0,
    "critical": 50.0,
}


class Processor(BaseProcessor):
    """
    Parallel market monitor implementation of the BaseProcessor.
    Calculates the premium between official and street rates to identify financial risk.
    
    Design intent:
    - Enforce environment-aware RBAC (Role-Based Access Control).
    - Limit payload size to maintain processing stability.
    - Track historical premiums for trend detection.
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
        # Set of mandatory fields required for valid parallel market analysis
        self._required_fields = {"currency", "official_rate", "parallel_rate"}

        # Internal state to track premium history for trend detection per currency
        self._premium_history: Dict[str, list] = {}

        self.logger.info(
            f"ParallelMarketMonitor configured: env={env}, "
            f"monitored_currencies={PARALLEL_MARKET_CURRENCIES}"
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

        # Validate rates are positive
        official = record.get("official_rate")
        parallel = record.get("parallel_rate")

        if official is not None and (
            not isinstance(official, (int, float)) or official <= 0
        ):
            raise ValueError("official_rate must be a positive number")

        if parallel is not None and (
            not isinstance(parallel, (int, float)) or parallel <= 0
        ):
            raise ValueError("parallel_rate must be a positive number")

        # Parallel rate should typically be >= official rate
        # (street rate is usually weaker)
        if parallel is not None and official is not None:
            if parallel < official * 0.9:
                self.logger.warning(
                    f"Unusual rate relationship: parallel ({parallel}) "
                    f"< official ({official})"
                )

        self.logger.debug(f"Record validation passed: {record.get('currency')}")

    def _calculate_premium(
        self,
        official_rate: float,
        parallel_rate: float,
    ) -> float:
        """
        Calculate parallel market premium percentage.

        Premium = (parallel - official) / official * 100
        """
        if official_rate <= 0:
            return 0.0

        return (parallel_rate - official_rate) / official_rate * 100

    def _get_premium_level(self, premium_pct: float) -> str:
        """Classify premium severity level."""
        if premium_pct >= PREMIUM_THRESHOLDS["critical"]:
            return "critical"
        elif premium_pct >= PREMIUM_THRESHOLDS["high"]:
            return "high"
        elif premium_pct >= PREMIUM_THRESHOLDS["moderate"]:
            return "moderate"
        elif premium_pct >= PREMIUM_THRESHOLDS["low"]:
            return "low"
        else:
            return "minimal"

    def _update_history(
        self,
        currency: str,
        premium_pct: float,
        timestamp: Optional[str] = None,
    ) -> None:
        """Update premium history for trend analysis."""
        if currency not in self._premium_history:
            self._premium_history[currency] = []

        self._premium_history[currency].append({
            "premium": premium_pct,
            "timestamp": timestamp,
        })

        # Keep only recent history (last 100 observations)
        if len(self._premium_history[currency]) > 100:
            self._premium_history[currency] = (
                self._premium_history[currency][-100:]
            )

    def _detect_trend(self, currency: str) -> Optional[str]:
        """Detect if premium is widening or narrowing."""
        history = self._premium_history.get(currency, [])

        if len(history) < 5:
            return None

        recent = [h["premium"] for h in history[-5:]]
        older = [h["premium"] for h in history[-10:-5]] if len(history) >= 10 else []

        if not older:
            return "stable"

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if recent_avg > older_avg * 1.1:
            return "widening"
        elif recent_avg < older_avg * 0.9:
            return "narrowing"
        else:
            return "stable"

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a parallel market monitoring request.

        Args:
            record: Rate record with official and parallel rates

        Returns:
            Processed record with premium analysis

        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        try:
            self.validate(record)

            out = dict(record)

            currency = record.get("currency")
            official_rate = record.get("official_rate", 0)
            parallel_rate = record.get("parallel_rate", 0)
            timestamp = record.get("timestamp")

            # Calculate premium
            premium_pct = self._calculate_premium(official_rate, parallel_rate)
            premium_level = self._get_premium_level(premium_pct)

            # Update history
            self._update_history(currency, premium_pct, timestamp)

            # Detect trend
            trend = self._detect_trend(currency)

            # Check if currency has parallel market
            has_parallel = currency in PARALLEL_MARKET_CURRENCIES

            out["parallel_premium_pct"] = round(premium_pct, 2)
            out["premium_level"] = premium_level
            out["premium_trend"] = trend
            out["has_parallel_market"] = has_parallel
            out["processed"] = True

            # Log alerts for high premiums
            if premium_level in ("high", "critical"):
                self.logger.warning(
                    f"Parallel market alert: {currency} "
                    f"premium={premium_pct:.1f}% level={premium_level} "
                    f"trend={trend or 'unknown'}"
                )
            else:
                self.logger.debug(
                    f"Parallel market: {currency} "
                    f"official={official_rate} parallel={parallel_rate} "
                    f"premium={premium_pct:.1f}%"
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
                    "currency": record.get("currency"),
                },
            )
            raise RuntimeError(f"Parallel market processing failed: {e}") from e
