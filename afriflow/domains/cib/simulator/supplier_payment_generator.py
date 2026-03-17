"""
Supplier Payment Generator

We generate realistic synthetic supplier payment records
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

from __future__ import annotations
import random
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional, Dict, Any

from afriflow.logging_config import get_logger
from afriflow.domains.shared.interfaces import SimulatorBase

logger = get_logger("domains.cib.simulator.supplier_payment_generator")


@dataclass
class SupplierPayment:
    """
    A single supplier payment record.

    We publish these to the CIB domain Kafka topic
    (cib.supplier_payments) in Avro format.
    """

    payment_id: str
    client_id: str
    supplier_id: str
    corridor: str
    currency: str
    amount: float
    timestamp: datetime
    purpose: Optional[str]


class SupplierPaymentGenerator(SimulatorBase):
    """
    We generate realistic synthetic supplier payments
    for testing and demo purposes.

    Usage:
        gen = SupplierPaymentGenerator(seed=42)
        payment = gen.generate_one(corridor="ZA-NG")
    """

    def initialize(self, config=None) -> None:
        """Initialize the generator with corridors and currencies."""
        self._corridors = ["ZA-NG", "NG-GH", "ZA-KE", "KE-TZ"]
        self._curr = {
            "ZA-NG": "USD",
            "NG-GH": "USD",
            "ZA-KE": "USD",
            "KE-TZ": "USD",
        }
        self._purposes = ["invoice", "advance", "freight", None]
        logger.info("SupplierPaymentGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validate input parameters.

        Raises:
            ValueError: If amount is not positive
        """
        amt = kwargs.get("amount")
        if amt is not None and amt <= 0:
            raise ValueError("amount must be positive")

        corridor = kwargs.get("corridor")
        if corridor is not None and corridor not in self._corridors:
            raise ValueError(f"Invalid corridor: {corridor}")

    def generate_one(self, **kwargs) -> SupplierPayment:
        """
        Generate a single supplier payment.

        Args:
            **kwargs: Optional overrides for corridor, client_id, supplier_id, amount

        Returns:
            SupplierPayment instance

        Raises:
            ValueError: If input validation fails
            RuntimeError: If generation fails
        """
        try:
            self.validate_input(**kwargs)

            corridor = kwargs.get("corridor") or random.choice(self._corridors)
            amount = kwargs.get("amount") or random.uniform(1000, 250000)

            payment = SupplierPayment(
                payment_id=str(uuid.uuid4()),
                client_id=kwargs.get("client_id") or f"CLIENT-{random.randint(1, 999):03d}",
                supplier_id=kwargs.get("supplier_id") or f"SUP-{random.randint(1, 999):03d}",
                corridor=corridor,
                currency=self._curr[corridor],
                amount=round(amount, 2),
                timestamp=datetime.now(timezone.utc),
                purpose=random.choice(self._purposes),
            )

            logger.debug(
                f"Generated supplier payment: {payment.payment_id[:8]}... "
                f"{corridor} {amount:.2f}"
            )

            return payment

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate supplier payment: {e}")
            raise RuntimeError(f"Payment generation failed: {e}") from e

    def stream(self, count: int = 1, **kwargs) -> Iterator[SupplierPayment]:
        """
        Stream supplier payments.

        Args:
            count: Number of payments to generate
            **kwargs: Passed to generate_one

        Yields:
            SupplierPayment instances
        """
        if count <= 0:
            logger.warning(f"Invalid stream count: {count}")
            return

        logger.info(f"Streaming {count} supplier payments")
        for _ in range(count):
            yield self.generate_one(**kwargs)

        logger.info(f"Streamed {count} supplier payments")
