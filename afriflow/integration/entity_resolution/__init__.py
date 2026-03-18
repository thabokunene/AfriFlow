"""
@file __init__.py
@description Package init for the entity_resolution integration module.
             Exposes all public classes and data types for cross-domain
             entity resolution: multilingual name normalisation, corporate
             subsidiary linkage, human-in-the-loop match verification,
             an entity relationship graph, client fuzzy matching, and
             golden ID generation. Callers import from this package root
             rather than from individual sub-modules.
@author Thabo Kunene
@created 2026-03-18
"""

# Multilingual normaliser: handles English, Swahili, Yoruba, Hausa,
# French West Africa, and Romanised Arabic name conventions.
from afriflow.integration.entity_resolution.multilingual_normaliser import (
    MultilingualNormaliser,   # main normaliser class
    NormalisedEntity,          # result dataclass returned by normalise()
    LanguageHint,              # enum of detected language / script families
    EntityType,                # enum: PERSON, COMPANY, MSISDN, AUTO
)

# Subsidiary linker: traces ownership chains to find UBOs and group structures.
from afriflow.integration.entity_resolution.subsidiary_linker import (
    SubsidiaryLinker,          # main linker class with UBO resolution
    OwnershipLink,             # directed ownership relationship dataclass
    UBOResult,                 # resolved UBO chain result dataclass
    RegisteredEntity,          # legal entity registered in the linker
    LinkType,                  # enum: DIRECT, INDIRECT, BENEFICIAL, NOMINEE
    EntityCategory,            # enum: HOLDING, OPERATING, BRANCH, TRUST, etc.
)

# Match verification queue: human-in-the-loop review for uncertain matches.
from afriflow.integration.entity_resolution.match_verification_queue import (
    MatchVerificationQueue,    # manages candidate lifecycle and reviewer assignments
    MatchCandidate,            # single pair awaiting or having received a decision
    VerificationStatus,        # enum: PENDING, IN_REVIEW, CONFIRMED_MATCH, etc.
    Priority,                  # enum: HIGH, MEDIUM, LOW — queue ordering
)

# Entity graph: directed weighted graph for traversal and impact analysis.
from afriflow.integration.entity_resolution.entity_graph import (
    EntityGraph,               # main graph class with BFS traversal methods
    EntityNode,                # vertex dataclass (entity_id, type, country, domains)
    EntityEdge,                # directed edge dataclass with relationship type
    RelationshipType,          # enum: SAME_AS, SUBSIDIARY_OF, DIRECTOR_OF, etc.
)

# Client matcher and entity resolver: fuzzy matching against golden records.
from afriflow.integration.entity_resolution.client_matcher import (
    ClientMatcher,             # fuzzy matcher against a golden record store
    EntityResolver,            # multi-entity resolver using deterministic + heuristic stages
    ClientEntity,              # raw entity record from a single source domain
    ResolvedEntity,            # unified cross-domain entity with canonical name
)

# Explicit public API — controls what `from package import *` exposes
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
