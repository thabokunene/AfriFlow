"""
Data Quality tests for Lekgotla

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from datetime import datetime
from afriflow.lekgotla.thread_store import ThreadStore, Thread, ThreadStatus, Post, PostType

def test_thread_post_referential_integrity():
    store = ThreadStore()
    thread = Thread(
        thread_id="THR-1",
        title="Test",
        author_id="A-1",
        author_name="N",
        author_role="R",
        author_country="C",
        created_at=datetime.now().isoformat(),
        status=ThreadStatus.OPEN,
    )
    store.create_thread(thread)
    
    post = Post(
        post_id="PST-1",
        thread_id="THR-1",
        author_id="A-2",
        author_name="N2",
        author_role="R",
        author_country="C",
        post_type=PostType.RESPONSE,
        content="C",
        created_at=datetime.now().isoformat(),
    )
    store.add_post("THR-1", post)
    
    # Check that post in store matches post in thread
    thread_in_store = store.search_threads("", {})[0]
    assert len(thread_in_store.posts) == 1
    assert thread_in_store.posts[0].post_id == "PST-1"
    assert thread_in_store.reply_count == 1

def test_missing_thread_raises_error():
    store = ThreadStore()
    post = Post(
        post_id="PST-1",
        thread_id="MISSING",
        author_id="A-2",
        author_name="N2",
        author_role="R",
        author_country="C",
        post_type=PostType.RESPONSE,
        content="C",
        created_at=datetime.now().isoformat(),
    )
    with pytest.raises(ValueError, match="Thread MISSING not found"):
        store.add_post("MISSING", post)
