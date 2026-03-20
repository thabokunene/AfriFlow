"""
Unit tests for Corridor Intelligence Engine

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from afriflow.corridor.corridor_engine import CorridorEngine

@pytest.fixture
def corridor_engine():
    return CorridorEngine()

def test_corridor_identification(corridor_engine):
    payment_data = [
        {"source": "ZA", "destination": "NG", "amount": 1000000.0, "client_id": "C-1"},
        {"source": "ZA", "destination": "NG", "amount": 2000000.0, "client_id": "C-2"},
        {"source": "KE", "destination": "GH", "amount": 500000.0, "client_id": "C-3"},
    ]
    corridors = corridor_engine.identify_corridors(payment_data)
    assert len(corridors) == 2
    
    za_ng = next(c for c in corridors if c.corridor_id == "ZA-NG")
    assert za_ng.total_clients == 2
    assert za_ng.total_volume_90d == 3000000.0

def test_top_corridors_ranking(corridor_engine):
    payment_data = [
        {"source": "ZA", "destination": "NG", "amount": 3000000.0, "client_id": "C-1"},
        {"source": "KE", "destination": "GH", "amount": 500000.0, "client_id": "C-3"},
    ]
    corridor_engine.identify_corridors(payment_data)
    top = corridor_engine.get_top_corridors(limit=1, sort_by="volume")
    assert len(top) == 1
    assert top[0].corridor_id == "ZA-NG"

def test_active_corridors(corridor_engine):
    payment_data = [{"source": "ZA", "destination": "NG", "amount": 1000.0, "client_id": "C-1"}]
    corridor_engine.identify_corridors(payment_data)
    active = corridor_engine.get_active_corridors()
    assert len(active) == 1
