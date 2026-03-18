"""
@file __init__.py
@description Package init for the alternative_scoring sub-package.
             Bundles the three alternative scoring models that go beyond
             traditional credit bureau data to assess African SME clients.
             Re-exports all public classes so callers import from one place.
@author Thabo Kunene
@created 2026-03-18
"""

# Business viability: cross-domain proxy for creditworthiness (300–850 scale)
from .business_viability_score import BusinessViabilityScorer, BusinessViabilityScore, ScoreComponent

# Digital maturity: how digitally engaged the client's org and workforce are
from .digital_maturity_score import DigitalMaturityScorer, DigitalMaturityScore, DigitalDimension

# Informal Economy Health Index: health of the informal cluster around a client
from .informal_economy_health_index import (
    InformalEconomyHealthIndexer,  # Main indexer class
    IEHIResult,                    # Full result dataclass
    IEHIComponent,                 # Per-component score
    InformalClusterProfile,        # Cluster summary profile
)

# Public API surface for this sub-package
__all__ = [
    "BusinessViabilityScorer",
    "BusinessViabilityScore",
    "ScoreComponent",
    "DigitalMaturityScorer",
    "DigitalMaturityScore",
    "DigitalDimension",
    "InformalEconomyHealthIndexer",
    "IEHIResult",
    "IEHIComponent",
    "InformalClusterProfile",
]
