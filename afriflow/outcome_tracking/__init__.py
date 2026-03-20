"""
@file __init__.py
@description Outcome Tracking Module - Signal outcome recording and feedback loop
@author Thabo Kunene
@created 2026-03-19

This module tracks the outcomes of signals from detection through RM action
to revenue booking. It enables measurement of signal effectiveness and ROI.

Key Components:
- outcome_recorder: Record RM actions and outcomes
- signal_lifecycle: Track signal state transitions
- revenue_attribution: Link outcomes to revenue
- feedback_loop: Update models based on outcomes

Key Features:
- Signal outcome tracking (acted/not acted, won/lost)
- Revenue attribution to specific signals
- Win rate calculation per signal type
- Feedback to Knowledge Cards and ML models
- ROI measurement for signal detection

Usage:
    >>> from afriflow.outcome_tracking import OutcomeRecorder
    >>> recorder = OutcomeRecorder()
    >>> recorder.record_outcome(
    ...     signal_id="SIG-001",
    ...     rm_actioned=True,
    ...     revenue_booked=50000.0,
    ...     won=True
    ... )

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

# Import outcome tracking components for re-export
from .outcome_recorder import OutcomeRecorder, OutcomeRecord
from .signal_lifecycle import SignalLifecycle, SignalState
from .revenue_attribution import RevenueAttribution as OutcomeRevenueAttribution
from .feedback_loop import FeedbackLoop

# Module metadata
__version__ = "1.0.0"  # Outcome tracking module version
__author__ = "Thabo Kunene"  # Module author

# Public API - defines what's exported for 'from afriflow.outcome_tracking import *'
__all__ = [
    # Outcome recording
    "OutcomeRecorder",
    "OutcomeRecord",
    # Signal lifecycle tracking
    "SignalLifecycle",
    "SignalState",
    # Revenue attribution
    "OutcomeRevenueAttribution",
    # Feedback loop
    "FeedbackLoop",
]
