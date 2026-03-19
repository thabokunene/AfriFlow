"""
@file golden_id_generator.py
@description Golden ID generator for the AfriFlow entity resolution layer,
    producing deterministic, collision-resistant identifiers for resolved
    client entities using stable government-issued identifiers or name fallbacks.
@author Thabo Kunene
@created 2026-03-19
"""

import hashlib                    # SHA-256 hashing for deterministic ID generation
from typing import Optional        # type hint for optional string parameters
import logging                    # standard library logger (supplemented by AfriFlow logger)

# AfriFlow internal imports
from afriflow.exceptions import EntityResolutionError  # raised when inputs are insufficient
from afriflow.logging_config import get_logger          # structured logging

# Module-level logger
logger = get_logger("entity_resolution.golden_id")


def generate_golden_id(
    registration_number: Optional[str] = None,
    tax_number: Optional[str] = None,
    name: Optional[str] = None,
    country: Optional[str] = None,
) -> str:
    """
    Generate a deterministic Golden ID using the most stable identifier available.

    Priority order:
      1. Registration number (most stable — government-issued, globally unique per registry)
      2. Tax number (stable — government-issued, unique per tax authority)
      3. Normalised name + country (fallback — less stable, avoid if possible)

    The ID is a truncated SHA-256 hash prefixed with 'GLD-' for easy identification
    in logs, queries, and audit trails.

    :param registration_number: Company registration number (e.g. "1979/003231/06" for SA).
    :param tax_number: Tax identification number (e.g. "4250089747").
    :param name: Company name — used only if no reg/tax number is available.
    :param country: ISO 3166-1 alpha-2 country code — required when using name fallback.
    :return: Golden ID string in format 'GLD-XXXXXXXXXXXX' (12 uppercase hex digits).
    :raises EntityResolutionError: If insufficient information is provided or input types
                                   are invalid.

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
        # ── Priority 1: Registration number ──────────────────────────────────
        # Most reliable: government-issued, unique within national registry
        if registration_number:
            if not isinstance(registration_number, str):
                raise EntityResolutionError(
                    "registration_number must be a string",
                    details={"type": type(registration_number).__name__}
                )
            stable_key = f"REG:{registration_number.strip()}"  # strip whitespace before hashing
            id_source = "registration_number"

        # ── Priority 2: Tax number ────────────────────────────────────────────
        # Second most reliable: government-issued, unique per tax authority
        elif tax_number:
            if not isinstance(tax_number, str):
                raise EntityResolutionError(
                    "tax_number must be a string",
                    details={"type": type(tax_number).__name__}
                )
            stable_key = f"TAX:{tax_number.strip()}"
            id_source = "tax_number"

        # ── Priority 3: Name + country fallback ──────────────────────────────
        # Least reliable: name-based IDs can change when names are corrected.
        # Only used when no government-issued identifier is available.
        elif name and country:
            if not isinstance(name, str) or not isinstance(country, str):
                raise EntityResolutionError(
                    "name and country must be strings",
                    details={
                        "name_type": type(name).__name__,
                        "country_type": type(country).__name__
                    }
                )
            # Normalise: uppercase + strip to maximise hash stability
            normalized = name.upper().strip()
            country_clean = country.strip().upper()
            stable_key = f"NAME:{normalized}:{country_clean}"
            id_source = "name_country"

        else:
            # No usable identifier provided — raise immediately rather than returning
            # a garbage ID that would pollute the golden record store
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

        # Hash the stable key using SHA-256 and truncate to 12 hex characters.
        # 12 hex chars = 48 bits → ~281 trillion unique values, collision probability
        # negligible for expected entity volumes.
        hash_hex = hashlib.sha256(
            stable_key.encode("utf-8")
        ).hexdigest()[:12].upper()

        golden_id = f"GLD-{hash_hex}"  # final ID in format GLD-XXXXXXXXXXXX

        logger.info(
            f"Generated Golden ID: {golden_id} "
            f"(source: {id_source})"
        )

        return golden_id

    except EntityResolutionError:
        # Re-raise our typed exceptions unchanged
        raise
    except Exception as e:
        # Wrap unexpected errors in EntityResolutionError for consistent error handling
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
    Validate that a string conforms to the Golden ID format.

    Expected format: GLD-XXXXXXXXXXXX (prefix 'GLD-' followed by exactly 12
    uppercase hexadecimal characters).

    :param golden_id: Golden ID string to validate.
    :return: True if the string matches the expected format, False otherwise.

    Example:
        >>> validate_golden_id("GLD-A1B2C3D4E5F6")
        True
        >>> validate_golden_id("INVALID")
        False
    """
    if not golden_id or not isinstance(golden_id, str):
        return False

    # Compile and apply the format regex at call time (simple enough to not pre-compile)
    import re
    pattern = r"^GLD-[A-F0-9]{12}$"   # 'GLD-' prefix + exactly 12 hex chars
    is_valid = bool(re.match(pattern, golden_id.upper()))

    logger.debug(f"Validated Golden ID {golden_id}: {is_valid}")
    return is_valid


def extract_hash_from_golden_id(golden_id: str) -> Optional[str]:
    """
    Extract the hash portion (12 hex characters) from a Golden ID.

    :param golden_id: Golden ID string to extract hash from.
    :return: 12-character uppercase hex string, or None if the input is invalid.

    Example:
        >>> extract_hash_from_golden_id("GLD-A1B2C3D4E5F6")
        'A1B2C3D4E5F6'
    """
    # Validate before extracting to avoid IndexError on malformed input
    if not validate_golden_id(golden_id):
        return None

    # The hash portion is always after the first '-' delimiter
    return golden_id.split("-")[1].upper()
