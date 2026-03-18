"""
@file name_normalizer.py
@description African Name Normalizer for the AfriFlow entity resolution layer.
             Normalises company names across multiple African languages and naming
             conventions to enable accurate entity matching. Handles French entity
             variations (SARL, GIE, SUCC), Portuguese suffixes (Lda, Ltda, Sociedade),
             Arabic transliteration prefixes (El-, Al-), accented characters in
             French and Portuguese, and a registry of known African state-enterprise
             acronyms (SNEL, NNPC, SONATEL, etc.).
@author Thabo Kunene
@created 2026-03-18
"""

import re                           # regex for suffix removal, article normalisation, and cleanup
from typing import Dict, List, Optional  # full type annotations
import logging                      # standard library logger (used via AfriFlow wrapper)

# AfriFlow internal imports
from afriflow.exceptions import EntityResolutionError  # raised on normalisation failures
from afriflow.logging_config import get_logger          # structured logging

# Module-level logger
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

    # Legal entity suffixes to strip during normalisation.
    # Sorted longest-first at runtime so compound suffixes (e.g. "PTY LTD") match
    # before simpler ones (e.g. "LTD").
    ENTITY_SUFFIXES: List[str] = [
        "PTY LTD", "(PTY) LTD", "PTY", "PROPRIETARY LIMITED",
        "LTD", "LIMITED", "INC", "INCORPORATED",
        "CORP", "CORPORATION", "PLC",
        "LLC", "GMBH", "AG",
        "SA", "SARL", "SAS", "SASU",    # French West Africa entity forms
        "LDA", "LTDA",                   # Portuguese (Angola, Mozambique)
        "NPC", "SOC LTD", "RF",          # South African special forms
        "BV", "NV",                      # Dutch/Belgian (Mauritius holding structures)
    ]

    # Abbreviation → full form expansion map.
    # Applied after suffix removal so that abbreviations in the company name core
    # are expanded for better matching consistency.
    ABBREVIATION_MAP: Dict[str, str] = {
        "STE":   "SOCIETE",           # French abbreviation for "Société"
        "SOC":   "SOCIEDADE",         # Portuguese "Sociedade" (company)
        "ETS":   "ETABLISSEMENTS",    # French "Établissements" (trading house)
        "CIE":   "COMPAGNIE",         # French "Compagnie" (company)
        "GRP":   "GROUP",             # common English abbreviation
        "HLDGS": "HOLDINGS",          # common English abbreviation
        "INTL":  "INTERNATIONAL",     # common English abbreviation
        "NATL":  "NATIONAL",          # common English abbreviation
        "MTN":   "MTN",               # kept as-is — it is the canonical brand name
        "STD":   "STANDARD",          # common in South African banking names
    }

    # Known state enterprise acronyms keyed by country code.
    # These are abbreviations that should resolve to full names for entity matching.
    # Keyed as {ACRONYM: {COUNTRY_CODE: FULL_NAME}} to handle cross-border ambiguity.
    ACRONYM_REGISTRY: Dict[str, Dict[str, str]] = {
        "SNEL": {
            "CD": "SOCIETE NATIONALE D ELECTRICITE",  # DRC national electricity utility
        },
        "NNPC": {
            "NG": "NIGERIAN NATIONAL PETROLEUM CORPORATION",  # Nigeria NOC
        },
        "SNCC": {
            "CD": "SOCIETE NATIONALE DES CHEMINS DE FER DU CONGO",  # DRC national railway
        },
        "SONATEL": {
            "SN": "SOCIETE NATIONALE DES TELECOMMUNICATIONS",  # Senegal telecoms
        },
        "SONATRACH": {
            "DZ": "SOCIETE NATIONALE POUR LA RECHERCHE",  # Algeria NOC
        },
        "ESKOM": {
            "ZA": "ELECTRICITY SUPPLY COMMISSION",  # South Africa national electricity utility
        },
    }

    def __init__(self) -> None:
        """
        Initialize the African name normalizer.

        No configuration is required at instantiation — all normalisation
        rules are defined as class-level constants.
        """
        logger.debug("AfricanNameNormalizer initialized")

    def normalize(self, name: str) -> str:
        """
        Normalize a company name for entity matching.

        Applies the following transformations in order:
          1. Upper-case and strip whitespace
          2. Strip Unicode accents (e.g. é → E)
          3. Remove entity type suffixes (e.g. PTY LTD, SARL)
          4. Expand abbreviations (e.g. STE → SOCIETE)
          5. Normalise Arabic article prefixes (El- / Al- → EL)
          6. Remove non-alphanumeric special characters
          7. Collapse multiple whitespace to a single space

        :param name: Raw company name to normalize.
        :return: Normalized company name (uppercase, no suffixes or accents).
        :raises EntityResolutionError: If normalisation raises an unexpected exception.

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

            result = self._strip_accents(result)           # step 1: remove diacritics
            result = self._remove_entity_suffixes(result)  # step 2: strip legal form
            result = self._expand_abbreviations(result)    # step 3: expand abbreviations
            result = self._normalize_arabic_articles(result)  # step 4: normalise AL-/EL-
            result = self._remove_special_characters(result)  # step 5: keep alphanum + space
            result = self._collapse_whitespace(result)     # step 6: normalise whitespace

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
        Remove accented characters by mapping to their ASCII equivalents.

        Covers the full set of accented Latin characters used in French
        and Portuguese corporate names (A-Z with accents).

        :param text: Upper-cased text with potential accented characters.
        :return: Text with all accented characters replaced by their base ASCII form.
        """
        # Explicit character-by-character replacement map (covers FR and PT accents)
        replacements: Dict[str, str] = {
            "\u00c0": "A", "\u00c1": "A", "\u00c2": "A",  # À Á Â
            "\u00c3": "A", "\u00c4": "A", "\u00c5": "A",  # Ã Ä Å
            "\u00c8": "E", "\u00c9": "E", "\u00ca": "E",  # È É Ê
            "\u00cb": "E",                                 # Ë
            "\u00cc": "I", "\u00cd": "I", "\u00ce": "I",  # Ì Í Î
            "\u00cf": "I",                                 # Ï
            "\u00d2": "O", "\u00d3": "O", "\u00d4": "O",  # Ò Ó Ô
            "\u00d5": "O", "\u00d6": "O",                 # Õ Ö
            "\u00d9": "U", "\u00da": "U", "\u00db": "U",  # Ù Ú Û
            "\u00dc": "U",                                 # Ü
            "\u00c7": "C",                                 # Ç
            "\u00e0": "A", "\u00e1": "A", "\u00e2": "A",  # à á â (lowercase versions)
            "\u00e3": "A", "\u00e4": "A", "\u00e5": "A",
            "\u00e8": "E", "\u00e9": "E", "\u00ea": "E",
            "\u00eb": "E",
            "\u00ec": "I", "\u00ed": "I", "\u00ee": "I",
            "\u00ef": "I",
            "\u00f2": "O", "\u00f3": "O", "\u00f4": "O",
            "\u00f5": "O", "\u00f6": "O",
            "\u00f9": "U", "\u00fa": "U", "\u00fb": "U",
            "\u00fc": "U",
            "\u00e7": "C",                                 # ç (cedilla)
        }
        for accented, replacement in replacements.items():
            text = text.replace(accented, replacement)
        return text

    def _remove_entity_suffixes(self, text: str) -> str:
        """
        Remove entity type suffixes from a company name.

        Iterates suffixes in reverse length order (longest first) to ensure
        compound suffixes like "PTY LTD" are matched before simpler "LTD".

        :param text: Upper-cased company name with potential legal form suffix.
        :return: Company name with entity suffixes removed.
        """
        # Sort longest-first here to ensure greedy matching of compound suffixes
        for suffix in sorted(self.ENTITY_SUFFIXES, key=len, reverse=True):
            pattern = r"\b" + re.escape(suffix) + r"\b"
            text = re.sub(pattern, "", text)
            text = text.replace(f"({suffix})", "")  # also handle parenthesised forms
        return text

    def _expand_abbreviations(self, text: str) -> str:
        """
        Expand common abbreviations to their full forms.

        :param text: Upper-cased company name after suffix removal.
        :return: Text with abbreviations expanded to full forms.
        """
        for abbrev, full in self.ABBREVIATION_MAP.items():
            pattern = r"\b" + re.escape(abbrev) + r"\b"
            text = re.sub(pattern, full, text)
        return text

    def _normalize_arabic_articles(self, text: str) -> str:
        """
        Normalise Arabic article prefixes (El-, Al-, El) to a standard 'EL' form.

        Both AL-X and EL-X variants are normalised to EL to prevent duplicates
        (e.g. "Al-Ameen Bank" and "El-Ameen Bank" should match).

        :param text: Upper-cased company name.
        :return: Text with Arabic articles normalised to 'EL'.
        """
        text = re.sub(r"\bEL[\s\-]+", "EL", text)  # EL- or EL  → EL
        text = re.sub(r"\bAL[\s\-]+", "EL", text)  # AL- or AL  → EL (unified form)
        return text

    def _remove_special_characters(self, text: str) -> str:
        """
        Remove special characters, keeping only alphanumeric characters and spaces.

        Also handles the French genitive apostrophe pattern "D'" (e.g. "d'Electricite")
        which produces "D " after apostrophe removal — collapsed to "D".

        :param text: Text after abbreviation expansion.
        :return: Text with special characters removed.
        """
        text = re.sub(r"[^A-Z0-9\s]", "", text)  # keep only A-Z, 0-9, and spaces
        text = re.sub(r"\bD\s+", "D", text)        # collapse "D " → "D" (French genitive)
        return text

    def _collapse_whitespace(self, text: str) -> str:
        """
        Collapse multiple consecutive whitespace characters to a single space and trim.

        :param text: Text after special character removal.
        :return: Whitespace-normalised string.
        """
        return re.sub(r"\s+", " ", text).strip()

    def resolve_acronym(
        self,
        acronym: str,
        country_code: str
    ) -> Optional[str]:
        """
        Resolve a known corporate acronym to its full legal name.

        :param acronym: Acronym to resolve (e.g. 'SNEL', 'NNPC').
        :param country_code: ISO 3166-1 alpha-2 country code to disambiguate
                             acronyms that appear in multiple countries.
        :return: Full company name string if found, None otherwise.

        Example:
            >>> normalizer = AfricanNameNormalizer()
            >>> normalizer.resolve_acronym("NNPC", "NG")
            'NIGERIAN NATIONAL PETROLEUM CORPORATION'
        """
        # Guard against None or non-string input
        if not acronym or not isinstance(acronym, str):
            return None

        acronym_upper = acronym.upper().strip()

        if acronym_upper in self.ACRONYM_REGISTRY:
            # Look up the full name for the given country code
            country_map = self.ACRONYM_REGISTRY[acronym_upper]
            result = country_map.get(country_code.upper())
            if result:
                logger.debug(
                    f"Resolved acronym {acronym} ({country_code}) -> {result}"
                )
            return result  # None if country_code not in registry for this acronym

        logger.debug(f"Unknown acronym: {acronym} ({country_code})")
        return None  # acronym not in registry

    def get_supported_suffixes(self) -> List[str]:
        """
        Get a copy of the list of supported entity suffixes.

        :return: List of entity suffix strings that will be stripped during normalisation.
        """
        return self.ENTITY_SUFFIXES.copy()

    def get_supported_abbreviations(self) -> Dict[str, str]:
        """
        Get a copy of the supported abbreviation expansion mapping.

        :return: Dict of abbreviation → full form.
        """
        return self.ABBREVIATION_MAP.copy()
