"""
Shared pytest fixtures for the AfriFlow test suite.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from datetime import datetime, timedelta
from .shared_test_utils import (
    MockDataGenerator, AssertionHelpers,
    generate_test_client, generate_test_payment,
    generate_test_currency_event, generate_test_sim_activation,
    generate_test_insurance_policy, generate_test_fx_trade,
    generate_utc_timestamp, mock_generator, assertions
)


@pytest.fixture
def sample_cib_payment():
    """A sample CIB payment event for testing."""

    return {
        "debtor_client_id": "CLIENT-001",
        "debtor_country": "ZA",
        "creditor_country": "KE",
        "creditor_name": "Kenya Supplies Ltd",
        "business_date": datetime.now().strftime("%Y-%m-%d"),
        "amount": 1_000_000,
        "currency": "KES",
        "payment_type": "SUPPLIER",
    }


@pytest.fixture
def sample_cell_activation():
    """A sample cell SIM activation event for testing."""

    return {
        "corporate_client_id": "CLIENT-001",
        "activation_country": "KE",
        "activation_date": datetime.now().strftime("%Y-%m-%d"),
        "sim_count": 50,
        "city": "Nairobi",
        "data_usage_mb": 12000,
    }


@pytest.fixture
def sample_client_metadata():
    """Sample client metadata for testing."""

    return {
        "CLIENT-001": {
            "client_name": "Test Corp",
            "tier": "Platinum",
            "relationship_manager": "RM-001",
            "home_country": "ZA",
        },
        "CLIENT-002": {
            "client_name": "Test Corp 2",
            "tier": "Gold",
            "relationship_manager": "RM-002",
            "home_country": "ZA",
        },
    }


@pytest.fixture
def sample_golden_record():
    """Sample unified golden record for testing."""

    return {
        "golden_id": "GLD-TEST001",
        "canonical_name": "Test Corp",
        "client_tier": "Platinum",
        "home_country": "ZA",
        "relationship_manager": "RM-001",
        "has_cib": True,
        "has_forex": True,
        "has_insurance": False,
        "has_cell": True,
        "has_pbb": False,
        "domains_active": 3,
        "total_relationship_value_zar": 450_000_000,
        "cross_sell_priority": "CRITICAL",
        "primary_risk_signal": "UNHEDGED_EXPOSURE",
        "last_activity_any_domain": datetime.now().strftime("%Y-%m-%d"),
        "data_classification": "AGGREGATED",
    }


@pytest.fixture
def sample_expansion_signal():
    """Sample expansion signal for testing."""

    return {
        "golden_id": "GLD-TEST001",
        "client_name": "Test Corp",
        "expansion_country": "KE",
        "confidence_score": 75.0,
        "estimated_opportunity_zar": 5_000_000,
        "cib_new_corridor_payments": 5,
        "cib_corridor_value": 5_000_000,
        "cell_new_sim_activations": 150,
        "forex_new_currency_trades": 0,
        "insurance_new_countries": 0,
        "pbb_new_countries": 0,
        "forex_hedging_in_place": False,
        "insurance_coverage_in_place": False,
        "recommended_products": ["FX hedging", "Working capital"],
        "urgency": "HIGH",
    }


@pytest.fixture
def sample_data_shadow():
    """Sample data shadow for testing."""

    return {
        "shadow_id": "SHADOW-TEST001",
        "client_golden_id": "GLD-TEST001",
        "client_name": "Test Corp",
        "source_domain": "cib",
        "expected_domain": "forex",
        "expected_country": "KE",
        "category": "COMPETITIVE_LEAKAGE",
        "confidence": 0.85,
        "estimated_revenue_opportunity_zar": 150_000,
        "recommended_action": "Offer FX hedging for KES exposure",
        "source_evidence": "CIB payments to KE without forex activity",
    }


@pytest.fixture
def sample_currency_event():
    """Sample currency event for testing."""

    return {
        "event_id": "FXE-NGN-TEST001",
        "currency": "NGN",
        "event_type": "DEVALUATION",
        "severity": "CRITICAL",
        "rate_change_pct": 15.0,
        "detected_at": datetime.now(),
        "is_official_announcement": True,
    }


@pytest.fixture
def sample_seasonal_factor():
    """Sample seasonal factor for testing."""

    return {
        "season_name": "maize",
        "period_name": "harvest",
        "start_month": 4,
        "end_month": 6,
        "expected_change_pct": 60,
        "cash_flow_impact": "positive",
        "confidence": 0.9,
    }


# Shared test utilities fixtures
@pytest.fixture
def mock_data_generator():
    """Mock data generator for consistent test data across domains."""
    return MockDataGenerator()


@pytest.fixture
def assertion_helpers():
    """Assertion helpers for validating test data."""
    return AssertionHelpers()


@pytest.fixture
def sample_client():
    """Generate a sample client for testing."""
    return generate_test_client()


@pytest.fixture
def sample_payment():
    """Generate a sample payment for testing."""
    return generate_test_payment()


@pytest.fixture
def sample_currency_event():
    """Generate a sample currency event for testing."""
    return generate_test_currency_event()


@pytest.fixture
def sample_sim_activation():
    """Generate a sample SIM activation for testing."""
    return generate_test_sim_activation()


@pytest.fixture
def sample_insurance_policy():
    """Generate a sample insurance policy for testing."""
    return generate_test_insurance_policy()


@pytest.fixture
def sample_fx_trade():
    """Generate a sample FX trade for testing."""
    return generate_test_fx_trade()


@pytest.fixture
def utc_timestamp():
    """Generate a UTC timestamp for testing."""
    return generate_utc_timestamp()
