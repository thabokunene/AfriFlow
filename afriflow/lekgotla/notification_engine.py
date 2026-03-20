"""
@file notification_engine.py
@description Lekgotla Notification Engine - User notification delivery and management
@author Thabo Kunene
@created 2026-03-19

This module manages the delivery of Lekgotla notifications to users.
Notifications alert users to new threads, replies, regulatory alerts,
Knowledge Card graduations, and unanswered challenges.

Key Classes:
- NotificationType: Types of notifications (NEW_THREAD, NEW_REPLY, etc.)
- Notification: Individual notification with recipient and content
- NotificationEngine: Main engine for creating and managing notifications

Features:
- Multiple notification types (threads, replies, alerts, cards)
- User-specific notification queues
- Read/unread tracking
- Urgency levels (LOW, MEDIUM, HIGH, CRITICAL)
- Country-based filtering for regulatory alerts
- Batch retrieval for efficient UI loading

Usage:
    >>> from afriflow.lekgotla.notification_engine import NotificationEngine
    >>> engine = NotificationEngine()
    >>> engine.notify_new_thread(
    ...     user_id="user-123",
    ...     thread_id="THR-456",
    ...     title="Ghana expansion approach"
    ... )
    >>> unread = engine.get_unread_count("user-123")

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Standard library imports
from dataclasses import dataclass, field  # For data class decorators and default values
from datetime import datetime  # For timestamp generation
from enum import Enum  # For enumerated notification types
from typing import Dict, List, Optional, Any  # Type hints for dictionaries, lists, optional values
import logging  # For debug and info logging
import uuid  # For generating unique notification IDs

# Import logging utility for structured logging
from afriflow.logging_config import get_logger

# Import Thread and Post for thread-related notifications
from afriflow.lekgotla.thread_store import Thread, Post

# Import KnowledgeCard for card-related notifications
from afriflow.lekgotla.knowledge_card_store import KnowledgeCard

logger = get_logger("lekgotla.notification")  # Get logger instance for this module


class NotificationType(Enum):
    """
    Notification type enumeration.

    Defines the different types of notifications that can be sent
    to users through the Lekgotla platform.

    Values:
        NEW_THREAD: New discussion thread created
        NEW_REPLY: New reply to a thread user is following
        REGULATORY_ALERT: Compliance officer regulatory alert
        KNOWLEDGE_CARD: Knowledge Card graduated or published
        UNANSWERED_CHALLENGE: Challenge thread without responses
    """
    NEW_THREAD = "NEW_THREAD"  # New discussion thread
    NEW_REPLY = "NEW_REPLY"  # New reply to followed thread
    REGULATORY_ALERT = "REGULATORY_ALERT"  # Compliance regulatory alert
    KNOWLEDGE_CARD = "KNOWLEDGE_CARD"  # Knowledge Card graduation/publication
    UNANSWERED_CHALLENGE = "UNANSWERED_CHALLENGE"  # Unanswered challenge


@dataclass
class Notification:
    """
    Individual notification for a user.

    Represents a single notification to be delivered to a user.
    Notifications are stored in user-specific queues and tracked
    for read/unread status.

    Attributes:
        notification_id: Unique identifier (UUID format)
        recipient_id: User ID of the notification recipient
        notification_type: Type of notification (enum)
        title: Notification title (short summary)
        body: Notification body (detailed message)
        created_at: ISO 8601 timestamp of creation
        read: Whether the notification has been read (default: False)
        thread_id: Related thread ID (if applicable)
        card_id: Related Knowledge Card ID (if applicable)
        countries: List of relevant country codes (for regulatory alerts)
        urgency: Urgency level (LOW, MEDIUM, HIGH, CRITICAL)

    Example:
        >>> notification = Notification(
        ...     notification_id="NOT-ABC123",
        ...     recipient_id="user-456",
        ...     notification_type=NotificationType.NEW_THREAD,
        ...     title="New expansion discussion",
        ...     body="New thread: Ghana expansion approach",
        ...     thread_id="THR-789"
        ... )
    """
    notification_id: str  # Unique notification identifier
    recipient_id: str  # User ID of recipient
    notification_type: NotificationType  # Type of notification
    title: str  # Short notification title
    body: str  # Detailed notification body
    created_at: str  # ISO 8601 creation timestamp
    read: bool = False  # Read status (default: unread)
    thread_id: Optional[str] = None  # Related thread ID
    card_id: Optional[str] = None  # Related Knowledge Card ID
    countries: List[str] = field(default_factory=list)  # Relevant countries
    urgency: str = "MEDIUM"  # Urgency level (LOW/MEDIUM/HIGH/CRITICAL)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert notification to dictionary for JSON serialization.

        This method enables easy serialization for API responses
        and database storage.

        Returns:
            Dictionary with all notification fields
        """
        return {
            "notification_id": self.notification_id,  # Unique ID
            "recipient_id": self.recipient_id,  # Recipient user ID
            "notification_type": self.notification_type.value,  # Type as string
            "title": self.title,  # Notification title
            "body": self.body,  # Notification body
            "created_at": self.created_at,  # Creation timestamp
            "read": self.read,  # Read status
            "thread_id": self.thread_id,  # Related thread ID
            "card_id": self.card_id,  # Related card ID
            "countries": self.countries,  # Country list
            "urgency": self.urgency,  # Urgency level
        }


class NotificationEngine:
    """
    Notification delivery and management engine.

    This class manages the creation, storage, and retrieval of
    notifications for all users. In production, this would use
    PostgreSQL with a message queue (e.g., Redis, RabbitMQ) for
    scalable delivery.

    Features:
    - User-specific notification queues
    - Read/unread tracking
    - Notification type filtering
    - Country-based filtering (for regulatory alerts)
    - Batch retrieval for efficient UI loading

    Attributes:
        _notifications: Dictionary mapping user_id to list of Notifications
        _user_preferences: Dictionary mapping user_id to notification preferences

    Example:
        >>> engine = NotificationEngine()
        >>> engine.notify_new_thread(
        ...     user_id="user-123",
        ...     thread_id="THR-456",
        ...     title="Ghana expansion approach"
        ... )
        >>> unread_count = engine.get_unread_count("user-123")
    """

    def __init__(self) -> None:
        """
        Initialize the notification engine with empty queues.

        Creates two data structures:
        1. _notifications: User notification queues (user_id -> [Notification])
        2. _user_preferences: User notification preferences (user_id -> {type: enabled})
        """
        # User notification queues (user_id -> list of notifications)
        self._notifications: Dict[str, List[Notification]] = {}
        # User notification preferences (user_id -> {notification_type: enabled})
        self._user_preferences: Dict[str, Dict[str, bool]] = {}

        logger.info("NotificationEngine initialized")  # Log initialization

    def notify_new_thread(
        self,
        user_id: str,
        thread_id: str,
        title: str,
        signal_type: Optional[str] = None,
        countries: Optional[List[str]] = None
    ) -> Optional[Notification]:
        """
        Notify a user about a new thread.

        This method creates a notification for a new thread. It checks
        user preferences before creating the notification.

        Args:
            user_id: User ID to notify
            thread_id: ID of the new thread
            title: Thread title for the notification
            signal_type: Optional signal type for context
            countries: Optional list of relevant countries

        Returns:
            Created Notification object, or None if user disabled this type

        Example:
            >>> engine.notify_new_thread(
            ...     user_id="user-123",
            ...     thread_id="THR-456",
            ...     title="Ghana expansion approach",
            ...     signal_type="EXPANSION",
            ...     countries=["GH"]
            ... )
        """
        # Check if user wants new thread notifications
        if not self._should_notify(user_id, "new_thread"):
            return None

        # Generate unique notification ID
        notification_id = f"NOT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        # Create notification object
        notification = Notification(
            notification_id=notification_id,
            recipient_id=user_id,
            notification_type=NotificationType.NEW_THREAD,
            title=f"New thread: {title}",
            body=f"New discussion on {signal_type or 'Lekgotla'}",
            created_at=now,
            thread_id=thread_id,
            countries=countries or [],
        )

        # Add to user's notification queue
        self._add_notification(user_id, notification)

        logger.info(
            f"Notification sent to {user_id} for thread {thread_id}"
        )

        return notification

    def notify_new_reply(
        self,
        user_id: str,
        thread_id: str,
        reply_author: str,
        thread_title: str
    ) -> Optional[Notification]:
        """
        Notify a user about a new reply to their thread.

        This method notifies thread authors when someone replies
        to their discussion.

        Args:
            user_id: User ID to notify (thread author)
            thread_id: ID of the thread with new reply
            reply_author: Name of the user who replied
            thread_title: Title of the thread

        Returns:
            Created Notification object, or None if disabled
        """
        # Check if user wants reply notifications
        if not self._should_notify(user_id, "reply"):
            return None

        notification_id = f"NOT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        notification = Notification(
            notification_id=notification_id,
            recipient_id=user_id,
            notification_type=NotificationType.NEW_REPLY,
            title=f"New reply on: {thread_title}",
            body=f"{reply_author} replied to your thread",
            created_at=now,
            thread_id=thread_id,
        )

        self._add_notification(user_id, notification)
        return notification

    def notify_regulatory_alert(
        self,
        user_ids: List[str],
        alert_id: str,
        title: str,
        countries: List[str],
        urgency: str = "HIGH"
    ) -> List[Notification]:
        """
        Notify multiple users about a regulatory alert.

        This method sends regulatory alerts to multiple users
        (e.g., all RMs in affected countries).

        Args:
            user_ids: List of user IDs to notify
            alert_id: ID of the regulatory alert
            title: Alert title
            countries: List of affected country codes
            urgency: Urgency level (default: HIGH)

        Returns:
            List of created Notification objects
        """
        notifications = []

        for user_id in user_ids:
            # Check if user wants regulatory alerts
            if not self._should_notify(user_id, "regulatory"):
                continue

            notification_id = f"NOT-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now().isoformat()

            notification = Notification(
                notification_id=notification_id,
                recipient_id=user_id,
                notification_type=NotificationType.REGULATORY_ALERT,
                title=title,
                body=f"Regulatory alert for: {', '.join(countries)}",
                created_at=now,
                thread_id=alert_id,
                countries=countries,
                urgency=urgency,
            )

            self._add_notification(user_id, notification)
            notifications.append(notification)

        logger.info(
            f"Regulatory alert sent to {len(notifications)} users"
        )

        return notifications

    def notify_knowledge_card(
        self,
        user_id: str,
        card_id: str,
        card_title: str,
        signal_type: str
    ) -> Optional[Notification]:
        """
        Notify a user about a new Knowledge Card.

        This method notifies users when a new Knowledge Card
        is published in their area of interest.

        Args:
            user_id: User ID to notify
            card_id: ID of the Knowledge Card
            card_title: Card title
            signal_type: Associated signal type

        Returns:
            Created Notification object, or None if disabled
        """
        if not self._should_notify(user_id, "card"):
            return None

        notification_id = f"NOT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        notification = Notification(
            notification_id=notification_id,
            recipient_id=user_id,
            notification_type=NotificationType.KNOWLEDGE_CARD,
            title=f"New Knowledge Card: {card_title}",
            body=f"Validated approach for {signal_type}",
            created_at=now,
            card_id=card_id,
        )

        self._add_notification(user_id, notification)
        return notification

    def get_unread_count(self, user_id: str) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            user_id: User ID to check

        Returns:
            Number of unread notifications
        """
        user_notifications = self._notifications.get(user_id, [])
        return sum(1 for n in user_notifications if not n.read)

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        country: Optional[str] = None
    ) -> List[Notification]:
        """
        Get notifications for a user with optional filters.

        This is the main method for retrieving notifications.
        It supports filtering by read status, type, and country.

        Args:
            user_id: User ID to get notifications for
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications
            notification_type: Filter by notification type
            country: Filter by country (for regulatory alerts)

        Returns:
            List of Notification objects sorted by creation date (newest first)
        """
        # Get user's notification queue
        user_notifications = self._notifications.get(user_id, [])

        # Filter by unread status if requested
        if unread_only:
            user_notifications = [
                n for n in user_notifications if not n.read
            ]

        # Filter by notification type if specified
        if notification_type:
            user_notifications = [
                n for n in user_notifications
                if n.notification_type == notification_type
            ]

        # Filter by country if specified (for regulatory alerts)
        if country:
            user_notifications = [
                n for n in user_notifications
                if not n.countries or country in n.countries
            ]

        # Sort by creation date (newest first)
        user_notifications.sort(
            key=lambda n: n.created_at, reverse=True
        )

        # Apply limit
        return user_notifications[:limit]

    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """
        Mark a specific notification as read.

        Args:
            user_id: User ID
            notification_id: ID of notification to mark as read

        Returns:
            True if marked successfully, False if not found
        """
        for notification in self._notifications.get(user_id, []):
            if notification.notification_id == notification_id:
                notification.read = True
                logger.debug(
                    f"Notification {notification_id} marked as read"
                )
                return True
        return False

    def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        count = 0
        for notification in self._notifications.get(user_id, []):
            if not notification.read:
                notification.read = True
                count += 1

        logger.info(
            f"Marked {count} notifications as read for {user_id}"
        )
        return count

    def set_user_preference(
        self,
        user_id: str,
        notification_type: str,
        enabled: bool
    ) -> None:
        """
        Set user notification preference.

        Args:
            user_id: User ID
            notification_type: Type of notification (e.g., "new_thread")
            enabled: Whether to enable this notification type
        """
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}
        self._user_preferences[user_id][notification_type] = enabled

        logger.debug(
            f"User {user_id} preference: {notification_type} = {enabled}"
        )

    def _should_notify(
        self,
        user_id: str,
        notification_type: str
    ) -> bool:
        """
        Check if user wants this notification type.

        Internal method to check user preferences before
        creating notifications.

        Args:
            user_id: User ID
            notification_type: Type of notification to check

        Returns:
            True if user wants this notification type
        """
        user_prefs = self._user_preferences.get(user_id, {})
        # Default to enabled if no preference set
        return user_prefs.get(notification_type, True)

    def _add_notification(
        self,
        user_id: str,
        notification: Notification
    ) -> None:
        """
        Add a notification to user's queue.

        Internal method for adding notifications to user queues.
        Maintains a maximum of 200 notifications per user to
        prevent unbounded growth.

        Args:
            user_id: User ID
            notification: Notification to add
        """
        # Initialize user queue if not exists
        if user_id not in self._notifications:
            self._notifications[user_id] = []

        # Add notification to queue
        self._notifications[user_id].append(notification)

        # Keep only last 200 notifications per user
        # This prevents unbounded memory growth
        if len(self._notifications[user_id]) > 200:
            self._notifications[user_id] = self._notifications[user_id][-200:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get notification system statistics.

        Returns aggregate metrics about notifications for
        monitoring and analytics.

        Returns:
            Dictionary with notification statistics
        """
        # Calculate total notifications across all users
        total = sum(
            len(notifs) for notifs in self._notifications.values()
        )

        # Calculate total unread notifications
        unread = sum(
            sum(1 for n in notifs if not n.read)
            for notifs in self._notifications.values()
        )

        return {
            "total_notifications": total,
            "unread_notifications": unread,
            "users_with_notifications": len(self._notifications),
        }


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.lekgotla.notification_engine import *'

__all__ = [
    # Notification type enumeration
    "NotificationType",
    # Notification data class
    "Notification",
    # Main notification engine class
    "NotificationEngine",
]
