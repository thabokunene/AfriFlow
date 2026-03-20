"""
Integration tests for Lekgotla Thread Lifecycle

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from datetime import datetime
from afriflow.lekgotla.thread_store import Thread, ThreadStore, ThreadStatus, Post, PostType
from afriflow.lekgotla.notification_engine import NotificationEngine, NotificationType
from afriflow.lekgotla.moderation import Moderator

def test_full_thread_lifecycle_integration():
    # 1. Initialize stores and engines
    store = ThreadStore()
    notifier = NotificationEngine()
    moderator = Moderator(client_golden_names=["Safaricom"])
    
    # 2. Create a new thread
    thread = Thread(
        thread_id="",
        title="Safaricom Expansion into Ethiopia",
        author_id="RM-1",
        author_name="Thabo",
        author_role="RM",
        author_country="ZA",
        created_at=datetime.now().isoformat(),
        status=ThreadStatus.OPEN,
        countries=["KE", "ET"],
        signal_type="EXPANSION",
    )
    store.create_thread(thread)
    assert thread.thread_id.startswith("THR-")
    
    # 3. Trigger notification for new thread
    notifications = notifier.notify_on_new_thread(thread)
    assert len(notifications) > 0
    assert notifications[0].notification_type == NotificationType.NEW_THREAD
    
    # 4. Post a reply (Specialist response)
    post_content = "The regulatory environment in Ethiopia for telcos is changing. Use the M-Pesa JV model."
    # Moderate post
    mod_result = moderator.scan_content(post_content)
    assert mod_result.approved is True
    
    post = Post(
        post_id="",
        thread_id=thread.thread_id,
        author_id="SPEC-1",
        author_name="Sarah",
        author_role="Specialist",
        author_country="KE",
        post_type=PostType.RESPONSE,
        content=post_content,
        created_at=datetime.now().isoformat(),
    )
    store.add_post(thread.thread_id, post)
    assert thread.reply_count == 1
    
    # 5. Upvote post
    store.upvote_post(post.post_id, "RM-1")
    assert post.upvotes == 1
    
    # 6. Mark best answer
    store.mark_best_answer(post.post_id)
    assert post.is_best_answer is True
    
    # 7. Record verified win
    store.mark_verified_win(post.post_id, 1000000.0)
    assert post.is_verified_win is True
