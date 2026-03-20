"""
@file contribution_tracker.py
@description Lekgotla Contribution Tracker - Gamification and scoring system
@author Thabo Kunene
@created 2026-03-19

This module tracks user contributions to Lekgotla and calculates scores
for gamification and leaderboard purposes.

Key Features:
- Point system for various contributions
- Level progression based on total score
- Badge awards for milestones
- Leaderboard generation
- User statistics

Usage:
    >>> from afriflow.lekgotla.contribution_tracker import ContributionTracker
    >>> tracker = ContributionTracker()
    >>> tracker.track_thread_created("user-123", "Sipho Mabena")
    >>> tracker.get_leaderboard(limit=10)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.contribution_tracker")


@dataclass
class ContributionRecord:
    """User contribution record with score and badges."""
    user_id: str
    user_name: str
    threads_created: int = 0
    replies_posted: int = 0
    solutions_marked: int = 0
    cards_contributed: int = 0
    cards_published: int = 0
    upvotes_received: int = 0
    upvotes_given: int = 0
    regulatory_posts: int = 0
    total_score: float = 0.0
    level: str = "newcomer"
    badges: List[str] = field(default_factory=list)
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "threads_created": self.threads_created,
            "replies_posted": self.replies_posted,
            "solutions_marked": self.solutions_marked,
            "cards_contributed": self.cards_contributed,
            "cards_published": self.cards_published,
            "upvotes_received": self.upvotes_received,
            "upvotes_given": self.upvotes_given,
            "regulatory_posts": self.regulatory_posts,
            "total_score": self.total_score,
            "level": self.level,
            "badges": self.badges,
            "last_activity": self.last_activity,
        }


class ContributionTracker:
    """
    Contribution tracking and gamification engine.

    Scoring weights:
    - Thread created: 10 points
    - Reply posted: 5 points
    - Solution marked: 25 points
    - Card contributed: 50 points
    - Card published: 100 points
    - Upvote received: 2 points
    - Regulatory post: 30 points
    """

    # Point values for each contribution type
    SCORES = {
        "thread_created": 10,
        "reply_posted": 5,
        "solution_marked": 25,
        "card_contributed": 50,
        "card_published": 100,
        "upvote_received": 2,
        "regulatory_post": 30,
    }

    # Level thresholds (minimum score for each level)
    LEVELS = [
        (0, "newcomer"),
        (100, "contributor"),
        (500, "active_contributor"),
        (1500, "expert"),
        (5000, "thought_leader"),
        (15000, "legend"),
    ]

    # Badge definitions
    BADGES = {
        "first_thread": "First Thread",
        "first_reply": "First Reply",
        "solution_provider": "Solution Provider",
        "card_author": "Knowledge Author",
        "top_contributor": "Top Contributor",
        "regulatory_expert": "Regulatory Expert",
    }

    def __init__(self) -> None:
        """Initialize tracker with empty records."""
        self._records: Dict[str, ContributionRecord] = {}
        logger.info("ContributionTracker initialized")

    def get_or_create_record(
        self, user_id: str, user_name: str
    ) -> ContributionRecord:
        """Get or create user contribution record."""
        if user_id not in self._records:
            self._records[user_id] = ContributionRecord(
                user_id=user_id, user_name=user_name
            )
        return self._records[user_id]

    def track_thread_created(
        self, user_id: str, user_name: str
    ) -> None:
        """Track thread creation and award points."""
        record = self.get_or_create_record(user_id, user_name)
        record.threads_created += 1
        record.total_score += self.SCORES["thread_created"]
        record.last_activity = datetime.now().isoformat()
        if record.threads_created == 1:
            self._award_badge(record, "first_thread")
        self._update_level(record)

    def track_reply_posted(
        self, user_id: str, user_name: str
    ) -> None:
        """Track reply posting and award points."""
        record = self.get_or_create_record(user_id, user_name)
        record.replies_posted += 1
        record.total_score += self.SCORES["reply_posted"]
        record.last_activity = datetime.now().isoformat()
        if record.replies_posted == 1:
            self._award_badge(record, "first_reply")
        self._update_level(record)

    def track_solution_marked(
        self, user_id: str, user_name: str
    ) -> None:
        """Track when user's reply is marked as solution."""
        record = self.get_or_create_record(user_id, user_name)
        record.solutions_marked += 1
        record.total_score += self.SCORES["solution_marked"]
        record.last_activity = datetime.now().isoformat()
        if record.solutions_marked >= 5:
            self._award_badge(record, "solution_provider")
        self._update_level(record)

    def track_card_contributed(
        self, user_id: str, user_name: str
    ) -> None:
        """Track contribution to Knowledge Card."""
        record = self.get_or_create_record(user_id, user_name)
        record.cards_contributed += 1
        record.total_score += self.SCORES["card_contributed"]
        record.last_activity = datetime.now().isoformat()
        self._update_level(record)

    def track_card_published(
        self, user_id: str, user_name: str
    ) -> None:
        """Track when user's card is published."""
        record = self.get_or_create_record(user_id, user_name)
        record.cards_published += 1
        record.total_score += self.SCORES["card_published"]
        record.last_activity = datetime.now().isoformat()
        if record.cards_published >= 1:
            self._award_badge(record, "card_author")
        self._update_level(record)

    def track_upvote_received(
        self, user_id: str, user_name: str, count: int = 1
    ) -> None:
        """Track upvotes received."""
        record = self.get_or_create_record(user_id, user_name)
        record.upvotes_received += count
        record.total_score += count * self.SCORES["upvote_received"]
        self._update_level(record)

    def track_regulatory_post(
        self, user_id: str, user_name: str
    ) -> None:
        """Track regulatory channel post."""
        record = self.get_or_create_record(user_id, user_name)
        record.regulatory_posts += 1
        record.total_score += self.SCORES["regulatory_post"]
        record.last_activity = datetime.now().isoformat()
        if record.regulatory_posts >= 10:
            self._award_badge(record, "regulatory_expert")
        self._update_level(record)

    def get_leaderboard(
        self, limit: int = 50, period_days: Optional[int] = None
    ) -> List[ContributionRecord]:
        """Get contribution leaderboard."""
        records = list(self._records.values())
        if period_days:
            cutoff = datetime.now() - timedelta(days=period_days)
            records = [
                r for r in records
                if datetime.fromisoformat(r.last_activity) >= cutoff
            ]
        records.sort(key=lambda r: r.total_score, reverse=True)
        return records[:limit]

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user."""
        record = self._records.get(user_id)
        if not record:
            return {"error": "User not found"}
        leaderboard = self.get_leaderboard(limit=100)
        rank = next(
            (i + 1 for i, r in enumerate(leaderboard) if r.user_id == user_id),
            None,
        )
        return {
            **record.to_dict(),
            "rank": rank,
            "percentile": (
                (100 - (rank / len(leaderboard) * 100))
                if rank else 0
            ),
        }

    def _update_level(self, record: ContributionRecord) -> None:
        """Update user's level based on score."""
        for threshold, level in reversed(self.LEVELS):
            if record.total_score >= threshold:
                record.level = level
                break

    def _award_badge(
        self, record: ContributionRecord, badge_key: str
    ) -> None:
        """Award a badge to user."""
        if badge_key not in record.badges:
            record.badges.append(badge_key)
            logger.info(
                f"Badge awarded to {record.user_name}: "
                f"{self.BADGES.get(badge_key, badge_key)}"
            )

    def get_statistics(self) -> Dict[str, Any]:
        """Get contribution statistics."""
        total_users = len(self._records)
        total_score = sum(r.total_score for r in self._records.values())
        level_counts = {}
        for record in self._records.values():
            level = record.level
            level_counts[level] = level_counts.get(level, 0) + 1
        return {
            "total_contributors": total_users,
            "total_score_awarded": total_score,
            "level_distribution": level_counts,
            "avg_score_per_user": (
                total_score / total_users if total_users else 0
            ),
        }


# Import Optional for type hints
from typing import Optional

__all__ = [
    "ContributionRecord",
    "ContributionTracker",
]
