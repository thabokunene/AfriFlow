"""
@file rate_anomaly_detector.py
@description Detects FX rate anomalies using Z-score; RBAC and structured logging included
@author Thabo Kunene
@created 2026-03-17
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
"""

import logging
import statistics
from typing import Any, Dict, List, Optional

from afriflow.domains.shared.interfaces import BaseProcessor
from afriflow.domains.shared.config import get_config

logger = logging.getLogger(__name__)


class Processor(BaseProcessor):
    """
    Processor for detecting FX rate anomalies with:
    - RBAC based on environment
    - Input validation (dict, required fields, size guard)
    - Statistical anomaly detection (Z-score based)
    - Structured error logging
    """

    # Anomaly detection thresholds
    DEFAULT_ZSCORE_THRESHOLD = 3.0
    MIN_HISTORY_SIZE = 10

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
        self._required_fields = {"currency_pair", "rate", "timestamp"}
        self._zscore_threshold = self.DEFAULT_ZSCORE_THRESHOLD

        # Rate history for Z-score calculation
        self._rate_history: Dict[str, List[float]] = {}

        self.logger.info(
            f"RateAnomalyDetector configured: env={env}, "
            f"zscore_threshold={self._zscore_threshold}"
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
