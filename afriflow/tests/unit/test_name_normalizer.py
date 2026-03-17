"""
tests/unit/test_name_normalizer.py

We test the multilingual company name normalizer
that handles French, Portuguese, Arabic transliteration,
and acronym resolution across African corporate registries.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity. It is a demonstration of concept,
    domain knowledge, and data engineering skill by
    Thabo Kunene.
"""

import pytest
from integration.entity_resolution.name_normalizer import (
    AfricanNameNormalizer,
)


class TestFrenchEntityNames:
    """We handle the Francophone African naming conventions
    found across CFA zone countries."""

    @pytest.fixture
    def normalizer(self):
        return AfricanNameNormalizer()

    def test_societe_variations(self, normalizer):
        variants = [
            "Societe Nationale d'Electricite",
            "Société Nationale d'Électricité",
            "SOCIETE NATIONALE D ELECTRICITE",
            "Sté Nationale d'Electricité",
        ]
        normalized = [normalizer.normalize(v) for v in variants]
        assert len(set(normalized)) == 1

    def test_sarl_suffix_removal(self, normalizer):
        result = normalizer.normalize("Cimenterie du Katanga SARL")
        assert "SARL" not in result

    def test_etablissements_abbreviation(self, normalizer):
        full = normalizer.normalize("Etablissements Duval")
        abbrev = normalizer.normalize("Ets Duval")
        assert full == abbrev


class TestPortugueseEntityNames:
    """We handle Lusophone naming conventions found in
    Mozambique, Angola, and Cabo Verde."""

    @pytest.fixture
    def normalizer(self):
        return AfricanNameNormalizer()

    def test_lda_suffix_removal(self, normalizer):
        result = normalizer.normalize(
            "Cervejas de Mocambique Lda"
        )
        assert "LDA" not in result

    def test_sociedade_abbreviation(self, normalizer):
        full = normalizer.normalize(
            "Sociedade Mineira de Angola"
        )
        abbrev = normalizer.normalize("Soc Mineira de Angola")
        assert full == abbrev


class TestAcronymResolution:
    """We test that common African corporate acronyms
    are correctly linked to their full names."""

    @pytest.fixture
    def normalizer(self):
        return AfricanNameNormalizer()

    def test_snel_resolves(self, normalizer):
        assert normalizer.resolve_acronym("SNEL", "CD") == (
            "SOCIETE NATIONALE D ELECTRICITE"
        )

    def test_nnpc_resolves(self, normalizer):
        assert normalizer.resolve_acronym("NNPC", "NG") == (
            "NIGERIAN NATIONAL PETROLEUM CORPORATION"
        )

    def test_unknown_acronym_returns_none(self, normalizer):
        assert normalizer.resolve_acronym("XYZABC", "ZA") is None


class TestArabicTransliteration:
    """We handle transliterated Arabic names found in
    North and East African business records."""

    @pytest.fixture
    def normalizer(self):
        return AfricanNameNormalizer()

    def test_el_al_article_normalization(self, normalizer):
        v1 = normalizer.normalize("El-Sewedy Electric")
        v2 = normalizer.normalize("Al Sewedy Electric")
        v3 = normalizer.normalize("Elsewedy Electric")
        assert v1 == v2 == v3
