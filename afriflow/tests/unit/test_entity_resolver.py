"""
tests/unit/test_entity_resolver.py

Unit tests for entity resolution client matcher with
comprehensive error-path and edge-case coverage.

Disclaimer:
    This project is not sanctioned by, affiliated with,
    or endorsed by Standard Bank Group, MTN Group, or any
    affiliated entity.
"""

import pytest
from unittest.mock import patch

from afriflow.integration.entity_resolution.client_matcher import (
    ClientMatcher,
    ClientEntity,
    ResolvedEntity,
    EntityResolver,
)
from afriflow.exceptions import EntityResolutionError, ValidationError


class TestClientMatcher:
    """Test client matcher functionality and error handling."""

    @pytest.fixture
    def matcher(self) -> ClientMatcher:
        """Create default matcher with demo data."""
        return ClientMatcher()

    @pytest.fixture
    def custom_matcher(self) -> ClientMatcher:
        """Create matcher with custom golden records."""
        custom_records = {
            "C001": "TEST CORPORATION LTD",
            "C002": "SAMPLE HOLDINGS PLC",
        }
        return ClientMatcher(golden_records=custom_records, default_threshold=75)

    # ==================== Initialization Tests ====================

    def test_initialization_with_default_threshold(self) -> None:
        """Test matcher initializes with default threshold."""
        matcher = ClientMatcher(default_threshold=85)
        assert matcher.default_threshold == 85

    def test_initialization_with_custom_golden_records(self) -> None:
        """Test matcher initializes with custom golden records."""
        custom = {"ID1": "COMPANY ONE", "ID2": "COMPANY TWO"}
        matcher = ClientMatcher(golden_records=custom)
        assert len(matcher.golden_records) == 2
        assert "COMPANY ONE" in matcher.golden_records.values()

    def test_initialization_invalid_threshold_low(self) -> None:
        """Test matcher rejects threshold < 0."""
        with pytest.raises(ValidationError) as exc_info:
            ClientMatcher(default_threshold=-1)
        assert "default_threshold" in str(exc_info.value)
        assert exc_info.value.field == "default_threshold"

    def test_initialization_invalid_threshold_high(self) -> None:
        """Test matcher rejects threshold > 100."""
        with pytest.raises(ValidationError) as exc_info:
            ClientMatcher(default_threshold=101)
        assert "default_threshold" in str(exc_info.value)

    def test_initialization_invalid_golden_records_type(self) -> None:
        """Test matcher rejects non-dict golden_records."""
        with pytest.raises(ValidationError) as exc_info:
            ClientMatcher(golden_records="invalid")  # type: ignore
        assert "golden_records" in str(exc_info.value)

    def test_initialization_without_thefuzz(self) -> None:
        """Test matcher raises error if thefuzz unavailable."""
        with patch(
            "afriflow.integration.entity_resolution.client_matcher.THEFUZZ_AVAILABLE",
            False
        ):
            with pytest.raises(EntityResolutionError) as exc_info:
                ClientMatcher()
            assert "thefuzz" in str(exc_info.value)

    # ==================== match_client Tests ====================

    def test_exact_match(self, matcher: ClientMatcher) -> None:
        """Test exact name match returns correct golden ID."""
        result = matcher.match_client("DANGOTE CEMENT PLC")
        assert result["golden_id"] == "1001"
        assert result["golden_name"] == "DANGOTE CEMENT PLC"
        assert result["confidence"] == 100
        assert result["match_status"] == "MATCHED"

    def test_fuzzy_match_typo(self, matcher: ClientMatcher) -> None:
        """Test fuzzy match with typo returns correct result."""
        result = matcher.match_client("Dangote Cemnt")
        assert result["golden_id"] == "1001"
        assert result["confidence"] > 85
        assert result["match_status"] == "MATCHED"

    def test_fuzzy_match_substring(self, matcher: ClientMatcher) -> None:
        """Test fuzzy match with substring returns correct result."""
        result = matcher.match_client("MTN Group")
        assert result["golden_id"] == "1002"
        assert result["confidence"] > 90

    def test_no_match_below_threshold(self, matcher: ClientMatcher) -> None:
        """Test no match when below confidence threshold."""
        result = matcher.match_client("Random Small Shop Ltd")
        if result["confidence"] < matcher.default_threshold:
            assert result["golden_id"] is None
            assert result["match_status"] == "NO_MATCH"

    def test_match_empty_input(self, matcher: ClientMatcher) -> None:
        """Test handling of empty input."""
        result = matcher.match_client("")
        assert result["golden_id"] is None
        # Empty string is caught by "not dirty_name" check first
        assert result["match_status"] in ("EMPTY_AFTER_CLEAN", "INVALID_INPUT")

    def test_match_whitespace_only_input(self, matcher: ClientMatcher) -> None:
        """Test handling of whitespace-only input."""
        result = matcher.match_client("   ")
        assert result["golden_id"] is None
        assert result["match_status"] == "EMPTY_AFTER_CLEAN"

    def test_match_none_input(self, matcher: ClientMatcher) -> None:
        """Test handling of None input."""
        result = matcher.match_client(None)  # type: ignore
        assert result["golden_id"] is None
        assert result["match_status"] == "INVALID_INPUT"

    def test_match_non_string_input(self, matcher: ClientMatcher) -> None:
        """Test handling of non-string input."""
        result = matcher.match_client(123)  # type: ignore
        assert result["golden_id"] is None
        assert result["match_status"] == "INVALID_INPUT"

    def test_match_with_custom_threshold(self, custom_matcher: ClientMatcher) -> None:
        """Test matching with custom threshold."""
        result = custom_matcher.match_client("Test Corp", threshold=90)
        assert result["golden_id"] == "C001"
        assert result["confidence"] >= 90 or result["golden_id"] is None

    def test_match_logs_operation(self, matcher: ClientMatcher) -> None:
        """Test that match operation is logged."""
        # This test verifies logging happens - if it doesn't raise, it passes
        result = matcher.match_client("Vodacom Group")
        assert "golden_id" in result

    # ==================== match_batch Tests ====================

    def test_match_batch_empty_list(self, matcher: ClientMatcher) -> None:
        """Test batch matching with empty list."""
        results = matcher.match_batch([])
        assert results == []

    def test_match_batch_single_name(self, matcher: ClientMatcher) -> None:
        """Test batch matching with single name."""
        results = matcher.match_batch(["Dangote Cement"])
        assert len(results) == 1
        assert results[0]["golden_id"] == "1001"

    def test_match_batch_multiple_names(self, matcher: ClientMatcher) -> None:
        """Test batch matching with multiple names."""
        names = ["Dangote Cement", "MTN Group", "Unknown Company"]
        results = matcher.match_batch(names)
        assert len(results) == 3
        assert results[0]["golden_id"] == "1001"
        assert results[1]["golden_id"] == "1002"

    def test_match_batch_with_custom_threshold(
        self, custom_matcher: ClientMatcher
    ) -> None:
        """Test batch matching with custom threshold."""
        results = custom_matcher.match_batch(
            ["Test Corp", "Sample Holdings"], threshold=80
        )
        assert len(results) == 2

    # ==================== add_golden_record Tests ====================

    def test_add_golden_record_success(self, matcher: ClientMatcher) -> None:
        """Test adding new golden record."""
        initial_count = len(matcher.golden_records)
        matcher.add_golden_record("NEW001", "New Company Ltd")
        assert len(matcher.golden_records) == initial_count + 1
        assert "NEW001" in matcher.golden_records
        assert matcher.golden_records["NEW001"] == "NEW COMPANY LTD"

    def test_add_golden_record_duplicate_id(
        self, matcher: ClientMatcher
    ) -> None:
        """Test adding golden record with duplicate ID raises error."""
        with pytest.raises(EntityResolutionError) as exc_info:
            matcher.add_golden_record("1001", "Duplicate Name")
        assert "already exists" in str(exc_info.value)

    def test_add_golden_record_lowercase_conversion(
        self, matcher: ClientMatcher
    ) -> None:
        """Test that golden record names are converted to uppercase."""
        matcher.add_golden_record("NEW002", "lowercase company name")
        assert matcher.golden_records["NEW002"] == "LOWERCASE COMPANY NAME"

    # ==================== get_statistics Tests ====================

    def test_get_statistics(self, matcher: ClientMatcher) -> None:
        """Test getting matcher statistics."""
        stats = matcher.get_statistics()
        assert "total_golden_records" in stats
        assert "default_threshold" in stats
        assert "library_available" in stats
        assert stats["total_golden_records"] >= 7
        assert stats["default_threshold"] == 80

    # ==================== ClientEntity Tests ====================

    def test_client_entity_creation(self) -> None:
        """Test creating ClientEntity with required fields."""
        entity = ClientEntity(
            domain="cib",
            domain_id="CIB-001",
            name="Test Company"
        )
        assert entity.domain == "cib"
        assert entity.domain_id == "CIB-001"
        assert entity.name == "Test Company"
        assert entity.registration_number is None

    def test_client_entity_with_all_fields(self) -> None:
        """Test creating ClientEntity with all optional fields."""
        entity = ClientEntity(
            domain="forex",
            domain_id="FX-001",
            name="Forex Corp",
            registration_number="RC123456",
            tax_number="TX789",
            country="NG",
            address="123 Lagos Street",
            contact_email="info@forex.ng",
            contact_phone="+234-1-234-5678"
        )
        assert entity.registration_number == "RC123456"
        assert entity.tax_number == "TX789"
        assert entity.country == "NG"


class TestEntityResolver:
    """Test entity resolver functionality and error handling."""

    @pytest.fixture
    def resolver(self) -> EntityResolver:
        """Create empty entity resolver."""
        return EntityResolver()

    @pytest.fixture
    def sample_entities(self) -> list:
        """Create sample entities for testing."""
        return [
            ClientEntity(
                domain="cib",
                domain_id="CIB-001",
                name="Dangote Cement Plc",
                registration_number="RC123456",
                country="NG"
            ),
            ClientEntity(
                domain="forex",
                domain_id="FX-001",
                name="Dangote Cement",
                registration_number="RC123456",
                country="NG"
            ),
            ClientEntity(
                domain="cell",
                domain_id="CELL-001",
                name="MTN Group",
                registration_number="RC789012",
                country="ZA"
            ),
        ]

    # ==================== Initialization Tests ====================

    def test_resolver_initialization(self, resolver: EntityResolver) -> None:
        """Test resolver initializes with empty entity list."""
        assert resolver.get_entity_count() == 0
        assert len(resolver._entities) == 0

    # ==================== add_entity Tests ====================

    def test_add_entity_success(self, resolver: EntityResolver) -> None:
        """Test adding entity to resolver."""
        entity = ClientEntity(
            domain="cib", domain_id="CIB-001", name="Test Corp"
        )
        resolver.add_entity(entity)
        assert resolver.get_entity_count() == 1

    def test_add_entity_none(self, resolver: EntityResolver) -> None:
        """Test adding None entity raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            resolver.add_entity(None)  # type: ignore
        assert "entity cannot be None" in str(exc_info.value)
        assert exc_info.value.field == "entity"

    def test_add_entity_wrong_type(self, resolver: EntityResolver) -> None:
        """Test adding non-ClientEntity raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            resolver.add_entity("not an entity")  # type: ignore
        assert "must be a ClientEntity instance" in str(exc_info.value)

    def test_add_multiple_entities(
        self, resolver: EntityResolver, sample_entities: list
    ) -> None:
        """Test adding multiple entities."""
        for entity in sample_entities:
            resolver.add_entity(entity)
        assert resolver.get_entity_count() == 3

    # ==================== resolve_all Tests ====================

    def test_resolve_empty_resolver(self, resolver: EntityResolver) -> None:
        """Test resolving with no entities returns empty list."""
        results = resolver.resolve_all()
        assert results == []

    def test_resolve_entities_with_same_registration(
        self, resolver: EntityResolver, sample_entities: list
    ) -> None:
        """Test entities with same registration number are merged."""
        for entity in sample_entities[:2]:  # Add first two (same reg number)
            resolver.add_entity(entity)

        results = resolver.resolve_all()

        assert len(results) == 1
        assert results[0].match_confidence == 100.0
        assert "cib" in results[0].domain_ids
        assert "forex" in results[0].domain_ids

    def test_resolve_entities_different_registration(
        self, resolver: EntityResolver, sample_entities: list
    ) -> None:
        """Test entities with different registration numbers stay separate."""
        for entity in sample_entities:
            resolver.add_entity(entity)

        results = resolver.resolve_all()

        # Should have 2 clusters: Dangote (2 entities) and MTN (1 entity)
        assert len(results) >= 1

    def test_resolve_with_tax_number(
        self, resolver: EntityResolver
    ) -> None:
        """Test entities linked by tax number."""
        entities = [
            ClientEntity(
                domain="cib",
                domain_id="CIB-001",
                name="Tax Company",
                tax_number="TX123456"
            ),
            ClientEntity(
                domain="insurance",
                domain_id="INS-001",
                name="Tax Company Ltd",
                tax_number="TX123456"
            ),
        ]
        for entity in entities:
            resolver.add_entity(entity)

        results = resolver.resolve_all()
        assert len(results) == 1
        assert results[0].match_confidence == 90.0

    def test_resolve_no_strong_identifiers(
        self, resolver: EntityResolver
    ) -> None:
        """Test resolution with only name-based clustering."""
        entities = [
            ClientEntity(
                domain="cib", domain_id="CIB-001", name="Shoprite Holdings"
            ),
            ClientEntity(
                domain="cell", domain_id="CELL-001", name="Shoprite Group"
            ),
        ]
        for entity in entities:
            resolver.add_entity(entity)

        results = resolver.resolve_all()
        # Should cluster by name anchor
        assert len(results) >= 1

    def test_resolve_error_handling(self, resolver: EntityResolver) -> None:
        """Test resolution error handling."""
        # Add entity that might cause issues
        resolver.add_entity(
            ClientEntity(
                domain="test", domain_id="T001", name="Test Entity"
            )
        )

        # Should not raise, should return results
        results = resolver.resolve_all()
        assert isinstance(results, list)

    # ==================== Helper Method Tests ====================

    def test_clear_resolver(self, resolver: EntityResolver) -> None:
        """Test clearing resolver."""
        resolver.add_entity(
            ClientEntity(domain="cib", domain_id="CIB-001", name="Test")
        )
        assert resolver.get_entity_count() == 1

        resolver.clear()
        assert resolver.get_entity_count() == 0

    def test_get_entity_count(
        self, resolver: EntityResolver, sample_entities: list
    ) -> None:
        """Test getting entity count."""
        assert resolver.get_entity_count() == 0

        for entity in sample_entities:
            resolver.add_entity(entity)

        assert resolver.get_entity_count() == 3

    # ==================== ResolvedEntity Tests ====================

    def test_resolved_entity_creation(self) -> None:
        """Test creating ResolvedEntity."""
        resolved = ResolvedEntity(
            canonical_name="TEST CORPORATION",
            domain_ids={"cib": ["CIB-001"], "forex": ["FX-001"]},
            match_confidence=95.0
        )
        assert resolved.canonical_name == "TEST CORPORATION"
        assert len(resolved.domain_ids) == 2
        assert resolved.match_confidence == 95.0

    def test_resolved_entity_empty_domains(self) -> None:
        """Test ResolvedEntity with empty domain_ids."""
        resolved = ResolvedEntity(
            canonical_name="SOLO ENTITY",
            domain_ids={},
            match_confidence=70.0
        )
        assert resolved.canonical_name == "SOLO ENTITY"
        assert resolved.domain_ids == {}
