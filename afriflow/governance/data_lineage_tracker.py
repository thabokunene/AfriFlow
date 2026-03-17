"""
Governance - Data Lineage Tracker

We track field-level data lineage from source systems
through transformations to the gold layer. This enables
impact analysis, root cause investigation, and regulatory
reporting on data origins.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import logging
import hashlib

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("governance.lineage_tracker")


class NodeType(Enum):
    """Type of lineage node."""
    SOURCE = "source"
    TRANSFORMATION = "transformation"
    TABLE = "table"
    COLUMN = "column"
    REPORT = "report"


class EdgeType(Enum):
    """Type of lineage edge."""
    FLOWS_TO = "flows_to"
    DERIVED_FROM = "derived_from"
    TRANSFORMS = "transforms"
    AGGREGATES = "aggregates"


@dataclass
class LineageNode:
    """
    A node in the data lineage graph.

    Attributes:
        node_id: Unique node identifier
        name: Node name
        node_type: Type of node
        metadata: Additional metadata
        created_at: Node creation timestamp
    """
    node_id: str
    name: str
    node_type: NodeType
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate node."""
        if not self.node_id or not self.name:
            raise ValueError("node_id and name are required")


@dataclass
class LineageEdge:
    """
    An edge in the data lineage graph.

    Attributes:
        source_id: Source node ID
        target_id: Target node ID
        edge_type: Type of edge
        transformation: Transformation description
        metadata: Additional metadata
    """
    source_id: str
    target_id: str
    edge_type: EdgeType
    transformation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataLineageTracker:
    """
    Tracks data lineage across the platform.

    We maintain a graph of nodes and edges representing
    data flow from sources through transformations to
    final outputs.

    Attributes:
        nodes: Nodes by ID
        edges: List of edges
    """

    def __init__(self) -> None:
        """Initialize the lineage tracker."""
        self.nodes: Dict[str, LineageNode] = {}
        self.edges: List[LineageEdge] = []

        logger.info("DataLineageTracker initialized")

    def create_node(
        self,
        name: str,
        node_type: NodeType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LineageNode:
        """
        Create a lineage node.

        Args:
            name: Node name
            node_type: Type of node
            metadata: Optional metadata

        Returns:
            Created node
        """
        node_id = self._generate_node_id(name, node_type)

        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already exists, returning existing")
            return self.nodes[node_id]

        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            metadata=metadata or {}
        )

        self.nodes[node_id] = node
        logger.debug(f"Created node: {node_id}")

        return node

    def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        transformation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LineageEdge:
        """
        Create a lineage edge.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of edge
            transformation: Optional transformation description
            metadata: Optional metadata

        Returns:
            Created edge

        Raises:
            ConfigurationError: If nodes don't exist
        """
        if source_id not in self.nodes:
            raise ConfigurationError(f"Source node {source_id} not found")
        if target_id not in self.nodes:
            raise ConfigurationError(f"Target node {target_id} not found")

        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            transformation=transformation,
            metadata=metadata or {}
        )

        self.edges.append(edge)
        logger.debug(f"Created edge: {source_id} -> {target_id}")

        return edge

    def trace_upstream(
        self,
        node_id: str,
        max_depth: int = 10
    ) -> List[str]:
        """
        Trace upstream lineage (data sources).

        Args:
            node_id: Node to trace from
            max_depth: Maximum depth to trace

        Returns:
            List of upstream node IDs
        """
        if node_id not in self.nodes:
            raise ConfigurationError(f"Node {node_id} not found")

        upstream: Set[str] = set()
        to_visit = [node_id]
        depth = 0

        while to_visit and depth < max_depth:
            current = to_visit.pop(0)
            depth += 1

            for edge in self.edges:
                if edge.target_id == current and edge.source_id not in upstream:
                    upstream.add(edge.source_id)
                    to_visit.append(edge.source_id)

        logger.debug(
            f"Traced {len(upstream)} upstream nodes from {node_id}"
        )

        return list(upstream)

    def trace_downstream(
        self,
        node_id: str,
        max_depth: int = 10
    ) -> List[str]:
        """
        Trace downstream lineage (data consumers).

        Args:
            node_id: Node to trace from
            max_depth: Maximum depth to trace

        Returns:
            List of downstream node IDs
        """
        if node_id not in self.nodes:
            raise ConfigurationError(f"Node {node_id} not found")

        downstream: Set[str] = set()
        to_visit = [node_id]
        depth = 0

        while to_visit and depth < max_depth:
            current = to_visit.pop(0)
            depth += 1

            for edge in self.edges:
                if edge.source_id == current and edge.target_id not in downstream:
                    downstream.add(edge.target_id)
                    to_visit.append(edge.target_id)

        logger.debug(
            f"Traced {len(downstream)} downstream nodes from {node_id}"
        )

        return list(downstream)

    def get_lineage(
        self,
        node_id: str
    ) -> Dict[str, Any]:
        """
        Get complete lineage for a node.

        Args:
            node_id: Node to get lineage for

        Returns:
            Lineage dictionary
        """
        if node_id not in self.nodes:
            raise ConfigurationError(f"Node {node_id} not found")

        node = self.nodes[node_id]

        return {
            "node": {
                "id": node.node_id,
                "name": node.name,
                "type": node.node_type.value,
                "metadata": node.metadata,
            },
            "upstream": self.trace_upstream(node_id),
            "downstream": self.trace_downstream(node_id),
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                    "transformation": e.transformation,
                }
                for e in self.edges
                if e.source_id == node_id or e.target_id == node_id
            ],
        }

    def _generate_node_id(
        self,
        name: str,
        node_type: NodeType
    ) -> str:
        """
        Generate unique node ID.

        Args:
            name: Node name
            node_type: Node type

        Returns:
            Unique node ID
        """
        key = f"{node_type.value}:{name}"
        hash_hex = hashlib.sha256(
            key.encode("utf-8")
        ).hexdigest()[:12].upper()
        return f"{node_type.value.upper()}-{hash_hex}"

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lineage statistics.

        Returns:
            Statistics dictionary
        """
        by_type: Dict[str, int] = {}
        for node in self.nodes.values():
            node_type = node.node_type.value
            by_type[node_type] = by_type.get(node_type, 0) + 1

        by_edge_type: Dict[str, int] = {}
        for edge in self.edges:
            edge_type = edge.edge_type.value
            by_edge_type[edge_type] = by_edge_type.get(edge_type, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": by_type,
            "edges_by_type": by_edge_type,
        }


if __name__ == "__main__":
    # Demo usage
    tracker = DataLineageTracker()

    # Create nodes
    source = tracker.create_node(
        "bronze_cib_payments",
        NodeType.TABLE,
        {"domain": "cib", "layer": "bronze"}
    )

    transform = tracker.create_node(
        "clean_cib_payments",
        NodeType.TRANSFORMATION,
        {"type": "dbt_model"}
    )

    silver = tracker.create_node(
        "silver_cib_payments",
        NodeType.TABLE,
        {"domain": "cib", "layer": "silver"}
    )

    # Create edges
    tracker.create_edge(
        source.node_id,
        transform.node_id,
        EdgeType.FLOWS_TO
    )

    tracker.create_edge(
        transform.node_id,
        silver.node_id,
        EdgeType.TRANSFORMS,
        transformation="Clean and validate CIB payments"
    )

    # Get lineage
    lineage = tracker.get_lineage(silver.node_id)
    print(f"Lineage for {silver.name}:")
    print(f"  Upstream: {lineage['upstream']}")
    print(f"  Edges: {len(lineage['edges'])}")
