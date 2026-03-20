"""
@file schema_evolution_tracker.py
@description Schema Evolution Tracker - Track and manage schema changes
@author Thabo Kunene
@created 2026-03-19

This module tracks schema evolution over time and manages migrations
between schema versions. It ensures backward compatibility and prevents
breaking changes.

Key Classes:
- SchemaVersion: Schema version record
- SchemaEvolutionTracker: Main tracking engine

Features:
- Schema version tracking
- Change detection (added, removed, modified fields)
- Backward compatibility checking
- Migration path management
- Breaking change detection

Usage:
    >>> from afriflow.data_quality.schema_evolution_tracker import SchemaEvolutionTracker
    >>> tracker = SchemaEvolutionTracker()
    >>> tracker.register_version("cib", "1.0", {"fields": ["amount", "currency"]})
    >>> tracker.register_version("cib", "1.1", {"fields": ["amount", "currency", "date"]})
    >>> changes = tracker.get_changes("cib", "1.0", "1.1")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from enum import Enum
import logging

from afriflow.logging_config import get_logger

logger = get_logger("data_quality.schema")


class ChangeType(Enum):
    """
    Schema change type enumeration.

    Defines the types of schema changes:
    - ADDED: New field added
    - REMOVED: Field removed
    - MODIFIED: Field type/definition modified
    - RENAMED: Field renamed
    """
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    RENAMED = "RENAMED"


@dataclass
class SchemaVersion:
    """
    Schema version record.

    Represents a specific version of a domain schema.

    Attributes:
        domain: Domain name
        version: Version string (e.g., "1.0", "1.1")
        schema: Schema definition dictionary
        created_at: Version creation timestamp
        is_breaking: Whether this is a breaking change
        migration_notes: Migration instructions

    Example:
        >>> version = SchemaVersion(
        ...     domain="cib",
        ...     version="1.1",
        ...     schema={"fields": ["amount", "currency", "date"]}
        ... )
    """
    domain: str  # Domain name
    version: str  # Version string
    schema: Dict[str, Any]  # Schema definition
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_breaking: bool = False  # Breaking change flag
    migration_notes: str = ""  # Migration instructions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "domain": self.domain,
            "version": self.version,
            "schema": self.schema,
            "created_at": self.created_at,
            "is_breaking": self.is_breaking,
            "migration_notes": self.migration_notes,
        }


class SchemaEvolutionTracker:
    """
    Schema evolution tracking engine.

    Tracks schema versions and detects changes between
    versions to manage migrations and prevent breaking changes.

    Attributes:
        _versions: Dictionary mapping domain to version list
        _current_versions: Dictionary mapping domain to current version

    Example:
        >>> tracker = SchemaEvolutionTracker()
        >>> tracker.register_version("cib", "1.0", {"fields": ["amount"]})
        >>> tracker.register_version("cib", "1.1", {"fields": ["amount", "date"]})
        >>> changes = tracker.get_changes("cib", "1.0", "1.1")
    """

    def __init__(self) -> None:
        """Initialize schema tracker with empty version store."""
        self._versions: Dict[str, List[SchemaVersion]] = {}
        self._current_versions: Dict[str, str] = {}
        logger.info("SchemaEvolutionTracker initialized")

    def register_version(
        self,
        domain: str,
        version: str,
        schema: Dict[str, Any],
        migration_notes: str = ""
    ) -> SchemaVersion:
        """
        Register a new schema version.

        Args:
            domain: Domain name
            version: Version string (e.g., "1.0")
            schema: Schema definition dictionary
            migration_notes: Migration instructions

        Returns:
            Created SchemaVersion object

        Example:
            >>> version = tracker.register_version(
            ...     "cib", "1.1",
            ...     {"fields": ["amount", "currency", "date"]}
            ... )
        """
        # Get previous version
        prev_version = self._current_versions.get(domain)
        is_breaking = False

        # Check if this is a breaking change
        if prev_version:
            changes = self._detect_changes(domain, prev_version, version)
            is_breaking = self._is_breaking_change(changes)

        # Create version record
        schema_version = SchemaVersion(
            domain=domain,
            version=version,
            schema=schema,
            is_breaking=is_breaking,
            migration_notes=migration_notes
        )

        # Store version
        if domain not in self._versions:
            self._versions[domain] = []
        self._versions[domain].append(schema_version)
        self._current_versions[domain] = version

        logger.info(
            f"Schema version {version} registered for {domain} "
            f"(breaking: {is_breaking})"
        )

        return schema_version

    def get_version(
        self,
        domain: str,
        version: str
    ) -> Optional[SchemaVersion]:
        """
        Get specific schema version.

        Args:
            domain: Domain name
            version: Version string

        Returns:
            SchemaVersion if found, None otherwise
        """
        versions = self._versions.get(domain, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def get_current_version(self, domain: str) -> Optional[str]:
        """
        Get current schema version for a domain.

        Args:
            domain: Domain name

        Returns:
            Current version string or None
        """
        return self._current_versions.get(domain)

    def get_changes(
        self,
        domain: str,
        from_version: str,
        to_version: str
    ) -> List[Dict[str, Any]]:
        """
        Get changes between two schema versions.

        Args:
            domain: Domain name
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of change dictionaries

        Example:
            >>> changes = tracker.get_changes("cib", "1.0", "1.1")
            >>> for change in changes:
            ...     print(f"{change['type']}: {change['field']}")
        """
        return self._detect_changes(domain, from_version, to_version)

    def _detect_changes(
        self,
        domain: str,
        from_version: str,
        to_version: str
    ) -> List[Dict[str, Any]]:
        """
        Detect changes between schema versions.

        Args:
            domain: Domain name
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of change dictionaries
        """
        from_v = self.get_version(domain, from_version)
        to_v = self.get_version(domain, to_version)

        if not from_v or not to_v:
            logger.warning(
                f"Version not found: {domain} {from_version} or {to_version}"
            )
            return []

        # Get field sets
        from_fields = set(from_v.schema.get("fields", []))
        to_fields = set(to_v.schema.get("fields", []))

        changes = []

        # Detect added fields
        added = to_fields - from_fields
        for field in added:
            changes.append({
                "type": ChangeType.ADDED.value,
                "field": field,
                "from_version": from_version,
                "to_version": to_version,
            })

        # Detect removed fields
        removed = from_fields - to_fields
        for field in removed:
            changes.append({
                "type": ChangeType.REMOVED.value,
                "field": field,
                "from_version": from_version,
                "to_version": to_version,
            })

        return changes

    def _is_breaking_change(
        self,
        changes: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if changes are breaking.

        Args:
            changes: List of change dictionaries

        Returns:
            True if changes are breaking
        """
        for change in changes:
            # Removed fields are breaking
            if change["type"] == ChangeType.REMOVED.value:
                return True
        return False

    def get_version_history(
        self,
        domain: str
    ) -> List[SchemaVersion]:
        """
        Get version history for a domain.

        Args:
            domain: Domain name

        Returns:
            List of SchemaVersion objects sorted by version
        """
        versions = self._versions.get(domain, [])
        return sorted(versions, key=lambda v: v.version)

    def get_breaking_changes(
        self,
        domain: str
    ) -> List[SchemaVersion]:
        """
        Get all breaking changes for a domain.

        Args:
            domain: Domain name

        Returns:
            List of breaking SchemaVersion objects
        """
        versions = self.get_version_history(domain)
        return [v for v in versions if v.is_breaking]

    def validate_compatibility(
        self,
        domain: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Validate backward compatibility of a version.

        Args:
            domain: Domain name
            version: Version to validate

        Returns:
            Compatibility report dictionary
        """
        current = self._current_versions.get(domain)
        if not current:
            return {
                "compatible": True,
                "message": "No previous version",
            }

        changes = self._detect_changes(domain, current, version)
        is_breaking = self._is_breaking_change(changes)

        return {
            "compatible": not is_breaking,
            "is_breaking": is_breaking,
            "changes": changes,
            "message": (
                "Backward compatible" if not is_breaking
                else "Breaking changes detected"
            ),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get schema evolution statistics."""
        total_versions = sum(len(v) for v in self._versions.values())
        breaking_count = sum(
            sum(1 for v in versions if v.is_breaking)
            for versions in self._versions.values()
        )

        return {
            "total_domains": len(self._versions),
            "total_versions": total_versions,
            "breaking_changes": breaking_count,
            "non_breaking_changes": total_versions - breaking_count,
        }


__all__ = [
    "ChangeType",
    "SchemaVersion",
    "SchemaEvolutionTracker",
]
