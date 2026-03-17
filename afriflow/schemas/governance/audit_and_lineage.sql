-- =========================================================
-- AFRIFLOW: GOVERNANCE - AUDIT AND LINEAGE TABLES
--
-- Immutable audit trail and field level data lineage
-- required by POPIA, FAIS, Insurance Act, and
-- country specific regulations across 20 African markets.
--
-- Retention: 7 years per FAIS requirements
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


-- ---------------------------------------------------------
-- Data Lineage
-- Field level lineage from source to gold
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS governance_data_lineage (
    lineage_id              VARCHAR(64)     NOT NULL,
    run_id                  VARCHAR(64)     NOT NULL,
    run_timestamp           TIMESTAMP       NOT NULL,

    -- Source
    source_system           VARCHAR(64)     NOT NULL,
    source_domain           VARCHAR(16)     NOT NULL,
    source_table            VARCHAR(128)    NOT NULL,
    source_field            VARCHAR(128),
    source_record_id        VARCHAR(64),

    -- Destination
    target_layer            VARCHAR(16)     NOT NULL,
    target_table            VARCHAR(128)    NOT NULL,
    target_field            VARCHAR(128),
    target_record_id        VARCHAR(64),

    -- Transformation
    transformation_type     VARCHAR(32),
    transformation_logic    VARCHAR(512),
    dbt_model_name          VARCHAR(128),

    -- Data quality at this point
    dq_score_at_transform   DECIMAL(5,2),
    dq_issues               VARCHAR(256),

    -- Partitioning
    lineage_date            DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (lineage_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'governance',
    'layer' = 'audit',
    'retention_days' = '2555'
);


-- ---------------------------------------------------------
-- Access Audit Log
-- Who accessed what data and when
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS governance_access_log (
    access_id               VARCHAR(64)     NOT NULL,
    access_timestamp        TIMESTAMP       NOT NULL,

    -- Who
    user_id                 VARCHAR(64)     NOT NULL,
    user_role               VARCHAR(32),
    user_division           VARCHAR(32),
    user_country            VARCHAR(4),

    -- What
    resource_type           VARCHAR(32)     NOT NULL,
    resource_name           VARCHAR(128)    NOT NULL,
    resource_domain         VARCHAR(16),
    resource_layer          VARCHAR(16),

    -- How
    access_type             VARCHAR(16)     NOT NULL,
    query_text_hash         VARCHAR(64),
    row_count_returned      INTEGER,
    columns_accessed        VARCHAR(512),

    -- Client data accessed
    golden_ids_accessed     VARCHAR(1024),
    client_countries        VARCHAR(64),
    cross_border_access     BOOLEAN,

    -- Result
    access_granted          BOOLEAN         NOT NULL,
    denial_reason           VARCHAR(128),

    -- Partitioning
    access_date             DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (access_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'governance',
    'layer' = 'audit',
    'retention_days' = '2555'
);


-- ---------------------------------------------------------
-- Data Quality Metrics
-- Per table per run quality measurements
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS governance_data_quality (
    quality_id              VARCHAR(64)     NOT NULL,
    run_id                  VARCHAR(64)     NOT NULL,
    run_timestamp           TIMESTAMP       NOT NULL,

    -- Table
    domain                  VARCHAR(16)     NOT NULL,
    layer                   VARCHAR(16)     NOT NULL,
    table_name              VARCHAR(128)    NOT NULL,

    -- Counts
    total_records           BIGINT,
    valid_records           BIGINT,
    invalid_records         BIGINT,
    duplicate_records       BIGINT,
    null_key_records        BIGINT,

    -- Scores
    completeness_pct        DECIMAL(5,2),
    accuracy_pct            DECIMAL(5,2),
    timeliness_pct          DECIMAL(5,2),
    consistency_pct         DECIMAL(5,2),
    overall_dq_score        DECIMAL(5,2)    NOT NULL,

    -- Freshness
    latest_record_timestamp TIMESTAMP,
    staleness_minutes       INTEGER,
    freshness_sla_met       BOOLEAN,

    -- Contract compliance
    contract_name           VARCHAR(64),
    contract_met            BOOLEAN,
    contract_violations     VARCHAR(512),

    -- Partitioning
    quality_date            DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (quality_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'governance',
    'layer' = 'audit'
);
