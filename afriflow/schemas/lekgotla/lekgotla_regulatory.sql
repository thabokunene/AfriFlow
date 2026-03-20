-- =========================================================
-- AFRIFLOW: LEKGOTLA - REGULATORY TABLES
--
-- These tables store regulatory alerts and compliance
-- review history.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================

CREATE TABLE IF NOT EXISTS lekgotla_regulatory_alerts (
    alert_id                VARCHAR(64)     NOT NULL,
    reference_number        VARCHAR(64),
    title                   VARCHAR(256)    NOT NULL,
    country                 VARCHAR(4)      NOT NULL,
    regulator               VARCHAR(128)    NOT NULL,
    severity                VARCHAR(16)     NOT NULL,
    effective_date          DATE            NOT NULL,
    summary                 TEXT            NOT NULL,
    posted_by               VARCHAR(64)     NOT NULL,
    posted_at               TIMESTAMP       NOT NULL,
    review_status           VARCHAR(16)     NOT NULL,
    reviewed_by             VARCHAR(64),
    reviewed_at             TIMESTAMP,
    affected_clients        INTEGER         DEFAULT 0,
    affected_value_zar      DECIMAL(18,2)   DEFAULT 0.0,
    knowledge_card_id       VARCHAR(64),
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_regulatory_impacts (
    impact_id               VARCHAR(64)     NOT NULL,
    alert_id                VARCHAR(64)     NOT NULL,
    domain                  VARCHAR(32)     NOT NULL,
    impact_description      VARCHAR(512),
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_compliance_reviews (
    review_id               VARCHAR(64)     NOT NULL,
    alert_id                VARCHAR(64)     NOT NULL,
    reviewer_id             VARCHAR(64)     NOT NULL,
    decision                VARCHAR(16)     NOT NULL,
    comments                TEXT,
    reviewed_at             TIMESTAMP       NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);
