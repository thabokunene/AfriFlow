"""
Integration tests for Lekgotla Knowledge Card Graduation

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from datetime import datetime
from afriflow.lekgotla.thread_store import Thread, ThreadStatus, Post, PostType
from afriflow.lekgotla.knowledge_card_store import KnowledgeCardStore, CardCategory

def test_thread_to_card_graduation_lifecycle():
    # 1. Initialize stores
    card_store = KnowledgeCardStore()
    
    # 2. Setup a thread that meets graduation criteria
    thread = Thread(
        thread_id="THR-WINNER-1",
        title="Winning Strategy for Ghana Cocoa Exports",
        author_id="RM-GH",
        author_name="Kofi",
        author_role="RM",
        author_country="GH",
        created_at=datetime.now().isoformat(),
        status=ThreadStatus.OPEN,
        countries=["GH"],
        signal_type="SEASONAL_ADJUSTMENT",
    )
    
    post = Post(
        post_id="PST-WIN-1",
        thread_id="THR-WINNER-1",
        author_id="SPEC-FX",
        author_name="Sarah",
        author_role="FX Specialist",
        author_country="ZA",
        post_type=PostType.RESPONSE,
        content="Hedge at 60% of expected harvest volume using forward contracts.",
        created_at=datetime.now().isoformat(),
        is_best_answer=True,
        is_verified_win=True,
    )
    thread.posts.append(post)
    
    # 3. Graduate thread to card
    card = card_store.graduate_from_thread(thread)
    assert card.card_id == "KCD-THR-WINNER-1"
    assert card.category == CardCategory.PROVEN
    assert card.win_rate == 1.0
    
    # 4. Record new outcomes on the card
    card_store.record_outcome(card.card_id, won=True, revenue=2000000.0)
    assert card_store._cards[card.card_id].revenue_attributed == 2000000.0
