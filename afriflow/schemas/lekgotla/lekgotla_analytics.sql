-- =========================================================
-- AFRIFLOW: LEKGOTLA - ANALYTICS TABLES
--
-- These tables store practitioner contributions and
-- platform health metrics.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================

CREATE TABLE IF NOT EXISTS lekgotla_contributions (
    contribution_id         VARCHAR(64)     NOT NULL,
    user_id                 VARCHAR(64)     NOT NULL,
    contribution_type       VARCHAR(32)     NOT NULL,
    points                  INTEGER         NOT NULL,
    reference_id            VARCHAR(64)     NOT NULL,
    timestamp               TIMESTAMP       NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_contributor_profiles (
    user_id                 VARCHAR(64)     NOT NULL,
    name                    VARCHAR(128)    NOT NULL,
    role                    VARCHAR(64),
    country                 VARCHAR(4),
    total_score             INTEGER         DEFAULT 0,
    posts_count             INTEGER         DEFAULT 0,
    cards_contributed       INTEGER         DEFAULT 0,
    verified_wins           INTEGER         DEFAULT 0,
    revenue_attributed_zar  DECIMAL(18,2)   DEFAULT 0.0,
    rank                    INTEGER,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);

CREATE TABLE IF NOT EXISTS lekgotla_onboarding_cohorts (
    cohort_id               VARCHAR(32)     NOT NULL,
    user_id                 VARCHAR(64)     NOT NULL,
    joined_date             DATE            NOT NULL,
    first_post_date         DATE,
    first_win_date          DATE,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date);
