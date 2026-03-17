"""
integration/entity_resolution/__init__.py

Entity Resolution package for AfriFlow.

We provide cross-domain entity resolution capabilities for the
pan-African data integration platform, including multilingual
name normalisation, corporate subsidiary linkage, human-in-the-loop
match verification, and an entity relationship graph.

DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
Group, MTN, or any affiliated entity. It is a demonstration of concept,
domain knowledge, and data engineering skill by Thabo Kunene.
"""

from afriflow.integration.entity_resolution.multilingual_normaliser import (
    MultilingualNormaliser,
    NormalisedEntity,
    LanguageHint,
    EntityType,
)

from afriflow.integration.entity_resolution.subsidiary_linker import (
    SubsidiaryLinker,
    OwnershipLink,
    UBOResult,
    RegisteredEntity,
    LinkType,
    EntityCategory,
)

from afriflow.integration.entity_resolution.match_verification_queue import (
    MatchVerificationQueue,
    MatchCandidate,
    VerificationStatus,
    Priority,
)

from afriflow.integration.entity_resolution.entity_graph import (
    EntityGraph,
    EntityNode,
    EntityEdge,
    RelationshipType,
)
from afriflow.integration.entity_resolution.client_matcher import (
    ClientMatcher,
    EntityResolver,
    ClientEntity,
    ResolvedEntity,
)

__all__ = [
    # Multilingual normaliser
    "MultilingualNormaliser",
    "NormalisedEntity",
    "LanguageHint",
    "EntityType",
    # Subsidiary linker
    "SubsidiaryLinker",
    "OwnershipLink",
    "UBOResult",
    "RegisteredEntity",
    "LinkType",
    "EntityCategory",
    # Match verification queue
    "MatchVerificationQueue",
    "MatchCandidate",
    "VerificationStatus",
    "Priority",
    # Entity graph
    "EntityGraph",
    "EntityNode",
    "EntityEdge",
    "RelationshipType",
    # Client matcher / resolver
    "ClientMatcher",
    "EntityResolver",
    "ClientEntity",
    "ResolvedEntity",
]
