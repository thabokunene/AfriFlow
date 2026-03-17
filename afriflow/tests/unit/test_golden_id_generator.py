"""
tests/unit/test_golden_id_generator.py

We test that Golden ID generation is deterministic,
collision-resistant, and stable across entity
resolution runs.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.entity_resolution.golden_id_generator import (
    generate_golden_id,
)


class TestGoldenIDProperties:
    """We verify the core properties that make a Golden
    ID reliable for cross-domain joining."""

    def test_deterministic_from_registration(self):
        id_a = generate_golden_id(
            registration_number="1979/003231/06"
        )
        id_b = generate_golden_id(
            registration_number="1979/003231/06"
        )
        assert id_a == id_b

    def test_deterministic_from_tax(self):
        id_a = generate_golden_id(
            tax_number="4250089747"
        )
        id_b = generate_golden_id(
            tax_number="4250089747"
        )
        assert id_a == id_b

    def test_different_inputs_different_ids(self):
        id_a = generate_golden_id(
            registration_number="1111/111111/01"
        )
        id_b = generate_golden_id(
            registration_number="2222/222222/02"
        )
        assert id_a != id_b

    def test_prefix_format(self):
        gid = generate_golden_id(
            registration_number="TEST/123456/00"
        )
        assert gid.startswith("GLD-")
        assert len(gid) == 16

    def test_fallback_to_name_country(self):
        gid = generate_golden_id(
            name="Acme Trading",
            country="ZA",
        )
        assert gid.startswith("GLD-")

    def test_registration_takes_priority(self):
        id_with_reg = generate_golden_id(
            registration_number="REG-001",
            tax_number="TAX-001",
            name="Acme",
            country="ZA",
        )
        id_reg_only = generate_golden_id(
            registration_number="REG-001",
        )
        assert id_with_reg == id_reg_only
