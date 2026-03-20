"""
Lekgotla Thread Store

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

logger = get_logger("lekgotla.thread_store")


class ThreadStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class PostType(Enum):
    CHALLENGE = "CHALLENGE"
    RESPONSE = "RESPONSE"
    REGULATORY = "REGULATORY"
    CONTEXT = "CONTEXT"
    QUESTION = "QUESTION"


@dataclass
class Post:
    post_id: str
    thread_id: str
    author_id: str
    author_name: str
    author_role: str
    author_country: str
    post_type: PostType
    content: str
    created_at: str
    upvotes: int = 0
    is_best_answer: bool = False
    is_verified_win: bool = False
    attachments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "post_id": self.post_id,
            "thread_id": self.thread_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_role": self.author_role,
            "author_country": self.author_country,
            "post_type": self.post_type.value,
            "content": self.content,
            "created_at": self.created_at,
            "upvotes": self.upvotes,
            "is_best_answer": self.is_best_answer,
            "is_verified_win": self.is_verified_win,
            "attachments": self.attachments,
            "tags": self.tags,
        }


@dataclass
class Thread:
    thread_id: str
    title: str
    author_id: str
    author_name: str
    author_role: str
    author_country: str
    created_at: str
    status: ThreadStatus
    signal_type: Optional[str] = None
    signal_id: Optional[str] = None
    countries: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    posts: List[Post] = field(default_factory=list)
    upvote_count: int = 0
    reply_count: int = 0
    view_count: int = 0
    knowledge_card_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "title": self.title,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_role": self.author_role,
            "author_country": self.author_country,
            "created_at": self.created_at,
            "status": self.status.value,
            "signal_type": self.signal_type,
            "signal_id": self.signal_id,
            "countries": self.countries,
            "products": self.products,
            "tags": self.tags,
            "posts": [p.to_dict() for p in self.posts],
            "upvote_count": self.upvote_count,
            "reply_count": self.reply_count,
            "view_count": self.view_count,
            "knowledge_card_id": self.knowledge_card_id,
        }


class ThreadStore:
    def __init__(self) -> None:
        self._threads: Dict[str, Thread] = {}
        self._posts: Dict[str, Post] = {}
        logger.info("Lekgotla ThreadStore initialized")

    def create_thread(self, thread: Thread) -> Thread:
        if not thread.thread_id:
            thread.thread_id = f"THR-{uuid.uuid4().hex[:8].upper()}"
        self._threads[thread.thread_id] = thread
        logger.info(f"Thread created: {thread.thread_id}")
        return thread

    def add_post(self, thread_id: str, post: Post) -> Post:
        if thread_id not in self._threads:
            raise ValueError(f"Thread {thread_id} not found")
        if not post.post_id:
            post.post_id = f"PST-{uuid.uuid4().hex[:8].upper()}"
        self._threads[thread_id].posts.append(post)
        self._threads[thread_id].reply_count += 1
        self._posts[post.post_id] = post
        logger.info(f"Post added to thread {thread_id}: {post.post_id}")
        return post

    def upvote_post(self, post_id: str, user_id: str) -> int:
        if post_id not in self._posts:
            raise ValueError(f"Post {post_id} not found")
        self._posts[post_id].upvotes += 1
        return self._posts[post_id].upvotes

    def mark_best_answer(self, post_id: str) -> None:
        if post_id not in self._posts:
            raise ValueError(f"Post {post_id} not found")
        self._posts[post_id].is_best_answer = True
        logger.info(f"Post {post_id} marked as best answer")

    def mark_verified_win(self, post_id: str, revenue: float) -> None:
        if post_id not in self._posts:
            raise ValueError(f"Post {post_id} not found")
        self._posts[post_id].is_verified_win = True
        logger.info(f"Post {post_id} marked as verified win. Revenue: {revenue}")

    def search_threads(self, query: str, filters: Dict) -> List[Thread]:
        results = list(self._threads.values())
        if query:
            q = query.lower()
            results = [
                t for t in results
                if q in t.title.lower() or any(q in p.content.lower() for p in t.posts)
            ]
        # Basic filtering logic
        for key, value in filters.items():
            if key == "country":
                results = [t for t in results if value in t.countries]
            elif key == "signal_type":
                results = [t for t in results if t.signal_type == value]
        return results

    def get_threads_by_signal(self, signal_type: str, country: str) -> List[Thread]:
        return [
            t for t in self._threads.values()
            if t.signal_type == signal_type and country in t.countries
        ]

    def get_threads_by_country(self, country: str) -> List[Thread]:
        return [t for t in self._threads.values() if country in t.countries]

    def get_unanswered(self, min_age_days: int) -> List[Thread]:
        unanswered = []
        for t in self._threads.values():
            if not any(p.is_best_answer for p in t.posts):
                unanswered.append(t)
        return unanswered

    def archive_stale(self, days: int) -> int:
        return 0
