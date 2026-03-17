"""
tests/integration/test_entity_resolution.py

We run end-to-end integration tests for the entity
resolution pipeline, simulating real-world conditions
where entities arrive from all five domains with
varying data quality, naming conventions, and identifier
availability.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.entity_resolution.client_matcher import (
    EntityResolver,
    ClientEntity,
)


class TestMultiDomainResolution:
    """We simulate a realistic scenario where one
    corporate client appears across all five domains
    with different identifiers and naming conventions."""

    @pytest.fixture
    def resolver_with_shoprite(self):
        resolver = EntityResolver()

        resolver.add_entity(
            ClientEntity(
                domain="cib",
                domain_id="CIB-SHP-001",
                name="Shoprite Holdings Limited",
                registration_number="1936/007721/06",
                tax_number="4000177505",
                country="ZA",
                address="Cnr William Dabs & Old Paarl Rd",
                contact_email="treasury @shoprite.co.za",
                contact_phone="+27218801000",
            )
        )
        resolver.add_entity(
            ClientEntity(
                domain="forex",
                domain_id="FX-SHOPRITE-ZA",
                name="SHOPRITE HLDGS LTD",
                registration_number="1936/007721/06",
                tax_number=None,
                country="ZA",
                address=None,
                contact_email="fx @shoprite.co.za",
                contact_phone=None,
            )
        )
        resolver.add_entity(
            ClientEntity(
                domain="insurance",
                domain_id="LIB-GRP-45892",
                name="Shoprite Holdings (Pty) Ltd",
                registration_number=None,
                tax_number="4000177505",
                country="ZA",
                address=None,
                contact_email=None,
                contact_phone=None,
            )
        )
        resolver.add_entity(
            ClientEntity(
                domain="cell",
                domain_id="MTN-CORP-SHP-3344",
                name="SHOPRITE GROUP",
                registration_number=None,
                tax_number=None,
                country="ZA",
                address=None,
                contact_email="it @shoprite.co.za",
                contact_phone="+27218801000",
            )
        )
        resolver.add_entity(
            ClientEntity(
                domain="pbb",
                domain_id="PBB-PAYROLL-778899",
                name="Shoprite Checkers",
                registration_number=None,
                tax_number=None,
                country="ZA",
                address=None,
                contact_email="payroll @shoprite.co.za",
                contact_phone=None,
            )
        )
        return resolver

    def test_all_five_domains_resolved_to_one_entity(
        self, resolver_with_shoprite
    ):
        resolved = resolver_with_shoprite.resolve_all()
        shoprite = [
            r for r in resolved
            if "SHOPRITE" in r.canonical_name.upper()
        ]
        assert len(shoprite) == 1

    def test_all_domain_ids_present(
        self, resolver_with_shoprite
    ):
        resolved = resolver_with_shoprite.resolve_all()
        shoprite = [
            r for r in resolved
            if "SHOPRITE" in r.canonical_name.upper()
        ][0]
        assert "cib" in shoprite.domain_ids
        assert "forex" in shoprite.domain_ids
        assert "insurance" in shoprite.domain_ids
        assert "cell" in shoprite.domain_ids
        assert "pbb" in shoprite.domain_ids

    def test_canonical_name_prefers_cib(
        self, resolver_with_shoprite
    ):
        resolved = resolver_with_shoprite.resolve_all()
        shoprite = [
            r for r in resolved
            if "SHOPRITE" in r.canonical_name.upper()
        ][0]
        assert shoprite.canonical_name == "Shoprite Holdings Limited"

    def test_high_confidence_with_registration_match(
        self, resolver_with_shoprite
    ):
        resolved = resolver_with_shoprite.resolve_all()
        shoprite = [
            r for r in resolved
            if "SHOPRITE" in r.canonical_name.upper()
        ][0]
        assert shoprite.match_confidence == 100.0
