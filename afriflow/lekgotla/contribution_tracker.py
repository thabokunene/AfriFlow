"""
Lekgotla Contribution Tracker

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.contribution")


class ContributionType(Enum):
    POST = "POST"
    REPLY = "REPLY"
    UPVOTE_RECEIVED = "UPVOTE_RECEIVED"
    KNOWLEDGE_CARD = "KNOWLEDGE_CARD"
    VERIFIED_WIN = "VERIFIED_WIN"
    REGULATORY_ALERT = "REGULATORY_ALERT"


@dataclass
class Contribution:
    user_id: str
    contribution_type: ContributionType
    points: int
    timestamp: str
    reference_id: str


@dataclass
class ContributorProfile:
    user_id: str
    name: str
    role: str
    country: str
    total_score: int = 0
    posts_count: int = 0
    cards_contributed: int = 0
    verified_wins: int = 0
    revenue_attributed: float = 0.0
    rank: int = 0


class ContributionTracker:
    POINT_VALUES = {
        ContributionType.POST: 10,
        ContributionType.REPLY: 5,
        ContributionType.UPVOTE_RECEIVED: 2,
        ContributionType.KNOWLEDGE_CARD: 50,
        ContributionType.VERIFIED_WIN: 100,
        ContributionType.REGULATORY_ALERT: 30,
    }

    def __init__(self) -> None:
        self._contributions: List[Contribution] = []
        self._profiles: Dict[str, ContributorProfile] = {}
        logger.info("ContributionTracker initialized")

    def record_contribution(self, user_id: str, c_type: ContributionType, reference_id: str, revenue: float = 0.0) -> None:
        points = self.POINT_VALUES.get(c_type, 0)
        c = Contribution(
            user_id=user_id,
            contribution_type=c_type,
            points=points,
            timestamp=datetime.now().isoformat(),
            reference_id=reference_id,
        )
        self._contributions.append(c)

        if user_id not in self._profiles:
            # In a real system, we'd fetch profile data
            self._profiles[user_id] = ContributorProfile(user_id=user_id, name="Unknown", role="Practitioner", country="ZA")

        profile = self._profiles[user_id]
        profile.total_score += points
        if c_type == ContributionType.POST:
            profile.posts_count += 1
        elif c_type == ContributionType.KNOWLEDGE_CARD:
            profile.cards_contributed += 1
        elif c_type == ContributionType.VERIFIED_WIN:
            profile.verified_wins += 1
            profile.revenue_attributed += revenue

        logger.info(f"Contribution recorded for {user_id}: {c_type.value} (+{points} pts)")

    def get_profile(self, user_id: str) -> Optional[ContributorProfile]:
        return self._profiles.get(user_id)

    def get_leaderboard(self, limit: int = 10, period: str = "ALL") -> List[ContributorProfile]:
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda p: p.total_score, reverse=True)
        for i, p in enumerate(profiles):
            p.rank = i + 1
        return profiles[:limit]

    def calculate_score(self, user_id: str) -> int:
        return self._profiles[user_id].total_score if user_id in self._profiles else 0

    def get_contribution_trend(self, user_id: str, months: int) -> List[Dict]:
        return []
