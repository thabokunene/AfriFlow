"""
@file fx_enrichment.py
@description Spark-based processor for enriching FX trade records with client segmentation, risk weights, and regulatory flags.
@author Thabo Kunene
@created 2026-03-19
"""

"""
FX Enrichment (Forex, Spark-style).

We enrich FX trade records with:
1. Client segmentation data
2. Counterparty risk ratings
3. Regulatory reporting flags
4. P&L calculations

This processor implements security-hardened validation
with RBAC and structured logging.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Standard logging for operational observability and trade lifecycle tracking
import logging
# Type hinting for defining strong collection and functional contracts
from typing import Any, Dict, Optional

# BaseProcessor defines the core processing contract used across all AfriFlow domains
from afriflow.domains.shared.interfaces import BaseProcessor
# get_config provides environment-aware settings for security and operational constraints
from afriflow.domains.shared.config import get_config

# Initialize module-level logger for Forex enrichment events
logger = logging.getLogger(__name__)


# Client segment definitions based on transaction volume and institutional risk.
# These buckets are used to prioritize processing and apply appropriate risk weights.
CLIENT_SEGMENTS = {
    "tier_1_corporate": {"min_notional": 10_000_000, "risk_weight": 0.5},
    "tier_2_sme": {"min_notional": 1_000_000, "risk_weight": 0.8},
    "tier_3_retail": {"min_notional": 0, "risk_weight": 1.0},
    "fi_bank": {"min_notional": 50_000_000, "risk_weight": 0.3},
}

# Regulatory constraints for specific African currencies with capital controls.
# These thresholds trigger additional validation or reporting steps.
REGULATORY_CURRENCIES = {
    "NGN": {"requires_approval": True, "limit_usd": 5_000_000},
    "AOA": {"requires_approval": True, "limit_usd": 1_000_000},
    "ETB": {"requires_approval": True, "limit_usd": 500_000},
    "ZWL": {"requires_approval": True, "limit_usd": 100_000},
}


class Processor(BaseProcessor):
    """
    FX enrichment implementation of the BaseProcessor.
    Responsible for adding business context and risk metadata to raw trade data.
    
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
        # Set of mandatory fields required for valid FX trade enrichment
        self._required_fields = {
            "trade_id", "currency_pair", "base_amount",
            "rate", "client_id"
        }

        self.logger.info(
            f"FXEnrichment configured: env={env}, "
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

        # Validate numeric fields
        amount = record.get("base_amount")
        if amount is not None and (
            not isinstance(amount, (int, float)) or amount <= 0
        ):
            raise ValueError("base_amount must be a positive number")

        rate = record.get("rate")
        if rate is not None and (
            not isinstance(rate, (int, float)) or rate <= 0
        ):
            raise ValueError("rate must be a positive number")

        self.logger.debug(f"Record validation passed: {record.get('trade_id')}")

    def _get_client_segment(self, notional_usd: float) -> str:
        """Determine client segment based on notional."""
        for segment, config in sorted(
            CLIENT_SEGMENTS.items(),
            key=lambda x: x[1]["min_notional"],
            reverse=True,
        ):
            if notional_usd >= config["min_notional"]:
                return segment
        return "tier_3_retail"

    def _check_regulatory_flag(
        self,
        currency_pair: str,
        amount_usd: float,
    ) -> Dict[str, Any]:
        """Check if regulatory approval is required."""
        # Extract quote currency (second part of pair)
        parts = currency_pair.split("/")
        quote_currency = parts[1] if len(parts) > 1 else ""

        reg_info = REGULATORY_CURRENCIES.get(quote_currency, {})

        requires_approval = reg_info.get("requires_approval", False)
        limit = reg_info.get("limit_usd", float("inf"))

        exceeds_limit = amount_usd > limit if requires_approval else False

        return {
            "requires_regulatory_approval": requires_approval,
            "exceeds_regulatory_limit": exceeds_limit,
            "regulatory_limit_usd": limit,
        }

    def _calculate_quote_amount(
        self,
        base_amount: float,
        rate: float,
    ) -> float:
        """Calculate quote currency amount."""
        return round(base_amount * rate, 2)

    def process_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an FX trade enrichment request.

        Args:
            record: FX trade record

        Returns:
            Enriched record with segmentation and flags

        Raises:
            ValueError: If validation fails
            RuntimeError: If processing fails
        """
        try:
            self.validate(record)

            out = dict(record)

            base_amount = record.get("base_amount", 0)
            rate = record.get("rate", 1.0)
            currency_pair = record.get("currency_pair", "")

            # Calculate quote amount
            quote_amount = self._calculate_quote_amount(base_amount, rate)

            # Determine client segment
            client_segment = self._get_client_segment(base_amount)

            # Check regulatory flags
            reg_flags = self._check_regulatory_flag(currency_pair, base_amount)

            # Get risk weight
            risk_weight = CLIENT_SEGMENTS.get(
                client_segment, {"risk_weight": 1.0}
            )["risk_weight"]

            out["quote_amount"] = quote_amount
            out["client_segment"] = client_segment
            out["risk_weight"] = risk_weight
            out.update(reg_flags)
            out["processed"] = True

            self.logger.debug(
                f"FX enrichment: {record.get('trade_id')} "
                f"{currency_pair} {base_amount:,.0f} @ {rate} "
                f"segment={client_segment}"
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
                    "trade_id": record.get("trade_id"),
                },
            )
            raise RuntimeError(f"FX enrichment processing failed: {e}") from e
