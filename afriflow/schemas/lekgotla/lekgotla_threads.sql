-- =========================================================
-- AFRIFLOW: LEKGOTLA - THREAD TABLES
--
-- These tables store the conversation threads and posts
-- that form the collective intelligence layer.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================

CREATE TABLE IF NOT EXISTS lekgotla_threads (
    thread_id               VARCHAR(64)     NOT NULL,
    title                   VARCHAR(256)    NOT NULL,
    author_id               VARCHAR(64)     NOT NULL,
    author_name             VARCHAR(128)    NOT NULL,
    author_role             VARCHAR(64),
    author_country          VARCHAR(4),
    created_at              TIMESTAMP       NOT NULL,
    status                  VARCHAR(16)     NOT NULL,
    signal_type             VARCHAR(32),
    signal_id               VARCHAR(64),
    upvote_count            INTEGER         DEFAULT 0,
    reply_count             INTEGER         DEFAULT 0,
    view_count              INTEGER         DEFAULT 0,
    knowledge_card_id       VARCHAR(64),
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_posts (
    post_id                 VARCHAR(64)     NOT NULL,
    thread_id               VARCHAR(64)     NOT NULL,
    author_id               VARCHAR(64)     NOT NULL,
    author_name             VARCHAR(128)    NOT NULL,
    author_role             VARCHAR(64),
    author_country          VARCHAR(4),
    post_type               VARCHAR(16)     NOT NULL,
    content                 TEXT            NOT NULL,
    created_at              TIMESTAMP       NOT NULL,
    upvotes                 INTEGER         DEFAULT 0,
    is_best_answer          BOOLEAN         DEFAULT FALSE,
    is_verified_win         BOOLEAN         DEFAULT FALSE,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_upvotes (
    upvote_id               VARCHAR(64)     NOT NULL,
    item_id                 VARCHAR(64)     NOT NULL,
    item_type               VARCHAR(16)     NOT NULL, -- 'thread' or 'post'
    user_id                 VARCHAR(64)     NOT NULL,
    created_at              TIMESTAMP       NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_tags (
    tag_id                  VARCHAR(64)     NOT NULL,
    item_id                 VARCHAR(64)     NOT NULL,
    tag_name                VARCHAR(64)     NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_thread_signals (
    link_id                 VARCHAR(64)     NOT NULL,
    thread_id               VARCHAR(64)     NOT NULL,
    signal_id               VARCHAR(64)     NOT NULL,
    signal_type             VARCHAR(32)     NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);
