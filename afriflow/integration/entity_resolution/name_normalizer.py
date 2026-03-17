"""
Entity Resolution - African Name Normalizer

Multilingual company name normalizer for African
corporate registries.

We handle French (Francophone West and Central Africa),
Portuguese (Mozambique, Angola), Arabic transliteration
(North Africa and parts of East Africa), and English
naming conventions across 20 African countries.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import re
from typing import Dict, List, Optional
import logging

from afriflow.exceptions import EntityResolutionError
from afriflow.logging_config import get_logger

logger = get_logger("entity_resolution.normalizer")


class AfricanNameNormalizer:
    """
    Normalizes company names across multiple African languages
    and naming conventions to enable accurate entity matching.

    This normalizer handles challenges that a US or European
    normalizer would miss:
    - French entity variations (Societe, Ste, Soc, SARL)
    - Portuguese suffixes (Lda, Ltda, Sociedade)
    - Arabic transliteration (El-, Al-, Al)
    - Accented characters in French and Portuguese
    - African-specific abbreviations

    Attributes:
        ENTITY_SUFFIXES: List of entity type suffixes to remove
        ABBREVIATION_MAP: Map of abbreviations to full forms
        ACRONYM_REGISTRY: Registry of known acronyms by country
    """

    ENTITY_SUFFIXES: List[str] = [
        "PTY LTD", "(PTY) LTD", "PTY", "PROPRIETARY LIMITED",
        "LTD", "LIMITED", "INC", "INCORPORATED",
        "CORP", "CORPORATION", "PLC",
        "LLC", "GMBH", "AG",
        "SA", "SARL", "SAS", "SASU",
        "LDA", "LTDA",
        "NPC", "SOC LTD", "RF",
        "BV", "NV",
    ]

    ABBREVIATION_MAP: Dict[str, str] = {
        "STE": "SOCIETE",
        "SOC": "SOCIEDADE",
        "ETS": "ETABLISSEMENTS",
        "CIE": "COMPAGNIE",
        "GRP": "GROUP",
        "HLDGS": "HOLDINGS",
        "INTL": "INTERNATIONAL",
        "NATL": "NATIONAL",
        "MTN": "MTN",
        "STD": "STANDARD",
    }

    ACRONYM_REGISTRY: Dict[str, Dict[str, str]] = {
        "SNEL": {
            "CD": "SOCIETE NATIONALE D ELECTRICITE",
        },
        "NNPC": {
            "NG": "NIGERIAN NATIONAL PETROLEUM CORPORATION",
        },
        "SNCC": {
            "CD": "SOCIETE NATIONALE DES CHEMINS DE FER DU CONGO",
        },
        "SONATEL": {
            "SN": "SOCIETE NATIONALE DES TELECOMMUNICATIONS",
        },
        "SONATRACH": {
            "DZ": "SOCIETE NATIONALE POUR LA RECHERCHE",
        },
        "ESKOM": {
            "ZA": "ELECTRICITY SUPPLY COMMISSION",
        },
    }

    def __init__(self) -> None:
        """Initialize the African name normalizer."""
        logger.debug("AfricanNameNormalizer initialized")

    def normalize(self, name: str) -> str:
        """
        Normalize a company name for entity matching.

        Removes entity suffixes, expands abbreviations,
        removes accented characters, and collapses whitespace.

        Args:
            name: Raw company name to normalize

        Returns:
            Normalized company name (uppercase, no suffixes)

        Example:
            >>> normalizer = AfricanNameNormalizer()
            >>> normalizer.normalize("Societe Nationale d'Electricite SARL")
            'SOCIETE NATIONALE D ELECTRICITE'
        """
        if not name or not isinstance(name, str):
            logger.warning(f"Invalid name input: {name}")
            return ""

        try:
            result = name.upper().strip()
            logger.debug(f"Normalizing: '{name}' -> '{result}'")

            result = self._strip_accents(result)
            result = self._remove_entity_suffixes(result)
            result = self._expand_abbreviations(result)
            result = self._normalize_arabic_articles(result)
            result = self._remove_special_characters(result)
            result = self._collapse_whitespace(result)

            logger.debug(f"Normalized result: '{result}'")
            return result

        except Exception as e:
            logger.error(f"Normalization failed for '{name}': {e}")
            raise EntityResolutionError(
                f"Failed to normalize name '{name}': {e}",
                details={"input_name": name}
            ) from e

    def _strip_accents(self, text: str) -> str:
        """
        Remove accented characters by mapping to ASCII equivalents.

        Args:
            text: Text with potential accented characters

        Returns:
            Text with accents removed
        """
        replacements: Dict[str, str] = {
            "\u00c0": "A", "\u00c1": "A", "\u00c2": "A",
            "\u00c3": "A", "\u00c4": "A", "\u00c5": "A",
            "\u00c8": "E", "\u00c9": "E", "\u00ca": "E",
            "\u00cb": "E",
            "\u00cc": "I", "\u00cd": "I", "\u00ce": "I",
            "\u00cf": "I",
            "\u00d2": "O", "\u00d3": "O", "\u00d4": "O",
            "\u00d5": "O", "\u00d6": "O",
            "\u00d9": "U", "\u00da": "U", "\u00db": "U",
            "\u00dc": "U",
            "\u00c7": "C",
            "\u00e0": "A", "\u00e1": "A", "\u00e2": "A",
            "\u00e3": "A", "\u00e4": "A", "\u00e5": "A",
            "\u00e8": "E", "\u00e9": "E", "\u00ea": "E",
            "\u00eb": "E",
            "\u00ec": "I", "\u00ed": "I", "\u00ee": "I",
            "\u00ef": "I",
            "\u00f2": "O", "\u00f3": "O", "\u00f4": "O",
            "\u00f5": "O", "\u00f6": "O",
            "\u00f9": "U", "\u00fa": "U", "\u00fb": "U",
            "\u00fc": "U",
            "\u00e7": "C",
        }
        for accented, replacement in replacements.items():
            text = text.replace(accented, replacement)
        return text

    def _remove_entity_suffixes(self, text: str) -> str:
        """
        Remove entity type suffixes from company name.

        Args:
            text: Company name with potential suffixes

        Returns:
            Company name with suffixes removed
        """
        for suffix in sorted(self.ENTITY_SUFFIXES, key=len, reverse=True):
            pattern = r"\b" + re.escape(suffix) + r"\b"
            text = re.sub(pattern, "", text)
            text = text.replace(f"({suffix})", "")
        return text

    def _expand_abbreviations(self, text: str) -> str:
        """
        Expand common abbreviations to full forms.

        Args:
            text: Text with potential abbreviations

        Returns:
            Text with abbreviations expanded
        """
        for abbrev, full in self.ABBREVIATION_MAP.items():
            pattern = r"\b" + re.escape(abbrev) + r"\b"
            text = re.sub(pattern, full, text)
        return text

    def _normalize_arabic_articles(self, text: str) -> str:
        """
        Normalize Arabic article prefixes (El-, Al-, El) to standard form.

        Args:
            text: Text with potential Arabic articles

        Returns:
            Text with articles normalized to 'EL'
        """
        text = re.sub(r"\bEL[\s\-]+", "EL", text)
        text = re.sub(r"\bAL[\s\-]+", "EL", text)
        return text

    def _remove_special_characters(self, text: str) -> str:
        """
        Remove special characters except alphanumeric and whitespace.

        Args:
            text: Text with potential special characters

        Returns:
            Text with special characters removed
        """
        text = re.sub(r"[^A-Z0-9\s]", "", text)
        text = re.sub(r"\bD\s+", "D", text)
        return text

    def _collapse_whitespace(self, text: str) -> str:
        """
        Collapse multiple whitespace to single space and trim.

        Args:
            text: Text with potential extra whitespace

        Returns:
            Text with normalized whitespace
        """
        return re.sub(r"\s+", " ", text).strip()

    def resolve_acronym(
        self,
        acronym: str,
        country_code: str
    ) -> Optional[str]:
        """
        Resolve a known corporate acronym to its full name.

        Args:
            acronym: Acronym to resolve (e.g., 'SNEL', 'NNPC')
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Full company name if found, None otherwise

        Example:
            >>> normalizer = AfricanNameNormalizer()
            >>> normalizer.resolve_acronym("NNPC", "NG")
            'NIGERIAN NATIONAL PETROLEUM CORPORATION'
        """
        if not acronym or not isinstance(acronym, str):
            return None

        acronym_upper = acronym.upper().strip()

        if acronym_upper in self.ACRONYM_REGISTRY:
            country_map = self.ACRONYM_REGISTRY[acronym_upper]
            result = country_map.get(country_code.upper())
            if result:
                logger.debug(
                    f"Resolved acronym {acronym} ({country_code}) -> {result}"
                )
            return result

        logger.debug(f"Unknown acronym: {acronym} ({country_code})")
        return None

    def get_supported_suffixes(self) -> List[str]:
        """
        Get list of supported entity suffixes.

        Returns:
            List of entity suffixes that will be removed
        """
        return self.ENTITY_SUFFIXES.copy()

    def get_supported_abbreviations(self) -> Dict[str, str]:
        """
        Get mapping of supported abbreviations.

        Returns:
            Dictionary of abbreviation to full form
        """
        return self.ABBREVIATION_MAP.copy()
