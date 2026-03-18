"""
@file client_matcher.py
@description Client Matcher and Entity Resolver for the AfriFlow entity resolution layer.
             ClientMatcher performs fuzzy string matching of dirty client names against
             a golden record store using the thefuzz library (token set ratio + WRatio).
             EntityResolver runs a three-stage pipeline — deterministic clustering by
             registration/tax number, heuristic merging by anchor tokens, and canonical
             name selection — to produce ResolvedEntity objects from raw ClientEntity
             records sourced across multiple domains.
@author Thabo Kunene
@created 2026-03-18
"""

from __future__ import annotations  # enables forward references in type hints

# Standard library imports
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass   # structured value objects for client and resolved entities
import re                           # regex for name cleaning before fuzzy matching

# Optional dependency: thefuzz provides Levenshtein-based fuzzy matching.
# Guarded import so the module can be imported even if the library is absent;
# any attempt to instantiate ClientMatcher will raise EntityResolutionError.
try:
    from thefuzz import process, fuzz  # fuzzy string matching algorithms
    THEFUZZ_AVAILABLE = True
except ImportError:
    THEFUZZ_AVAILABLE = False  # flag checked in ClientMatcher.__init__

# AfriFlow internal imports
from afriflow.exceptions import EntityResolutionError, ValidationError  # typed exceptions
from afriflow.logging_config import get_logger, log_operation            # structured logging

# Module-level logger — use DEBUG for per-match detail, INFO for batch summaries
logger = get_logger("entity_resolution.matcher")


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Regex to collapse multiple whitespace characters into a single space
WHITESPACE_PATTERN = re.compile(r"\s+")

# Regex that strips any character that is not an uppercase letter, digit, or space.
# Applied AFTER upper-casing so we only need to handle [^A-Z0-9\s].
SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Z0-9\s]")

# Legal entity suffixes that should be stripped or ignored during matching.
# Presence of these tokens is normalised so that "DANGOTE CEMENT PLC" and
# "DANGOTE CEMENT LIMITED" resolve to the same golden record.
COMMON_SUFFIXES = {
    "LTD", "LIMITED", "PLC", "PUBLIC LIMITED COMPANY",
    "PTY", "PTY LTD", "PROPRIETARY LIMITED",
    "INC", "INCORPORATED", "CORP", "CORPORATION",
    "LLC", "LP", "LLP", "NV", "SA", "AG", "GMBH",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ClientEntity:
    """
    A raw entity record as seen in a specific domain.

    Represents a client entity from a source domain before
    cross-domain resolution. Contains all available identifiers
    and contact information for matching purposes.

    Attributes:
        domain: Source domain name (e.g., 'cib', 'forex', 'cell')
        domain_id: Unique identifier within the source domain
        name: Client name as recorded in source system
        registration_number: Company registration number (if available)
        tax_number: Tax identification number (if available)
        country: ISO 3166-1 alpha-2 country code (if available)
        address: Registered address (if available)
        contact_email: Primary contact email (if available)
        contact_phone: Primary contact phone (if available)

    Example:
        >>> entity = ClientEntity(
        ...     domain="cib",
        ...     domain_id="CIB-001",
        ...     name="Dangote Cement Plc",
        ...     registration_number="RC123456",
        ...     country="NG"
        ... )
    """
    domain: str                                    # source domain (e.g. 'cib', 'forex')
    domain_id: str                                 # unique ID within the source domain
    name: str                                      # client name as recorded in the source system
    registration_number: Optional[str] = None      # company registration number if available
    tax_number: Optional[str] = None               # tax identification number if available
    country: Optional[str] = None                  # ISO 3166-1 alpha-2 country code
    address: Optional[str] = None                  # registered address if available
    contact_email: Optional[str] = None            # primary contact email
    contact_phone: Optional[str] = None            # primary contact phone number


@dataclass
class ResolvedEntity:
    """
    A resolved, cross-domain entity with canonical name and metadata.

    Represents a unified client entity after cross-domain resolution.
    Contains the canonical name and all linked domain identifiers.

    Attributes:
        canonical_name: Standardized name for the resolved entity
        domain_ids: Dictionary mapping domain names to lists of domain IDs
        match_confidence: Confidence score (0-100) for the resolution

    Example:
        >>> resolved = ResolvedEntity(
        ...     canonical_name="DANGOTE CEMENT PLC",
        ...     domain_ids={"cib": ["CIB-001"], "forex": ["FX-002"]},
        ...     match_confidence=95.0
        ... )
    """
    canonical_name: str                        # standardised canonical name
    domain_ids: Dict[str, List[str]]           # domain → list of source IDs
    match_confidence: float                    # resolution confidence score (0–100)


# ---------------------------------------------------------------------------
# ClientMatcher
# ---------------------------------------------------------------------------

class ClientMatcher:
    """
    Matches client names to golden records using fuzzy matching.

    This matcher uses thefuzz library for fuzzy string matching
    with special handling for African corporate naming conventions.
    It supports multiple matching strategies and confidence scoring.

    Attributes:
        golden_records: Dictionary of golden_id to canonical name
        _names_list: List of canonical names for matching
        _name_to_id: Reverse lookup from name to golden ID
        default_threshold: Default confidence threshold for matches

    Example:
        >>> matcher = ClientMatcher(default_threshold=85)
        >>> result = matcher.match_client("Dangote Cemnt")
        >>> print(result["golden_id"])
        '1001'
    """

    def __init__(
        self,
        golden_records: Optional[Dict[str, str]] = None,
        default_threshold: int = 80
    ) -> None:
        """
        Initialize the client matcher.

        :param golden_records: Optional custom golden records dict.
                               If not provided, uses demo data.
        :param default_threshold: Default confidence threshold (0-100).
                                  Matches below this score are rejected.

        :raises EntityResolutionError: If thefuzz library not available.
        :raises ValidationError: If golden_records format is invalid.

        Example:
            >>> custom_records = {"C001": "CLIENT ONE LTD"}
            >>> matcher = ClientMatcher(golden_records=custom_records, default_threshold=90)
        """
        # Fail fast if the fuzzy matching library is not installed
        if not THEFUZZ_AVAILABLE:
            raise EntityResolutionError(
                "thefuzz library not installed. "
                "Install with: pip install thefuzz"
            )

        # Threshold must be a valid percentage in [0, 100]
        if default_threshold < 0 or default_threshold > 100:
            raise ValidationError(
                f"default_threshold must be between 0 and 100, got {default_threshold}",
                field="default_threshold",
                value=str(default_threshold)
            )

        self.default_threshold = default_threshold  # stored for use in match_client()

        if golden_records is not None:
            # Validate that the caller provided a dict, not a list or other type
            if not isinstance(golden_records, dict):
                raise ValidationError(
                    "golden_records must be a dictionary",
                    field="golden_records",
                    value=str(type(golden_records))
                )
            self.golden_records = golden_records
        else:
            # Demo golden records for testing and portfolio demonstration.
            # These represent major pan-African corporate clients.
            self.golden_records = {
                "1001": "DANGOTE CEMENT PLC",
                "1002": "MTN GROUP LIMITED",
                "1003": "SAFARICOM PLC",
                "1004": "SHOPRITE HOLDINGS LTD",
                "1005": "STANDARD BANK GROUP",
                "1006": "VODACOM GROUP",
                "1007": "AIRTEL AFRICA PLC",
            }

        # Pre-build name list and reverse index for fast lookup after matching
        self._names_list = list(self.golden_records.values())
        self._name_to_id: Dict[str, str] = {
            name: gid for gid, name in self.golden_records.items()
        }

        logger.info(
            f"ClientMatcher initialized with "
            f"{len(self.golden_records)} golden records"
        )

    def match_client(
        self,
        dirty_name: str,
        threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Match a dirty client name to a golden record.

        Uses a cascade of fuzzy matching strategies:
        1. token_set_ratio (primary — handles word order variations)
        2. WRatio, token_sort_ratio, partial_token_set_ratio (secondary — max ensemble)
        3. Subset token boost (+3 pts) when all dirty tokens appear in the match

        :param dirty_name: Client name to match (may be incomplete or misspelled).
        :param threshold: Optional confidence threshold override (0–100).
                          Falls back to default_threshold if not provided.
        :return: Dict with keys: golden_id, golden_name, confidence, original_name,
                 match_status (MATCHED / NO_MATCH / INVALID_INPUT / EMPTY_AFTER_CLEAN).
        :raises EntityResolutionError: If the underlying matching operation fails.
        """
        log_operation(
            logger,
            "match_client",
            "started",
            dirty_name=dirty_name,
            threshold=threshold or self.default_threshold,
        )

        try:
            # Guard: reject None, non-string, or empty inputs immediately
            if not dirty_name or not isinstance(dirty_name, str):
                logger.warning(f"Invalid input: {dirty_name}")
                return {
                    "golden_id": None,
                    "golden_name": None,
                    "confidence": 0,
                    "original_name": dirty_name,
                    "match_status": "INVALID_INPUT"
                }

            effective_threshold = threshold or self.default_threshold

            # Normalise to uppercase before fuzzy matching
            cleaned = dirty_name.strip().upper()

            # Guard: check for empty string after stripping
            if not cleaned:
                return {
                    "golden_id": None,
                    "golden_name": None,
                    "confidence": 0,
                    "original_name": dirty_name,
                    "match_status": "EMPTY_AFTER_CLEAN"
                }

            # Primary match: token_set_ratio handles transposed and partial tokens well
            result: Optional[Tuple[str, int]] = process.extractOne(
                cleaned,
                self._names_list,
                scorer=fuzz.token_set_ratio
            )

            if result:
                match_name, score = result
                try:
                    # Secondary ensemble: take the max across multiple scorer algorithms.
                    # This catches cases where token_set_ratio under-scores (e.g. acronyms).
                    alt_scores = [
                        fuzz.WRatio(cleaned, match_name),
                        fuzz.token_sort_ratio(cleaned, match_name),
                        fuzz.partial_token_set_ratio(cleaned, match_name),
                    ]
                    score = max([score] + alt_scores)

                    # Tiny boost when all major tokens align (subset match confirms intent)
                    cleaned_tokens = set(cleaned.split())
                    matched_tokens = set(match_name.split())
                    if cleaned_tokens and cleaned_tokens.issubset(matched_tokens):
                        score = min(100, score + 3)  # cap at 100 to stay in valid range
                except Exception:
                    pass  # secondary scoring is a best-effort enhancement only

                if score >= effective_threshold:
                    # Confidence threshold met — return the matched golden record
                    golden_id = self._name_to_id.get(match_name)
                    logger.info(
                        f"Match found: '{dirty_name}' -> "
                        f"'{match_name}' (confidence: {score})"
                    )
                    return {
                        "golden_id": golden_id,
                        "golden_name": match_name,
                        "confidence": score,
                        "original_name": dirty_name,
                        "match_status": "MATCHED"
                    }
                else:
                    # Score below threshold — log for debugging but do not match
                    logger.debug(
                        f"Match below threshold: '{dirty_name}' -> "
                        f"'{match_name}' (confidence: {score}, "
                        f"threshold: {effective_threshold})"
                    )

            logger.debug(f"No match found for: '{dirty_name}'")
            return {
                "golden_id": None,
                "golden_name": None,
                "confidence": result[1] if result else 0,  # best score even if below threshold
                "original_name": dirty_name,
                "match_status": "NO_MATCH"
            }

        except Exception as e:
            log_operation(
                logger,
                "match_client",
                "failed",
                dirty_name=dirty_name,
                error=str(e),
            )
            raise EntityResolutionError(
                f"Failed to match client '{dirty_name}': {e}",
                details={"dirty_name": dirty_name}
            ) from e

    def match_batch(
        self,
        names: List[str],
        threshold: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Match multiple client names in batch.

        :param names: List of client names to match.
        :param threshold: Optional confidence threshold override.
        :return: List of match result dicts in the same order as the input.
        """
        logger.info(f"Batch matching {len(names)} names")
        return [
            self.match_client(name, threshold)
            for name in names
        ]

    def add_golden_record(
        self,
        golden_id: str,
        canonical_name: str
    ) -> None:
        """
        Add a new golden record to the matcher.

        Appends to the internal name list and reverse index so that
        subsequent calls to match_client() consider the new record.

        :param golden_id: Unique identifier for the record.
        :param canonical_name: Canonical name for matching (stored uppercased).
        :raises EntityResolutionError: If golden_id already exists.
        """
        if golden_id in self.golden_records:
            raise EntityResolutionError(
                f"Golden ID {golden_id} already exists"
            )

        self.golden_records[golden_id] = canonical_name.upper()
        self._names_list.append(canonical_name.upper())
        self._name_to_id[canonical_name.upper()] = golden_id

        logger.info(f"Added golden record: {golden_id} = {canonical_name}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get matcher statistics.

        :return: Dictionary with total_golden_records, default_threshold,
                 and library_available flag.
        """
        return {
            "total_golden_records": len(self.golden_records),
            "default_threshold": self.default_threshold,
            "library_available": THEFUZZ_AVAILABLE,
        }


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------

class EntityResolver:
    """
    Resolve multiple ClientEntity records into unified entities.

    This resolver uses a two-stage approach:
    1. Deterministic matching using strong identifiers (registration number, tax number)
    2. Heuristic matching using name anchors for entities without strong identifiers

    The resolver produces ResolvedEntity objects that represent unified
    cross-domain client entities with confidence scores.

    Attributes:
        _entities: List of client entities to resolve

    Example:
        >>> resolver = EntityResolver()
        >>> resolver.add_entity(ClientEntity(
        ...     domain="cib", domain_id="CIB-001", name="Dangote Cement",
        ...     registration_number="RC123"
        ... ))
        >>> resolver.add_entity(ClientEntity(
        ...     domain="forex", domain_id="FX-001", name="Dangote Cement Plc",
        ...     registration_number="RC123"
        ... ))
        >>> resolved = resolver.resolve_all()
        >>> len(resolved)
        1
    """

    # Known corporate anchor tokens for heuristic name-based clustering.
    # When two records share an anchor token (e.g. both contain "DANGOTE"),
    # they are merged into the same cluster even without a shared reg number.
    ANCHOR_NAMES: Tuple[str, ...] = (
        "SHOPRITE", "DANGOTE", "MTN", "VODACOM", "SAFARICOM",
        "AIRTEL", "STANDARD BANK", "BARCLAYS", "ECOBANK"
    )

    def __init__(self) -> None:
        """
        Initialize the entity resolver with an empty entity list.

        Example:
            >>> resolver = EntityResolver()
            >>> len(resolver._entities)
            0
        """
        # Internal list accumulates entities until resolve_all() is called
        self._entities: List[ClientEntity] = []

    def add_entity(self, entity: ClientEntity) -> None:
        """
        Add a client entity to the resolver.

        :param entity: ClientEntity instance to add for resolution.
        :raises ValidationError: If entity is None or not a ClientEntity instance.

        Example:
            >>> resolver = EntityResolver()
            >>> entity = ClientEntity(domain="cib", domain_id="CIB-001", name="Test Corp")
            >>> resolver.add_entity(entity)
        """
        # Validate the entity before appending to prevent silent failures in resolve_all()
        if entity is None:
            raise ValidationError(
                "entity cannot be None",
                field="entity",
                value="None"
            )
        if not isinstance(entity, ClientEntity):
            raise ValidationError(
                "entity must be a ClientEntity instance",
                field="entity",
                value=str(type(entity))
            )
        self._entities.append(entity)
        logger.debug(f"Added entity: domain={entity.domain}, id={entity.domain_id}")

    def resolve_all(self) -> List[ResolvedEntity]:
        """
        Resolve all added entities into unified cross-domain entities.

        Uses a three-stage resolution process:
          Stage 1: Cluster by strong identifiers (registration_number or tax_number).
                   Entities sharing an identifier are grouped deterministically.
          Stage 2: Merge clusters using name anchor heuristics.
                   Entities from different clusters that share a known anchor token
                   (e.g. "DANGOTE") are merged.
          Stage 3: Build ResolvedEntity objects with canonical names and confidence.

        :return: List of ResolvedEntity objects representing unified entities.
        :raises EntityResolutionError: If the resolution pipeline fails.

        Example:
            >>> resolver = EntityResolver()
            >>> # Add entities...
            >>> resolved = resolver.resolve_all()
            >>> len(resolved)
            1
        """
        if not self._entities:
            logger.debug("No entities to resolve")
            return []

        logger.info(f"Resolving {len(self._entities)} entities")

        try:
            # ── Stage 1: Cluster by strong identifiers ────────────────────────
            clusters: List[List[ClientEntity]] = []
            id_to_cluster: Dict[str, int] = {}  # identifier key → cluster index

            def key_for(e: ClientEntity) -> Optional[str]:
                """Generate a unique stable key from the entity's strong identifiers."""
                if e.registration_number:
                    return f"REG:{e.registration_number.upper()}"
                if e.tax_number:
                    return f"TAX:{str(e.tax_number).upper()}"
                return None  # no strong identifier available → separate cluster

            for e in self._entities:
                k = key_for(e)
                if k and k in id_to_cluster:
                    # Merge into existing cluster with the same identifier
                    clusters[id_to_cluster[k]].append(e)
                elif k:
                    # First entity with this identifier → create a new cluster
                    id_to_cluster[k] = len(clusters)
                    clusters.append([e])
                else:
                    # No strong identifier → each gets its own cluster initially
                    clusters.append([e])

            logger.debug(f"Stage 1 complete: {len(clusters)} initial clusters")

            # ── Stage 2: Merge clusters using name anchor heuristics ──────────
            merged: List[List[ClientEntity]] = []
            consumed: Set[int] = set()  # indices of clusters already absorbed

            def norm_name(n: str) -> str:
                """Normalise a name for anchor comparison."""
                return (n or "").upper().strip()

            def has_anchor(name: str, anchor: str) -> bool:
                """Return True if the normalised name contains the anchor token."""
                return anchor in norm_name(name)

            for i, c in enumerate(clusters):
                if i in consumed:
                    continue

                # Collect anchor tokens present in this cluster
                anchor_tokens: Set[str] = set()
                for e in c:
                    nm = norm_name(e.name)
                    for t in self.ANCHOR_NAMES:
                        if t in nm:
                            anchor_tokens.add(t)

                merged_cluster: List[ClientEntity] = list(c)

                # Scan remaining clusters for matching anchor tokens
                for j in range(i + 1, len(clusters)):
                    if j in consumed:
                        continue
                    other = clusters[j]
                    # If any entity in the other cluster shares an anchor, merge
                    if any(
                        any(has_anchor(e2.name, tok) for e2 in other)
                        for tok in anchor_tokens
                    ):
                        merged_cluster.extend(other)
                        consumed.add(j)  # mark as absorbed so we skip it

                merged.append(merged_cluster)

            logger.debug(f"Stage 2 complete: {len(merged)} merged clusters")

            # ── Stage 3: Build ResolvedEntity objects ─────────────────────────
            results: List[ResolvedEntity] = []

            for cluster in merged:
                if not cluster:
                    continue

                resolved = self._build_resolved_entity(cluster)
                if resolved:
                    results.append(resolved)

            logger.info(f"Resolution complete: {len(results)} unified entities")

            return results

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}")
            raise EntityResolutionError(
                f"Entity resolution failed: {e}",
                details={"entity_count": len(self._entities)}
            ) from e

    def _build_resolved_entity(
        self,
        cluster: List[ClientEntity]
    ) -> Optional[ResolvedEntity]:
        """
        Build a ResolvedEntity from a cluster of ClientEntity objects.

        :param cluster: List of ClientEntity objects belonging to the same real-world entity.
        :return: ResolvedEntity, or None if the cluster is empty.
        """
        if not cluster:
            return None

        # Select the canonical name using domain priority rules
        canonical = self._select_canonical_name(cluster)

        # Aggregate domain IDs: each domain can have multiple source IDs
        domain_ids: Dict[str, List[str]] = {}
        for e in cluster:
            if e.domain:
                if e.domain not in domain_ids:
                    domain_ids[e.domain] = []
                domain_ids[e.domain].append(e.domain_id)

        # Calculate confidence based on the quality of identifier overlap
        confidence = self._calculate_confidence(cluster)

        return ResolvedEntity(
            canonical_name=canonical,
            domain_ids=domain_ids,
            match_confidence=confidence
        )

    def _select_canonical_name(
        self,
        cluster: List[ClientEntity]
    ) -> str:
        """
        Select the canonical name from a cluster of entities.

        Priority order:
          1. CIB domain entity — CIB systems have the most rigorous KYC vetting.
          2. Entity with a registration number — government-issued, more reliable.
          3. Longest name — most complete/descriptive as a fallback.

        :param cluster: List of ClientEntity objects.
        :return: Selected canonical name string.
        """
        # CIB is the primary system of record for corporate client names
        cib_entities = [
            e for e in cluster
            if (e.domain or "").lower() == "cib"
        ]
        if cib_entities:
            return cib_entities[0].name

        # Registered entities are more reliably named than unregistered ones
        with_registration = [
            e for e in cluster if e.registration_number
        ]
        if with_registration:
            return with_registration[0].name

        # Fallback: longest name is typically the most complete representation
        return max(
            (e.name for e in cluster),
            key=lambda x: len(x or ""),
            default=""
        )

    def _calculate_confidence(
        self,
        cluster: List[ClientEntity]
    ) -> float:
        """
        Calculate a confidence score for a resolved entity cluster.

        Scoring is based on the quality of the matching evidence:
          100.0 — single shared registration number (government-issued, unique)
           90.0 — single shared tax number (government-issued, unique)
           70.0 — name-based clustering only (heuristic, lower reliability)

        :param cluster: List of ClientEntity objects.
        :return: Confidence score in [0.0, 100.0].
        """
        # Collect unique registration and tax numbers across the cluster
        reg_numbers = {
            e.registration_number
            for e in cluster
            if e.registration_number
        }
        tax_numbers = {
            e.tax_number
            for e in cluster
            if e.tax_number
        }

        if len(reg_numbers) == 1 and len(reg_numbers) > 0:
            return 100.0   # deterministic match on registration number
        elif len(tax_numbers) == 1 and len(tax_numbers) > 0:
            return 90.0    # deterministic match on tax number
        else:
            return 70.0    # heuristic name-anchor match only

    def get_entity_count(self) -> int:
        """
        Get the number of entities currently in the resolver.

        :return: Count of ClientEntity objects added via add_entity().
        """
        return len(self._entities)

    def clear(self) -> None:
        """
        Clear all entities from the resolver.

        Use this to reset the resolver between processing batches.
        """
        self._entities.clear()
        logger.debug("Entity resolver cleared")


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Demo usage — runs when the module is executed directly
    matcher = ClientMatcher()
    samples = [
        "Dangote Cement",
        "MTN Group",
        "Vodacom",
        "Unknown Company Ltd"
    ]
    for s in samples:
        result = matcher.match_client(s)
        print(f"Input: {s} -> Match: {result}")
