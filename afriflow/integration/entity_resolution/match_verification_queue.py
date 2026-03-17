"""
integration/entity_resolution/match_verification_queue.py

Human-in-the-loop verification queue for uncertain entity matches.

We route match candidates that fall below the HIGH_CONFIDENCE threshold
to a structured review queue where domain experts adjudicate.  Reviewer
decisions feed a feedback loop that tracks per-reviewer accuracy and
informs threshold calibration over time.

Key design principles:
  - AUTO_ACCEPT at or above HIGH_CONFIDENCE_THRESHOLD (0.92).
  - AUTO_REJECT below REVIEW_THRESHOLD (0.70).
  - All scores in [0.70, 0.92) enter the queue with priority based on
    proximity to the high-confidence boundary.
  - Queue is in-memory for the portfolio demo; a production implementation
    would persist to a Delta table or relational store.

DISCLAIMER: This project is not a sanctioned initiative of Standard Bank
Group, MTN, or any affiliated entity. It is a demonstration of concept,
domain knowledge, and data engineering skill by Thabo Kunene.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from afriflow.exceptions import ConfigurationError
from afriflow.logging_config import get_logger, log_operation

logger = get_logger("entity_resolution.match_verification_queue")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationStatus(Enum):
    """Lifecycle status of a match candidate in the queue."""
    PENDING          = "pending"
    IN_REVIEW        = "in_review"
    CONFIRMED_MATCH  = "confirmed_match"
    CONFIRMED_NON_MATCH = "confirmed_non_match"
    ESCALATED        = "escalated"
    AUTO_ACCEPTED    = "auto_accepted"
    AUTO_REJECTED    = "auto_rejected"


class Priority(Enum):
    """Queue priority for reviewer assignment and ordering."""
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class MatchCandidate:
    """
    We represent a single pair of entity candidates awaiting (or having
    received) human verification.

    Attributes:
        candidate_id:       UUID for this review item.
        source_entity_id:   First entity in the candidate pair.
        target_entity_id:   Second entity in the candidate pair.
        match_score:        Algorithm confidence score in [0, 1].
        matching_fields:    Field names that agree across both records.
        conflicting_fields: Field names where values disagree.
        status:             Current VerificationStatus.
        priority:           Queue priority (high / medium / low).
        assigned_reviewer:  Reviewer ID if assigned, else None.
        submitted_at:       When the candidate was submitted to the queue.
        reviewed_at:        When a final decision was made, else None.
        reviewer_notes:     Free-text notes from the reviewing analyst.
        auto_decision:      True if the decision was made automatically.
    """

    candidate_id: str
    source_entity_id: str
    target_entity_id: str
    match_score: float
    matching_fields: List[str] = field(default_factory=list)
    conflicting_fields: List[str] = field(default_factory=list)
    status: VerificationStatus = VerificationStatus.PENDING
    priority: str = Priority.MEDIUM.value
    assigned_reviewer: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None
    auto_decision: bool = False


# ---------------------------------------------------------------------------
# Queue class
# ---------------------------------------------------------------------------

class MatchVerificationQueue:
    """
    We manage the lifecycle of uncertain entity-match candidates through
    submission, assignment, review, and statistical reporting.

    Thresholds::

        AUTO_ACCEPT  ≥ HIGH_CONFIDENCE_THRESHOLD (0.92) → CONFIRMED_MATCH
        REVIEW_THRESHOLD ≤ score < HIGH_CONFIDENCE_THRESHOLD → queued
        score < REVIEW_THRESHOLD                         → AUTO_REJECTED

    Usage::

        queue = MatchVerificationQueue()
        candidate = queue.submit("GLD-001", "GLD-002", 0.83, ["name"], ["country"])
        queue.assign_reviewer(candidate.candidate_id, "analyst_01")
        queue.submit_decision(candidate.candidate_id, "confirmed_match",
                              "analyst_01", notes="Same entity, different branches")
    """

    HIGH_CONFIDENCE_THRESHOLD: float = 0.92
    REVIEW_THRESHOLD: float = 0.70

    def __init__(self) -> None:
        """Initialise the queue with empty stores."""
        # candidate_id → MatchCandidate
        self._candidates: Dict[str, MatchCandidate] = {}
        # reviewer_id → list of decision dicts (for accuracy tracking)
        self._reviewer_decisions: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("MatchVerificationQueue initialised")

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit(
        self,
        source_id: str,
        target_id: str,
        score: float,
        matching_fields: Optional[List[str]] = None,
        conflicting_fields: Optional[List[str]] = None,
    ) -> MatchCandidate:
        """
        We submit a candidate match pair to the queue for review.

        If score ≥ HIGH_CONFIDENCE_THRESHOLD the candidate is immediately
        auto-accepted.  If score < REVIEW_THRESHOLD it is auto-rejected.
        Otherwise it enters the human review queue with a priority derived
        from the score band.

        Args:
            source_id:         First entity in the pair.
            target_id:         Second entity in the pair.
            score:             Algorithm match score in [0, 1].
            matching_fields:   Field names that agree.
            conflicting_fields: Field names that conflict.

        Returns:
            MatchCandidate with initial status set.

        Raises:
            ConfigurationError: If score is outside [0, 1].
        """
        if not (0.0 <= score <= 1.0):
            raise ConfigurationError(
                f"Match score must be in [0, 1], got {score}",
                details={"score": score},
            )

        candidate_id = str(uuid.uuid4())
        priority = self._compute_priority(score)

        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            status = VerificationStatus.AUTO_ACCEPTED
            auto = True
        elif score < self.REVIEW_THRESHOLD:
            status = VerificationStatus.AUTO_REJECTED
            auto = True
        else:
            status = VerificationStatus.PENDING
            auto = False

        candidate = MatchCandidate(
            candidate_id=candidate_id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            match_score=score,
            matching_fields=matching_fields or [],
            conflicting_fields=conflicting_fields or [],
            status=status,
            priority=priority,
            auto_decision=auto,
            reviewed_at=datetime.utcnow() if auto else None,
        )
        self._candidates[candidate_id] = candidate

        log_operation(
            logger, "submit", "completed",
            candidate_id=candidate_id,
            score=score,
            status=status.value,
            auto=auto,
        )
        return candidate

    # ------------------------------------------------------------------
    # Reviewer assignment
    # ------------------------------------------------------------------

    def assign_reviewer(
        self,
        candidate_id: str,
        reviewer_id: str,
    ) -> MatchCandidate:
        """
        We assign a reviewer to a PENDING candidate, moving it to IN_REVIEW.

        Args:
            candidate_id: Target candidate.
            reviewer_id:  Reviewer identifier (user ID / email).

        Returns:
            Updated MatchCandidate.

        Raises:
            ConfigurationError: If candidate not found, is auto-decided, or
                                 is already assigned.
        """
        candidate = self._get_candidate(candidate_id)

        if candidate.auto_decision:
            raise ConfigurationError(
                f"Candidate '{candidate_id}' was auto-decided and does not "
                "require manual review.",
                details={"status": candidate.status.value},
            )
        if candidate.status == VerificationStatus.IN_REVIEW:
            raise ConfigurationError(
                f"Candidate '{candidate_id}' is already assigned to "
                f"'{candidate.assigned_reviewer}'.",
                details={"assigned_reviewer": candidate.assigned_reviewer},
            )
        if candidate.status not in (
            VerificationStatus.PENDING, VerificationStatus.ESCALATED
        ):
            raise ConfigurationError(
                f"Candidate '{candidate_id}' cannot be assigned in "
                f"status '{candidate.status.value}'.",
                details={"status": candidate.status.value},
            )

        candidate.assigned_reviewer = reviewer_id
        candidate.status = VerificationStatus.IN_REVIEW
        self._reviewer_decisions.setdefault(reviewer_id, [])
        logger.info(f"Assigned {candidate_id} to reviewer {reviewer_id}")
        return candidate

    # ------------------------------------------------------------------
    # Decision submission
    # ------------------------------------------------------------------

    def submit_decision(
        self,
        candidate_id: str,
        decision: str,
        reviewer_id: str,
        notes: Optional[str] = None,
    ) -> MatchCandidate:
        """
        We record a reviewer's decision on a match candidate.

        Args:
            candidate_id: Candidate being decided.
            decision:     One of "confirmed_match", "confirmed_non_match",
                          "escalated".
            reviewer_id:  Reviewer submitting the decision.
            notes:        Optional free-text justification.

        Returns:
            Updated MatchCandidate.

        Raises:
            ConfigurationError: If candidate not found, reviewer mismatch,
                                 or decision value is invalid.
        """
        valid_decisions = {
            VerificationStatus.CONFIRMED_MATCH.value,
            VerificationStatus.CONFIRMED_NON_MATCH.value,
            VerificationStatus.ESCALATED.value,
        }
        if decision not in valid_decisions:
            raise ConfigurationError(
                f"decision must be one of {sorted(valid_decisions)}",
                details={"received": decision},
            )

        candidate = self._get_candidate(candidate_id)

        if candidate.assigned_reviewer != reviewer_id:
            raise ConfigurationError(
                f"Reviewer '{reviewer_id}' is not assigned to candidate "
                f"'{candidate_id}'. Assigned: '{candidate.assigned_reviewer}'.",
                details={
                    "assigned": candidate.assigned_reviewer,
                    "submitting": reviewer_id,
                },
            )
        if candidate.status not in (
            VerificationStatus.IN_REVIEW, VerificationStatus.ESCALATED
        ):
            raise ConfigurationError(
                f"Cannot submit decision for candidate in status "
                f"'{candidate.status.value}'.",
                details={"status": candidate.status.value},
            )

        candidate.status = VerificationStatus(decision)
        candidate.reviewed_at = datetime.utcnow()
        candidate.reviewer_notes = notes

        # Record for accuracy tracking
        self._reviewer_decisions.setdefault(reviewer_id, []).append({
            "candidate_id": candidate_id,
            "decision": decision,
            "match_score": candidate.match_score,
            "reviewed_at": candidate.reviewed_at.isoformat(),
        })

        log_operation(
            logger, "submit_decision", "completed",
            candidate_id=candidate_id,
            reviewer_id=reviewer_id,
            decision=decision,
        )
        return candidate

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_pending(
        self,
        reviewer_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
    ) -> List[MatchCandidate]:
        """
        We retrieve pending (unresolved) candidates from the queue.

        Args:
            reviewer_id: If supplied, return only candidates assigned to this
                         reviewer (or unassigned).
            priority:    Filter by priority ("high", "medium", "low").
            limit:       Maximum number of results to return.

        Returns:
            List of MatchCandidate ordered by priority then submission time.
        """
        active_statuses = {
            VerificationStatus.PENDING,
            VerificationStatus.IN_REVIEW,
            VerificationStatus.ESCALATED,
        }
        priority_order = {
            Priority.HIGH.value: 0,
            Priority.MEDIUM.value: 1,
            Priority.LOW.value: 2,
        }

        results = []
        for candidate in self._candidates.values():
            if candidate.status not in active_statuses:
                continue
            if priority is not None and candidate.priority != priority:
                continue
            if reviewer_id is not None:
                if (candidate.assigned_reviewer is not None
                        and candidate.assigned_reviewer != reviewer_id):
                    continue
            results.append(candidate)

        results.sort(
            key=lambda c: (
                priority_order.get(c.priority, 9),
                c.submitted_at,
            )
        )
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """
        We return queue-wide statistics for dashboards and SLA monitoring.

        Returns:
            Dictionary with counts by status, priority, auto-decision rate,
            average match scores, and per-reviewer workload.
        """
        total = len(self._candidates)
        by_status: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        auto_accepted = 0
        auto_rejected = 0
        score_sum = 0.0
        pending_scores: List[float] = []

        for c in self._candidates.values():
            by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
            by_priority[c.priority] = by_priority.get(c.priority, 0) + 1
            score_sum += c.match_score
            if c.status == VerificationStatus.AUTO_ACCEPTED:
                auto_accepted += 1
            elif c.status == VerificationStatus.AUTO_REJECTED:
                auto_rejected += 1
            if c.status in (
                VerificationStatus.PENDING,
                VerificationStatus.IN_REVIEW,
                VerificationStatus.ESCALATED,
            ):
                pending_scores.append(c.match_score)

        reviewer_workload: Dict[str, int] = {}
        for c in self._candidates.values():
            if c.assigned_reviewer:
                reviewer_workload[c.assigned_reviewer] = (
                    reviewer_workload.get(c.assigned_reviewer, 0) + 1
                )

        return {
            "total_candidates": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "auto_accepted": auto_accepted,
            "auto_rejected": auto_rejected,
            "pending_review": len(pending_scores),
            "average_match_score": round(score_sum / total, 4) if total else 0.0,
            "average_pending_score": (
                round(sum(pending_scores) / len(pending_scores), 4)
                if pending_scores else 0.0
            ),
            "reviewer_workload": reviewer_workload,
            "thresholds": {
                "high_confidence": self.HIGH_CONFIDENCE_THRESHOLD,
                "review": self.REVIEW_THRESHOLD,
            },
        }

    def get_reviewer_accuracy(self, reviewer_id: str) -> Dict[str, float]:
        """
        We compute accuracy metrics for a reviewer based on their decision
        history.

        Accuracy here is defined relative to auto-accept/reject signals:
        decisions that agree with the algorithm (high-score → confirmed_match,
        low-score → confirmed_non_match) are counted as "consistent".

        Args:
            reviewer_id: Reviewer to evaluate.

        Returns:
            Dictionary with total_decisions, match_rate, non_match_rate,
            escalation_rate, and consistency_rate.

        Raises:
            ConfigurationError: If reviewer_id has no decisions on record.
        """
        decisions = self._reviewer_decisions.get(reviewer_id, [])
        if not decisions:
            raise ConfigurationError(
                f"No decisions found for reviewer '{reviewer_id}'.",
                details={"reviewer_id": reviewer_id},
            )

        total = len(decisions)
        match_count = sum(
            1 for d in decisions
            if d["decision"] == VerificationStatus.CONFIRMED_MATCH.value
        )
        non_match_count = sum(
            1 for d in decisions
            if d["decision"] == VerificationStatus.CONFIRMED_NON_MATCH.value
        )
        escalated_count = sum(
            1 for d in decisions
            if d["decision"] == VerificationStatus.ESCALATED.value
        )

        # Consistency: high-score matches → confirmed_match expected;
        # low-score matches → confirmed_non_match expected
        high_score_threshold = (self.HIGH_CONFIDENCE_THRESHOLD + self.REVIEW_THRESHOLD) / 2
        consistent = 0
        for d in decisions:
            if (d["match_score"] >= high_score_threshold
                    and d["decision"] == VerificationStatus.CONFIRMED_MATCH.value):
                consistent += 1
            elif (d["match_score"] < high_score_threshold
                    and d["decision"] == VerificationStatus.CONFIRMED_NON_MATCH.value):
                consistent += 1

        return {
            "total_decisions": total,
            "match_rate": round(match_count / total, 4),
            "non_match_rate": round(non_match_count / total, 4),
            "escalation_rate": round(escalated_count / total, 4),
            "consistency_rate": round(consistent / total, 4) if total else 0.0,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_candidate(self, candidate_id: str) -> MatchCandidate:
        """We retrieve a candidate by ID, raising ConfigurationError if absent."""
        if candidate_id not in self._candidates:
            raise ConfigurationError(
                f"Candidate '{candidate_id}' not found in queue.",
                details={"candidate_id": candidate_id},
            )
        return self._candidates[candidate_id]

    def _compute_priority(self, score: float) -> str:
        """We assign queue priority based on how close score is to the boundary."""
        mid = (self.HIGH_CONFIDENCE_THRESHOLD + self.REVIEW_THRESHOLD) / 2
        if score >= mid:
            return Priority.HIGH.value
        elif score >= self.REVIEW_THRESHOLD:
            return Priority.MEDIUM.value
        return Priority.LOW.value


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    queue = MatchVerificationQueue()

    # Submit a mix of candidates
    test_cases = [
        ("GLD-001", "GLD-002", 0.95, ["name", "reg_no"], []),           # auto-accept
        ("GLD-003", "GLD-004", 0.60, ["name"], ["country", "address"]), # auto-reject
        ("GLD-005", "GLD-006", 0.85, ["name", "country"], ["address"]), # high priority
        ("GLD-007", "GLD-008", 0.74, ["name"], ["address", "phone"]),   # medium priority
        ("GLD-009", "GLD-010", 0.91, ["name", "tax_no"], ["phone"]),    # high priority
    ]

    print("=== Submissions ===")
    candidates = []
    for src, tgt, score, matching, conflicting in test_cases:
        c = queue.submit(src, tgt, score, matching, conflicting)
        print(
            f"  {c.candidate_id[:8]}... "
            f"score={score:.2f}  status={c.status.value:<22}  priority={c.priority}"
        )
        candidates.append(c)

    print("\n=== Pending queue (no filter) ===")
    pending = queue.get_pending()
    for c in pending:
        print(
            f"  {c.candidate_id[:8]}... "
            f"score={c.match_score:.2f}  priority={c.priority}"
        )

    # Assign and decide on a candidate
    review_candidate = pending[0]
    queue.assign_reviewer(review_candidate.candidate_id, "analyst_zola")
    queue.submit_decision(
        review_candidate.candidate_id,
        "confirmed_match",
        "analyst_zola",
        notes="Verified via CIB registry — same entity, name variant.",
    )

    # Submit more decisions for accuracy reporting
    if len(pending) > 1:
        queue.assign_reviewer(pending[1].candidate_id, "analyst_zola")
        queue.submit_decision(
            pending[1].candidate_id,
            "confirmed_non_match",
            "analyst_zola",
            notes="Different entities confirmed by RM.",
        )

    print("\n=== Queue Statistics ===")
    stats = queue.get_statistics()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== Reviewer Accuracy: analyst_zola ===")
    accuracy = queue.get_reviewer_accuracy("analyst_zola")
    for k, v in accuracy.items():
        print(f"  {k}: {v}")
