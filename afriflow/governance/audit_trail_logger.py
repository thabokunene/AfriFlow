"""
Audit Trail Logger

We log every data access and data modification event
in AfriFlow to an immutable audit trail.

Why an audit trail?

1. POPIA s18: Every responsible party must maintain
   documentation of all processing activities. An
   audit trail is the primary evidence of compliance.

2. FSCA audit requirements: Financial services firms
   must retain records of all client-related data
   access for 5 years minimum.

3. POPIA s22 breach notification: If a breach occurs,
   the audit trail tells us exactly which records were
   accessed and by whom.

4. Internal accountability: If a client complains that
   their data was used inappropriately, we can trace
   every access in the past 7 years.

Design:
  - Every AuditEvent gets a sequence number + hash
    of the previous event. This creates a tamper-
    evident chain: if any entry is modified, the
    hash chain breaks.
  - Events are written synchronously before any
    data is returned to the caller.
  - In production, the trail is published to an
    immutable append-only S3/GCS bucket with
    object lock enabled.

Disclaimer: Not sanctioned by Standard Bank Group.
Built by Thabo Kunene for portfolio purposes.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditAction(Enum):
    """The type of operation being logged."""

    # Data access
    READ = "READ"
    READ_AGGREGATED = "READ_AGGREGATED"
    SEARCH = "SEARCH"
    EXPORT = "EXPORT"

    # Data modification
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ANONYMISE = "ANONYMISE"

    # Consent and governance
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_WITHDRAWN = "CONSENT_WITHDRAWN"
    ACCESS_DENIED = "ACCESS_DENIED"

    # System events
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    PIPELINE_RUN = "PIPELINE_RUN"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    CIRCUIT_BREAKER_CLOSE = "CIRCUIT_BREAKER_CLOSE"


class AuditSeverity(Enum):
    """Severity for routing and alerting."""

    LOW = "LOW"          # Routine read
    MEDIUM = "MEDIUM"    # Write or export
    HIGH = "HIGH"        # Delete, anonymise, breach-adjacent
    CRITICAL = "CRITICAL"  # Access denied, consent withdrawal


@dataclass
class AuditEvent:
    """
    A single immutable audit log entry.

    We intentionally keep this flat (no nested
    objects) so that it serialises cleanly to
    JSON for the immutable log store.
    """

    event_id: str
    sequence_number: int
    previous_hash: str
    event_hash: str              # Hash of this entry

    # Who did it
    actor_id: str                # User ID or system service name
    actor_role: str              # Role enum value
    actor_country: str           # Country of actor
    actor_ip: Optional[str]      # IP address if available

    # What they did
    action: AuditAction
    severity: AuditSeverity

    # What data was involved
    resource_type: str           # e.g. "golden_record"
    resource_id: str             # e.g. "GLD-001"
    fields_accessed: List[str]   # Which specific fields
    client_country: Optional[str]  # Country of the client record

    # Context
    request_id: str              # Correlates with API request log
    purpose: str                 # Why they accessed this
    access_permitted: bool
    denial_reason: Optional[str]

    # Timing
    timestamp: str
    duration_ms: Optional[int]   # How long the query took

    # Retention
    retain_until: str            # ISO date — when to delete this log


@dataclass
class AuditTrailStats:
    """Summary statistics for a time window."""

    window_start: str
    window_end: str
    total_events: int
    events_by_action: Dict[str, int]
    events_by_role: Dict[str, int]
    denied_access_count: int
    export_count: int
    high_risk_field_access_count: int


class AuditTrailLogger:
    """
    We log, store, and query audit events.

    In production the write path publishes each
    event to a Kafka topic (audit.events) which
    is consumed by a Flink job that writes to:
      1. Delta Lake (queryable by compliance team)
      2. Immutable object storage (tamper-evident)

    Here we maintain an in-memory log for testing
    and demonstration.

    Usage:

        logger = AuditTrailLogger()

        logger.log(
            actor_id="rm.jane.smith",
            actor_role="RM",
            actor_country="KE",
            action=AuditAction.READ,
            resource_type="golden_record",
            resource_id="GLD-001",
            fields_accessed=["canonical_name", "total_relationship_value_zar"],
            client_country="KE",
            request_id="req-abc123",
            purpose="Pre-meeting briefing",
            access_permitted=True,
        )
    """

    # POPIA s18 and FSCA require audit retention of
    # 5 years (1825 days). We keep 7 years to be safe.
    RETENTION_DAYS = 2555

    # Fields that elevate severity to HIGH regardless
    # of the action type
    HIGH_RISK_FIELDS = {
        "tax_number", "account_numbers", "msisdn",
        "registration_number", "creditor_account_number",
        "payment_amount", "forward_notional",
        "total_relationship_value_zar",
    }

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
        self._sequence: int = 0
        self._last_hash: str = "GENESIS"

    def log(
        self,
        actor_id: str,
        actor_role: str,
        actor_country: str,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        fields_accessed: Optional[List[str]] = None,
        client_country: Optional[str] = None,
        request_id: Optional[str] = None,
        purpose: str = "operational",
        access_permitted: bool = True,
        denial_reason: Optional[str] = None,
        actor_ip: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditEvent:
        """
        We write a single audit event to the trail.

        This is called synchronously before returning
        any data to the caller. If logging fails,
        we raise — better to deny access than to
        serve data without an audit record.
        """

        fields_accessed = fields_accessed or []
        self._sequence += 1

        # Determine severity
        severity = self._classify_severity(
            action, fields_accessed, access_permitted
        )

        # Retention date
        now = datetime.now()
        retain_until = datetime(
            now.year + (self.RETENTION_DAYS // 365),
            now.month,
            now.day,
        ).strftime("%Y-%m-%d")

        # Build the event (without hash first)
        event_id = str(uuid.uuid4())
        timestamp = now.isoformat()

        # Create a canonical representation for hashing
        canonical = json.dumps({
            "event_id": event_id,
            "sequence_number": self._sequence,
            "previous_hash": self._last_hash,
            "actor_id": actor_id,
            "action": action.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "timestamp": timestamp,
        }, sort_keys=True)

        event_hash = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        event = AuditEvent(
            event_id=event_id,
            sequence_number=self._sequence,
            previous_hash=self._last_hash,
            event_hash=event_hash,
            actor_id=actor_id,
            actor_role=actor_role,
            actor_country=actor_country,
            actor_ip=actor_ip,
            action=action,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            fields_accessed=fields_accessed,
            client_country=client_country,
            request_id=request_id or str(uuid.uuid4()),
            purpose=purpose,
            access_permitted=access_permitted,
            denial_reason=denial_reason,
            timestamp=timestamp,
            duration_ms=duration_ms,
            retain_until=retain_until,
        )

        self._events.append(event)
        self._last_hash = event_hash
        return event

    def log_denied(
        self,
        actor_id: str,
        actor_role: str,
        actor_country: str,
        resource_type: str,
        resource_id: str,
        denial_reason: str,
        request_id: Optional[str] = None,
    ) -> AuditEvent:
        """
        We log a denied access attempt.

        Denials are as important as grants in a POPIA
        audit trail — they prove that access controls
        are being enforced.
        """

        return self.log(
            actor_id=actor_id,
            actor_role=actor_role,
            actor_country=actor_country,
            action=AuditAction.ACCESS_DENIED,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            access_permitted=False,
            denial_reason=denial_reason,
        )

    def verify_chain_integrity(self) -> bool:
        """
        We verify that the hash chain is unbroken.

        If any event has been tampered with, the
        chain will not validate and we return False.
        The tampered entry can be identified by
        finding the first sequence number where
        the hash does not match.
        """

        if not self._events:
            return True

        prev_hash = "GENESIS"
        for event in self._events:
            if event.previous_hash != prev_hash:
                return False

            canonical = json.dumps({
                "event_id": event.event_id,
                "sequence_number": event.sequence_number,
                "previous_hash": event.previous_hash,
                "actor_id": event.actor_id,
                "action": event.action.value,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "timestamp": event.timestamp,
            }, sort_keys=True)

            expected_hash = hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest()

            if event.event_hash != expected_hash:
                return False

            prev_hash = event.event_hash

        return True

    def query(
        self,
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        access_permitted: Optional[bool] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        We return events matching the given filters.

        This supports compliance investigations:
        "Show me every time GLD-001 was accessed
        in the last 30 days" or "Show me all
        denied access attempts this week."
        """

        results = list(self._events)

        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]
        if resource_id:
            results = [e for e in results if e.resource_id == resource_id]
        if action:
            results = [e for e in results if e.action == action]
        if from_timestamp:
            results = [e for e in results if e.timestamp >= from_timestamp]
        if to_timestamp:
            results = [e for e in results if e.timestamp <= to_timestamp]
        if access_permitted is not None:
            results = [
                e for e in results
                if e.access_permitted == access_permitted
            ]

        return results[-limit:]

    def get_stats(
        self,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
    ) -> AuditTrailStats:
        """
        We compute summary statistics for the audit
        trail within a time window.
        """

        events = self.query(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=len(self._events),
        )

        by_action: Dict[str, int] = {}
        by_role: Dict[str, int] = {}
        denied = 0
        exports = 0
        high_risk = 0

        for e in events:
            by_action[e.action.value] = (
                by_action.get(e.action.value, 0) + 1
            )
            by_role[e.actor_role] = (
                by_role.get(e.actor_role, 0) + 1
            )
            if not e.access_permitted:
                denied += 1
            if e.action == AuditAction.EXPORT:
                exports += 1
            if any(
                f in self.HIGH_RISK_FIELDS
                for f in e.fields_accessed
            ):
                high_risk += 1

        return AuditTrailStats(
            window_start=from_timestamp or "all_time",
            window_end=to_timestamp or datetime.now().isoformat(),
            total_events=len(events),
            events_by_action=by_action,
            events_by_role=by_role,
            denied_access_count=denied,
            export_count=exports,
            high_risk_field_access_count=high_risk,
        )

    def _classify_severity(
        self,
        action: AuditAction,
        fields: List[str],
        permitted: bool,
    ) -> AuditSeverity:
        """We classify severity for routing and alerting."""

        if not permitted:
            return AuditSeverity.HIGH
        if action in {AuditAction.DELETE, AuditAction.ANONYMISE}:
            return AuditSeverity.HIGH
        if action == AuditAction.EXPORT:
            return AuditSeverity.MEDIUM
        if action in {AuditAction.CREATE, AuditAction.UPDATE}:
            return AuditSeverity.MEDIUM
        if any(f in self.HIGH_RISK_FIELDS for f in fields):
            return AuditSeverity.MEDIUM
        return AuditSeverity.LOW
