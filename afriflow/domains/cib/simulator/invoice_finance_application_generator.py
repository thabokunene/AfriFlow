"""
Invoice Finance Application Generator

We generate realistic synthetic invoice finance applications
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

from __future__ import annotations
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, List, Optional

from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.cib.simulator.invoice_finance_application_generator")


@dataclass
class InvoiceFinanceApplication:
    """
    A single invoice finance application record.

    We publish these to the CIB domain Kafka topic
    (cib.invoice_finance.applications) for processing.
    """

    application_id: str
    client_id: str
    invoice_amount: float
    currency: str
    timestamp: datetime
    tenor_days: int


class InvoiceFinanceApplicationGenerator(SimulatorBase):
    """
    We generate realistic synthetic invoice finance applications
    for testing and demo purposes.

    Usage:
        gen = InvoiceFinanceApplicationGenerator(seed=42)
        app = gen.generate_one(currency="USD")
    """

    def initialize(self, config=None) -> None:
        """Initialize the generator with currencies."""
        self._curr = ["USD", "ZAR", "NGN", "KES", "GHS", "EUR", "GBP"]
        logger.info("InvoiceFinanceApplicationGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If currency is invalid or amount is malformed
        """
        currency = kwargs.get("currency")
        if currency is not None:
            if not isinstance(currency, str) or len(currency) != 3:
                raise ValueError(f"Invalid currency format: {currency}")

        amount = kwargs.get("invoice_amount")
        if amount is not None:
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ValueError("invoice_amount must be a positive number")

        tenor = kwargs.get("tenor_days")
        if tenor is not None:
            if not isinstance(tenor, int) or tenor < 1 or tenor > 365:
                raise ValueError("tenor_days must be between 1 and 365")

    def generate_one(self, **kwargs) -> InvoiceFinanceApplication:
        """
        Generate a single invoice finance application.

        Args:
            **kwargs: Optional overrides for currency, invoice_amount, tenor_days

        Returns:
            InvoiceFinanceApplication instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

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
