"""
Entity Resolution - Golden ID Generator

Deterministic Golden ID generation for cross-domain
entity resolution.

We generate stable, collision-resistant identifiers
that remain consistent across resolution runs regardless
of the order in which entities are processed.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import hashlib
from typing import Optional
import logging

from afriflow.exceptions import EntityResolutionError
from afriflow.logging_config import get_logger

logger = get_logger("entity_resolution.golden_id")


def generate_golden_id(
    registration_number: Optional[str] = None,
    tax_number: Optional[str] = None,
    name: Optional[str] = None,
    country: Optional[str] = None,
) -> str:
    """
    Generate a deterministic Golden ID using the most stable
    identifier available.

    Priority order:
    1. Registration number (most stable, government-issued)
    2. Tax number (stable, government-issued)
    3. Normalized name + country (fallback, less stable)

    The ID is a truncated SHA-256 hash prefixed with
    'GLD-' for easy identification in logs and queries.

    Args:
        registration_number: Company registration number
        tax_number: Tax identification number
        name: Company name (used if no reg/tax number)
        country: Country code (required if using name)

    Returns:
        Golden ID in format 'GLD-XXXXXXXXXXXX' where X is hex

    Raises:
        EntityResolutionError: If insufficient information provided

    Example:
        >>> generate_golden_id(registration_number="1979/003231/06")
        'GLD-A1B2C3D4E5F6'
        >>> generate_golden_id(tax_number="4250089747")
        'GLD-F6E5D4C3B2A1'
        >>> generate_golden_id(name="Acme Ltd", country="ZA")
        'GLD-123456789ABC'
    """
    logger.debug(
        f"Generating golden ID: reg={registration_number}, "
        f"tax={tax_number}, name={name}, country={country}"
    )

    try:
        # Priority 1: Registration number (most reliable)
        if registration_number:
            if not isinstance(registration_number, str):
                raise EntityResolutionError(
                    "registration_number must be a string",
                    details={"type": type(registration_number).__name__}
                )
            stable_key = f"REG:{registration_number.strip()}"
            id_source = "registration_number"

        # Priority 2: Tax number
        elif tax_number:
            if not isinstance(tax_number, str):
                raise EntityResolutionError(
                    "tax_number must be a string",
                    details={"type": type(tax_number).__name__}
                )
            stable_key = f"TAX:{tax_number.strip()}"
            id_source = "tax_number"

        # Priority 3: Name + country (least reliable)
        elif name and country:
            if not isinstance(name, str) or not isinstance(country, str):
                raise EntityResolutionError(
                    "name and country must be strings",
                    details={
                        "name_type": type(name).__name__,
                        "country_type": type(country).__name__
                    }
                )
            normalized = name.upper().strip()
            country_clean = country.strip().upper()
            stable_key = f"NAME:{normalized}:{country_clean}"
            id_source = "name_country"

        else:
            error_msg = (
                "Insufficient information for Golden ID generation. "
                "Provide at least: registration_number, OR "
                "tax_number, OR (name AND country)"
            )
            logger.error(error_msg)
            raise EntityResolutionError(
                error_msg,
                details={
                    "registration_number": registration_number,
                    "tax_number": tax_number,
                    "name": name,
                    "country": country
                }
            )

        # Generate SHA-256 hash and truncate to 12 characters
        hash_hex = hashlib.sha256(
            stable_key.encode("utf-8")
        ).hexdigest()[:12].upper()

        golden_id = f"GLD-{hash_hex}"

        logger.info(
            f"Generated Golden ID: {golden_id} "
            f"(source: {id_source})"
        )

        return golden_id

    except EntityResolutionError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Golden ID generation failed: {e}")
        raise EntityResolutionError(
            f"Failed to generate Golden ID: {e}",
            details={
                "registration_number": registration_number,
                "tax_number": tax_number,
                "name": name,
                "country": country
            }
        ) from e


def validate_golden_id(golden_id: str) -> bool:
    """
    Validate a Golden ID format.

    Args:
        golden_id: Golden ID to validate

    Returns:
        True if valid format, False otherwise

    Example:
        >>> validate_golden_id("GLD-A1B2C3D4E5F6")
        True
        >>> validate_golden_id("INVALID")
        False
    """
    if not golden_id or not isinstance(golden_id, str):
        return False

    # Format: GLD-XXXXXXXXXXXX (12 hex characters)
    import re
    pattern = r"^GLD-[A-F0-9]{12}$"
    is_valid = bool(re.match(pattern, golden_id.upper()))

    logger.debug(f"Validated Golden ID {golden_id}: {is_valid}")
    return is_valid


def extract_hash_from_golden_id(golden_id: str) -> Optional[str]:
    """
    Extract the hash portion from a Golden ID.

    Args:
        golden_id: Golden ID to extract hash from

    Returns:
        12-character hash or None if invalid

    Example:
        >>> extract_hash_from_golden_id("GLD-A1B2C3D4E5F6")
        'A1B2C3D4E5F6'
    """
    if not validate_golden_id(golden_id):
        return None

    return golden_id.split("-")[1].upper()
