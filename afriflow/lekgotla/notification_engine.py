"""
@file notification_engine.py
@description Notification engine for the Lekgotla module, delivering contextual
    alerts to practitioners about relevant threads, Knowledge Cards, and replies
    based on their portfolio and past activity.
@author Thabo Kunene
@created 2026-03-19
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import logging

from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.notification_engine")


@dataclass
class Notification:
    """A notification to a user."""
    notification_id: str
    user_id: str
    notification_type: str
    title: str
    content: str
    related_thread_id: Optional[str]
    related_card_id: Optional[str]
    related_signal_id: Optional[str]
    created_at: datetime
    is_read: bool = False
    priority: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "notification_type": self.notification_type,
            "title": self.title,
            "content": self.content,
            "related_thread_id": self.related_thread_id,
            "related_card_id": self.related_card_id,
            "related_signal_id": self.related_signal_id,
            "created_at": self.created_at.isoformat(),
            "is_read": self.is_read,
            "priority": self.priority,
        }


class NotificationEngine:
    """
    Notification delivery engine.

    Sends contextual notifications to practitioners about:
    - New threads on their signals
    - New Knowledge Cards for their signal types
    - Replies to threads they participated in
    - Cards they contributed to being published
    """

    def __init__(self):
        self._notifications: Dict[str, List[Notification]] = {}
        self._user_preferences: Dict[str, Dict[str, bool]] = {}

        logger.info("NotificationEngine initialized")

    def notify_new_thread(
        self,
        user_ids: List[str],
        thread_id: str,
        thread_title: str,
        signal_type: str,
        client_name: Optional[str] = None,
    ) -> List[Notification]:
        """Notify users about a new thread."""
        import uuid

        notifications = []

        for user_id in user_ids:
            if not self._should_notify(user_id, "new_thread"):
                continue

            notification = Notification(
                notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
                user_id=user_id,
                notification_type="new_thread",
                title=f"New thread: {thread_title}",
                content=(
                    f"New discussion on {signal_type}"
                    f"{' for ' + client_name if client_name else ''}"
                ),
                related_thread_id=thread_id,
                related_card_id=None,
                related_signal_id=None,
                created_at=datetime.now(),
            )

            self._add_notification(user_id, notification)
            notifications.append(notification)

        logger.info(
            f"Sent {len(notifications)} notifications for thread {thread_id}"
        )

        return notifications

    def notify_new_card(
        self,
        user_ids: List[str],
        card_id: str,
        card_title: str,
        signal_type: str,
    ) -> List[Notification]:
        """Notify users about a new Knowledge Card."""
        import uuid

        notifications = []

        for user_id in user_ids:
            if not self._should_notify(user_id, "new_card"):
                continue

            notification = Notification(
                notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
                user_id=user_id,
                notification_type="new_card",
                title=f"New Knowledge Card: {card_title}",
                content=f"Validated approach for {signal_type}",
                related_thread_id=None,
                related_card_id=card_id,
                related_signal_id=None,
                created_at=datetime.now(),
            )

            self._add_notification(user_id, notification)
            notifications.append(notification)

        logger.info(
            f"Sent {len(notifications)} notifications for card {card_id}"
        )

        return notifications

    def notify_reply(
        self,
        user_id: str,
        thread_id: str,
        reply_author: str,
        thread_title: str,
    ) -> Optional[Notification]:
        """Notify a user about a reply to their thread."""
        import uuid

        if not self._should_notify(user_id, "reply"):
            return None

        notification = Notification(
            notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            notification_type="reply",
            title=f"New reply on: {thread_title}",
            content=f"{reply_author} replied to your thread",
            related_thread_id=thread_id,
            related_card_id=None,
            related_signal_id=None,
            created_at=datetime.now(),
        )

        self._add_notification(user_id, notification)

        return notification

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        user_notifications = self._notifications.get(user_id, [])
        return sum(1 for n in user_notifications if not n.is_read)

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
    ) -> List[Notification]:
        """Get notifications for a user."""
        user_notifications = self._notifications.get(user_id, [])

        if unread_only:
            user_notifications = [
                n for n in user_notifications if not n.is_read
            ]

        user_notifications.sort(
            key=lambda n: n.created_at, reverse=True
        )

        return user_notifications[:limit]

    def mark_as_read(self, user_id: str, notification_id: str) -> None:
        """Mark a notification as read."""
        for notification in self._notifications.get(user_id, []):
            if notification.notification_id == notification_id:
                notification.is_read = True
                break

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        count = 0
        for notification in self._notifications.get(user_id, []):
            if not notification.is_read:
                notification.is_read = True
                count += 1
        return count

    def set_user_preference(
        self,
        user_id: str,
        notification_type: str,
        enabled: bool,
    ) -> None:
        """Set user notification preference."""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][notification_type] = enabled

    def _should_notify(
        self, user_id: str, notification_type: str
    ) -> bool:
        """Check if user wants this notification type."""
        user_prefs = self._user_preferences.get(user_id, {})
        return user_prefs.get(notification_type, True)

    def _add_notification(
        self, user_id: str, notification: Notification
    ) -> None:
        """Add a notification to user's list."""
        if user_id not in self._notifications:
            self._notifications[user_id] = []
        self._notifications[user_id].append(notification)

        # Keep only last 200 notifications per user
        if len(self._notifications[user_id]) > 200:
            self._notifications[user_id] = self._notifications[
                user_id
            ][-200:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        total = sum(
            len(notifs) for notifs in self._notifications.values()
        )
        unread = sum(
            sum(1 for n in notifs if not n.is_read)
            for notifs in self._notifications.values()
        )

        return {
            "total_notifications": total,
            "unread_notifications": unread,
            "users_with_notifications": len(self._notifications),
        }
