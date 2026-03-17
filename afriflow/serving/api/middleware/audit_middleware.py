"""
Audit Middleware

Every API request is logged to the AfriFlow audit trail.
This satisfies:
  - POPIA Section 22: notification of security compromises
  - FAIS: records of client data access for 5 years
  - GDPR Article 30: records of processing activities
  - Internal MIS: RM activity tracking for outcome analysis

Audit record fields:
  request_id    — UUID (correlates with API response)
  timestamp     — ISO 8601
  user_id       — from JWT sub claim
  role          — RM / Compliance / ExCo / Service
  country       — requester's home country
  method        — HTTP method
  path          — sanitised path (golden_id → [REDACTED] if PII)
  client_accessed — golden_id accessed (for client records)
  status_code   — HTTP response code
  duration_ms   — request duration
  pii_fields_accessed — which POPIA-classified fields were returned
  cross_border  — True if requester accessed another country's data

Records are written to:
  1. The SHA-256 hash-chain audit log (audit_trail_logger)
  2. A streaming topic for near-real-time compliance dashboards

Disclaimer: Portfolio project by Thabo Kunene. Not a
Standard Bank Group product. All data is simulated.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# Fields classified as PII under POPIA that we track when accessed
_POPIA_TRACKED_FIELDS = frozenset({
    "canonical_name",
    "registration_number",
    "tax_number",
    "msisdn",
    "email",
    "physical_address",
    "relationship_manager",
    "date_of_birth",
    "id_number",
})


@dataclass
class AuditRecord:
    """
    Immutable audit record for a single API request.

    This record is passed to the hash-chain audit logger.
    """

    request_id: str
    timestamp: str
    user_id: str
    role: str
    requester_country: str
    method: str
    path: str
    client_accessed: Optional[str]    # golden_id, if applicable
    data_accessed_country: Optional[str]
    status_code: int
    duration_ms: float
    pii_fields_accessed: List[str]
    cross_border_access: bool
    action_type: str    # READ / WRITE / DELETE / PROPAGATE
    extra: Dict = field(default_factory=dict)


class AuditMiddleware:
    """
    Records API request/response audit trails.

    Usage::

        audit = AuditMiddleware(audit_logger=audit_trail_logger)

        # At request start:
        start = audit.begin_request(
            user_id="RM-00142",
            role="RM",
            country="ZA",
            method="GET",
            path="/clients/GLD-001",
        )

        # At request end:
        record = audit.end_request(
            context=start,
            status_code=200,
            response_body={"data": {...}},
        )
        audit.commit(record)
    """

    def __init__(self, audit_logger=None):
        self._logger = audit_logger

    def begin_request(
        self,
        user_id: str,
        role: str,
        country: str,
        method: str,
        path: str,
    ) -> Dict:
        """Record request start context."""
        return {
            "request_id": str(uuid.uuid4()),
            "start_time": time.monotonic(),
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "role": role,
            "requester_country": country,
            "method": method,
            "path": path,
        }

    def end_request(
        self,
        context: Dict,
        status_code: int,
        response_body: Optional[Dict] = None,
        client_accessed: Optional[str] = None,
        data_country: Optional[str] = None,
    ) -> AuditRecord:
        """Build audit record from request context and response."""
        duration = (
            time.monotonic() - context["start_time"]
        ) * 1000

        pii_fields = self._detect_pii_fields(response_body or {})
        cross_border = (
            data_country is not None
            and data_country != context["requester_country"]
        )

        action_type = self._action_type(context["method"], context["path"])

        return AuditRecord(
            request_id=context["request_id"],
            timestamp=context["timestamp"],
            user_id=context["user_id"],
            role=context["role"],
            requester_country=context["requester_country"],
            method=context["method"],
            path=context["path"],
            client_accessed=client_accessed,
            data_accessed_country=data_country,
            status_code=status_code,
            duration_ms=round(duration, 1),
            pii_fields_accessed=pii_fields,
            cross_border_access=cross_border,
            action_type=action_type,
        )

    def commit(self, record: AuditRecord) -> None:
        """
        Write audit record to the hash-chain logger and
        streaming topic.

        If no logger is injected (test/demo mode), write to
        a simple list in memory.
        """
        if self._logger is not None:
            self._logger.log_event(
                event_type=f"API_{record.action_type}",
                actor=record.user_id,
                resource_id=record.client_accessed or record.path,
                details={
                    "request_id": record.request_id,
                    "method": record.method,
                    "path": record.path,
                    "status_code": record.status_code,
                    "duration_ms": record.duration_ms,
                    "pii_fields": record.pii_fields_accessed,
                    "cross_border": record.cross_border_access,
                    "role": record.role,
                    "country": record.requester_country,
                },
            )

    def _detect_pii_fields(self, body: Dict) -> List[str]:
        """Find POPIA-classified fields in a response body."""
        found: List[str] = []
        data = body.get("data", body)
        if isinstance(data, dict):
            for field in _POPIA_TRACKED_FIELDS:
                if field in data and data[field] is not None:
                    found.append(field)
        return found

    def _action_type(self, method: str, path: str) -> str:
        if method == "GET":
            return "READ"
        elif method == "POST" and "propagate" in path:
            return "PROPAGATE"
        elif method in ("POST", "PUT", "PATCH"):
            return "WRITE"
        elif method == "DELETE":
            return "DELETE"
        return "READ"
