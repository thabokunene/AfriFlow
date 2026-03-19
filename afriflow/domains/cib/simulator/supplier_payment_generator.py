"""
@file supplier_payment_generator.py
@description Generator for synthetic CIB supplier payments, simulating B2B settlement flows in trade corridors.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Supplier Payment Generator

We generate realistic synthetic supplier payment records
for the CIB domain.

Disclaimer: This is not a sanctioned Standard Bank Group
project. All data is simulated.
Built by Thabo Kunene for portfolio purposes only.
"""

# Enables postponed evaluation of type annotations for forward references
from __future__ import annotations
# Random library for stochastic event generation
import random
# UUID for generating unique transaction and record identifiers
import uuid
# Standard logging for operational observability and audit trails
import logging
# Dataclass for structured representation of supplier payment records
from dataclasses import dataclass
# Datetime utilities for timestamping generated payments
from datetime import datetime, timezone
# Typing hints for defining strong functional and collection contracts
from typing import Iterator, Optional, Dict, Any

# AfriFlow logging utility for consistent log formatting and traceability
from afriflow.logging_config import get_logger
# Base simulator class providing standard initialization and streaming methods
from afriflow.domains.shared.interfaces import SimulatorBase

# Initialize logger for the supplier payment generator namespace
logger = get_logger("domains.cib.simulator.supplier_payment_generator")


@dataclass
class SupplierPayment:
    """
    A single supplier payment record.
    Represents a B2B payment transaction between a corporate client and a supplier.

    Attributes:
        payment_id: Unique identifier for the payment.
        client_id: Identifier of the corporate client making the payment.
        supplier_id: Identifier of the receiving supplier entity.
        corridor: The payment corridor (e.g., 'ZA-NG').
        currency: ISO currency code of the payment.
        amount: The monetary value of the payment.
        timestamp: The precise timestamp when the payment was initiated.
        purpose: Optional description of the payment intent (e.g., 'invoice').
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
    Generator for realistic synthetic supplier payments.
    Useful for testing B2B settlement pipelines and trade finance logic.

    Usage:
        gen = SupplierPaymentGenerator()
        payment = gen.generate_one(corridor="ZA-NG")
    """

    def initialize(self, config=None) -> None:
        """
        Initializes the generator with a registry of corridors, currencies, and purposes.
        
        :param config: Optional configuration object.
        """
        # Supported trade corridors for simulation.
        self._corridors = ["ZA-NG", "NG-GH", "ZA-KE", "KE-TZ"]
        # Default currencies mapped to each corridor.
        self._curr = {
            "ZA-NG": "USD",
            "NG-GH": "USD",
            "ZA-KE": "USD",
            "KE-TZ": "USD",
        }
        # Common business purposes for B2B payments.
        self._purposes = ["invoice", "advance", "freight", None]
        logger.info("SupplierPaymentGenerator initialized")

    def validate_input(self, **kwargs) -> None:
        """
        Validates input parameters before payment generation.

        :param kwargs: Keyword arguments to validate.
        :raises ValueError: If the amount is non-positive or the corridor is unknown.
        """
        # Guard against invalid or zero-value payment amounts.
        amt = kwargs.get("amount")
        if amt is not None and amt <= 0:
            raise ValueError("amount must be positive")

        # Ensure the corridor is within our registry.
        corridor = kwargs.get("corridor")
        if corridor is not None and corridor not in self._corridors:
            raise ValueError(f"Invalid corridor: {corridor}")

    def generate_one(self, **kwargs) -> SupplierPayment:
        """
        Generates a single synthetic supplier payment record.

        :param kwargs: Optional overrides for corridor, client_id, supplier_id, and amount.
        :return: A SupplierPayment instance.
        :raises ValueError: If input validation fails.
        :raises RuntimeError: If generation fails due to unexpected errors.
        """
        try:
            self.validate_input(**kwargs)

            # Use provided values or generate random ones within realistic ranges.
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
