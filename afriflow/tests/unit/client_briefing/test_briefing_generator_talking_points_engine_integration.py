"""
Unit tests for BriefingGenerator integration with TalkingPointsEngine.

Tests the enhanced talking points functionality including:
- Dynamic talking points generation from signal data
- Error handling and rollback mechanisms
- Mock data scenarios for validation
- Integration pipeline validation

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity.
"""

import pytest
from afriflow.client_briefing.briefing_generator import BriefingGenerator
from afriflow.integration.client_briefing.talking_points_engine import (
    ProcessingTimeoutError,
)


class DummyEngine:
    def __init__(self, points):
        self._points = points

    def process(self, input_data, output_format=None):
        return {"points": [{"text": p, "relevance": 1.0, "conciseness": 1.0, "uniqueness": 1.0} for p in self._points]}


class TimeoutEngine:
    def process(self, input_data, output_format=None):
        raise ProcessingTimeoutError("timed out")


def _minimal_inputs():
    unified_record = {
        "canonical_name": "Acme Mining Ltd",
        "client_tier": "Platinum",
        "relationship_manager": "RM-John-Smith",
        "total_relationship_value_zar": 123_000_000,
        "domains_active": 3,
        "primary_risk_signal": "STABLE",
        "cross_sell_priority": "STANDARD",
        "has_cib": True,
        "has_forex": True,
        "has_insurance": False,
        "has_cell": True,
        "has_pbb": False,
    }
    recent_signals = [
        {"type": "EXPANSION", "description": "Expansion in Kenya", "country": "Kenya", "opportunity_zar": 1_000_000},
        {"type": "RISK", "description": "FX volatility rising", "headline": "FX risk"},
    ]
    return unified_record, recent_signals


def test_generator_enhances_talking_points_with_engine():
    unified_record, recent_signals = _minimal_inputs()
    engine = DummyEngine(points=["Kenya focus and next steps", "Fx focus and next steps"])
    gen = BriefingGenerator(talking_points_engine=engine, enable_talking_points_engine=True)
    briefing = gen.generate(
        golden_id="GLD-1",
        unified_record=unified_record,
        recent_signals=recent_signals,
        shadow_gaps=[],
    )
    assert any("Kenya" in p for p in briefing.talking_points)


def test_generator_rolls_back_on_engine_failure():
    unified_record, recent_signals = _minimal_inputs()
    gen = BriefingGenerator(talking_points_engine=TimeoutEngine(), enable_talking_points_engine=True)
    briefing = gen.generate(
        golden_id="GLD-1",
        unified_record=unified_record,
        recent_signals=recent_signals,
        shadow_gaps=[],
    )
    assert briefing.talking_points
