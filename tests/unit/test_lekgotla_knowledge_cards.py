"""
Unit tests for Lekgotla Knowledge Card Store

DISCLAIMER: This project is not a sanctioned initiative
of Standard Bank Group, MTN, or any affiliated entity.
It is a demonstration of concept, domain knowledge,
and data engineering skill by Thabo Kunene.
"""

import pytest
from datetime import datetime
from afriflow.lekgotla.thread_store import Thread, ThreadStatus, Post, PostType
from afriflow.lekgotla.knowledge_card_store import (
    KnowledgeCardStore,
    KnowledgeCard,
    CardCategory,
)

@pytest.fixture
def card_store():
    return KnowledgeCardStore()

@pytest.fixture
def sample_thread():
    thread = Thread(
        thread_id="THR-1",
        title="Proven Strategy for CBN Repatriation",
        author_id="USER-1",
        author_name="Thabo",
        author_role="RM",
        author_country="ZA",
        created_at=datetime.now().isoformat(),
        status=ThreadStatus.OPEN,
        signal_type="CURRENCY_EVENT",
        countries=["NG"],
        products=["Forex"],
    )
    # Add a post that is a best answer and verified win
    p1 = Post(
        post_id="PST-1",
        thread_id="THR-1",
        author_id="USER-2",
        author_name="Sarah",
        author_role="Specialist",
        author_country="NG",
        post_type=PostType.RESPONSE,
        content="Use the newly approved CBN window for Tier 1 banks.",
        created_at=datetime.now().isoformat(),
        is_best_answer=True,
        is_verified_win=True,
    )
    thread.posts.append(p1)
    return thread

def test_card_graduation_from_thread(card_store, sample_thread):
    card = card_store.graduate_from_thread(sample_thread)
    assert card.card_id == "KCD-THR-1"
    assert card.category == CardCategory.PROVEN
    assert card.win_rate == 1.0
    assert "USER-2" in card.contributor_ids

def test_card_graduation_fails_without_best_answer(card_store, sample_thread):
    sample_thread.posts[0].is_best_answer = False
    with pytest.raises(ValueError, match="must have a best answer"):
        card_store.graduate_from_thread(sample_thread)

def test_card_creation_with_all_fields(card_store):
    card = KnowledgeCard(
        card_id="KCD-TEST",
        title="Test Card",
        subtitle="Subtitle",
        category=CardCategory.PRODUCT,
        signal_type="EXPANSION",
        countries=["ZA"],
        products=["Lending"],
        approach_steps=["Step 1"],
        avoid_items=["Avoid 1"],
        documents=[],
        source_thread_ids=[],
        contributor_ids=["USER-1"],
        win_rate=0.5,
        uses_count=10,
        revenue_attributed=1000000.0,
        rating=4.5,
        created_at=datetime.now().isoformat(),
        last_updated=datetime.now().isoformat(),
        last_validated=datetime.now().isoformat(),
    )
    created = card_store.create_card(card)
    assert created.card_id == "KCD-TEST"
    assert card_store.get_cards_by_signal("EXPANSION")[0].title == "Test Card"

def test_outcome_recording(card_store):
    card = KnowledgeCard(
        card_id="KCD-TEST",
        title="Test Card",
        subtitle="Subtitle",
        category=CardCategory.PRODUCT,
        signal_type="EXPANSION",
        countries=["ZA"],
        products=["Lending"],
        approach_steps=[],
        avoid_items=[],
        documents=[],
        source_thread_ids=[],
        contributor_ids=[],
        win_rate=0.0,
        uses_count=0,
        revenue_attributed=0.0,
        rating=0.0,
        created_at="",
        last_updated="",
        last_validated="",
    )
    card_store.create_card(card)
    card_store.record_outcome("KCD-TEST", won=True, revenue=500000.0)
    assert card_store._cards["KCD-TEST"].revenue_attributed == 500000.0
