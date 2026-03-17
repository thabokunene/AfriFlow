"""
Data Shadow Module

We model the expected data footprint for every client
across all domains and generate signals from the gaps
between expectation and reality.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from afriflow.data_shadow.expectation_rules import (
    ExpectationRuleEngine,
)
from afriflow.data_shadow.shadow_calculator import (
    ShadowCalculator,
    DomainShadow,
    ClientFootprint,
)
from afriflow.data_shadow.shadow_monitor import (
    ShadowMonitor,
    ShadowStateChange,
)

__all__ = [
    "ExpectationRuleEngine",
    "ShadowCalculator",
    "DomainShadow",
    "ClientFootprint",
    "ShadowMonitor",
    "ShadowStateChange",
]
