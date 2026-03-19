"""
@file __init__.py
@description Data Shadow Module. Models the expected data footprint for every
             client across all five business domains. Generates signals from
             the gaps between expectation and reality to identify competitive
             leakage and cross-sell opportunities.
@author Thabo Kunene
@created 2026-03-19
"""

# ---------------------------------------------------------------------------
# Data Shadow Module
#
# We model the expected data footprint for every client
# across all domains and generate signals from the gaps
# between expectation and reality.
#
# Disclaimer: Portfolio project by Thabo Kunene. Not a
# Standard Bank Group product. All data is simulated.
# ---------------------------------------------------------------------------

# --- Internal imports: pull public symbols up for consumer convenience ---
# Core engine for defining and evaluating cross-domain expectations
from afriflow.data_shadow.expectation_rules import (
    ExpectationRuleEngine,
)
# Calculator for identifying specific gaps in a client's data footprint
from afriflow.data_shadow.shadow_calculator import (
    ShadowCalculator,
    DomainShadow,
    ClientFootprint,
)
# Monitor for tracking changes in shadow state over time
from afriflow.data_shadow.shadow_monitor import (
    ShadowMonitor,
    ShadowStateChange,
)

# Public API surface — controls what 'from afriflow.data_shadow import *' exposes
__all__ = [
    # Expectation logic
    "ExpectationRuleEngine",
    # Calculation and results
    "ShadowCalculator",
    "DomainShadow",
    "ClientFootprint",
    # Monitoring and state
    "ShadowMonitor",
    "ShadowStateChange",
]
