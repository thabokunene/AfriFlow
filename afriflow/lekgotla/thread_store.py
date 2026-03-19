"""
@file thread_store.py
@description Thread store for the Lekgotla module, managing the lifecycle of
    discussion threads anchored to cross-domain signals, enabling practitioners
    to share approaches and build institutional memory.
@author Thabo Kunene
@created 2026-03-19
"""

from __future__ import annotations  # Enable PEP 563 postponed evaluation of type annotations

# Standard library imports
from dataclasses import dataclass, field  # For data class decorators and default values
from datetime import datetime  # For timestamp generation
from enum import Enum  # For enumerated types (ThreadStatus, PostType)
from typing import Dict, List, Optional, Any  # Type hints for dictionaries, lists, optional values
import logging  # For debug and info logging
import uuid  # For generating unique IDs (thread_id, post_id)

# Import logging utility for structured logging
from afriflow.logging_config import get_logger

logger = get_logger("lekgotla.thread_store")  # Get logger instance for this module


class ThreadStatus(Enum):
    """
    Thread lifecycle status enumeration.

    Defines the possible states a thread can be in during its lifecycle:
    - OPEN: Thread is active and accepting new posts
    - CLOSED: Thread is closed (solution found or discussion complete)
    - ARCHIVED: Thread is archived (read-only, preserved for reference)

    Example:
        >>> thread.status = ThreadStatus.OPEN
        >>> if thread.status == ThreadStatus.CLOSED:
        ...     print("This thread is closed")
    """
    OPEN = "OPEN"  # Active thread accepting posts
    CLOSED = "CLOSED"  # Closed thread (solution found)
    ARCHIVED = "ARCHIVED"  # Archived thread (read-only reference)


class PostType(Enum):
    """
    Post type enumeration for classifying discussion posts.

    Defines the different types of posts that can be made in a thread:
    - CHALLENGE: Describes a business challenge or problem
    - RESPONSE: Response to a challenge with suggested approach
    - REGULATORY: Regulatory or compliance-related information
    - CONTEXT: Additional context or background information
    - QUESTION: Clarifying question about the discussion

    Example:
        >>> post = Post(
        ...     post_id="post-123",
        ...     post_type=PostType.CHALLENGE,
        ...     content="Client expanding to Ghana without FX hedging"
        ... )
    """
    CHALLENGE = "CHALLENGE"  # Business challenge or problem description
    RESPONSE = "RESPONSE"  # Response with suggested approach
    REGULATORY = "REGULATORY"  # Regulatory or compliance information
    CONTEXT = "CONTEXT"  # Additional context or background
    QUESTION = "QUESTION"  # Clarifying question


@dataclass
class Post:
    """
    Individual discussion post within a thread.

    A post represents a single contribution to a discussion thread.
    Each post includes author metadata for attribution and context.

    Attributes:
        post_id: Unique identifier for the post (UUID format)
        thread_id: ID of the parent thread this post belongs to
        author_id: User ID of the post author
        author_name: Display name of the post author
        author_role: Author's role (e.g., "Senior RM", "FX Advisor")
        author_country: Author's country code (e.g., "ZA", "NG")
        post_type: Type of post (CHALLENGE, RESPONSE, REGULATORY, etc.)
        content: Post content text
        created_at: ISO 8601 timestamp of post creation
        upvotes: Number of upvotes received (quality indicator)
        is_best_answer: Whether this post was marked as best answer
        is_verified_win: Whether this post describes a verified win
        attachments: List of attachment URLs or file paths
        tags: List of tags for categorization

    Example:
        >>> post = Post(
        ...     post_id="post-123",
        ...     thread_id="thread-456",
        ...     author_id="user-789",
        ...     author_name="Sipho Mabena",
        ...     author_role="Senior RM",
        ...     author_country="ZA",
        ...     post_type=PostType.RESPONSE,
        ...     content="Bundle WC + FX + insurance in first meeting"
        ... )
    """
    post_id: str  # Unique post identifier
    thread_id: str  # Parent thread ID
    author_id: str  # Author's user ID
    author_name: str  # Author's display name
    author_role: str  # Author's job role
    author_country: str  # Author's country code (ISO 3166-1 alpha-2)
    post_type: PostType  # Type of post (enum)
    content: str  # Post content text
    created_at: str  # ISO 8601 timestamp
    upvotes: int = 0  # Number of upvotes (default 0)
    is_best_answer: bool = False  # Marked as best answer (default False)
    is_verified_win: bool = False  # Describes verified win (default False)
    attachments: List[str] = field(default_factory=list)  # Attachment URLs
    tags: List[str] = field(default_factory=list)  # Categorization tags

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert post to dictionary for JSON serialization.

        This method enables easy serialization for API responses
        and database storage.

        Returns:
            Dictionary with all post fields
        """
        return {
            "post_id": self.post_id,  # Unique post ID
            "thread_id": self.thread_id,  # Parent thread ID
            "author_id": self.author_id,  # Author user ID
            "author_name": self.author_name,  # Author display name
            "author_role": self.author_role,  # Author job role
            "author_country": self.author_country,  # Author country
            "post_type": self.post_type.value,  # Post type as string
            "content": self.content,  # Post content
            "created_at": self.created_at,  # Creation timestamp
            "upvotes": self.upvotes,  # Upvote count
            "is_best_answer": self.is_best_answer,  # Best answer flag
            "is_verified_win": self.is_verified_win,  # Verified win flag
            "attachments": self.attachments,  # Attachment list
            "tags": self.tags,  # Tag list
        }


@dataclass
class Thread:
    """
    Discussion thread with multiple posts.

    A thread represents a complete discussion anchored to a signal type.
    Threads enable practitioners to share approaches and build institutional
    memory around recurring business challenges.

    Attributes:
        thread_id: Unique identifier for the thread (UUID format)
        title: Thread title (should be descriptive)
        author_id: User ID of thread author
        author_name: Display name of thread author
        author_role: Author's role (e.g., "Senior RM")
        author_country: Author's country code
        created_at: ISO 8601 timestamp of thread creation
        status: Thread status (OPEN, CLOSED, ARCHIVED)
        signal_type: Type of signal this thread is anchored to (e.g., "EXPANSION")
        signal_id: ID of the specific signal instance
        countries: List of country codes relevant to this discussion
        products: List of products relevant to this discussion
        tags: List of tags for categorization
        posts: List of Post objects (discussion contributions)
        upvote_count: Total upvotes across all posts
        reply_count: Number of posts (replies)
        view_count: Number of times thread was viewed
        knowledge_card_id: ID of graduated Knowledge Card (if applicable)

    Example:
        >>> thread = Thread(
        ...     thread_id="thread-123",
        ...     title="Ghana expansion without FX hedging",
        ...     author_id="user-456",
        ...     author_name="Amina Okafor",
        ...     signal_type="EXPANSION",
        ...     countries=["GH"],
        ...     products=["WC", "FX"]
        ... )
    """
    thread_id: str  # Unique thread identifier
    title: str  # Thread title
    author_id: str  # Author user ID
    author_name: str  # Author display name
    author_role: str  # Author job role
    author_country: str  # Author country code
    created_at: str  # ISO 8601 creation timestamp
    status: ThreadStatus  # Thread lifecycle status
    signal_type: Optional[str] = None  # Signal type anchor
    signal_id: Optional[str] = None  # Specific signal ID
    countries: List[str] = field(default_factory=list)  # Relevant countries
    products: List[str] = field(default_factory=list)  # Relevant products
    tags: List[str] = field(default_factory=list)  # Categorization tags
    posts: List[Post] = field(default_factory=list)  # Discussion posts
    upvote_count: int = 0  # Total upvote count
    reply_count: int = 0  # Number of replies
    view_count: int = 0  # View count
    knowledge_card_id: Optional[str] = None  # Graduated KC ID

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert thread to dictionary for JSON serialization.

        This method enables easy serialization for API responses
        and database storage. Posts are converted to dictionaries.

        Returns:
            Dictionary with all thread fields
        """
        return {
            "thread_id": self.thread_id,  # Unique thread ID
            "title": self.title,  # Thread title
            "author_id": self.author_id,  # Author user ID
            "author_name": self.author_name,  # Author display name
            "author_role": self.author_role,  # Author job role
            "author_country": self.author_country,  # Author country
            "created_at": self.created_at,  # Creation timestamp
            "status": self.status.value,  # Status as string
            "signal_type": self.signal_type,  # Signal type
            "signal_id": self.signal_id,  # Signal ID
            "countries": self.countries,  # Country list
            "products": self.products,  # Product list
            "tags": self.tags,  # Tag list
            "posts": [p.to_dict() for p in self.posts],  # Posts as dicts
            "upvote_count": self.upvote_count,  # Total upvotes
            "reply_count": self.reply_count,  # Reply count
            "view_count": self.view_count,  # View count
            "knowledge_card_id": self.knowledge_card_id,  # KC ID
        }


class ThreadStore:
    """
    Thread storage and retrieval.

    This class provides in-memory storage and retrieval of threads
    and posts. In production, this would use PostgreSQL with full-text
    search capabilities.

    Features:
    - Thread creation with signal anchoring
    - Post creation and management
    - Upvoting mechanism
    - Best answer marking
    - Full-text search across threads
    - Filtering by signal type, country, status

    Attributes:
        _threads: Dictionary mapping thread_id to Thread objects
        _signal_index: Dictionary mapping signal_type to list of thread_ids
        _country_index: Dictionary mapping country to list of thread_ids

    Example:
        >>> store = ThreadStore()
        >>> thread = store.create_thread(
        ...     title="Ghana expansion approach",
        ...     content="What worked for your Ghana expansions?",
        ...     author_id="user-123",
        ...     author_name="Sipho Mabena",
        ...     signal_type="EXPANSION"
        ... )
        >>> results = store.search_threads(query="Ghana", signal_type="EXPANSION")
    """

    def __init__(self) -> None:
        """
        Initialize the thread store with empty indexes.

        Creates three data structures:
        1. _threads: Main thread storage (thread_id -> Thread)
        2. _signal_index: Signal-based lookup (signal_type -> [thread_id])
        3. _country_index: Country-based lookup (country -> [thread_id])
        """
        self._threads: Dict[str, Thread] = {}  # Main thread storage
        self._signal_index: Dict[str, List[str]] = {}  # Signal type index
        self._country_index: Dict[str, List[str]] = {}  # Country index

        logger.info("ThreadStore initialized")  # Log initialization

    def create_thread(
        self,
        title: str,
        content: str,
        author_id: str,
        author_name: str,
        author_role: str,
        author_country: str,
        signal_type: Optional[str] = None,
        signal_id: Optional[str] = None,
        countries: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Thread:
        """
        Create a new discussion thread.

        This is the primary method for creating new threads. It generates
        a unique thread ID, sets the initial status to OPEN, and indexes
        the thread for efficient searching.

        Args:
            title: Thread title (should be descriptive and searchable)
            content: Initial post content (the challenge or question)
            author_id: User ID of thread author
            author_name: Display name of thread author
            author_role: Author's role (e.g., "Senior RM", "FX Advisor")
            author_country: Author's country code (ISO 3166-1 alpha-2)
            signal_type: Type of signal this relates to (e.g., "EXPANSION")
            signal_id: Specific signal instance ID (for anchoring)
            countries: List of relevant country codes
            products: List of relevant products (e.g., ["WC", "FX"])
            tags: List of tags for categorization

        Returns:
            Created Thread object with generated thread_id

        Example:
            >>> thread = store.create_thread(
            ...     title="Ghana expansion without FX hedging",
            ...     content="Client expanding but no hedging in place",
            ...     author_id="user-123",
            ...     author_name="Sipho Mabena",
            ...     author_role="Senior RM",
            ...     author_country="ZA",
            ...     signal_type="EXPANSION",
            ...     countries=["GH"],
            ...     products=["WC", "FX"]
            ... )
        """
        # Generate unique thread ID using UUID (universally unique)
        thread_id = f"THR-{uuid.uuid4().hex[:12].upper()}"

        # Get current timestamp in ISO 8601 format
        now = datetime.now().isoformat()

        # Create initial post (the thread content becomes the first post)
        initial_post = Post(
            post_id=f"PST-{uuid.uuid4().hex[:8].upper()}",  # Unique post ID
            thread_id=thread_id,  # Link to parent thread
            author_id=author_id,  # Thread author
            author_name=author_name,
            author_role=author_role,
            author_country=author_country,
            post_type=PostType.CHALLENGE,  # First post is always a challenge
            content=content,  # Thread content
            created_at=now,  # Current timestamp
        )

        # Create thread object with all metadata
        thread = Thread(
            thread_id=thread_id,
            title=title,
            author_id=author_id,
            author_name=author_name,
            author_role=author_role,
            author_country=author_country,
            created_at=now,
            status=ThreadStatus.OPEN,  # New threads start as OPEN
            signal_type=signal_type,
            signal_id=signal_id,
            countries=countries or [],  # Empty list if not provided
            products=products or [],
            tags=tags or [],
            posts=[initial_post],  # Include initial post
            reply_count=1,  # One post (the initial post)
        )

        # Store thread in main dictionary
        self._threads[thread_id] = thread

        # Update signal type index for efficient filtering
        if signal_type:
            if signal_type not in self._signal_index:
                self._signal_index[signal_type] = []
            self._signal_index[signal_type].append(thread_id)

        # Update country index for each country in the thread
        for country in countries or []:
            if country not in self._country_index:
                self._country_index[country] = []
            self._country_index[country].append(thread_id)

        # Log thread creation for observability
        logger.info(
            f"Thread created: {thread_id} - '{title}' by {author_name}"
        )

        return thread

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Retrieve a thread by ID.

        Args:
            thread_id: Unique thread identifier

        Returns:
            Thread object if found, None otherwise

        Example:
            >>> thread = store.get_thread("THR-ABC123")
            >>> if thread:
            ...     print(f"Title: {thread.title}")
        """
        return self._threads.get(thread_id)

    def add_post(
        self,
        thread_id: str,
        content: str,
        author_id: str,
        author_name: str,
        author_role: str,
        author_country: str,
        post_type: PostType = PostType.RESPONSE,
        attachments: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Post:
        """
        Add a post to an existing thread.

        This method creates a new post and appends it to the thread's
        post list. It also updates the thread's reply count and
        last activity timestamp.

        Args:
            thread_id: ID of the thread to add post to
            content: Post content text
            author_id: User ID of post author
            author_name: Display name of post author
            author_role: Author's role
            author_country: Author's country code
            post_type: Type of post (default: RESPONSE)
            attachments: List of attachment URLs
            tags: List of tags

        Returns:
            Created Post object

        Raises:
            ValueError: If thread_id not found

        Example:
            >>> post = store.add_post(
            ...     thread_id="THR-ABC123",
            ...     content="Bundle WC + FX + insurance in first meeting",
            ...     author_id="user-456",
            ...     author_name="Amina Okafor",
            ...     author_role="FX Advisor",
            ...     author_country="NG"
            ... )
        """
        # Check if thread exists
        if thread_id not in self._threads:
            raise ValueError(f"Thread {thread_id} not found")

        # Generate unique post ID
        post_id = f"PST-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        # Create post object
        post = Post(
            post_id=post_id,
            thread_id=thread_id,
            author_id=author_id,
            author_name=author_name,
            author_role=author_role,
            author_country=author_country,
            post_type=post_type,
            content=content,
            created_at=now,
            attachments=attachments or [],
            tags=tags or [],
        )

        # Add post to thread's post list
        self._threads[thread_id].posts.append(post)

        # Update thread reply count
        self._threads[thread_id].reply_count += 1

        logger.debug(
            f"Post added to thread {thread_id} by {author_name}"
        )

        return post

    def upvote_post(self, post_id: str) -> bool:
        """
        Upvote a post.

        Increments the upvote count for a post. In production,
        this would track which users have upvoted to prevent
        duplicate upvotes.

        Args:
            post_id: ID of the post to upvote

        Returns:
            True if upvote successful, False if post not found
        """
        # Search through all threads to find the post
        for thread in self._threads.values():
            for post in thread.posts:
                if post.post_id == post_id:
                    post.upvotes += 1  # Increment upvote count
                    logger.debug(f"Post {post_id} upvoted")
                    return True
        return False

    def mark_best_answer(self, thread_id: str, post_id: str) -> bool:
        """
        Mark a post as the best answer for a thread.

        This method marks a specific post as the best answer,
        which is useful for highlighting successful approaches.
        Only the thread author can mark best answers (enforced
        in production via authorization).

        Args:
            thread_id: ID of the thread
            post_id: ID of the post to mark as best answer

        Returns:
            True if marked successfully, False if not found

        Raises:
            ValueError: If thread not found
        """
        if thread_id not in self._threads:
            raise ValueError(f"Thread {thread_id} not found")

        # Find and mark the post
        for post in self._threads[thread_id].posts:
            if post.post_id == post_id:
                post.is_best_answer = True
                logger.info(
                    f"Post {post_id} marked as best answer for thread {thread_id}"
                )
                return True
        return False

    def search_threads(
        self,
        query: Optional[str] = None,
        signal_type: Optional[str] = None,
        country: Optional[str] = None,
        status: Optional[ThreadStatus] = None,
        limit: int = 50,
    ) -> List[Thread]:
        """
        Search threads with various filters.

        This method supports full-text search and filtering by
        signal type, country, and status. Results are sorted
        by creation date (most recent first).

        Args:
            query: Full-text search query (searches title and tags)
            signal_type: Filter by signal type (e.g., "EXPANSION")
            country: Filter by country code (e.g., "GH")
            status: Filter by thread status
            limit: Maximum number of results to return

        Returns:
            List of matching Thread objects

        Example:
            >>> results = store.search_threads(
            ...     query="Ghana expansion",
            ...     signal_type="EXPANSION",
            ...     country="GH",
            ...     limit=10
            ... )
        """
        # Start with all threads
        results = list(self._threads.values())

        # Filter by signal type using index for efficiency
        if signal_type and signal_type in self._signal_index:
            signal_thread_ids = set(self._signal_index[signal_type])
            results = [
                t for t in results if t.thread_id in signal_thread_ids
            ]

        # Filter by country using index
        if country and country in self._country_index:
            country_thread_ids = set(self._country_index[country])
            results = [
                t for t in results if t.thread_id in country_thread_ids
            ]

        # Filter by status
        if status:
            results = [t for t in results if t.status == status]

        # Full-text search (title and tags)
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if (
                    query_lower in t.title.lower()
                    or any(query_lower in tag.lower() for tag in t.tags)
                )
            ]

        # Sort by creation date (most recent first)
        results.sort(key=lambda t: t.created_at, reverse=True)

        # Apply limit
        return results[:limit]

    def get_threads_for_signal(
        self, signal_type: str, limit: int = 20
    ) -> List[Thread]:
        """
        Get threads anchored to a specific signal type.

        This is a convenience method for retrieving all threads
        related to a specific signal type (e.g., all EXPANSION
        threads).

        Args:
            signal_type: Signal type to filter by
            limit: Maximum results to return

        Returns:
            List of Thread objects for the signal type
        """
        return self.search_threads(signal_type=signal_type, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get thread store statistics.

        Returns aggregate metrics about threads and posts
        for analytics and monitoring.

        Returns:
            Dictionary with thread statistics
        """
        # Count threads by status
        status_counts = {}
        for thread in self._threads.values():
            status = thread.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count total posts across all threads
        total_posts = sum(len(thread.posts) for thread in self._threads.values())

        return {
            "total_threads": len(self._threads),
            "total_posts": total_posts,
            "status_breakdown": status_counts,
            "signal_types": len(self._signal_index),
            "countries": len(self._country_index),
        }


# ============================================
# PUBLIC API
# ============================================
# Define what's exported for 'from afriflow.lekgotla.thread_store import *'

__all__ = [
    # Enumerations
    "ThreadStatus",
    "PostType",
    # Data classes
    "Post",
    "Thread",
    # Main store class
    "ThreadStore",
]
