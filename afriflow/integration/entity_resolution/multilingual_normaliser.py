"""
integration/entity_resolution/multilingual_normaliser.py

Multilingual entity name normaliser for pan-African financial services.

We normalise entity names — personal, corporate, and MSISDN — across
the full linguistic landscape encountered in 20 African markets: Bantu
languages (Swahili, Zulu, Xhosa), Niger-Congo (Yoruba, Hausa), French
West/Central Africa, Romanised Arabic (North Africa), and English. This
is foundational to the Golden Record pipeline: without it, "Dangote
Cement Plc", "DANGOTE CEMENT", and "Dangote Cement Limited" produce
three golden IDs instead of one.

DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
Group, MTN, or any affiliated entity. It is a demonstration of concept,
domain knowledge, and data engineering skill by Thabo Kunene.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("entity_resolution.multilingual_normaliser")


# ---------------------------------------------------------------------------
# Language hint enum
# ---------------------------------------------------------------------------

class LanguageHint(Enum):
    """Detected language / script family for a raw entity string."""
    ENGLISH = "en"
    SWAHILI = "sw"
    YORUBA = "yo"
    ZULU_XHOSA = "zu"
    FRENCH = "fr"
    ARABIC = "ar"
    HAUSA = "ha"
    UNKNOWN = "unk"


class EntityType(Enum):
    """Broad type of the entity being normalised."""
    PERSON = "person"
    COMPANY = "company"
    MSISDN = "msisdn"
    AUTO = "auto"


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

    original: str
    normalised: str
    language_hint: str
    entity_type: str
    tokens: List[str] = field(default_factory=list)
    phonetic_key: str = ""
    confidence: float = 1.0
    suffix_found: Optional[str] = None


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

    # Map raw suffix variants → canonical key.  Sorted longest-first at
    # runtime so that "(PTY) LTD" matches before plain "LTD".
    COMPANY_SUFFIX_MAP: Dict[str, str] = {
        "(PTY) LTD":          "PTY_LTD",
        "(PTY) LIMITED":      "PTY_LTD",
        "PTY LTD":            "PTY_LTD",
        "PTY LIMITED":        "PTY_LTD",
        "PROPRIETARY LIMITED": "PTY_LTD",
        "PROPRIETARY LTD":    "PTY_LTD",
        "LIMITED":            "LTD",
        "LTD":                "LTD",
        "PLC":                "PLC",
        "PUBLIC LIMITED COMPANY": "PLC",
        "LLC":                "LLC",
        "L.L.C":              "LLC",
        "L.L.C.":             "LLC",
        "INC":                "INC",
        "INCORPORATED":       "INC",
        "CORP":               "CORP",
        "CORPORATION":        "CORP",
        "SA":                 "SA",
        "S.A.":               "SA",
        "S.A":                "SA",
        "NV":                 "NV",
        "N.V.":               "NV",
        "SARL":               "SARL",   # Société à responsabilité limitée
        "S.A.R.L.":           "SARL",
        "S.A.R.L":            "SARL",
        "SAS":                "SAS",    # Société par actions simplifiée
        "GIE":                "GIE",    # Groupement d'intérêt économique
        "SUCC":               "SUCC",   # Succursale (branch)
        "EP":                 "EP",     # Entreprise personnelle
        "GMBH":               "GMBH",
        "AG":                 "AG",
        "BV":                 "BV",
        "N.V":                "NV",
        "RF":                 "RF",     # Ring-fenced (SA non-profit)
        "NPC":                "NPC",    # Non-profit company (SA)
        "SOC":                "SOC",
        "CC":                 "CC",     # Close corporation (legacy SA)
    }

    # Noise tokens stripped from all entity types
    NOISE_TOKENS: frozenset = frozenset({
        "AND", "ET", "&", "OF", "THE", "DE", "DU", "DES",
        "LA", "LE", "LES", "L", "D", "A", "AN",
    })

    # Hausa phonetic substitutions (source → target)
    HAUSA_SUBSTITUTIONS: Dict[str, str] = {
        "KH": "K",
        "GH": "G",
        "PH": "F",
        "TS": "C",   # Hausa ejective ts → approximate
        "DY": "J",   # palatalisation
    }

    # Arabic article prefixes normalised to bare form
    ARABIC_ARTICLES: Tuple[str, ...] = (
        "AL-", "AL ", "EL-", "EL ", "EL",
    )

    # Swahili patronymic tokens stripped from person names
    SWAHILI_PATRONYMICS: frozenset = frozenset({
        "BIN", "BINTI", "BINT",
    })

    # Zulu / Xhosa nominal-class prefixes commonly seen in personal names
    BANTU_PREFIXES: Tuple[str, ...] = (
        "NK", "MA", "SI", "MU", "MI", "BA", "BU", "LU", "KU",
    )

    # Country code → international dialling prefix
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

        Args:
            custom_suffixes: Optional override / extension to COMPANY_SUFFIX_MAP.

        Raises:
            ConfigurationError: If custom_suffixes contains non-string values.
        """
        if custom_suffixes is not None:
            for k, v in custom_suffixes.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ConfigurationError(
                        "custom_suffixes keys and values must be strings",
                        details={"bad_key": k, "bad_value": v},
                    )
            merged = {**self.COMPANY_SUFFIX_MAP, **custom_suffixes}
        else:
            merged = dict(self.COMPANY_SUFFIX_MAP)

        # Build a sorted list of suffixes (longest first) for greedy matching
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

        Args:
            text:        Raw entity string (name, company, or MSISDN).
            entity_type: One of "auto", "person", "company", "msisdn".

        Returns:
            NormalisedEntity with all fields populated.

        Raises:
            ConfigurationError: If entity_type is not a recognised value.
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

        if not text or not isinstance(text, str):
            return NormalisedEntity(
                original=text,
                normalised="",
                language_hint=LanguageHint.UNKNOWN.value,
                entity_type=entity_type if entity_type != "auto" else EntityType.UNKNOWN.value,
                confidence=0.0,
            )

        # Auto-detect type if needed
        resolved_type = self._resolve_entity_type(text, entity_type)

        if resolved_type == EntityType.MSISDN.value:
            normalised_msisdn = self.normalise_msisdn(text)
            return NormalisedEntity(
                original=text,
                normalised=normalised_msisdn,
                language_hint=LanguageHint.UNKNOWN.value,
                entity_type=EntityType.MSISDN.value,
                tokens=[normalised_msisdn],
                phonetic_key=normalised_msisdn,
                confidence=1.0,
            )

        lang_hint = self.detect_language_hint(text)
        upper = self._to_upper_strip_accents(text)

        suffix_found: Optional[str] = None
        if resolved_type == EntityType.COMPANY.value:
            base, suffix_found = self.extract_company_suffix(upper)
            upper = base

        # Apply Hausa substitutions when hinted
        if lang_hint == LanguageHint.HAUSA.value:
            upper = self._apply_hausa_substitutions(upper)

        # Normalise Arabic articles
        upper = self._normalise_arabic_articles(upper)

        # Tokenise and remove noise
        tokens = self._tokenise(upper)
        if resolved_type == EntityType.PERSON.value:
            tokens = self._strip_patronymics(tokens)
        tokens = [t for t in tokens if t not in self.NOISE_TOKENS]

        normalised = " ".join(tokens)
        phonetic_key = self.generate_phonetic_key(normalised)

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

        Args:
            texts:       List of raw strings to normalise.
            entity_type: Entity type hint applied to all items.

        Returns:
            List of NormalisedEntity objects in the same order.
        """
        logger.info(f"Batch normalising {len(texts)} entities (type={entity_type})")
        return [self.normalise(t, entity_type) for t in texts]

    def generate_phonetic_key(self, text: str) -> str:
        """
        We generate a Soundex-inspired phonetic key for grouping
        near-homophone entity names.

        The algorithm:
          1. Upper-case and take the first character.
          2. Replace consonant groups with digit codes.
          3. Remove vowels (except leading letter).
          4. Collapse adjacent identical codes.
          5. Pad or truncate to 6 characters.

        Args:
            text: Normalised (upper-cased) text.

        Returns:
            6-character phonetic key string (letter + 5 digits).
        """
        if not text:
            return "000000"

        # Use only the first word for the phonetic key
        word = text.split()[0] if " " in text else text
        word = re.sub(r"[^A-Z]", "", word.upper())

        if not word:
            return "000000"

        # Soundex coding table
        coding: Dict[str, str] = {
            "B": "1", "F": "1", "P": "1", "V": "1",
            "C": "2", "G": "2", "J": "2", "K": "2",
            "Q": "2", "S": "2", "X": "2", "Z": "2",
            "D": "3", "T": "3",
            "L": "4",
            "M": "5", "N": "5",
            "R": "6",
        }

        first_letter = word[0]
        coded = first_letter
        prev_code = coding.get(first_letter, "0")

        for char in word[1:]:
            code = coding.get(char, "0")
            if code != "0" and code != prev_code:
                coded += code
            prev_code = code
            if len(coded) == 6:
                break

        return coded.ljust(6, "0")

    def detect_language_hint(self, text: str) -> str:
        """
        We detect the most likely language / script family of a raw
        entity string using a lightweight heuristic approach.

        Args:
            text: Raw entity string.

        Returns:
            Language hint code from LanguageHint enum values.
        """
        upper = text.upper()
        tokens_set = set(re.findall(r"[A-Z]+", upper))

        # Swahili patronymics
        if tokens_set & {"BIN", "BINTI", "BINT"}:
            return LanguageHint.SWAHILI.value

        # Yoruba markers (tonal diacritics or common Yoruba words)
        if any(ch in text for ch in ("Ọ", "ọ", "Ẹ", "ẹ", "Ṣ", "ṣ")):
            return LanguageHint.YORUBA.value
        if tokens_set & {"OLU", "ADE", "OBI", "CHI", "EMEKA"}:
            return LanguageHint.YORUBA.value

        # French West Africa markers
        if tokens_set & {"SARL", "GIE", "SUCC", "SOCIETE", "ETS", "CIE"}:
            return LanguageHint.FRENCH.value
        if any(ch in text for ch in ("é", "è", "ê", "ç", "â", "ô")):
            return LanguageHint.FRENCH.value

        # Arabic / North African markers
        if tokens_set & {"AL", "EL"} or re.search(r"\bAL[-\s]|\bEL[-\s]", upper):
            return LanguageHint.ARABIC.value

        # Hausa markers
        if tokens_set & {"ALHAJI", "MALAM", "MALLAM", "SARKI"}:
            return LanguageHint.HAUSA.value

        # Zulu / Xhosa markers
        if any(upper.startswith(p) for p in ("NK", "MA", "SI", "ND", "MZ")):
            return LanguageHint.ZULU_XHOSA.value

        return LanguageHint.ENGLISH.value

    def extract_company_suffix(self, text: str) -> Tuple[str, Optional[str]]:
        """
        We extract the canonical company suffix from an upper-cased name,
        returning the base name and the suffix key.

        Args:
            text: Upper-cased company name (accents already stripped).

        Returns:
            Tuple of (base_name_without_suffix, canonical_suffix_key or None).
        """
        # Clean parenthetical punctuation for matching
        cleaned = re.sub(r"[(),.]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        for raw_suffix, canonical_key in self._sorted_suffixes:
            pattern = r"(?:^|\s)\(?" + re.escape(raw_suffix) + r"\)?(?:\s|$)"
            if re.search(pattern, cleaned):
                base = re.sub(pattern, " ", cleaned).strip()
                base = re.sub(r"\s+", " ", base).strip()
                return base, canonical_key

        return text, None

    def normalise_msisdn(
        self,
        msisdn: str,
        default_country: str = "ZA",
    ) -> str:
        """
        We normalise a mobile subscriber number (MSISDN) to E.164 format
        without the leading '+', stripping spaces, dashes, and brackets.

        Country code is added if the number begins with '0' (local format).

        Args:
            msisdn:          Raw MSISDN string.
            default_country: ISO 3166-1 alpha-2 code used when no country
                             prefix is detected (default "ZA").

        Returns:
            Normalised digits-only MSISDN string.

        Raises:
            ConfigurationError: If default_country is not in the dial
                                 prefix table.
        """
        if default_country not in self.COUNTRY_DIAL_PREFIX:
            raise ConfigurationError(
                f"Unknown default_country '{default_country}'. "
                f"Supported: {sorted(self.COUNTRY_DIAL_PREFIX.keys())}",
                details={"default_country": default_country},
            )

        # Strip all non-digit characters except leading '+'
        digits_only = re.sub(r"[^\d+]", "", msisdn)

        # Remove leading '+'
        if digits_only.startswith("+"):
            digits_only = digits_only[1:]

        # If already has a known country prefix, leave as-is
        for _country, prefix in self.COUNTRY_DIAL_PREFIX.items():
            if digits_only.startswith(prefix):
                return digits_only

        # Local format: starts with 0 → replace with country prefix
        if digits_only.startswith("0"):
            prefix = self.COUNTRY_DIAL_PREFIX[default_country]
            return prefix + digits_only[1:]

        # Assume it's already a full number without prefix
        return digits_only

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_entity_type(self, text: str, entity_type: str) -> str:
        """We resolve 'auto' entity type using heuristics."""
        if entity_type != EntityType.AUTO.value:
            return entity_type

        stripped = re.sub(r"[^\d+]", "", text)
        # If mostly digits, treat as MSISDN
        if len(stripped) >= 8 and len(stripped) / max(len(text), 1) > 0.7:
            return EntityType.MSISDN.value

        upper = text.upper()
        # Check for known company suffix markers
        for raw_suffix in self.COMPANY_SUFFIX_MAP:
            if raw_suffix in upper:
                return EntityType.COMPANY.value

        # Token count heuristic: short names with all-caps are often companies
        tokens = upper.split()
        if len(tokens) <= 2 and all(t.isupper() for t in tokens):
            return EntityType.COMPANY.value

        return EntityType.PERSON.value

    def _to_upper_strip_accents(self, text: str) -> str:
        """We upper-case and strip Unicode accents / diacritics."""
        upper = text.upper()
        # NFD decomposition then remove combining characters
        nfd = unicodedata.normalize("NFD", upper)
        stripped = "".join(
            ch for ch in nfd
            if unicodedata.category(ch) != "Mn"
        )
        return stripped

    def _apply_hausa_substitutions(self, text: str) -> str:
        """We apply Hausa phonetic substitutions to normalise spelling variants."""
        for source, target in self.HAUSA_SUBSTITUTIONS.items():
            text = re.sub(r"\b" + source, target, text)
        return text

    def _normalise_arabic_articles(self, text: str) -> str:
        """We strip or normalise Arabic definite-article prefixes."""
        for article in self.ARABIC_ARTICLES:
            text = re.sub(r"\b" + re.escape(article), "AL", text)
        return text

    def _tokenise(self, text: str) -> List[str]:
        """We tokenise on whitespace and punctuation, keeping only alpha-numeric tokens."""
        raw_tokens = re.split(r"[\s\-_/\\,;:.()\[\]{}\"']+", text)
        return [t for t in raw_tokens if t]

    def _strip_patronymics(self, tokens: List[str]) -> List[str]:
        """We remove Swahili patronymic connector tokens from person names."""
        return [t for t in tokens if t not in self.SWAHILI_PATRONYMICS]

    def _estimate_confidence(
        self,
        original: str,
        normalised: str,
        entity_type: str,
        lang_hint: str,
    ) -> float:
        """
        We estimate normalisation confidence based on how much the string
        changed and whether the language was clearly identified.
        """
        if not normalised:
            return 0.0

        # Jaccard similarity between original tokens and normalised tokens
        orig_tokens = set(re.findall(r"[A-Z]+", original.upper()))
        norm_tokens = set(normalised.split())
        if not orig_tokens:
            return 0.5

        intersection = orig_tokens & norm_tokens
        union = orig_tokens | norm_tokens
        jaccard = len(intersection) / len(union) if union else 0.0

        # Boost for known entity type
        type_bonus = 0.05 if entity_type != EntityType.AUTO.value else 0.0

        # Small bonus for clear language detection
        lang_bonus = 0.05 if lang_hint != LanguageHint.UNKNOWN.value else 0.0

        return min(1.0, jaccard + type_bonus + lang_bonus)


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

    # Batch demo
    print("\nBatch normalisation (3 items):")
    batch = normaliser.normalise_batch(
        ["Ecobank Ghana Ltd", "ECOBANK GHANA LIMITED", "ecobank ghana"],
        entity_type="company",
    )
    for item in batch:
        print(f"  {item.original!r:35} → {item.normalised!r:25} key={item.phonetic_key}")
