"""
@file __init__.py
@description Package init for the data_shadow integration module.
             Exposes the AbsenceSignalGenerator and ShadowGapDetector
             components for use by the integration pipeline and RM alert
             routing layer. Data Shadow treats missing cross-domain signals
             as first-class business intelligence rather than data quality gaps.
@author Thabo Kunene
@created 2026-03-18

Data Shadow package for AfriFlow.

We detect and score the absence of expected cross-domain
signals — treating data absence as a business intelligence
signal in its own right.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Import AbsenceSignalGenerator and its data types.
# AbsenceSignals are raw, unscored absence observations generated from domain snapshots.
from .absence_signal_generator import (
    AbsenceSignalGenerator,
    AbsenceSignal,
    AbsenceType,
)

# Import ShadowGapDetector and its data types.
# ShadowGaps are scored, prioritised gap records derived from CIB activity analysis.
from .shadow_gap_detector import (
    ShadowGapDetector,
    ShadowGap,
    GapDomain,
    GapSeverity,
    ShadowExpectation,
)

__all__ = [
    "AbsenceSignalGenerator",
    "AbsenceSignal",
    "AbsenceType",
    "ShadowGapDetector",
    "ShadowGap",
    "GapDomain",
    "GapSeverity",
    "ShadowExpectation",
]
