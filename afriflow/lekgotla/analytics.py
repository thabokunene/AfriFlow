"""
@file analytics.py
@description Lekgotla Analytics - Platform health metrics and engagement tracking
@author Thabo Kunene
@created 2026-03-19

This module provides analytics for the Lekgotla platform including
engagement metrics, content quality indicators, and ROI tracking.

Key Features:
- Daily metrics aggregation
- Engagement tracking (threads, replies, upvotes)
- Content quality indicators
- User activity patterns
- ROI attribution from Knowledge Cards

Usage:
    >>> from afriflow.lekgotla.analytics import LekgotlaAnalytics
    >>> analytics = LekgotlaAnalytics()
    >>> analytics.record_thread_created("THR-123", "EXPANSION", "user-456")
    >>> stats = analytics.get_summary_stats(period_days=30)

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.analytics")


@dataclass
class DailyMetrics:
    """Daily aggregated metrics for Lekgotla."""
    date: str
    new_threads: int = 0
    new_replies: int = 0
    new_cards: int = 0
    total_upvotes: int = 0
    active_users: int = 0
    solutions_marked: int = 0
    regulatory_posts: int = 0


class LekgotlaAnalytics:
    """
    Analytics engine for Lekgotla platform.

    Tracks:
    - Engagement metrics (threads, replies, upvotes)
    - Content quality indicators
    - User activity patterns
    - ROI attribution from Knowledge Cards
    """

    def __init__(self) -> None:
        """Initialize analytics with empty metrics store."""
        self._daily_metrics: Dict[str, DailyMetrics] = {}
        self._signal_thread_map: Dict[str, int] = {}
        self._card_usage_log: List[Dict[str, Any]] = []
        logger.info("LekgotlaAnalytics initialized")

    def record_thread_created(
        self,
        thread_id: str,
        signal_id: Optional[str],
        author_id: str,
    ) -> None:
        """Record thread creation for analytics."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_metrics:
            self._daily_metrics[today] = DailyMetrics(date=today)
        self._daily_metrics[today].new_threads += 1
        if signal_id:
            self._signal_thread_map[signal_id] = (
                self._signal_thread_map.get(signal_id, 0) + 1
            )

    def record_reply_posted(self, author_id: str) -> None:
        """Record reply for analytics."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_metrics:
            self._daily_metrics[today] = DailyMetrics(date=today)
        self._daily_metrics[today].new_replies += 1

    def record_card_created(
        self, card_id: str, contributor_ids: List[str]
    ) -> None:
        """Record Knowledge Card creation."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_metrics:
            self._daily_metrics[today] = DailyMetrics(date=today)
        self._daily_metrics[today].new_cards += 1

    def record_card_usage(
        self,
        card_id: str,
        user_id: str,
        client_id: Optional[str],
        revenue: float,
        won: bool,
    ) -> None:
        """Record Knowledge Card usage for ROI tracking."""
        self._card_usage_log.append({
            "card_id": card_id,
            "user_id": user_id,
            "client_id": client_id,
            "revenue": revenue,
            "won": won,
            "timestamp": datetime.now().isoformat(),
        })

    def record_upvote(self, voter_id: str) -> None:
        """Record upvote for analytics."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_metrics:
            self._daily_metrics[today] = DailyMetrics(date=today)
        self._daily_metrics[today].total_upvotes += 1

    def record_solution_marked(self, author_id: str) -> None:
        """Record solution marking."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_metrics:
            self._daily_metrics[today] = DailyMetrics(date=today)
        self._daily_metrics[today].solutions_marked += 1

    def get_daily_metrics(
        self, start_date: str, end_date: str
    ) -> List[DailyMetrics]:
        """Get daily metrics for date range."""
        metrics = []
        for date_str, metric in sorted(self._daily_metrics.items()):
            if start_date <= date_str <= end_date:
                metrics.append(metric)
        return metrics

    def get_summary_stats(
        self, period_days: int = 30
    ) -> Dict[str, Any]:
        """Get summary statistics for period."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (
            datetime.now() - timedelta(days=period_days)
        ).strftime("%Y-%m-%d")
        metrics = self.get_daily_metrics(start_date, end_date)
        if not metrics:
            return self._empty_summary()
        total_threads = sum(m.new_threads for m in metrics)
        total_replies = sum(m.new_replies for m in metrics)
        total_cards = sum(m.new_cards for m in metrics)
        total_upvotes = sum(m.total_upvotes for m in metrics)
        total_solutions = sum(m.solutions_marked for m in metrics)
        return {
            "period_days": period_days,
            "start_date": start_date,
            "end_date": end_date,
            "total_threads": total_threads,
            "total_replies": total_replies,
            "total_cards": total_cards,
            "total_upvotes": total_upvotes,
            "total_solutions": total_solutions,
            "avg_threads_per_day": total_threads / len(metrics),
            "avg_replies_per_day": total_replies / len(metrics),
            "thread_to_reply_ratio": (
                total_replies / total_threads
                if total_threads > 0 else 0
            ),
        }

    def get_roi_attribution(self) -> Dict[str, Any]:
        """Calculate ROI attribution from Knowledge Cards."""
        if not self._card_usage_log:
            return {
                "total_revenue": 0,
                "opportunities_won": 0,
                "opportunities_total": 0,
                "win_rate": 0,
                "avg_revenue_per_use": 0,
            }
        total_revenue = sum(
            u["revenue"] for u in self._card_usage_log
        )
        won = sum(1 for u in self._card_usage_log if u["won"])
        total = len(self._card_usage_log)
        return {
            "total_revenue": total_revenue,
            "opportunities_won": won,
            "opportunities_total": total,
            "win_rate": won / total if total > 0 else 0,
            "avg_revenue_per_use": total_revenue / total,
            "total_uses": total,
        }

    def get_signal_engagement(self) -> Dict[str, int]:
        """Get thread count per signal type."""
        return dict(self._signal_thread_map)

    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "period_days": 0,
            "total_threads": 0,
            "total_replies": 0,
            "total_cards": 0,
            "total_upvotes": 0,
            "total_solutions": 0,
            "avg_threads_per_day": 0,
            "avg_replies_per_day": 0,
            "thread_to_reply_ratio": 0,
        }

    def get_health_score(self) -> Dict[str, Any]:
        """
        Calculate platform health score.

        Based on:
        - Thread activity
        - Reply engagement
        - Solution rate
        - Card adoption
        """
        summary = self.get_summary_stats(period_days=30)
        activity_score = min(100, summary["avg_threads_per_day"] * 10)
        engagement_score = min(
            100, summary["thread_to_reply_ratio"] * 25
        )
        solution_rate = (
            summary["total_solutions"] / summary["total_threads"]
            if summary["total_threads"] > 0 else 0
        )
        solution_score = min(100, solution_rate * 200)
        health_score = (
            activity_score * 0.3 +
            engagement_score * 0.3 +
            solution_score * 0.4
        )
        return {
            "overall_health": round(health_score, 1),
            "activity_score": round(activity_score, 1),
            "engagement_score": round(engagement_score, 1),
            "solution_score": round(solution_score, 1),
            "health_level": self._get_health_level(health_score),
        }

    def _get_health_level(self, score: float) -> str:
        """Convert score to health level."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "moderate"
        elif score >= 20:
            return "low"
        else:
            return "critical"


__all__ = [
    "DailyMetrics",
    "LekgotlaAnalytics",
]
