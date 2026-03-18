"""
@file entity_graph.py
@description Entity Relationship Graph for the AfriFlow entity resolution layer.
             Maintains a lightweight adjacency-list directed graph of resolved
             entities and their relationships. Supports connected-component
             clustering, BFS shortest-path analysis, key-connector identification
             (hub entities with high degree centrality), and multi-hop traversal
             for hidden related-party discovery. All operations use only the Python
             standard library — no networkx dependency required.
@author Thabo Kunene
@created 2026-03-18
"""

from collections import deque   # used for BFS queue in traversal methods
from dataclasses import dataclass, field  # structured node and edge value objects
from typing import Any, Dict, List, Optional, Set  # full type annotations
from enum import Enum            # typed relationship categories

# AfriFlow internal imports
from afriflow.exceptions import ConfigurationError   # raised for invalid graph operations
from afriflow.logging_config import get_logger, log_operation  # structured logging

# Module-level logger
logger = get_logger("entity_resolution.entity_graph")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RelationshipType(Enum):
    """Semantic type of a directed edge in the entity graph."""
    SAME_AS         = "same_as"          # Golden ID merge or alias — both IDs are the same entity
    SUBSIDIARY_OF   = "subsidiary_of"    # Ownership relationship — source is owned by target
    DIRECTOR_OF     = "director_of"      # Natural person sits on board of the target entity
    COUNTERPARTY    = "counterparty"     # Transaction counterparty relationship
    GUARANTOR_OF    = "guarantor_of"     # Credit guarantee — source guarantees target's obligations
    CONNECTED_PARTY = "connected_party"  # Regulatory connected-party declaration (KYC)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EntityNode:
    """
    We represent a single entity vertex in the graph.

    Attributes:
        entity_id:   Unique identifier (may be a golden ID).
        entity_type: Broad type — "person", "company", or "group".
        golden_id:   Golden record ID if the entity has been resolved.
        domains:     List of domains where this entity appears
                     (cib, forex, cell, insurance, pbb).
        country:     ISO 3166-1 alpha-2 country code.
        metadata:    Arbitrary key-value attributes.
    """

    entity_id: str                                       # unique vertex identifier
    entity_type: str                                     # "person", "company", or "group"
    country: str                                         # ISO 3166-1 alpha-2 country code
    domains: List[str] = field(default_factory=list)     # domains where this entity appears
    golden_id: Optional[str] = None                      # resolved golden record ID (if any)
    metadata: Dict[str, Any] = field(default_factory=dict)  # arbitrary additional attributes


@dataclass
class EntityEdge:
    """
    We represent a directed relationship between two entity nodes.

    Attributes:
        source_id:          Origin entity.
        target_id:          Destination entity.
        relationship_type:  RelationshipType enum value.
        weight:             Edge weight (default 1.0; lower = closer).
        metadata:           Arbitrary key-value attributes.
    """

    source_id: str                                       # origin entity ID
    target_id: str                                       # destination entity ID
    relationship_type: RelationshipType                  # semantic type of the relationship
    weight: float = 1.0                                  # edge weight — lower means closer
    metadata: Dict[str, Any] = field(default_factory=dict)  # arbitrary edge attributes


# ---------------------------------------------------------------------------
# Graph class
# ---------------------------------------------------------------------------

class EntityGraph:
    """
    We provide a directed, weighted graph of entity relationships with
    traversal methods suited to financial services use cases.

    The graph is stored as:
      - _nodes: entity_id → EntityNode
      - _adj:   source_id → list of EntityEdge (outgoing edges)
      - _radj:  target_id → list of EntityEdge (incoming edges, for reverse traversal)

    Usage::

        graph = EntityGraph()
        graph.add_node("GLD-001", "company", "ZA", ["cib", "forex"])
        graph.add_node("GLD-002", "company", "NG", ["cib"])
        graph.add_edge("GLD-001", "GLD-002", RelationshipType.COUNTERPARTY)
        connected = graph.find_connected_entities("GLD-001", max_depth=2)
    """

    def __init__(self) -> None:
        """Initialise an empty entity graph with no nodes or edges."""
        self._nodes: Dict[str, EntityNode] = {}           # vertex store
        self._adj: Dict[str, List[EntityEdge]] = {}        # outgoing edges per node
        self._radj: Dict[str, List[EntityEdge]] = {}       # incoming edges per node (reverse)
        logger.info("EntityGraph initialised")

    # ------------------------------------------------------------------
    # Node / edge management
    # ------------------------------------------------------------------

    def add_node(
        self,
        entity_id: str,
        entity_type: str,
        country: str,
        domains: Optional[List[str]] = None,
        golden_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EntityNode:
        """
        We add a new entity node to the graph.

        If a node with the same entity_id already exists it is updated
        in-place (domains are merged, metadata is merged).

        :param entity_id:   Unique identifier.
        :param entity_type: "person", "company", or "group".
        :param country:     ISO 3166-1 alpha-2 country code.
        :param domains:     Domain list (cib / forex / cell / insurance / pbb).
        :param golden_id:   Optional resolved golden record ID.
        :param metadata:    Optional key-value attributes.
        :return: The new or updated EntityNode.
        :raises ConfigurationError: If entity_type is not one of the valid values.
        """
        # Enforce the three recognised entity types to prevent typos in data pipelines
        valid_types = {"person", "company", "group"}
        if entity_type not in valid_types:
            raise ConfigurationError(
                f"entity_type must be one of {sorted(valid_types)}",
                details={"received": entity_type},
            )

        if entity_id in self._nodes:
            # Update existing node: merge domains (deduplicated) and metadata
            node = self._nodes[entity_id]
            if domains:
                # dict.fromkeys preserves insertion order while deduplicating
                merged = list(dict.fromkeys(node.domains + domains))
                node.domains = merged
            if golden_id:
                node.golden_id = golden_id  # overwrite with the latest resolved ID
            if metadata:
                node.metadata.update(metadata)  # shallow merge
            logger.debug(f"Updated existing node: {entity_id}")
            return node

        # Create and register a new node
        node = EntityNode(
            entity_id=entity_id,
            entity_type=entity_type,
            country=country.upper(),  # normalise to uppercase ISO code
            domains=domains or [],
            golden_id=golden_id,
            metadata=metadata or {},
        )
        self._nodes[entity_id] = node
        # Pre-initialise adjacency lists to avoid KeyError on first edge add
        self._adj.setdefault(entity_id, [])
        self._radj.setdefault(entity_id, [])
        logger.debug(f"Added node: {entity_id} ({entity_type}, {country})")
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EntityEdge:
        """
        We add a directed relationship edge between two nodes.

        :param source_id:          Origin entity.
        :param target_id:          Destination entity.
        :param relationship_type:  RelationshipType enum value.
        :param weight:             Edge weight (default 1.0; must be > 0).
        :param metadata:           Optional key-value attributes.
        :return: The created EntityEdge.
        :raises ConfigurationError: If either node is not registered or weight <= 0.
        """
        # Both nodes must exist before an edge can be created
        if source_id not in self._nodes:
            raise ConfigurationError(
                f"Source node '{source_id}' not in graph. Add it first.",
                details={"source_id": source_id},
            )
        if target_id not in self._nodes:
            raise ConfigurationError(
                f"Target node '{target_id}' not in graph. Add it first.",
                details={"target_id": target_id},
            )
        # Zero or negative weights are invalid for this graph model
        if weight <= 0:
            raise ConfigurationError(
                f"Edge weight must be > 0, got {weight}",
                details={"weight": weight},
            )

        edge = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            weight=weight,
            metadata=metadata or {},
        )
        # Record edge in both forward (adj) and reverse (radj) indexes
        self._adj[source_id].append(edge)
        self._radj[target_id].append(edge)
        logger.debug(
            f"Added edge: {source_id} -[{relationship_type.value}]-> {target_id}"
        )
        return edge

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def find_connected_entities(
        self,
        entity_id: str,
        max_depth: int = 3,
        relationship_types: Optional[List[RelationshipType]] = None,
    ) -> List[EntityNode]:
        """
        We find all entity nodes reachable from entity_id within max_depth
        hops, traversing both outgoing and incoming edges (undirected view).

        :param entity_id:          Starting node.
        :param max_depth:          Maximum number of hops (default 3).
        :param relationship_types: If provided, only traverse edges of these types.
        :return: List of EntityNode objects ordered by discovery depth then entity_id.
                 Does not include the starting node.
        :raises ConfigurationError: If entity_id is not in the graph.
        """
        if entity_id not in self._nodes:
            raise ConfigurationError(
                f"Node '{entity_id}' not in graph.",
                details={"entity_id": entity_id},
            )

        log_operation(
            logger, "find_connected_entities", "started",
            entity_id=entity_id, max_depth=max_depth,
        )

        # Convert optional list to a set for O(1) membership tests
        rt_filter: Optional[Set[RelationshipType]] = (
            set(relationship_types) if relationship_types else None
        )

        visited: Set[str] = {entity_id}  # track visited nodes to avoid cycles
        queue: deque = deque([(entity_id, 0)])  # (node_id, depth)
        result_ids: List[str] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue  # do not traverse beyond the depth limit

            # Traverse outgoing edges (forward direction)
            for edge in self._adj.get(current_id, []):
                if rt_filter and edge.relationship_type not in rt_filter:
                    continue  # skip edge types not in the filter
                neighbour = edge.target_id
                if neighbour not in visited:
                    visited.add(neighbour)
                    result_ids.append(neighbour)
                    queue.append((neighbour, depth + 1))

            # Traverse incoming edges (reverse direction — undirected BFS)
            for edge in self._radj.get(current_id, []):
                if rt_filter and edge.relationship_type not in rt_filter:
                    continue
                neighbour = edge.source_id
                if neighbour not in visited:
                    visited.add(neighbour)
                    result_ids.append(neighbour)
                    queue.append((neighbour, depth + 1))

        nodes = [self._nodes[nid] for nid in result_ids if nid in self._nodes]
        log_operation(
            logger, "find_connected_entities", "completed",
            entity_id=entity_id, found=len(nodes),
        )
        return nodes

    def find_path(
        self,
        source_id: str,
        target_id: str,
    ) -> Optional[List[str]]:
        """
        We find the shortest path between two entities using BFS on the
        undirected view of the graph.

        :param source_id: Starting entity.
        :param target_id: Destination entity.
        :return: Ordered list of entity IDs from source to target,
                 or None if no path exists.
        :raises ConfigurationError: If either node is not in the graph.
        """
        # Validate both endpoints before starting BFS
        for nid in (source_id, target_id):
            if nid not in self._nodes:
                raise ConfigurationError(
                    f"Node '{nid}' not in graph.",
                    details={"node_id": nid},
                )

        # Trivial case: source and target are the same node
        if source_id == target_id:
            return [source_id]

        # BFS with predecessor path tracking
        visited: Set[str] = {source_id}
        queue: deque = deque([(source_id, [source_id])])  # (node_id, path_so_far)

        while queue:
            current_id, path = queue.popleft()

            # Collect all neighbours in both directions (undirected BFS)
            neighbours: List[str] = []
            for edge in self._adj.get(current_id, []):
                neighbours.append(edge.target_id)
            for edge in self._radj.get(current_id, []):
                neighbours.append(edge.source_id)

            for neighbour in neighbours:
                if neighbour == target_id:
                    return path + [target_id]  # shortest path found
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append((neighbour, path + [neighbour]))

        return None  # no path exists between source and target

    def get_cluster(self, entity_id: str) -> List[str]:
        """
        We return the connected component containing entity_id — all
        entity IDs reachable from it in the undirected graph.

        :param entity_id: Any node in the graph.
        :return: Sorted list of all entity IDs in the same connected component,
                 including entity_id itself.
        :raises ConfigurationError: If entity_id is not in the graph.
        """
        if entity_id not in self._nodes:
            raise ConfigurationError(
                f"Node '{entity_id}' not in graph.",
                details={"entity_id": entity_id},
            )

        # Unlimited BFS to collect the full connected component
        visited: Set[str] = set()
        queue: deque = deque([entity_id])
        visited.add(entity_id)

        while queue:
            current_id = queue.popleft()
            # Collect all undirected neighbours
            neighbours: List[str] = []
            for edge in self._adj.get(current_id, []):
                neighbours.append(edge.target_id)
            for edge in self._radj.get(current_id, []):
                neighbours.append(edge.source_id)
            for n in neighbours:
                if n not in visited:
                    visited.add(n)
                    queue.append(n)

        return sorted(visited)  # sorted for deterministic output

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def identify_key_connectors(
        self,
        min_connections: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        We identify hub entities with high degree centrality — nodes with
        many connections that serve as critical connectors in the graph.

        These hubs are important for:
          - AML typology detection (structuring hubs).
          - Cross-sell opportunity mapping (widely-connected clients).
          - Contagion analysis (default propagation risk).

        :param min_connections: Minimum total degree (in + out) to be included.
        :return: List of dicts sorted descending by total_degree. Each dict
                 contains: entity_id, entity_type, country, in_degree,
                 out_degree, total_degree, domains, golden_id.
        """
        result = []
        for entity_id, node in self._nodes.items():
            out_degree = len(self._adj.get(entity_id, []))   # outgoing edge count
            in_degree = len(self._radj.get(entity_id, []))   # incoming edge count
            total = in_degree + out_degree
            if total >= min_connections:
                result.append({
                    "entity_id": entity_id,
                    "entity_type": node.entity_type,
                    "country": node.country,
                    "domains": node.domains,
                    "in_degree": in_degree,
                    "out_degree": out_degree,
                    "total_degree": total,
                    "golden_id": node.golden_id,
                })

        # Sort by total degree descending so the most connected entities appear first
        result.sort(key=lambda x: x["total_degree"], reverse=True)
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """
        We return graph-wide structural statistics.

        :return: Dictionary with node/edge counts, relationship type distribution,
                 domain coverage, country coverage, and isolated node count.
        """
        total_edges = sum(len(edges) for edges in self._adj.values())

        # Count edges by relationship type
        by_relationship: Dict[str, int] = {}
        for edges in self._adj.values():
            for edge in edges:
                rt = edge.relationship_type.value
                by_relationship[rt] = by_relationship.get(rt, 0) + 1

        countries: Set[str] = {n.country for n in self._nodes.values()}

        # Count nodes by entity type (person / company / group)
        entity_types: Dict[str, int] = {}
        for n in self._nodes.values():
            entity_types[n.entity_type] = entity_types.get(n.entity_type, 0) + 1

        # Collect all distinct domain names across all nodes
        all_domains: Set[str] = set()
        for n in self._nodes.values():
            all_domains.update(n.domains)

        # Isolated nodes have no edges in either direction — potential data quality issues
        isolated = sum(
            1 for eid in self._nodes
            if not self._adj.get(eid) and not self._radj.get(eid)
        )

        return {
            "total_nodes": len(self._nodes),
            "total_edges": total_edges,
            "isolated_nodes": isolated,
            "entity_types": entity_types,
            "by_relationship_type": by_relationship,
            "countries_represented": sorted(countries),
            "domains_represented": sorted(all_domains),
        }


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    graph = EntityGraph()

    # Build a small pan-African entity graph for demonstration
    entities = [
        ("GLD-001", "company", "ZA", ["cib", "forex"],   "MTN Group Limited"),
        ("GLD-002", "company", "NG", ["cib", "cell"],    "MTN Nigeria"),
        ("GLD-003", "company", "GH", ["cell"],           "MTN Ghana"),
        ("GLD-004", "company", "KE", ["cell", "forex"],  "Safaricom"),
        ("GLD-005", "person",  "ZA", ["cib"],            "Ralph Mupita"),   # CEO
        ("GLD-006", "company", "ZA", ["cib", "pbb"],     "Standard Bank Group"),
        ("GLD-007", "company", "MU", ["cib"],            "Africa Growth Holdings"),
    ]
    for eid, etype, country, domains, _name in entities:
        graph.add_node(eid, etype, country, domains, metadata={"name": _name})

    # Add relationship edges
    edges = [
        ("GLD-002", "GLD-001", RelationshipType.SUBSIDIARY_OF),
        ("GLD-003", "GLD-001", RelationshipType.SUBSIDIARY_OF),
        ("GLD-005", "GLD-001", RelationshipType.DIRECTOR_OF),
        ("GLD-001", "GLD-006", RelationshipType.COUNTERPARTY),
        ("GLD-004", "GLD-006", RelationshipType.COUNTERPARTY),
        ("GLD-007", "GLD-001", RelationshipType.SUBSIDIARY_OF),
        ("GLD-006", "GLD-007", RelationshipType.GUARANTOR_OF),
    ]
    for src, tgt, rtype in edges:
        graph.add_edge(src, tgt, rtype)

    print("=== Graph Statistics ===")
    import json
    print(json.dumps(graph.get_statistics(), indent=2))

    print("\n=== Connected entities from GLD-001 (depth 2) ===")
    connected = graph.find_connected_entities("GLD-001", max_depth=2)
    for n in connected:
        print(f"  {n.entity_id} ({n.entity_type}, {n.country}) — {n.metadata.get('name')}")

    print("\n=== Shortest path: GLD-002 → GLD-006 ===")
    path = graph.find_path("GLD-002", "GLD-006")
    print(f"  {' → '.join(path)}" if path else "  No path found")

    print("\n=== Cluster containing GLD-003 ===")
    cluster = graph.get_cluster("GLD-003")
    print(f"  {cluster}")

    print("\n=== Key connectors (min_connections=2) ===")
    connectors = graph.identify_key_connectors(min_connections=2)
    for c in connectors:
        print(
            f"  {c['entity_id']:<10} "
            f"total={c['total_degree']}  "
            f"(in={c['in_degree']}, out={c['out_degree']})  "
            f"{c.get('name', '')}"
        )

    print("\n=== Filter: SUBSIDIARY_OF edges only (from GLD-001) ===")
    subs_connected = graph.find_connected_entities(
        "GLD-001",
        max_depth=2,
        relationship_types=[RelationshipType.SUBSIDIARY_OF],
    )
    for n in subs_connected:
        print(f"  {n.entity_id} — {n.metadata.get('name')}")
