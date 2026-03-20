"""
Integration tests for Corridor Revenue Attribution

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from afriflow.corridor.corridor_engine import CorridorEngine
from afriflow.corridor.revenue_attribution import RevenueAttribution, CorridorRevenue
from afriflow.corridor.leakage_detector import LeakageDetector

def test_full_corridor_analytics_lifecycle():
    # 1. Initialize engines
    engine = CorridorEngine()
    attribution = RevenueAttribution()
    leakage_detector = LeakageDetector()
    
    # 2. Identify corridors from payment data
    payments = [
        {"source": "ZA", "destination": "NG", "amount": 10000000.0, "client_id": "C-1"},
        {"source": "ZA", "destination": "NG", "amount": 5000000.0, "client_id": "C-2"},
    ]
    corridors = engine.identify_corridors(payments)
    assert len(corridors) == 1
    za_ng = corridors[0]
    
    # 3. Calculate revenue attribution
    cib_data = {"volume": 15000000.0}
    forex_data = {"volume": 5000000.0} # Capture rate ~33%
    
    revenue = attribution.calculate_corridor_revenue(
        za_ng.corridor_id,
        cib_data,
        forex_data,
        {}, {}, {}
    )
    assert revenue.corridor_id == "ZA-NG"
    
    # 4. Detect leakage
    signals = leakage_detector.detect_leakage(
        za_ng.corridor_id,
        cib_data,
        forex_data,
        {}, {}, {}
    )
    assert len(signals) > 0
    assert any(s.product == "Forex Hedging" for s in signals)
    assert signals[0].estimated_leakage_zar > 0
