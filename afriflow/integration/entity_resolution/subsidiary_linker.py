"""
integration/entity_resolution/subsidiary_linker.py

Corporate subsidiary linkage and Ultimate Beneficial Owner (UBO) resolution.

We trace ownership chains across cross-border corporate structures common
in African CIB portfolios — Mauritius holding companies, South African
OpCos, and Nigerian/Ghanaian branches nested under European ultimate
parents.  Circular ownership (common in Southern African holding structures)
is detected and flagged rather than causing infinite loops.

This is critical for:
  - Know Your Customer (KYC) / AML group-level exposure aggregation.
  - Relationship Manager briefings that surface cross-subsidiary signals.
  - CIB pricing: aggregate fee relationships across a group.

DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
Group, MTN, or any affiliated entity. It is a demonstration of concept,
domain knowledge, and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation
from afriflow.governance.cross_border_data_rules import DataResidencyTier

logger = get_logger("entity_resolution.subsidiary_linker")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LinkType(Enum):
    """Nature of the ownership relationship between two entities."""
    DIRECT = "direct"           # Entity A owns Entity B directly
    INDIRECT = "indirect"       # Entity A controls Entity B via intermediary
    BENEFICIAL = "beneficial"   # Beneficial interest only (e.g. trust beneficiary)
    NOMINEE = "nominee"         # Registered owner acting on behalf of another


class EntityCategory(Enum):
    """High-level category of a registered entity."""
    HOLDING = "holding"
    OPERATING = "operating"
    BRANCH = "branch"
    TRUST = "trust"
    INDIVIDUAL = "individual"
    FUND = "fund"
    SPECIAL_PURPOSE = "special_purpose"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RegisteredEntity:
    """
    We represent a legal entity registered in the subsidiary graph.

    Attributes:
        entity_id:       Unique identifier (may be a golden ID).
        name:            Legal name of the entity.
        country:         ISO 3166-1 alpha-2 country of registration.
        entity_type:     EntityCategory value.
        residency_tier:  Data residency tier from governance rules.
        registered_at:   ISO timestamp of when the entity was registered here.
        metadata:        Arbitrary additional attributes.
    """

    entity_id: str
    name: str
    country: str
    entity_type: str
    residency_tier: DataResidencyTier = DataResidencyTier.UNREGULATED
    registered_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OwnershipLink:
    """
    We represent a single directed ownership link from a child entity
    to its parent.

    Attributes:
        entity_id:      The owned (child) entity.
        parent_id:      The owning (parent) entity.
        ownership_pct:  Percentage of the child held by the parent (0–100).
        country:        Country where the ownership instrument is registered.
        link_type:      Nature of the link (direct / indirect / beneficial).
        confidence:     Confidence in this link, 0–1 (1 = verified from registry).
        effective_date: ISO date from which this link applies.
    """

    entity_id: str
    parent_id: str
    ownership_pct: float
    country: str
    link_type: str = LinkType.DIRECT.value
    confidence: float = 1.0
    effective_date: str = field(
        default_factory=lambda: datetime.utcnow().date().isoformat()
    )


@dataclass
class UBOResult:
    """
    We represent the resolved Ultimate Beneficial Owner for an entity.

    Attributes:
        entity_id:           Starting entity for the resolution.
        ultimate_owner_id:   Entity ID of the UBO (deepest non-owned entity).
        chain:               Ordered list of entity IDs from start → UBO.
        total_ownership_pct: Product of ownership percentages along the chain.
        countries_in_chain:  Distinct countries present in the chain.
        is_circular:         True if a circular ownership loop was detected.
        depth:               Number of hops from entity to UBO.
    """

    entity_id: str
    ultimate_owner_id: str
    chain: List[str] = field(default_factory=list)
    total_ownership_pct: float = 100.0
    countries_in_chain: List[str] = field(default_factory=list)
    is_circular: bool = False
    depth: int = 0


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SubsidiaryLinker:
    """
    We maintain a registry of corporate entities and their ownership links,
    and resolve Ultimate Beneficial Owners through ownership chains of
    arbitrary depth.

    Circular ownership structures are detected and flagged; the traversal
    terminates at the first repeated node.

    Usage::

        linker = SubsidiaryLinker()
        linker.register_entity("MU-HOLD-001", "Africa Growth Holdings", "MU", "holding")
        linker.register_entity("ZA-OP-001",   "AfriFlow OpCo SA",        "ZA", "operating")
        linker.add_ownership_link("ZA-OP-001", "MU-HOLD-001", 100.0, "MU")
        result = linker.find_ubo("ZA-OP-001")
        print(result.ultimate_owner_id)   # → "MU-HOLD-001"
    """

    def __init__(self) -> None:
        """Initialise the linker with empty registries."""
        # entity_id → RegisteredEntity
        self._entities: Dict[str, RegisteredEntity] = {}
        # entity_id → list of OwnershipLink (links pointing to parents)
        self._ownership_links: Dict[str, List[OwnershipLink]] = {}
        logger.info("SubsidiaryLinker initialised")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_entity(
        self,
        entity_id: str,
        name: str,
        country: str,
        entity_type: str,
        residency_tier: DataResidencyTier = DataResidencyTier.UNREGULATED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RegisteredEntity:
        """
        We register a new legal entity in the linker's internal registry.

        Args:
            entity_id:      Unique identifier for this entity.
            name:           Legal name.
            country:        ISO 3166-1 alpha-2 country code.
            entity_type:    EntityCategory value string.
            residency_tier: DataResidencyTier from governance rules.
            metadata:       Optional key-value metadata.

        Returns:
            The created RegisteredEntity.

        Raises:
            ConfigurationError: If entity_id is already registered or
                                 entity_type is not a valid EntityCategory.
        """
        if entity_id in self._entities:
            raise ConfigurationError(
                f"Entity '{entity_id}' is already registered.",
                details={"entity_id": entity_id},
            )
        valid_types = {e.value for e in EntityCategory}
        if entity_type not in valid_types:
            raise ConfigurationError(
                f"entity_type must be one of {sorted(valid_types)}",
                details={"received": entity_type},
            )

        entity = RegisteredEntity(
            entity_id=entity_id,
            name=name,
            country=country.upper(),
            entity_type=entity_type,
            residency_tier=residency_tier,
            metadata=metadata or {},
        )
        self._entities[entity_id] = entity
        self._ownership_links.setdefault(entity_id, [])
        logger.info(f"Registered entity: {entity_id} ({name}, {country})")
        return entity

    def add_ownership_link(
        self,
        child_id: str,
        parent_id: str,
        ownership_pct: float,
        country: str,
        link_type: str = LinkType.DIRECT.value,
        confidence: float = 1.0,
    ) -> OwnershipLink:
        """
        We add a directional ownership link from a child entity to a parent.

        Args:
            child_id:      The entity being owned.
            parent_id:     The owning entity.
            ownership_pct: Percentage held (0.0–100.0).
            country:       Country of the ownership instrument.
            link_type:     LinkType value string.
            confidence:    Confidence level (0–1).

        Returns:
            The created OwnershipLink.

        Raises:
            ConfigurationError: If either entity is not registered, ownership_pct
                                 is out of range, or link_type is invalid.
        """
        if child_id not in self._entities:
            raise ConfigurationError(
                f"Child entity '{child_id}' is not registered. "
                "Call register_entity first.",
                details={"child_id": child_id},
            )
        if parent_id not in self._entities:
            raise ConfigurationError(
                f"Parent entity '{parent_id}' is not registered. "
                "Call register_entity first.",
                details={"parent_id": parent_id},
            )
        if not (0.0 < ownership_pct <= 100.0):
            raise ConfigurationError(
                f"ownership_pct must be in (0, 100], got {ownership_pct}",
                details={"ownership_pct": ownership_pct},
            )
        valid_types = {e.value for e in LinkType}
        if link_type not in valid_types:
            raise ConfigurationError(
                f"link_type must be one of {sorted(valid_types)}",
                details={"received": link_type},
            )

        link = OwnershipLink(
            entity_id=child_id,
            parent_id=parent_id,
            ownership_pct=ownership_pct,
            country=country.upper(),
            link_type=link_type,
            confidence=confidence,
        )
        self._ownership_links[child_id].append(link)
        logger.info(
            f"Ownership link: {child_id} → {parent_id} "
            f"({ownership_pct:.1f}%, {link_type})"
        )
        return link

    # ------------------------------------------------------------------
    # UBO resolution
    # ------------------------------------------------------------------

    def find_ubo(
        self,
        entity_id: str,
        max_depth: int = 10,
    ) -> UBOResult:
        """
        We traverse the ownership chain upward to find the Ultimate
        Beneficial Owner — the topmost entity with no registered parent.

        When multiple parents exist (common in partial ownership or
        consortium structures) we follow the parent with the highest
        ownership percentage.

        Args:
            entity_id:  Starting entity.
            max_depth:  Maximum chain length before stopping (prevents runaway
                        traversal in very deep structures).

        Returns:
            UBOResult with the resolved chain and metadata.

        Raises:
            ConfigurationError: If entity_id is not registered.
        """
        if entity_id not in self._entities:
            raise ConfigurationError(
                f"Entity '{entity_id}' is not registered.",
                details={"entity_id": entity_id},
            )

        log_operation(logger, "find_ubo", "started", entity_id=entity_id)

        chain: List[str] = [entity_id]
        visited: Set[str] = {entity_id}
        current_id = entity_id
        running_pct: float = 100.0
        is_circular = False
        countries: List[str] = [self._entities[entity_id].country]

        for _ in range(max_depth):
            parents = self._ownership_links.get(current_id, [])
            if not parents:
                # No parent → current_id is the UBO
                break

            # Choose parent with the highest ownership percentage
            dominant = max(parents, key=lambda lnk: lnk.ownership_pct)
            next_id = dominant.parent_id

            if next_id in visited:
                is_circular = True
                logger.warning(
                    f"Circular ownership detected at {next_id} "
                    f"while tracing UBO from {entity_id}"
                )
                break

            running_pct *= dominant.ownership_pct / 100.0
            visited.add(next_id)
            chain.append(next_id)
            countries.append(self._entities[next_id].country)
            current_id = next_id

        ubo_id = chain[-1]
        result = UBOResult(
            entity_id=entity_id,
            ultimate_owner_id=ubo_id,
            chain=chain,
            total_ownership_pct=round(running_pct, 6),
            countries_in_chain=list(dict.fromkeys(countries)),  # deduplicated, ordered
            is_circular=is_circular,
            depth=len(chain) - 1,
        )
        log_operation(
            logger, "find_ubo", "completed",
            entity_id=entity_id, ubo=ubo_id, depth=result.depth,
        )
        return result

    # ------------------------------------------------------------------
    # Subsidiary traversal
    # ------------------------------------------------------------------

    def get_subsidiaries(
        self,
        parent_id: str,
        max_depth: int = 5,
    ) -> List[str]:
        """
        We return all entity IDs that are subsidiaries of parent_id,
        up to max_depth levels below.

        Args:
            parent_id:  Root parent entity.
            max_depth:  Maximum depth to descend.

        Returns:
            Flat list of subsidiary entity IDs (not including parent_id).

        Raises:
            ConfigurationError: If parent_id is not registered.
        """
        if parent_id not in self._entities:
            raise ConfigurationError(
                f"Entity '{parent_id}' is not registered.",
                details={"parent_id": parent_id},
            )

        # Build a reverse index: parent_id → [child_id, ...]
        reverse: Dict[str, List[str]] = {}
        for eid, links in self._ownership_links.items():
            for lnk in links:
                reverse.setdefault(lnk.parent_id, []).append(eid)

        result: List[str] = []
        queue: List[tuple] = [(parent_id, 0)]
        visited: Set[str] = {parent_id}

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for child_id in reverse.get(current, []):
                if child_id not in visited:
                    visited.add(child_id)
                    result.append(child_id)
                    queue.append((child_id, depth + 1))

        return result

    # ------------------------------------------------------------------
    # Circular ownership detection
    # ------------------------------------------------------------------

    def detect_circular_ownership(self, entity_id: str) -> List[List[str]]:
        """
        We find all cycles that pass through entity_id in the ownership graph.

        Args:
            entity_id: Entity to check for circular ownership.

        Returns:
            List of cycles, each cycle is a list of entity IDs forming the loop.
            Returns an empty list if no cycles are found.

        Raises:
            ConfigurationError: If entity_id is not registered.
        """
        if entity_id not in self._entities:
            raise ConfigurationError(
                f"Entity '{entity_id}' is not registered.",
                details={"entity_id": entity_id},
            )

        cycles: List[List[str]] = []
        self._dfs_cycles(entity_id, [], set(), cycles)
        return cycles

    def _dfs_cycles(
        self,
        current: str,
        path: List[str],
        path_set: Set[str],
        cycles: List[List[str]],
    ) -> None:
        """We perform a DFS to find all cycles through the current node."""
        path_set.add(current)
        path.append(current)

        for link in self._ownership_links.get(current, []):
            next_id = link.parent_id
            if next_id == path[0]:
                # Full cycle back to the starting node
                cycles.append(path[:] + [next_id])
            elif next_id not in path_set and next_id in self._entities:
                self._dfs_cycles(next_id, path, path_set, cycles)

        path.pop()
        path_set.discard(current)

    # ------------------------------------------------------------------
    # Group structure
    # ------------------------------------------------------------------

    def get_group_structure(self, root_id: str) -> Dict[str, Any]:
        """
        We return a nested dictionary describing the full group structure
        beneath root_id.

        Args:
            root_id: Top-level entity of the group.

        Returns:
            Dictionary with keys:
                - entity:       RegisteredEntity dict
                - subsidiaries: List of recursive get_group_structure results
                - direct_links: Summary of immediate ownership links
        """
        if root_id not in self._entities:
            raise ConfigurationError(
                f"Entity '{root_id}' is not registered.",
                details={"root_id": root_id},
            )

        entity = self._entities[root_id]

        # Reverse index for children
        reverse: Dict[str, List[OwnershipLink]] = {}
        for eid, links in self._ownership_links.items():
            for lnk in links:
                reverse.setdefault(lnk.parent_id, []).append(lnk)

        def _build(eid: str, visited: Set[str]) -> Dict[str, Any]:
            ent = self._entities[eid]
            children = reverse.get(eid, [])
            subs = []
            for lnk in sorted(children, key=lambda x: x.ownership_pct, reverse=True):
                if lnk.entity_id not in visited:
                    visited.add(lnk.entity_id)
                    subs.append({
                        "ownership_pct": lnk.ownership_pct,
                        "link_type": lnk.link_type,
                        "country": lnk.country,
                        "structure": _build(lnk.entity_id, visited),
                    })
            return {
                "entity_id": ent.entity_id,
                "name": ent.name,
                "country": ent.country,
                "entity_type": ent.entity_type,
                "residency_tier": ent.residency_tier.name,
                "subsidiaries": subs,
            }

        return _build(root_id, {root_id})

    def get_statistics(self) -> Dict[str, Any]:
        """We return summary statistics for the current registry."""
        total_links = sum(len(v) for v in self._ownership_links.values())
        countries = {e.country for e in self._entities.values()}
        return {
            "total_entities": len(self._entities),
            "total_ownership_links": total_links,
            "countries_represented": sorted(countries),
            "entity_types": {
                etype: sum(
                    1 for e in self._entities.values()
                    if e.entity_type == etype
                )
                for etype in {e.entity_type for e in self._entities.values()}
            },
        }


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    linker = SubsidiaryLinker()

    # Register a simple Mauritius → SA → Nigeria group structure
    linker.register_entity(
        "MU-HOLD-001", "Africa Growth Holdings Ltd", "MU", "holding",
        residency_tier=DataResidencyTier.MODERATE,
    )
    linker.register_entity(
        "ZA-OP-001", "AfriFlow OpCo (Pty) Ltd", "ZA", "operating",
        residency_tier=DataResidencyTier.STRICT,
    )
    linker.register_entity(
        "NG-BR-001", "AfriFlow Nigeria Branch", "NG", "branch",
        residency_tier=DataResidencyTier.MODERATE,
    )
    linker.register_entity(
        "KE-OP-001", "AfriFlow Kenya Ltd", "KE", "operating",
        residency_tier=DataResidencyTier.MODERATE,
    )

    # Ownership chain: NG-BR-001 and KE-OP-001 → ZA-OP-001 → MU-HOLD-001
    linker.add_ownership_link("ZA-OP-001", "MU-HOLD-001", 100.0, "MU")
    linker.add_ownership_link("NG-BR-001", "ZA-OP-001", 100.0, "ZA")
    linker.add_ownership_link("KE-OP-001", "ZA-OP-001", 75.0, "ZA")

    print("=== UBO Resolution ===")
    for eid in ["NG-BR-001", "KE-OP-001", "ZA-OP-001"]:
        res = linker.find_ubo(eid)
        print(
            f"  {eid:<15} → UBO: {res.ultimate_owner_id:<15} "
            f"chain: {' → '.join(res.chain):<40} "
            f"ownership: {res.total_ownership_pct:.2f}%  "
            f"countries: {res.countries_in_chain}"
        )

    print("\n=== Subsidiaries of MU-HOLD-001 ===")
    subs = linker.get_subsidiaries("MU-HOLD-001")
    for s in subs:
        e = linker._entities[s]
        print(f"  {s:<15} ({e.name}, {e.country})")

    print("\n=== Group Structure ===")
    import json
    structure = linker.get_group_structure("MU-HOLD-001")
    print(json.dumps(structure, indent=2))

    print("\n=== Circular Ownership Test ===")
    linker.register_entity("X-001", "Entity X", "ZA", "holding")
    linker.register_entity("X-002", "Entity Y", "ZA", "operating")
    linker.add_ownership_link("X-001", "X-002", 60.0, "ZA")
    linker.add_ownership_link("X-002", "X-001", 40.0, "ZA")  # circular!
    cycles = linker.detect_circular_ownership("X-001")
    print(f"  Cycles found: {len(cycles)}")
    for c in cycles:
        print(f"    {' → '.join(c)}")

    print("\n=== Statistics ===")
    print(linker.get_statistics())
