"""
Data Shadow package for AfriFlow.

We detect and score the absence of expected cross-domain
signals — treating data absence as a business intelligence
signal in its own right.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from .absence_signal_generator import (
    AbsenceSignalGenerator,
    AbsenceSignal,
    AbsenceType,
)
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
