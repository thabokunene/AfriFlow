"""
@file rate_anomaly_detector.py
@description Flink-based processor for detecting anomalous FX rate movements using statistical Z-score analysis.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Rate Anomaly Detector (Forex, Flink-style).

We detect anomalous FX rate movements that may indicate:
1. Flash crashes or spikes
2. Fat-finger trades
3. Market manipulation
4. Data quality issues

This processor implements security-hardened validation
with RBAC, statistical anomaly detection, and structured logging.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Standard logging for operational observability and market integrity monitoring
import logging
# Statistics library for calculating Z-scores based on historical price data
import statistics
# Type hinting for defining strong collection and functional contracts
from typing import Any, Dict, List, Optional

# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config

# Initialize module-level logger for rate anomaly detection events
logger = logging.getLogger(__name__)


class Processor(BaseProcessor):
    """
    Rate anomaly detector implementation of the BaseProcessor.
    Uses rolling Z-score analysis to identify price points that deviate significantly from the mean.
    
    Design intent:
    - Enforce environment-aware RBAC (Role-Based Access Control).
    - Limit payload size to maintain processing stability.
    - Maintain historical rate windows for statistical baseline calculation.
    - Provide structured error logging for troubleshooting.
    """

    # Default statistical thresholds for anomaly classification.
    DEFAULT_ZSCORE_THRESHOLD = 3.0
    # Minimum number of data points required before a baseline is considered reliable.
    MIN_HISTORY_SIZE = 10

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
        # Set of mandatory fields required for valid rate anomaly analysis
        self._required_fields = {"currency_pair", "rate", "timestamp"}
        self._zscore_threshold = self.DEFAULT_ZSCORE_THRESHOLD

        # Internal state to track historical rates per currency pair for Z-score calculation
        self._rate_history: Dict[str, List[float]] = {}

        self.logger.info(
            f"RateAnomalyDetector configured: env={env}, "
            f"zscore_threshold={self._zscore_threshold}"
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

        # Lineage check: source must be clearly identified
        if not src or not isinstance(src, str):
            raise ValueError("source is required and must be a string")

        # Structural check: ensure all mandatory fields for anomaly detection are present
        missing = self._required_fields - set(record.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Payload safety check
        if len(str(record)) > self._max_record_size:
            raise ValueError(
                f"record size exceeds limit ({self._max_record_size} bytes)"
            )

        # Validate rate is positive
        rate = record.get("rate")
        if rate is not None and (
            not isinstance(rate, (int, float)) or rate <= 0
        ):
            raise ValueError("rate must be a positive number")

        self.logger.debug(
            f"Record validation passed: {record.get('currency_pair')}"
        )

    def _update_history(self, currency_pair: str, rate: float) -> None:
        """Update rate history for a currency pair."""
        if currency_pair not in self._rate_history:
            self._rate_history[currency_pair] = []

        self._rate_history[currency_pair].append(rate)

        # Keep only recent history (last 1000 observations)
        if len(self._rate_history[currency_pair]) > 1000:
            self._rate_history[currency_pair] = (
                self._rate_history[currency_pair][-1000:]
            )

    def _calculate_zscore(
        self,
        currency_pair: str,
        rate: float,
    ) -> Optional[float]:
        """
        Calculate Z-score for the current rate.

        Returns None if insufficient history.
        """
        history = self._rate_history.get(currency_pair, [])

        if len(history) < self.MIN_HISTORY_SIZE:
            return None

        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0

        if stdev == 0:
            return 0.0

        return (rate - mean) / stdev

    def _detect_anomaly_type(self, zscore: float) -> str:
        """Classify the type of anomaly based on Z-score."""
        abs_z = abs(zscore)

        if abs_z >= 5.0:
            return "extreme_spike"
        elif abs_z >= 4.0:
            return "severe_spike"
        elif abs_z >= 3.0:
            return "moderate_spike"
        elif abs_z >= 2.5:
            return "mild_spike"
        else:
            return "normal"

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a rate anomaly detection request.

        Args:
            record: Rate tick record

        Returns:
            Processed record with anomaly analysis

        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        try:
            self.validate(record)

            out = dict(record)

            currency_pair = record.get("currency_pair")
            rate = record.get("rate")

            # Update history first
            self._update_history(currency_pair, rate)

            # Calculate Z-score
            zscore = self._calculate_zscore(currency_pair, rate)

            if zscore is not None:
                anomaly_type = self._detect_anomaly_type(zscore)
                is_anomaly = abs(zscore) >= self._zscore_threshold

                out["zscore"] = round(zscore, 3)
                out["anomaly_type"] = anomaly_type
                out["is_anomaly"] = is_anomaly

                if is_anomaly:
                    self.logger.warning(
                        f"Rate anomaly detected: {currency_pair} "
                        f"rate={rate} zscore={zscore:.2f} type={anomaly_type}"
                    )
                else:
                    self.logger.debug(
                        f"Rate normal: {currency_pair} "
                        f"rate={rate} zscore={zscore:.2f}"
                    )
            else:
                out["zscore"] = None
                out["anomaly_type"] = "insufficient_history"
                out["is_anomaly"] = False

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
                    "currency_pair": record.get("currency_pair"),
                },
            )
            raise RuntimeError(f"Rate anomaly processing failed: {e}") from e
