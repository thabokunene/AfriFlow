"""
@file __init__.py
@description Root package initialization for AfriFlow domains, exposing business-specific processing modules.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Domains package for AfriFlow.

We organize domain-specific data processing code
by business domain: CIB, Forex, Insurance, Cell,
and PBB.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Defines the public interface for the domains package,
# ensuring clear separation between business domains.
__all__ = [
    "cib", # Corporate and Investment Banking domain logic
    "forex", # Foreign Exchange and Treasury domain logic
    "insurance", # Insurance and Risk Management domain logic
    "cell", # Telecommunications and Mobile Money domain logic
    "pbb", # Personal and Business Banking domain logic
    "shared", # Common utilities and shared domain constants
]
