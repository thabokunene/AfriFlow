"""
@file multilingual_normaliser.py
@description Multilingual entity name normalizer for the AfriFlow entity resolution
    layer, handling corporate suffixes, personal name conventions, and phonetic
    substitutions across English, Swahili, Yoruba, Hausa, and French.
@author Thabo Kunene
@created 2026-03-19
"""

import re                        # regex for tokenisation, suffix matching, and MSISDN cleaning
import unicodedata               # NFD decomposition for accent stripping
from dataclasses import dataclass, field  # structured result value objects
from typing import Dict, List, Optional, Tuple  # full type annotations
from enum import Enum            # typed language hints and entity type categories

# AfriFlow internal imports
from afriflow.exceptions import ConfigurationError  # raised for invalid entity_type inputs
from afriflow.logging_config import get_logger, log_operation  # structured logging

# Module-level logger
logger = get_logger("entity_resolution.multilingual_normaliser")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LanguageHint(Enum):
    """Detected language / script family for a raw entity string."""
    ENGLISH    = "en"   # English (default for most corporate names)
    SWAHILI    = "sw"   # Swahili (East Africa — detected via patronymics BIN/BINTI)
    YORUBA     = "yo"   # Yoruba (Nigeria — detected via diacritics or tokens)
    ZULU_XHOSA = "zu"   # Zulu / Xhosa (Southern Africa — detected via Bantu prefixes)
    FRENCH     = "fr"   # French (West/Central Africa — detected via SARL, GIE, accents)
    ARABIC     = "ar"   # Arabic / Romanised Arabic (North Africa — detected via AL-/EL-)
    HAUSA      = "ha"   # Hausa (Northern Nigeria — detected via ALHAJI, MALAM)
    UNKNOWN    = "unk"  # Could not determine language with confidence


class EntityType(Enum):
    """Broad type of the entity being normalised."""
    PERSON  = "person"   # natural person (individual)
    COMPANY = "company"  # legal entity (corporate)
    MSISDN  = "msisdn"   # mobile subscriber number
    AUTO    = "auto"     # auto-detect type from the input string


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class NormalisedEntity:
    """
    We represent the result of normalising a single raw entity string.

    Attributes:
        original:       Unmodified input string.
        normalised:     Cleaned, upper-cased canonical form.
        language_hint:  Detected language / script family code.
        entity_type:    Resolved entity type (person / company / msisdn).
        tokens:         Whitespace-tokenised normalised string.
        phonetic_key:   Soundex-like phonetic key for fuzzy bucket matching.
        confidence:     Normalisation confidence in [0.0, 1.0].
        suffix_found:   Canonical company suffix key found (if any).
    """

    original: str                                        # raw input string
    normalised: str                                      # cleaned canonical form
    language_hint: str                                   # LanguageHint value
    entity_type: str                                     # EntityType value
    tokens: List[str] = field(default_factory=list)      # tokenised normalised form
    phonetic_key: str = ""                               # Soundex-inspired phonetic key
    confidence: float = 1.0                             # normalisation confidence [0, 1]
    suffix_found: Optional[str] = None                  # canonical suffix key (e.g. "PTY_LTD")


# ---------------------------------------------------------------------------
# Main normaliser class
# ---------------------------------------------------------------------------

class MultilingualNormaliser:
    """
    We normalise entity names across the linguistic diversity of 20
    African markets, handling corporate suffixes, personal-name
    conventions, Hausa phonetic substitutions, Romanised Arabic
    prefixes, and MSISDN country-code stripping.

    Usage::

        normaliser = MultilingualNormaliser()
        result = normaliser.normalise("Dangote Cement (Pty) Ltd")
        print(result.normalised)   # → "DANGOTE CEMENT"
    """

    # ------------------------------------------------------------------
    # Class-level lookup tables
    # ------------------------------------------------------------------

    # Map raw suffix variants → canonical key. Sorted longest-first at runtime
    # so that "(PTY) LTD" matches before plain "LTD" (greedy longest-suffix matching).
    COMPANY_SUFFIX_MAP: Dict[str, str] = {
        "(PTY) LTD":           "PTY_LTD",
        "(PTY) LIMITED":       "PTY_LTD",
        "PTY LTD":             "PTY_LTD",
        "PTY LIMITED":         "PTY_LTD",
        "PROPRIETARY LIMITED": "PTY_LTD",
        "PROPRIETARY LTD":     "PTY_LTD",
        "LIMITED":             "LTD",
        "LTD":                 "LTD",
        "PLC":                 "PLC",
        "PUBLIC LIMITED COMPANY": "PLC",
        "LLC":                 "LLC",
        "L.L.C":               "LLC",
        "L.L.C.":              "LLC",
        "INC":                 "INC",
        "INCORPORATED":        "INC",
        "CORP":                "CORP",
        "CORPORATION":         "CORP",
        "SA":                  "SA",
        "S.A.":                "SA",
        "S.A":                 "SA",
        "NV":                  "NV",
        "N.V.":                "NV",
        "SARL":                "SARL",   # Société à responsabilité limitée (French WA)
        "S.A.R.L.":            "SARL",
        "S.A.R.L":             "SARL",
        "SAS":                 "SAS",    # Société par actions simplifiée
        "GIE":                 "GIE",    # Groupement d'intérêt économique
        "SUCC":                "SUCC",   # Succursale (branch)
        "EP":                  "EP",     # Entreprise personnelle
        "GMBH":                "GMBH",
        "AG":                  "AG",
        "BV":                  "BV",
        "N.V":                 "NV",
        "RF":                  "RF",     # Ring-fenced (SA non-profit)
        "NPC":                 "NPC",    # Non-profit company (South Africa)
        "SOC":                 "SOC",
        "CC":                  "CC",     # Close corporation (legacy South Africa)
    }

    # Noise tokens stripped from all entity types — prepositions and articles
    # that carry no identifying information.
    NOISE_TOKENS: frozenset = frozenset({
        "AND", "ET", "&", "OF", "THE", "DE", "DU", "DES",
        "LA", "LE", "LES", "L", "D", "A", "AN",
    })

    # Hausa phonetic substitutions: source token → normalised equivalent.
    # Applied to the upper-cased text when the Hausa language hint is detected.
    HAUSA_SUBSTITUTIONS: Dict[str, str] = {
        "KH": "K",   # velar fricative → stop
        "GH": "G",   # velar fricative → stop
        "PH": "F",   # labio-dental fricative (borrowed English)
        "TS": "C",   # ejective approximation
        "DY": "J",   # palatalisation
    }

    # Arabic definite-article prefixes normalised to bare form.
    # Both AL- and EL- variants are encountered in North African entity names.
    ARABIC_ARTICLES: Tuple[str, ...] = (
        "AL-", "AL ", "EL-", "EL ", "EL",
    )

    # Swahili patronymic connectors stripped from person names.
    # "Ahmed bin Hassan" and "Ahmed Hassan" should produce the same normalised form.
    SWAHILI_PATRONYMICS: frozenset = frozenset({
        "BIN", "BINTI", "BINT",
    })

    # Zulu / Xhosa nominal-class prefixes commonly seen in personal names.
    # Detected for language hinting purposes.
    BANTU_PREFIXES: Tuple[str, ...] = (
        "NK", "MA", "SI", "MU", "MI", "BA", "BU", "LU", "KU",
    )

    # Country code → international dialling prefix (E.164 without the leading '+').
    # Used by normalise_msisdn() to convert local-format numbers.
    COUNTRY_DIAL_PREFIX: Dict[str, str] = {
        "ZA": "27",   # South Africa
        "NG": "234",  # Nigeria
        "KE": "254",  # Kenya
        "GH": "233",  # Ghana
        "TZ": "255",  # Tanzania
        "UG": "256",  # Uganda
        "CI": "225",  # Côte d'Ivoire
        "SN": "221",  # Senegal
        "CM": "237",  # Cameroon
        "ET": "251",  # Ethiopia
        "EG": "20",   # Egypt
        "MA": "212",  # Morocco
        "DZ": "213",  # Algeria
        "TN": "216",  # Tunisia
        "ZM": "260",  # Zambia
        "ZW": "263",  # Zimbabwe
        "MZ": "258",  # Mozambique
        "AO": "244",  # Angola
        "RW": "250",  # Rwanda
        "MU": "230",  # Mauritius
    }

    def __init__(self, custom_suffixes: Optional[Dict[str, str]] = None) -> None:
        """
        Initialise the multilingual normaliser.

        :param custom_suffixes: Optional override/extension dict for COMPANY_SUFFIX_MAP.
                                Keys and values must both be strings.
        :raises ConfigurationError: If custom_suffixes contains non-string values.
        """
        if custom_suffixes is not None:
            # Validate each key-value pair before merging
            for k, v in custom_suffixes.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ConfigurationError(
                        "custom_suffixes keys and values must be strings",
                        details={"bad_key": k, "bad_value": v},
                    )
            merged = {**self.COMPANY_SUFFIX_MAP, **custom_suffixes}  # custom overrides built-in
        else:
            merged = dict(self.COMPANY_SUFFIX_MAP)

        # Pre-sort suffixes longest-first so greedy matching works correctly.
        # "(PTY) LTD" (9 chars) must match before "LTD" (3 chars).
        self._sorted_suffixes: List[Tuple[str, str]] = sorted(
            merged.items(), key=lambda item: len(item[0]), reverse=True
        )
        logger.info(
            "MultilingualNormaliser initialised with "
            f"{len(self._sorted_suffixes)} company suffixes"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalise(
        self,
        text: str,
        entity_type: str = "auto",
    ) -> NormalisedEntity:
        """
        We normalise a single raw entity string.

        :param text: Raw entity string (name, company name, or MSISDN).
        :param entity_type: One of "auto", "person", "company", "msisdn".
        :return: NormalisedEntity with all fields populated.
        :raises ConfigurationError: If entity_type is not a recognised value.
        """
        valid_types = {e.value for e in EntityType}
        if entity_type not in valid_types:
            raise ConfigurationError(
                f"entity_type must be one of {sorted(valid_types)}",
                details={"received": entity_type},
            )

        log_operation(
            logger, "normalise", "started",
            text_len=len(text), entity_type=entity_type,
        )

        # Guard: return empty result for None or non-string input
        if not text or not isinstance(text, str):
            return NormalisedEntity(
                original=text,
                normalised="",
                language_hint=LanguageHint.UNKNOWN.value,
                entity_type=entity_type if entity_type != "auto" else EntityType.UNKNOWN.value,
                confidence=0.0,
            )

        # Auto-detect entity type from the content if not explicitly specified
        resolved_type = self._resolve_entity_type(text, entity_type)

        # MSISDN normalisation is a separate, simpler pipeline
        if resolved_type == EntityType.MSISDN.value:
            normalised_msisdn = self.normalise_msisdn(text)
            return NormalisedEntity(
                original=text,
                normalised=normalised_msisdn,
                language_hint=LanguageHint.UNKNOWN.value,
                entity_type=EntityType.MSISDN.value,
                tokens=[normalised_msisdn],
                phonetic_key=normalised_msisdn,
                confidence=1.0,  # MSISDN normalisation is deterministic
            )

        # Detect language family for language-specific transformations
        lang_hint = self.detect_language_hint(text)
        upper = self._to_upper_strip_accents(text)  # normalise casing and remove diacritics

        suffix_found: Optional[str] = None
        if resolved_type == EntityType.COMPANY.value:
            # Strip company legal form suffix (e.g. "Pty Ltd", "PLC", "SARL")
            base, suffix_found = self.extract_company_suffix(upper)
            upper = base  # continue processing with the stripped base name

        # Apply Hausa phonetic substitutions (only when Hausa is detected)
        if lang_hint == LanguageHint.HAUSA.value:
            upper = self._apply_hausa_substitutions(upper)

        # Normalise Arabic article prefixes (AL- → AL, EL- → AL)
        upper = self._normalise_arabic_articles(upper)

        # Tokenise on whitespace and punctuation, then remove noise tokens
        tokens = self._tokenise(upper)
        if resolved_type == EntityType.PERSON.value:
            tokens = self._strip_patronymics(tokens)  # remove BIN/BINTI for Swahili names
        tokens = [t for t in tokens if t not in self.NOISE_TOKENS]

        normalised = " ".join(tokens)
        phonetic_key = self.generate_phonetic_key(normalised)  # Soundex-style bucket key

        # Estimate how much the normalisation changed the input (Jaccard similarity)
        confidence = self._estimate_confidence(
            text, normalised, resolved_type, lang_hint
        )

        result = NormalisedEntity(
            original=text,
            normalised=normalised,
            language_hint=lang_hint,
            entity_type=resolved_type,
            tokens=tokens,
            phonetic_key=phonetic_key,
            confidence=confidence,
            suffix_found=suffix_found,
        )

        log_operation(
            logger, "normalise", "completed",
            normalised=normalised, lang_hint=lang_hint,
        )
        return result

    def normalise_batch(
        self,
        texts: List[str],
        entity_type: str = "auto",
    ) -> List[NormalisedEntity]:
        """
        We normalise a list of raw entity strings in batch.

        :param texts: List of raw strings to normalise.
        :param entity_type: Entity type hint applied to all items.
        :return: List of NormalisedEntity objects in the same order as input.
        """
        logger.info(f"Batch normalising {len(texts)} entities (type={entity_type})")
        return [self.normalise(t, entity_type) for t in texts]

    def generate_phonetic_key(self, text: str) -> str:
        """
        We generate a Soundex-inspired phonetic key for grouping near-homophone
        entity names into the same fuzzy matching bucket.

        Algorithm:
          1. Upper-case and take the first character of the first word.
          2. Replace consonant groups with Soundex digit codes.
          3. Remove vowels (except the leading letter).
          4. Collapse adjacent identical digit codes.
          5. Pad or truncate to exactly 6 characters.

        :param text: Normalised (upper-cased) text string.
        :return: 6-character phonetic key (letter + up to 5 digits, zero-padded).
        """
        if not text:
            return "000000"  # sentinel for empty input

        # Use only the first word — company names are primarily differentiated by first token
        word = text.split()[0] if " " in text else text
        word = re.sub(r"[^A-Z]", "", word.upper())  # keep only alpha characters

        if not word:
            return "000000"

        # Soundex consonant coding table (vowels → "0", not stored)
        coding: Dict[str, str] = {
            "B": "1", "F": "1", "P": "1", "V": "1",   # labial consonants
            "C": "2", "G": "2", "J": "2", "K": "2",   # velar/palatal consonants
            "Q": "2", "S": "2", "X": "2", "Z": "2",
            "D": "3", "T": "3",                         # dental/alveolar stops
            "L": "4",                                   # lateral
            "M": "5", "N": "5",                         # nasals
            "R": "6",                                   # rhotic
        }

        first_letter = word[0]
        coded = first_letter
        prev_code = coding.get(first_letter, "0")  # initial code prevents double-coding

        for char in word[1:]:
            code = coding.get(char, "0")
            # Add code only if it is a consonant AND differs from the previous code
            if code != "0" and code != prev_code:
                coded += code
            prev_code = code
            if len(coded) == 6:  # stop once we have the target length
                break

        return coded.ljust(6, "0")  # zero-pad to exactly 6 characters

    def detect_language_hint(self, text: str) -> str:
        """
        We detect the most likely language / script family of a raw entity string
        using a lightweight heuristic approach (no ML model required).

        :param text: Raw entity string.
        :return: Language hint code from LanguageHint enum values.
        """
        upper = text.upper()
        tokens_set = set(re.findall(r"[A-Z]+", upper))

        # Swahili: patronymic tokens are highly distinctive
        if tokens_set & {"BIN", "BINTI", "BINT"}:
            return LanguageHint.SWAHILI.value

        # Yoruba: tonal diacritics (Ọ, Ẹ, Ṣ) or common Yoruba name tokens
        if any(ch in text for ch in ("Ọ", "ọ", "Ẹ", "ẹ", "Ṣ", "ṣ")):
            return LanguageHint.YORUBA.value
        if tokens_set & {"OLU", "ADE", "OBI", "CHI", "EMEKA"}:
            return LanguageHint.YORUBA.value

        # French West Africa: entity form markers or accented characters
        if tokens_set & {"SARL", "GIE", "SUCC", "SOCIETE", "ETS", "CIE"}:
            return LanguageHint.FRENCH.value
        if any(ch in text for ch in ("é", "è", "ê", "ç", "â", "ô")):
            return LanguageHint.FRENCH.value

        # Arabic / North African: article prefix AL- or EL-
        if tokens_set & {"AL", "EL"} or re.search(r"\bAL[-\s]|\bEL[-\s]", upper):
            return LanguageHint.ARABIC.value

        # Hausa: honorific/title tokens common in Northern Nigerian corporate names
        if tokens_set & {"ALHAJI", "MALAM", "MALLAM", "SARKI"}:
            return LanguageHint.HAUSA.value

        # Zulu / Xhosa: names often start with Bantu nominal-class prefixes
        if any(upper.startswith(p) for p in ("NK", "MA", "SI", "ND", "MZ")):
            return LanguageHint.ZULU_XHOSA.value

        # Default: English (covers most formal corporate names in Africa)
        return LanguageHint.ENGLISH.value

    def extract_company_suffix(self, text: str) -> Tuple[str, Optional[str]]:
        """
        We extract the canonical company suffix from an upper-cased name,
        returning the base name and the suffix key.

        :param text: Upper-cased company name (accents already stripped).
        :return: Tuple of (base_name_without_suffix, canonical_suffix_key or None).
        """
        # Clean parenthetical punctuation before suffix matching
        cleaned = re.sub(r"[(),.]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Iterate sorted suffixes (longest first) and remove the first match found
        for raw_suffix, canonical_key in self._sorted_suffixes:
            pattern = r"(?:^|\s)\(?" + re.escape(raw_suffix) + r"\)?(?:\s|$)"
            if re.search(pattern, cleaned):
                base = re.sub(pattern, " ", cleaned).strip()
                base = re.sub(r"\s+", " ", base).strip()
                return base, canonical_key

        return text, None  # no suffix found — return original text unchanged

    def normalise_msisdn(
        self,
        msisdn: str,
        default_country: str = "ZA",
    ) -> str:
        """
        We normalise a mobile subscriber number (MSISDN) to E.164 format
        without the leading '+', stripping spaces, dashes, and brackets.

        Country code is prepended if the number begins with '0' (local format).

        :param msisdn: Raw MSISDN string.
        :param default_country: ISO 3166-1 alpha-2 code used when no country
                                prefix is detected (default "ZA" for South Africa).
        :return: Normalised digits-only MSISDN string.
        :raises ConfigurationError: If default_country is not in the dial prefix table.
        """
        if default_country not in self.COUNTRY_DIAL_PREFIX:
            raise ConfigurationError(
                f"Unknown default_country '{default_country}'. "
                f"Supported: {sorted(self.COUNTRY_DIAL_PREFIX.keys())}",
                details={"default_country": default_country},
            )

        # Strip all non-digit characters except leading '+' which indicates E.164
        digits_only = re.sub(r"[^\d+]", "", msisdn)

        # Remove leading '+' after stripping — we work with bare digits
        if digits_only.startswith("+"):
            digits_only = digits_only[1:]

        # If the number already starts with a known country dialling prefix, return as-is
        for _country, prefix in self.COUNTRY_DIAL_PREFIX.items():
            if digits_only.startswith(prefix):
                return digits_only

        # Local format: numbers starting with '0' need country prefix prepended
        if digits_only.startswith("0"):
            prefix = self.COUNTRY_DIAL_PREFIX[default_country]
            return prefix + digits_only[1:]  # replace leading '0' with country prefix

        # Assume already a full number without any country prefix
        return digits_only

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_entity_type(self, text: str, entity_type: str) -> str:
        """
        We resolve 'auto' entity type using heuristics.

        Heuristic order:
          1. Digit-heavy string → MSISDN
          2. Known company suffix present → COMPANY
          3. Short all-caps tokens → COMPANY
          4. Default → PERSON

        :param text: Raw entity string.
        :param entity_type: May be "auto" or an explicit type value.
        :return: Resolved entity type string.
        """
        if entity_type != EntityType.AUTO.value:
            return entity_type  # already explicit — nothing to do

        stripped = re.sub(r"[^\d+]", "", text)
        # If more than 70% of characters are digits, treat as MSISDN
        if len(stripped) >= 8 and len(stripped) / max(len(text), 1) > 0.7:
            return EntityType.MSISDN.value

        upper = text.upper()
        # If any known company suffix is present, classify as COMPANY
        for raw_suffix in self.COMPANY_SUFFIX_MAP:
            if raw_suffix in upper:
                return EntityType.COMPANY.value

        # Short all-caps names are typically corporate abbreviations (e.g. "MTN", "SAFCO")
        tokens = upper.split()
        if len(tokens) <= 2 and all(t.isupper() for t in tokens):
            return EntityType.COMPANY.value

        return EntityType.PERSON.value  # default fallback

    def _to_upper_strip_accents(self, text: str) -> str:
        """
        We upper-case a string and strip Unicode accents / diacritics using NFD decomposition.

        :param text: Any string, possibly containing accented characters.
        :return: Upper-cased string with combining characters removed.
        """
        upper = text.upper()
        # NFD decomposition separates base characters from their combining marks
        nfd = unicodedata.normalize("NFD", upper)
        # Category "Mn" = Mark, Nonspacing — these are the combining diacritics
        stripped = "".join(
            ch for ch in nfd
            if unicodedata.category(ch) != "Mn"
        )
        return stripped

    def _apply_hausa_substitutions(self, text: str) -> str:
        """
        We apply Hausa phonetic substitutions to normalise spelling variants.

        :param text: Upper-cased entity name.
        :return: Text with Hausa phoneme substitutions applied.
        """
        for source, target in self.HAUSA_SUBSTITUTIONS.items():
            text = re.sub(r"\b" + source, target, text)  # word-boundary anchor
        return text

    def _normalise_arabic_articles(self, text: str) -> str:
        """
        We strip or normalise Arabic definite-article prefixes to a standard "AL" form.

        :param text: Upper-cased entity name.
        :return: Text with Arabic articles normalised.
        """
        for article in self.ARABIC_ARTICLES:
            text = re.sub(r"\b" + re.escape(article), "AL", text)
        return text

    def _tokenise(self, text: str) -> List[str]:
        """
        We tokenise on whitespace and punctuation, keeping only alpha-numeric tokens.

        :param text: Upper-cased, cleaned entity string.
        :return: List of non-empty tokens.
        """
        # Split on any punctuation or whitespace character
        raw_tokens = re.split(r"[\s\-_/\\,;:.()\[\]{}\"']+", text)
        return [t for t in raw_tokens if t]  # filter empty strings

    def _strip_patronymics(self, tokens: List[str]) -> List[str]:
        """
        We remove Swahili patronymic connector tokens from person name token lists.

        :param tokens: Tokenised person name.
        :return: Tokens with BIN/BINTI/BINT removed.
        """
        return [t for t in tokens if t not in self.SWAHILI_PATRONYMICS]

    def _estimate_confidence(
        self,
        original: str,
        normalised: str,
        entity_type: str,
        lang_hint: str,
    ) -> float:
        """
        We estimate normalisation confidence based on how much the string changed
        and whether the language was clearly identified.

        Method: Jaccard similarity between original tokens and normalised tokens,
        with small bonuses for explicit entity_type and non-UNKNOWN language.

        :param original: Original input string.
        :param normalised: Resulting normalised string.
        :param entity_type: Resolved entity type.
        :param lang_hint: Detected language hint.
        :return: Confidence score in [0.0, 1.0].
        """
        if not normalised:
            return 0.0  # completely empty result — zero confidence

        # Jaccard similarity: how many tokens survive normalisation
        orig_tokens = set(re.findall(r"[A-Z]+", original.upper()))
        norm_tokens = set(normalised.split())
        if not orig_tokens:
            return 0.5  # no original tokens — uncertain

        intersection = orig_tokens & norm_tokens
        union = orig_tokens | norm_tokens
        jaccard = len(intersection) / len(union) if union else 0.0

        # Small bonus for explicitly declared entity type (reduces ambiguity)
        type_bonus = 0.05 if entity_type != EntityType.AUTO.value else 0.0

        # Small bonus for a clearly identified language (reduces noise token risk)
        lang_bonus = 0.05 if lang_hint != LanguageHint.UNKNOWN.value else 0.0

        return min(1.0, jaccard + type_bonus + lang_bonus)  # cap at 1.0


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    normaliser = MultilingualNormaliser()

    samples = [
        # Corporate names — various suffix conventions
        ("Dangote Cement (Pty) Ltd",       "company"),
        ("MTN Group Limited",              "company"),
        ("SAFARICOM PLC",                  "company"),
        ("Société Générale de Banque SA",  "company"),  # French West Africa
        ("Groupe Banque Populaire SARL",   "company"),  # French/Arabic
        ("Al-Baraka Bank NV",              "company"),  # Arabic prefix
        # Personal names
        ("Amina Binti Hassan",             "person"),   # Swahili patronymic
        ("Nkosazana Dlamini",              "person"),   # Zulu prefix
        ("Malam Khadafi Ghali",            "person"),   # Hausa kh/gh substitution
        # MSISDN normalisation
        ("0721234567",                     "msisdn"),   # SA local format
        ("+27821234567",                   "msisdn"),   # SA E.164
        ("+2348012345678",                 "msisdn"),   # Nigeria
        # Auto-detection
        ("Shoprite Holdings",              "auto"),
    ]

    print(f"{'Original':<40} {'Type':<10} {'Normalised':<35} {'Key':<8} {'Conf'}")
    print("-" * 110)
    for raw, etype in samples:
        result = normaliser.normalise(raw, etype)
        print(
            f"{result.original:<40} "
            f"{result.entity_type:<10} "
            f"{result.normalised:<35} "
            f"{result.phonetic_key:<8} "
            f"{result.confidence:.2f}"
        )

    # Batch normalisation demo: three variants of the same company
    print("\nBatch normalisation (3 items):")
    batch = normaliser.normalise_batch(
        ["Ecobank Ghana Ltd", "ECOBANK GHANA LIMITED", "ecobank ghana"],
        entity_type="company",
    )
    for item in batch:
        print(f"  {item.original!r:35} → {item.normalised!r:25} key={item.phonetic_key}")
