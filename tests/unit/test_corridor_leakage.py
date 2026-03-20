"""
Unit tests for Corridor Leakage and Formal/Informal Divergence

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from afriflow.corridor.leakage_detector import LeakageDetector
from afriflow.corridor.formal_vs_informal import FormalVsInformal

@pytest.fixture
def leakage_detector():
    return LeakageDetector()

@pytest.fixture
def formal_vs_informal():
    return FormalVsInformal()

def test_leakage_detection_on_known_gap(leakage_detector):
    # CIB volume is R10M, but Forex volume is only R1M
    cib_data = {"volume": 10000000.0}
    forex_data = {"volume": 1000000.0}
    signals = leakage_detector.detect_leakage("ZA-NG", cib_data, forex_data, {}, {}, {})
    
    fx_signal = next(s for s in signals if s.product == "Forex Hedging")
    assert fx_signal.capture_rate_pct == 10.0
    assert fx_signal.estimated_leakage_zar > 0

def test_no_leakage_when_fully_captured(leakage_detector):
    # CIB volume is R10M, Forex volume is R9M (90% capture)
    cib_data = {"volume": 10000000.0}
    forex_data = {"volume": 9000000.0}
    signals = leakage_detector.detect_leakage("ZA-NG", cib_data, forex_data, {}, {}, {})
    
    # Forex Hedging signal should not be present if capture is > 80%
    assert not any(s.product == "Forex Hedging" for s in signals)

def test_formal_vs_informal_divergence(formal_vs_informal):
    # CIB volume dropped 20%, MoMo volume rose 15%
    cib_data = {"volume": 8000000.0, "previous_volume": 10000000.0}
    momo_data = {"volume": 1150000.0, "previous_volume": 1000000.0}
    comparison = formal_vs_informal.compare_flows("ZA-NG", cib_data, momo_data)
    
    assert comparison.divergence_detected is True
    assert comparison.divergence_interpretation == "CAPITAL_FLIGHT_TO_INFORMAL"

def test_divergence_interpretation_with_context(formal_vs_informal):
    comparison = formal_vs_informal.compare_flows(
        "ZA-NG", 
        {"volume": 80, "previous_volume": 100}, 
        {"volume": 120, "previous_volume": 100}
    )
    context = {"capital_controls": "SEVERE"}
    interpretation = formal_vs_informal.interpret_divergence(comparison, context)
    assert "Regulatory arbitrage" in interpretation
