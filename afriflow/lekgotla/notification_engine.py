"""
Lekgotla Notification Engine

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
import uuid

from afriflow.logging_config import get_logger
from afriflow.lekgotla.thread_store import Thread, Post
from afriflow.lekgotla.knowledge_card_store import KnowledgeCard

logger = get_logger("lekgotla.notification")


class NotificationType(Enum):
    NEW_THREAD = "NEW_THREAD"
    NEW_REPLY = "NEW_REPLY"
    REGULATORY_ALERT = "REGULATORY_ALERT"
    KNOWLEDGE_CARD = "KNOWLEDGE_CARD"
    UNANSWERED_CHALLENGE = "UNANSWERED_CHALLENGE"


@dataclass
class Notification:
    notification_id: str
    recipient_id: str
    notification_type: NotificationType
    title: str
    body: str
    created_at: str
    read: bool = False
    thread_id: Optional[str] = None
    card_id: Optional[str] = None
    countries: List[str] = field(default_factory=list)
    urgency: str = "MEDIUM"


class NotificationEngine:
    def __init__(self) -> None:
        self._notifications: Dict[str, List[Notification]] = {}
        logger.info("NotificationEngine initialized")

    def notify_on_new_thread(self, thread: Thread) -> List[Notification]:
        recipients = self.get_recipients_for_context(
            thread.countries, thread.signal_type or "", thread.products
        )
        notifications = []
        for rid in recipients:
            n = Notification(
                notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
                recipient_id=rid,
                notification_type=NotificationType.NEW_THREAD,
                title=f"New Lekgotla Thread: {thread.title}",
                body=f"{thread.author_name} posted a new challenge in {', '.join(thread.countries)}",
                created_at=datetime.now().isoformat(),
                thread_id=thread.thread_id,
                countries=thread.countries,
            )
            self._add_notification(rid, n)
            notifications.append(n)
        return notifications

    def notify_on_regulatory_alert(self, alert_id: str, title: str, countries: List[str]) -> List[Notification]:
        recipients = self.get_recipients_for_context(countries, "REGULATORY", [])
        notifications = []
        for rid in recipients:
            n = Notification(
                notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
                recipient_id=rid,
                notification_type=NotificationType.REGULATORY_ALERT,
                title=f"REGULATORY ALERT: {title}",
                body=f"A new regulatory alert affecting {', '.join(countries)} has been posted.",
                created_at=datetime.now().isoformat(),
                countries=countries,
                urgency="HIGH",
            )
            self._add_notification(rid, n)
            notifications.append(n)
        return notifications

    def notify_on_card_graduation(self, card: KnowledgeCard) -> List[Notification]:
        recipients = self.get_recipients_for_context(card.countries, card.signal_type, card.products)
        notifications = []
        for rid in recipients:
            n = Notification(
                notification_id=f"NOT-{uuid.uuid4().hex[:8].upper()}",
                recipient_id=rid,
                notification_type=NotificationType.KNOWLEDGE_CARD,
                title=f"New Knowledge Card: {card.title}",
                body=f"A new proven strategy for {card.signal_type} is now available.",
                created_at=datetime.now().isoformat(),
                card_id=card.card_id,
            )
            self._add_notification(rid, n)
            notifications.append(n)
        return notifications

    def get_recipients_for_context(self, countries: List[str], signal_type: str, products: List[str]) -> List[str]:
        # Placeholder for recipient resolution logic
        return ["RM-GLOBAL-1"]

    def get_unread(self, user_id: str) -> List[Notification]:
        return [n for n in self._notifications.get(user_id, []) if not n.read]

    def mark_read(self, notification_id: str) -> None:
        for notifications in self._notifications.values():
            for n in notifications:
                if n.notification_id == notification_id:
                    n.read = True
                    return

    def _add_notification(self, user_id: str, notification: Notification) -> None:
        if user_id not in self._notifications:
            self._notifications[user_id] = []
        self._notifications[user_id].append(notification)
