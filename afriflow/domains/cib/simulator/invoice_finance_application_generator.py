"""
@file invoice_finance_application_generator.py
@description Generator for synthetic CIB invoice finance applications, supporting trade finance and supply chain simulations.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Invoice Finance Application Generator

We generate realistic synthetic invoice finance applications
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# Random library for stochastic event generation
import random
# Standard logging for operational observability and audit trails
import logging
# Dataclass for structured representation of invoice finance applications
from dataclasses import dataclass
# Datetime utilities for timestamping generated applications
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, List, Optional

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the invoice finance application generator namespace
logger = get_logger("domains.cib.simulator.invoice_finance_application_generator")


@dataclass
class InvoiceFinanceApplication:
    """
    A single invoice finance application record.
    Represents a corporate request for short-term liquidity backed by an outstanding invoice.

    Attributes:
        application_id: Unique identifier for the finance request.
        client_id: Identifier of the corporate client making the request.
        invoice_amount: The face value of the invoice to be financed.
        currency: ISO currency code of the invoice.
        timestamp: The precise timestamp when the application was submitted.
        tenor_days: The requested duration of the financing in days.
    """

    application_id: str
    client_id: str
    invoice_amount: float
    currency: str
    timestamp: datetime
    tenor_days: int


class InvoiceFinanceApplicationGenerator(SimulatorBase):
    """
    Generator for realistic synthetic invoice finance applications.
    Useful for testing credit models, supply chain finance pipelines, and dashboards.

    Usage:
        gen = InvoiceFinanceApplicationGenerator()
        app = gen.generate_one(currency="USD")
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with a list of supported currencies for trade finance.
        
        :param config: Optional configuration object.
        """
        # Supported currencies for CIB trade and invoice finance products.
        self._curr = ["USD", "ZAR", "NGN", "KES", "GHS", "EUR", "GBP"]
        logger.info("InvoiceFinanceApplicationGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before application generation.

        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the currency format is invalid or metrics are out of range.
        """
        # Validate currency code format (must be 3-letter ISO code).
        currency = kwargs.get("currency")
        if currency is not None:
            if not isinstance(currency, str) or len(currency) != 3:
                raise ValueError(f"Invalid currency format: {currency}")

        # Guard against invalid or zero-value invoice amounts.
        amount = kwargs.get("invoice_amount")
        if amount is not None:
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ValueError("invoice_amount must be a positive number")

        # Ensure the tenor is within standard corporate banking limits.
        tenor = kwargs.get("tenor_days")
        if tenor is not None:
            if not isinstance(tenor, int) or tenor < 1 or tenor > 365:
                raise ValueError("tenor_days must be between 1 and 365")

    def generate_one(self, **kwargs) -> InvoiceFinanceApplication:
        """
        Generates a single synthetic invoice finance application.

        :param kwargs: Optional overrides for currency, invoice_amount, and tenor_days.
        :return: An InvoiceFinanceApplication instance.
        :raises ValueError: If input validation fails.
        :raises RuntimeError: If generation fails due to unexpected errors.
        """
        try:
            self.validate_input(**kwargs)

            # Use provided values or generate random ones within realistic ranges.
            currency = kwargs.get("currency") or random.choice(self._curr)
            amount = kwargs.get("invoice_amount") or round(
                random.uniform(5000, 5_000_000), 2
            )
            tenor = kwargs.get("tenor_days") or random.randint(15, 120)

            app = InvoiceFinanceApplication(
                application_id=f"IF-{random.randint(100000, 999999)}",
                client_id=f"CLIENT-{random.randint(100, 999)}",
                invoice_amount=amount,
                currency=currency,
                timestamp=datetime.now(timezone.utc),
                tenor_days=tenor,
            )

            logger.debug(
                f"Generated invoice finance app: {app.application_id} "
                f"{amount:.2f} {currency} ({tenor} days)"
            )

            return app

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate invoice finance application: {e}")
            raise RuntimeError(f"Application generation failed: {e}") from e

    def stream(self, count: int = 1, **kwargs) -> Iterator[InvoiceFinanceApplication]:
        """
        Stream invoice finance applications.

        Args:
            count: Number of applications to generate
            **kwargs: Passed to generate_one

        Yields:
            InvoiceFinanceApplication instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} invoice finance applications")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} invoice finance applications")
