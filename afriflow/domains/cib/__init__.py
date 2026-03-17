"""
CIB (Corporate Investment Banking) domain.

We process cross-border corporate payments, trade
finance, and cash management data.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from afriflow.domains.cib.simulator.payment_generator import (
    PaymentGenerator,
)

__all__ = [
    "PaymentGenerator",
]
