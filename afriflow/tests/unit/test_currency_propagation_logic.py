"""
tests/unit/test_currency_propagation_logic.py

Unit tests for the Currency Event Propagator logic.
Verifies cross-domain impact calculation.
"""

import pytest
from afriflow.currency_events.propagator import CurrencyEventPropagator
from afriflow.currency_events.event_classifier import CurrencyEvent, EventTier, EventType
from afriflow.currency_events.constants import (
    DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE,
    DOMAIN_CELL, DOMAIN_PBB
)

class TestCurrencyPropagation:
    
    @pytest.fixture
    def propagator(self):
        return CurrencyEventPropagator()
    
    @pytest.fixture
    def critical_ngn_event(self):
        return CurrencyEvent(
            event_id="FXE-NGN-20260317",
            currency_code="NGN",
            event_tier=EventTier.CRITICAL,
            event_type=EventType.DEVALUATION,
            magnitude_pct=20.0,
            official_rate_before=1000.0,
            official_rate_after=1200.0,
            affected_domains=[DOMAIN_CIB, DOMAIN_FOREX, DOMAIN_INSURANCE, DOMAIN_CELL, DOMAIN_PBB]
        )

    def test_cib_impact_calculation(self, propagator, critical_ngn_event):
        # Setup client with CIB exposure
        # utilization=80%, after 20% devaluation -> 80 * 1.2 = 96% (> 90%)
        propagator.register_client_exposure(
            golden_id="CLIENT-001",
            currency="NGN",
            domain=DOMAIN_CIB,
            exposure_details={
                "facility_value_local": 10_000_000,
                "utilization_pct": 80.0
            }
        )
        
        result = propagator.propagate(critical_ngn_event)
        
        assert result.total_clients_affected == 1
        cib_impacts = [i for i in result.domain_impacts if i.domain == DOMAIN_CIB]
        assert len(cib_impacts) == 1
        assert cib_impacts[0].impact_type == "FACILITY_INADEQUACY"
        assert cib_impacts[0].action_required is True

    def test_forex_impact_calculation(self, propagator, critical_ngn_event):
        # Setup client with Forex exposure
        propagator.register_client_exposure(
            golden_id="CLIENT-001",
            currency="NGN",
            domain=DOMAIN_FOREX,
            exposure_details={
                "forward_notional_zar": 10_000_000,
                "booked_rate": 1000.0
            }
        )
        
        result = propagator.propagate(critical_ngn_event)
        
        forex_impacts = [i for i in result.domain_impacts if i.domain == DOMAIN_FOREX]
        assert len(forex_impacts) == 1
        # mtm_impact = 10M * 20% = 2M
        assert forex_impacts[0].impact_value_zar == 2_000_000
        assert forex_impacts[0].urgency == "MEDIUM"  # < 5M

    def test_pbb_impact_calculation(self, propagator, critical_ngn_event):
        # Setup client with PBB exposure
        propagator.register_client_exposure(
            golden_id="CORP-001",
            currency="NGN",
            domain=DOMAIN_PBB,
            exposure_details={
                "employee_count": 600
            }
        )
        
        result = propagator.propagate(critical_ngn_event)
        
        pbb_impacts = [i for i in result.domain_impacts if i.domain == DOMAIN_PBB]
        assert len(pbb_impacts) == 1
        assert pbb_impacts[0].impact_type == "SALARY_ADVANCE_DEMAND"
        assert pbb_impacts[0].urgency == "HIGH"  # > 500 employees

    def test_no_propagation_if_domain_not_affected(self, propagator):
        # Event only affects Forex
        event = CurrencyEvent(
            event_id="FXE-LOW",
            currency_code="ZAR",
            event_tier=EventTier.LOW,
            event_type=EventType.RATE_MOVE,
            magnitude_pct=2.0,
            official_rate_before=19.0,
            official_rate_after=19.38,
            affected_domains=[DOMAIN_FOREX]
        )
        
        # Client has CIB exposure
        propagator.register_client_exposure(
            golden_id="CLIENT-001",
            currency="ZAR",
            domain=DOMAIN_CIB,
            exposure_details={"facility_value_local": 1000, "utilization_pct": 50}
        )
        
        result = propagator.propagate(event)
        assert result.total_clients_affected == 0
        assert len(result.domain_impacts) == 0
