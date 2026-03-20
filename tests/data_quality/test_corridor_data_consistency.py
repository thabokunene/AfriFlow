"""
Data Quality tests for Corridor consistency

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from afriflow.corridor.corridor_engine import CorridorEngine
from afriflow.corridor.leakage_detector import LeakageDetector

def test_corridor_volume_consistency():
    engine = CorridorEngine()
    payments = [
        {"source": "ZA", "destination": "NG", "amount": 1000.0, "client_id": "C-1"},
        {"source": "ZA", "destination": "NG", "amount": 2000.0, "client_id": "C-1"},
    ]
    corridors = engine.identify_corridors(payments)
    za_ng = corridors[0]
    
    # Total volume must match sum of payments
    assert za_ng.total_volume_90d == 3000.0

def test_leakage_capture_ratio_consistency():
    detector = LeakageDetector()
    cib_data = {"volume": 1000.0}
    forex_data = {"volume": 500.0}
    
    signals = detector.detect_leakage("ZA-NG", cib_data, forex_data, {}, {}, {})
    fx_signal = next(s for s in signals if s.product == "Forex Hedging")
    
    # Capture rate + Leakage ratio should align with expectation (80% target)
    # Expected target is 800. Actual is 500. Leakage is 300.
    # Capture rate is 50%.
    assert fx_signal.capture_rate_pct == 50.0
    assert fx_signal.cib_volume == 1000.0
    assert fx_signal.product_volume == 500.0
