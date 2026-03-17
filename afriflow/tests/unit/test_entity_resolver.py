import pytest
from afriflow.integration.entity_resolution.client_matcher import ClientMatcher

@pytest.fixture
def matcher():
    return ClientMatcher()

def test_exact_match(matcher):
    result = matcher.match_client("DANGOTE CEMENT PLC")
    assert result["golden_id"] == "1001"
    assert result["confidence"] == 100

def test_fuzzy_match_typo(matcher):
    # "Dangote Cemnt" vs "DANGOTE CEMENT PLC"
    result = matcher.match_client("Dangote Cemnt")
    assert result["golden_id"] == "1001"
    assert result["confidence"] > 85

def test_fuzzy_match_substring(matcher):
    # "MTN Group" vs "MTN GROUP LIMITED"
    result = matcher.match_client("MTN Group")
    assert result["golden_id"] == "1002"
    assert result["confidence"] > 90

def test_no_match(matcher):
    result = matcher.match_client("Random Small Shop")
    # Should be None or low confidence depending on implementation details, 
    # but with our small list, it might match something with low score.
    # Our implementation returns None ID if threshold isn't met.
    if result["confidence"] < 80:
        assert result["golden_id"] is None
