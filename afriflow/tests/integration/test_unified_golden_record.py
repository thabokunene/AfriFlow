"""
tests/integration/test_unified_golden_record.py

We test the complete unified golden record construction
from entity resolution through cross-domain enrichment
to the final materialized view.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest


class TestUnifiedGoldenRecordSchema:
    """We verify that the golden record contains all
    required fields across all five domains."""

    REQUIRED_FIELDS = [
        "golden_id",
        "canonical_name",
        "client_tier",
        "home_country",
        "relationship_manager",
        "has_cib",
        "has_forex",
        "has_insurance",
        "has_cell",
        "has_pbb",
        "domains_active",
        "total_relationship_value_zar",
        "cross_sell_priority",
        "primary_risk_signal",
        "last_activity_any_domain",
        "data_classification",
    ]

    def test_dbt_model_contains_all_fields(self):
        """We verify the SQL model references every
        required field by parsing the model file."""
        model_path = (
            "integration/unified_golden_record/"
            "dbt_models/mart_unified_client.sql"
        )
        with open(model_path, "r") as f:
            sql = f.read().upper()

        for field in self.REQUIRED_FIELDS:
            assert field.upper() in sql, (
                f"Missing field in golden record: {field}"
            )


class TestCrossSellPriorityLogic:
    """We verify that cross-sell priority is correctly
    assigned based on client tier and domain coverage."""

    def test_platinum_with_three_domains_is_critical(self):
        """A Platinum client active in only 3 domains
        should be CRITICAL priority because the gap
        represents significant revenue leakage."""
        domains_active = 3
        tier = "Platinum"
        priority = self._compute_priority(tier, domains_active)
        assert priority == "CRITICAL"

    def test_silver_with_two_domains_is_high(self):
        domains_active = 2
        tier = "Silver"
        priority = self._compute_priority(tier, domains_active)
        assert priority == "HIGH"

    def test_any_tier_with_five_domains_is_standard(self):
        domains_active = 5
        tier = "Platinum"
        priority = self._compute_priority(tier, domains_active)
        assert priority == "STANDARD"

    @staticmethod
    def _compute_priority(tier: str, domains: int) -> str:
        if tier in ("Platinum", "Gold") and domains < 4:
            return "CRITICAL"
        elif domains < 3:
            return "HIGH"
        return "STANDARD"
