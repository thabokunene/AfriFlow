"""
@file __init__.py
@description Root package initialization for the Insurance domain, exposing core simulators and processing components.
@author Thabo Kunene
@created 2026-03-19
"""

"""
Insurance domain for AfriFlow.

We process insurance policies, claims, and premiums
to identify risk and coverage gaps.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Core simulators for generating synthetic insurance data
from .simulator.policy_generator import PolicyGenerator
from .simulator.claims_generator import ClaimsGenerator

# Defines the public interface for the insurance domain package
__all__ = [
    "PolicyGenerator", # Synthetic policy lifecycle generator
    "ClaimsGenerator", # Synthetic claims event generator
]
