-- =========================================================
-- AFRIFLOW: LEKGOTLA - KNOWLEDGE CARD TABLES
--
-- These tables store graduated knowledge cards and their
-- performance outcomes.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================

CREATE TABLE IF NOT EXISTS lekgotla_knowledge_cards (
    card_id                 VARCHAR(64)     NOT NULL,
    title                   VARCHAR(256)    NOT NULL,
    subtitle                VARCHAR(256),
    category                VARCHAR(32)     NOT NULL,
    signal_type             VARCHAR(32)     NOT NULL,
    win_rate                DECIMAL(5,4)    DEFAULT 0.0,
    uses_count              INTEGER         DEFAULT 0,
    revenue_attributed_zar  DECIMAL(18,2)   DEFAULT 0.0,
    rating                  DECIMAL(3,2)    DEFAULT 0.0,
    created_at              TIMESTAMP       NOT NULL,
    last_updated            TIMESTAMP       NOT NULL,
    last_validated          TIMESTAMP,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_card_usage (
    usage_id                VARCHAR(64)     NOT NULL,
    card_id                 VARCHAR(64)     NOT NULL,
    user_id                 VARCHAR(64)     NOT NULL,
    used_at                 TIMESTAMP       NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_card_outcomes (
    outcome_id              VARCHAR(64)     NOT NULL,
    card_id                 VARCHAR(64)     NOT NULL,
    user_id                 VARCHAR(64)     NOT NULL,
    won                     BOOLEAN         NOT NULL,
    revenue_zar             DECIMAL(18,2),
    recorded_at             TIMESTAMP       NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_card_documents (
    doc_id                  VARCHAR(64)     NOT NULL,
    card_id                 VARCHAR(64)     NOT NULL,
    doc_name                VARCHAR(256)    NOT NULL,
    doc_type                VARCHAR(32),
    doc_url                 VARCHAR(512)    NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);
