"""
Lekgotla Content Moderation

Content filtering, review workflows, and community guidelines
enforcement for Lekgotla posts.

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import logging
import re

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.moderation")


class ModerationAction(Enum):
    """Moderation actions."""
    APPROVED = "approved"
    FLAGGED = "flagged"
    HIDDEN = "hidden"
    REMOVED = "removed"
    ESCALATED = "escalated"


class ViolationType(Enum):
    """Content violation types."""
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    CONFIDENTIAL = "confidential"
    OFF_TOPIC = "off_topic"
    MISINFORMATION = "misinformation"
    HARASSMENT = "harassment"


class ContentModerator:
    """
    Content moderation engine.

    Performs automated content screening and manages
    human review workflows.
    """

    # Patterns that trigger flags
    CONFIDENTIAL_PATTERNS = [
        r"client\s*(name|number|id)\s*[:\s]*\w+",
        r"account\s*(number|id)\s*[:\s]*\d+",
        r"password|credential|secret",
        r"internal\s*(memo|document|report)",
    ]

    SPAM_PATTERNS = [
        r"http[s]?://\S+",  # Multiple URLs
        r"\b(CALL|CONTACT|CLICK)\s+(NOW|TODAY)\b",
        r"\b(FREE|WIN|PRIZE)\b",
    ]

    def __init__(self):
        self._flagged_content: Dict[str, Dict[str, Any]] = {}
        self._review_queue: List[str] = []
        self._moderation_log: List[Dict[str, Any]] = []

        # Compile regex patterns
        self._confidential_regex = [
            re.compile(p, re.IGNORECASE)
            for p in self.CONFIDENTIAL_PATTERNS
        ]
        self._spam_regex = [
            re.compile(p, re.IGNORECASE)
            for p in self.SPAM_PATTERNS
        ]

        logger.info("ContentModerator initialized")

    def screen_content(
        self,
        content_id: str,
        content: str,
        content_type: str,
        author_id: str,
    ) -> Tuple[ModerationAction, List[str]]:
        """
        Screen content for violations.

        Args:
            content_id: ID of the content
            content: Content text to screen
            content_type: Type (thread, reply, card, alert)
            author_id: Author's user ID

        Returns:
            Tuple of (action, violation_reasons)
        """
        violations = []
        action = ModerationAction.APPROVED

        # Check for confidential information
        confidential_matches = self._check_confidential(content)
        if confidential_matches:
            violations.append(
                f"confidential ({', '.join(confidential_matches)})"
            )
            action = ModerationAction.FLAGGED

        # Check for spam
        spam_matches = self._check_spam(content)
        if spam_matches:
            violations.append(
                f"spam ({', '.join(spam_matches)})"
            )
            action = ModerationAction.FLAGGED

        # Check for inappropriate language
        if self._check_inappropriate(content):
            violations.append("inappropriate_language")
            action = ModerationAction.FLAGGED

        # Log and queue if flagged
        if action == ModerationAction.FLAGGED:
            self._flagged_content[content_id] = {
                "content_id": content_id,
                "content_type": content_type,
                "author_id": author_id,
                "content_preview": content[:200],
                "violations": violations,
                "flagged_at": datetime.now(),
                "status": "pending_review",
            }
            self._review_queue.append(content_id)

            logger.warning(
                f"Content {content_id} flagged: {violations}"
            )

        return action, violations

    def _check_confidential(self, content: str) -> List[str]:
        """Check for confidential information patterns."""
        matches = []
        for i, regex in enumerate(self._confidential_regex):
            if regex.search(content):
                matches.append(self.CONFIDENTIAL_PATTERNS[i][:20])
        return matches

    def _check_spam(self, content: str) -> List[str]:
        """Check for spam patterns."""
        matches = []
        for i, regex in enumerate(self._spam_regex):
            if regex.search(content):
                matches.append(self.SPAM_PATTERNS[i][:20])
        return matches

    def _check_inappropriate(self, content: str) -> bool:
        """Check for inappropriate language."""
        # Simplified check - in production would use comprehensive list
        inappropriate_words = [
            "inappropriate_word_placeholder",
        ]
        content_lower = content.lower()
        return any(
            word in content_lower
            for word in inappropriate_words
        )

    def review_content(
        self,
        content_id: str,
        moderator_id: str,
        action: ModerationAction,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Review flagged content.

        Args:
            content_id: Content to review
            moderator_id: Moderator's user ID
            action: Moderation decision
            reason: Optional reason for decision

        Returns:
            True if review successful
        """
        if content_id not in self._flagged_content:
            raise ValueError(f"Content {content_id} not flagged")

        flagged = self._flagged_content[content_id]
        flagged["reviewed_by"] = moderator_id
        flagged["reviewed_at"] = datetime.now()
        flagged["decision"] = action.value
        flagged["reason"] = reason

        if action == ModerationAction.APPROVED:
            flagged["status"] = "approved"
            if content_id in self._review_queue:
                self._review_queue.remove(content_id)

        elif action in (
            ModerationAction.HIDDEN,
            ModerationAction.REMOVED,
        ):
            flagged["status"] = action.value

        # Log the moderation action
        self._moderation_log.append({
            "content_id": content_id,
            "moderator_id": moderator_id,
            "action": action.value,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

        logger.info(
            f"Content {content_id} reviewed by {moderator_id}: "
            f"{action.value}"
        )

        return True

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Get content pending review."""
        return [
            self._flagged_content[cid]
            for cid in self._review_queue
            if cid in self._flagged_content
        ]

    def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation statistics."""
        action_counts = {}
        violation_counts = {}

        for flagged in self._flagged_content.values():
            decision = flagged.get("decision", "pending")
            action_counts[decision] = action_counts.get(
                decision, 0
            ) + 1

            for violation in flagged.get("violations", []):
                vtype = violation.split()[0]
                violation_counts[vtype] = violation_counts.get(
                    vtype, 0
                ) + 1

        return {
            "total_flagged": len(self._flagged_content),
            "pending_review": len(self._review_queue),
            "action_breakdown": action_counts,
            "violation_breakdown": violation_counts,
            "total_reviews": len(self._moderation_log),
        }

    def get_user_violations(
        self, user_id: str
    ) -> Dict[str, Any]:
        """Get violation history for a user."""
        user_flags = [
            f for f in self._flagged_content.values()
            if f["author_id"] == user_id
        ]

        return {
            "total_flags": len(user_flags),
            "pending": sum(
                1 for f in user_flags
                if f.get("status") == "pending_review"
            ),
            "approved": sum(
                1 for f in user_flags
                if f.get("status") == "approved"
            ),
            "removed": sum(
                1 for f in user_flags
                if f.get("status") == "removed"
            ),
        }
