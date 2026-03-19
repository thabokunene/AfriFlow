"""
@file __init__.py
@description Root package initialization for the CIB (Corporate Investment Banking) domain, exposing core simulators and processors.
@author Thabo Kunene
@created 2026-03-19
"""

"""
CIB (Corporate Investment Banking) domain.

We process cross-border corporate payments, trade
finance, and cash management data.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Core payment generator for synthetic CIB transaction data
from afriflow.domains.cib.simulator.payment_generator import (
    PaymentGenerator,
)

# Defines the public interface for the CIB domain package
__all__ = [
    "PaymentGenerator",
]
