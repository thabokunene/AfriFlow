"""
Authentication Middleware

Validates Bearer JWT tokens and populates the auth context
with the requester's identity, role, and country for
downstream POPIA field masking and access control.

JWT payload structure:
    {
        "sub": "RM-00142",                 # User ID
        "role": "RM",                      # RM / Compliance / ExCo / Service
        "country": "ZA",                   # Requester's home country
        "permissions": ["read:clients",    # Fine-grained permissions
                         "read:signals"],
        "exp": 1735689600,                 # Expiry timestamp
        "iss": "afriflow-auth"             # Issuer
    }

POPIA / GDPR implication:
  - "country" in the JWT determines which records the user can see.
  - Cross-border access requires explicit "cross_border:read" permission.
  - Service accounts (for DAGs, batch jobs) use a separate issuer.

This is a stub implementation — in production, JWT signature
verification uses the HS256 key from the secrets manager.
For portfolio purposes we verify structure only.

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# Roles known to the system
_VALID_ROLES: Set[str] = {"RM", "Compliance", "ExCo", "Service", "FXAdvisor"}

# Permissions available
_KNOWN_PERMISSIONS: Set[str] = {
    "read:clients",
    "read:signals",
    "read:currency_events",
    "write:alerts",
    "read:briefings",
    "cross_border:read",
    "admin:governance",
}


@dataclass
class AuthContext:
    """
    Populated auth context after successful token validation.
    Passed to route handlers for access control decisions.
    """

    user_id: str
    role: str
    country: str
    permissions: List[str]
    is_service_account: bool = False
    token_expiry: int = 0

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def can_access_country(self, target_country: str) -> bool:
        if self.country == target_country:
            return True
        return self.has_permission("cross_border:read")


@dataclass
class AuthError:
    """Authentication failure details."""

    code: str        # MISSING_TOKEN / INVALID_FORMAT / EXPIRED / INVALID_ROLE
    message: str
    http_status: int = 401


class AuthMiddleware:
    """
    JWT authentication middleware.

    In production this is a WSGI/ASGI middleware that validates
    every inbound request. Here it is a callable class that
    extract and validates the auth context from a token string.

    Usage::

        middleware = AuthMiddleware(
            allowed_issuers={"afriflow-auth", "afriflow-service"}
        )
        result = middleware.authenticate("Bearer eyJhbGciOi...")
        if isinstance(result, AuthError):
            return http_error(result.http_status, result.message)
        # result is AuthContext — pass to route handlers
    """

    def __init__(
        self,
        allowed_issuers: Optional[Set[str]] = None,
        clock_skew_seconds: int = 30,
    ):
        self._issuers = allowed_issuers or {"afriflow-auth"}
        self._clock_skew = clock_skew_seconds

    def authenticate(
        self, authorization_header: str
    ) -> "AuthContext | AuthError":
        """
        Parse and validate a Bearer JWT token from the
        Authorization header.

        Returns AuthContext on success, AuthError on failure.
        """
        if not authorization_header:
            return AuthError(
                code="MISSING_TOKEN",
                message="Authorization header is required.",
            )

        if not authorization_header.startswith("Bearer "):
            return AuthError(
                code="INVALID_FORMAT",
                message="Authorization header must start with 'Bearer '.",
            )

        token = authorization_header[7:]

        parts = token.split(".")
        if len(parts) != 3:
            return AuthError(
                code="INVALID_FORMAT",
                message="JWT must have three dot-separated parts.",
            )

        # Decode payload (base64url)
        payload = self._decode_payload(parts[1])
        if payload is None:
            return AuthError(
                code="INVALID_FORMAT",
                message="JWT payload could not be decoded.",
            )

        # Validate issuer
        issuer = payload.get("iss", "")
        if issuer not in self._issuers:
            return AuthError(
                code="INVALID_ISSUER",
                message=f"Issuer '{issuer}' is not trusted.",
            )

        # Validate expiry
        exp = payload.get("exp", 0)
        now = int(time.time())
        if exp < now - self._clock_skew:
            return AuthError(
                code="EXPIRED",
                message="Token has expired.",
            )

        # Validate role
        role = payload.get("role", "")
        if role not in _VALID_ROLES:
            return AuthError(
                code="INVALID_ROLE",
                message=f"Role '{role}' is not recognised.",
                http_status=403,
            )

        user_id = payload.get("sub", "")
        country = payload.get("country", "ZA")
        permissions = payload.get("permissions", [])
        is_service = issuer == "afriflow-service"

        return AuthContext(
            user_id=user_id,
            role=role,
            country=country,
            permissions=permissions,
            is_service_account=is_service,
            token_expiry=exp,
        )

    def require_permission(
        self, auth: AuthContext, permission: str
    ) -> Optional[AuthError]:
        """Return AuthError if permission is missing, else None."""
        if not auth.has_permission(permission):
            return AuthError(
                code="FORBIDDEN",
                message=f"Permission '{permission}' is required.",
                http_status=403,
            )
        return None

    @staticmethod
    def _decode_payload(b64_payload: str) -> Optional[Dict]:
        """Base64url-decode and JSON-parse a JWT payload segment."""
        try:
            # Add padding if needed
            padding = 4 - len(b64_payload) % 4
            if padding < 4:
                b64_payload += "=" * padding
            decoded = base64.urlsafe_b64decode(b64_payload)
            return json.loads(decoded.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def build_service_token_payload(
        service_name: str,
        country: str = "ZA",
        permissions: Optional[List[str]] = None,
        ttl_seconds: int = 3600,
    ) -> Dict:
        """
        Build a service account JWT payload for batch jobs.
        In production this would be signed with the HMAC key.
        """
        return {
            "sub": f"svc:{service_name}",
            "role": "Service",
            "country": country,
            "permissions": permissions or list(_KNOWN_PERMISSIONS),
            "exp": int(time.time()) + ttl_seconds,
            "iss": "afriflow-service",
        }
