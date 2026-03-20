"""
Lekgotla Moderation

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging
import re

from afriflow.logging_config import get_logger
from afriflow.lekgotla.thread_store import Post

logger = get_logger("lekgotla.moderation")


@dataclass
class ModerationResult:
    approved: bool
    reasons: List[str]
    held_for_review: bool
    pii_detected: List[str]


class Moderator:
    PII_PATTERNS = {
        "account_number": r"\b\d{10,12}\b",
        "phone_number": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{2,3}\)?([-.\s]?\d{2,4}){2,4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "id_number": r"\b\d{13}\b",  # Typical SA ID
    }

    def __init__(self, client_golden_names: Optional[List[str]] = None) -> None:
        self.client_golden_names = client_golden_names or []
        logger.info("Moderator initialized")

    def scan_content(self, content: str) -> ModerationResult:
        pii_found = self.check_pii(content)
        reasons = []
        approved = True
        held = False

        if pii_found:
            reasons.append(f"PII Detected: {', '.join(pii_found)}")
            approved = False
            held = True

        # Check for client names
        for name in self.client_golden_names:
            if name.lower() in content.lower():
                reasons.append(f"Sensitive Client Reference: {name}")
                approved = False
                held = True

        if self.check_proprietary(content):
            reasons.append("Proprietary pricing detected")
            approved = False
            held = True

        return ModerationResult(
            approved=approved,
            reasons=reasons,
            held_for_review=held,
            pii_detected=pii_found,
        )

    def check_pii(self, content: str) -> List[str]:
        pii_found = []
        for label, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, content):
                pii_found.append(label)
        return pii_found

    def check_proprietary(self, content: str) -> bool:
        keywords = ["internal use only", "confidential spread", "markup"]
        return any(k in content.lower() for k in keywords)

    def hold_for_compliance(self, post: Post) -> None:
        logger.warning(f"Post {post.post_id} held for compliance review")

    def approve_held_post(self, post_id: str, reviewer_id: str) -> None:
        logger.info(f"Post {post_id} approved by reviewer {reviewer_id}")

    def reject_held_post(self, post_id: str, reviewer_id: str, reason: str) -> None:
        logger.info(f"Post {post_id} rejected by reviewer {reviewer_id}: {reason}")
