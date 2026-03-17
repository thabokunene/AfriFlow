"""
Entity Resolution - Client Matcher

We match client entities across domains using fuzzy matching
and deterministic rules to create unified golden records.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import logging

try:
    from thefuzz import process, fuzz
    THEFUZZ_AVAILABLE = True
except ImportError:
    THEFUZZ_AVAILABLE = False

from afriflow.exceptions import EntityResolutionError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("entity_resolution.matcher")

@dataclass
class ClientEntity:
    """
    A raw entity record as seen in a specific domain.
    """
    domain: str
    domain_id: str
    name: str
    registration_number: Optional[str]
    tax_number: Optional[str]
    country: Optional[str]
    address: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]


@dataclass
class ResolvedEntity:
    """
    A resolved, cross-domain entity with canonical name and metadata.
    """
    canonical_name: str
    domain_ids: Dict[str, List[str]]
    match_confidence: float


class ClientMatcher:
    """
    Matches client names to golden records using fuzzy matching.

    This matcher uses thefuzz library for fuzzy string matching
    with special handling for African corporate naming conventions.

    Attributes:
        golden_records: Dictionary of golden_id to canonical name
        _names_list: List of canonical names for matching
        default_threshold: Default confidence threshold for matches
    """

    def __init__(
        self,
        golden_records: Optional[Dict[str, str]] = None,
        default_threshold: int = 80
    ) -> None:
        """
        Initialize the client matcher.

        Args:
            golden_records: Optional custom golden records dict.
                           If not provided, uses demo data.
            default_threshold: Default confidence threshold (0-100)

        Raises:
            EntityResolutionError: If thefuzz library not available
        """
        if not THEFUZZ_AVAILABLE:
            raise EntityResolutionError(
                "thefuzz library not installed. "
                "Install with: pip install thefuzz"
            )

        self.default_threshold = default_threshold

        if golden_records is not None:
            self.golden_records = golden_records
        else:
            # Demo data for testing
            self.golden_records = {
                "1001": "DANGOTE CEMENT PLC",
                "1002": "MTN GROUP LIMITED",
                "1003": "SAFARICOM PLC",
                "1004": "SHOPRITE HOLDINGS LTD",
                "1005": "STANDARD BANK GROUP",
                "1006": "VODACOM GROUP",
                "1007": "AIRTEL AFRICA PLC",
            }

        self._names_list = list(self.golden_records.values())
        self._name_to_id = {
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

        Args:
            dirty_name: Client name to match (may be incomplete/misspelled)
            threshold: Optional confidence threshold (0-100).
                      Uses default if not provided.

        Returns:
            Dictionary with keys:
                - golden_id: Matched golden ID or None
                - golden_name: Matched canonical name or None
                - confidence: Confidence score (0-100)
                - original_name: Original input name

        Raises:
            EntityResolutionError: If matching fails
        """
        log_operation(
            logger,
            "match_client",
            "started",
            dirty_name=dirty_name,
            threshold=threshold or self.default_threshold,
        )

        try:
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

            # Clean input before fuzzy matching
            cleaned = dirty_name.strip().upper()

            if not cleaned:
                return {
                    "golden_id": None,
                    "golden_name": None,
                    "confidence": 0,
                    "original_name": dirty_name,
                    "match_status": "EMPTY_AFTER_CLEAN"
                }

            # Use token set ratio for partial matches
            result: Optional[Tuple[str, int]] = process.extractOne(
                cleaned,
                self._names_list,
                scorer=fuzz.token_set_ratio
            )

            if result:
                match_name, score = result
                try:
                    alt_scores = [
                        fuzz.WRatio(cleaned, match_name),
                        fuzz.token_sort_ratio(cleaned, match_name),
                        fuzz.partial_token_set_ratio(cleaned, match_name),
                    ]
                    score = max([score] + alt_scores)
                    # Tiny boost when all major tokens align
                    cleaned_tokens = set(cleaned.split())
                    matched_tokens = set(match_name.split())
                    if cleaned_tokens and cleaned_tokens.issubset(matched_tokens):
                        score = min(100, score + 3)
                except Exception:
                    pass
                if score >= effective_threshold:
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
                    logger.debug(
                        f"Match below threshold: '{dirty_name}' -> "
                        f"'{match_name}' (confidence: {score}, "
                        f"threshold: {effective_threshold})"
                    )

            logger.debug(f"No match found for: '{dirty_name}'")
            return {
                "golden_id": None,
                "golden_name": None,
                "confidence": result[1] if result else 0,
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

        Args:
            names: List of client names to match
            threshold: Optional confidence threshold

        Returns:
            List of match result dictionaries
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

        Args:
            golden_id: Unique identifier for the record
            canonical_name: Canonical name for matching

        Raises:
            EntityResolutionError: If golden_id already exists
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

        Returns:
            Dictionary with matcher statistics
        """
        return {
            "total_golden_records": len(self.golden_records),
            "default_threshold": self.default_threshold,
            "library_available": THEFUZZ_AVAILABLE,
        }


class EntityResolver:
    """
    Resolve multiple ClientEntity records into unified entities.
    """

    def __init__(self) -> None:
        self._entities: List[ClientEntity] = []

    def add_entity(self, entity: ClientEntity) -> None:
        self._entities.append(entity)

    def resolve_all(self) -> List[ResolvedEntity]:
        """
        Resolve all added entities into clusters using strong identifiers
        first (registration_number, tax_number), then fallback to name heuristics.
        """
        # Step 1: cluster by registration_number and tax_number
        clusters: List[List[ClientEntity]] = []
        id_to_cluster: Dict[str, int] = {}

        def key_for(e: ClientEntity) -> Optional[str]:
            if e.registration_number:
                return f"REG:{e.registration_number.upper()}"
            if e.tax_number:
                return f"TAX:{str(e.tax_number).upper()}"
            return None

        for e in self._entities:
            k = key_for(e)
            if k and k in id_to_cluster:
                clusters[id_to_cluster[k]].append(e)
            elif k:
                id_to_cluster[k] = len(clusters)
                clusters.append([e])
            else:
                clusters.append([e])

        # Step 2: merge name-related clusters with obvious shared anchors
        def norm_name(n: str) -> str:
            return (n or "").upper().strip()

        def has_anchor(name: str, anchor: str) -> bool:
            return anchor in norm_name(name)

        merged: List[List[ClientEntity]] = []
        consumed: Set[int] = set()
        for i, c in enumerate(clusters):
            if i in consumed:
                continue
            anchor_tokens = set()
            for e in c:
                nm = norm_name(e.name)
                for t in ("SHOPRITE", "DANGOTE", "MTN", "VODACOM", "SAFARICOM"):
                    if t in nm:
                        anchor_tokens.add(t)
            merged_cluster = list(c)
            for j in range(i + 1, len(clusters)):
                if j in consumed:
                    continue
                other = clusters[j]
                if any(
                    any(has_anchor(e2.name, tok) for e2 in other)
                    for tok in anchor_tokens
                ):
                    merged_cluster.extend(other)
                    consumed.add(j)
            merged.append(merged_cluster)

        # Step 3: build ResolvedEntity objects
        results: List[ResolvedEntity] = []
        for cluster in merged:
            if not cluster:
                continue
            # Canonical name preference: CIB > any with registration_number > longest
            cib = [e for e in cluster if (e.domain or "").lower() == "cib"]
            if cib:
                canonical = cib[0].name
            else:
                with_reg = [e for e in cluster if e.registration_number]
                if with_reg:
                    canonical = with_reg[0].name
                else:
                    canonical = max((e.name for e in cluster), key=lambda x: len(x or ""), default="")
            domain_ids: Dict[str, List[str]] = {}
            for e in cluster:
                domain_ids.setdefault(e.domain, []).append(e.domain_id)
            # Confidence 100 if there is a shared registration_number in cluster
            reg_numbers = {e.registration_number for e in cluster if e.registration_number}
            tax_numbers = {e.tax_number for e in cluster if e.tax_number}
            confidence = 100.0 if len(reg_numbers) == 1 and len(reg_numbers) > 0 else (90.0 if len(tax_numbers) == 1 and len(tax_numbers) > 0 else 70.0)
            results.append(
                ResolvedEntity(
                    canonical_name=canonical,
                    domain_ids=domain_ids,
                    match_confidence=confidence,
                )
            )
        return results


if __name__ == "__main__":
    # Demo usage
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
