"""
@file __init__.py
@description Data Quality Module - Runtime data quality scoring and monitoring
@author Thabo Kunene
@created 2026-03-19

This module provides runtime data quality scoring, freshness monitoring,
circuit breaking, and contract validation for the AfriFlow platform.

Key Components:
- quality_scorer: Calculate data quality scores
- freshness_monitor: Monitor data freshness SLAs
- circuit_breaker: Protect pipelines from bad data
- contract_validator: Validate data against contracts
- schema_evolution_tracker: Track schema changes

Key Features:
- Real-time quality scoring (0-100 scale)
- Freshness SLA monitoring with alerts
- Circuit breaker for pipeline protection
- Contract validation against YAML schemas
- Schema evolution tracking and migration

Usage:
    >>> from afriflow.data_quality import QualityScorer
    >>> scorer = QualityScorer()
    >>> score = scorer.calculate_score("cib", {"completeness": 0.95, "accuracy": 0.98})

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Import data quality components for re-export
from .quality_scorer import QualityScorer, QualityDimensions
from .freshness_monitor import FreshnessMonitor, FreshnessSLA
from .circuit_breaker import CircuitBreaker, CircuitState
from .contract_validator import ContractValidator, ContractViolation
from .schema_evolution_tracker import SchemaEvolutionTracker, SchemaVersion

# Module metadata
__version__ = "1.0.0"  # Data quality module version
__author__ = "Thabo Kunene"  # Module author

# Public API - defines what's exported for 'from afriflow.data_quality import *'
__all__ = [
    # Quality scoring
    "QualityScorer",
    "QualityDimensions",
    # Freshness monitoring
    "FreshnessMonitor",
    "FreshnessSLA",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    # Contract validation
    "ContractValidator",
    "ContractViolation",
    # Schema evolution
    "SchemaEvolutionTracker",
    "SchemaVersion",
]
