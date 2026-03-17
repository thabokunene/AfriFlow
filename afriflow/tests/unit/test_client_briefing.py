"""
tests/unit/test_client_briefing.py

Unit tests for the Client Briefing Module.

We verify that:
1. Briefing cards are rendered correctly.
2. Cross-domain signals are integrated.
3. Data shadow gaps are highlighted.
4. Risk alerts are generated appropriately.

DISCLAIMER: This project is not sanctioned by, affiliated with, or
endorsed by Standard Bank Group, MTN Group, or any of their subsidiaries.
It is a demonstration of concept, domain knowledge, and technical skill
built by Thabo Kunene for portfolio and learning purposes only.
"""

import pytest
from afriflow.client_briefing.briefing_generator import (
    ClientBriefing,
    ChangeEvent,
    Opportunity,
    RiskAlert,
    BriefingSection,
)


class TestClientBriefingRendering:
    """Tests for the text rendering of the briefing."""

    def _make_briefing(self, **overrides):
        """Helper to create a test briefing with defaults."""

        defaults = {
            "client_golden_id": "GLD-TEST001",
            "client_name": "Acme Mining Ltd",
            "client_tier": "Platinum",
            "meeting_datetime": "2024-06-15 14:00",
            "relationship_manager": "RM-John-Smith",
            "total_relationship_value_zar": 450_000_000,
            "health_status": "STABLE",
            "domains_active": {
                "cib": True,
                "forex": True,
                "insurance": True,
                "cell": True,
                "pbb": False,
            },
            "changes_since_last_meeting": [
                ChangeEvent(
                    domain="cib",
                    description="3 new payment corridors opened (GH, SN, CI)",
                    magnitude="significant",
                    direction="increase",
                ),
            ],
            "top_opportunities": [
                Opportunity(
                    rank=1,
                    description="Working capital for Ghana expansion",
                    estimated_value_zar=120_000_000,
                    source_signal="expansion_signal",
                    talking_point=(
                        "We have noticed your team growing in Accra. "
                        "Have you considered our working capital solutions?"
                    ),
                ),
            ],
            "risk_alerts": [
                RiskAlert(
                    domain="forex",
                    description="Unhedged GHS exposure detected",
                    severity="MEDIUM",
                    recommended_discussion_point=(
                        "Given recent cedi volatility, have you "
                        "reviewed your hedging strategy?"
                    ),
                ),
            ],
            "talking_points": [
                "We have noticed your team growing in Accra.",
                "Given recent cedi volatility, have you reviewed hedging?",
            ],
            "last_meeting_date": "2024-05-01",
            "generated_at": "2024-06-15T13:30:00",
            "relationship_snapshot": BriefingSection(
                title="RELATIONSHIP SNAPSHOT",
                icon="[R]",
                content=["TRV: R450m", "Health: OK", "Domains: CIB: Y | FOREX: Y | INSURANCE: Y | CELL: Y | PBB: N"],
                priority="NORMAL"
            ),
            "seasonal_context": None
        }

        defaults.update(overrides)
        return ClientBriefing(**defaults)

    def test_briefing_contains_client_name(self):
        """Briefing text must include the client name."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "Acme Mining Ltd" in text

    def test_briefing_contains_total_value(self):
        """Briefing must show the total relationship value."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "450,000,000" in text

    def test_briefing_contains_domain_flags(self):
        """Briefing must show which domains are active."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "CIB: Y" in text
        assert "PBB: N" in text

    def test_briefing_contains_opportunities(self):
        """Briefing must list revenue opportunities."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "Ghana expansion" in text
        assert "120,000,000" in text

    def test_briefing_contains_risk_alerts(self):
        """Briefing must show risk alerts."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "Unhedged GHS exposure" in text
        assert "MEDIUM" in text

    def test_briefing_contains_talking_points(self):
        """Briefing must include suggested talking points."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "growing in Accra" in text

    def test_briefing_contains_last_meeting_date(self):
        """Briefing must reference the last meeting date."""
        briefing = self._make_briefing()
        text = briefing.render_text()
        assert "2024-05-01" in text

    def test_briefing_with_no_changes(self):
        """Briefing with no changes should say so gracefully."""
        briefing = self._make_briefing(
            changes_since_last_meeting=[]
        )
        text = briefing.render_text()
        assert "No significant changes" in text

    def test_briefing_with_no_risks(self):
        """Briefing with no risks should say so gracefully."""
        briefing = self._make_briefing(risk_alerts=[])
        text = briefing.render_text()
        assert "No active risk alerts" in text
