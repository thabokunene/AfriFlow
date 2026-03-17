-- =========================================================
-- AFRIFLOW: SILVER LAYER - CIB
--
-- Cleaned, validated, and enriched CIB data.
-- We apply schema validation, null handling, deduplication,
-- type casting, and basic enrichment (country name lookup,
-- currency standardisation, corridor identification).
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS silver_cib_payments (
    -- Record identity
    payment_id              VARCHAR(64)     NOT NULL,
    message_id              VARCHAR(64)     NOT NULL,
    message_type            VARCHAR(32)     NOT NULL,

    -- Debtor (cleaned and validated)
    debtor_name             VARCHAR(256)    NOT NULL,
    debtor_name_normalised  VARCHAR(256)    NOT NULL,
    debtor_account           VARCHAR(64),
    debtor_bic              VARCHAR(16),
    debtor_country_code     VARCHAR(4)      NOT NULL,
    debtor_country_name     VARCHAR(64),
    debtor_client_id        VARCHAR(64),
    debtor_region           VARCHAR(32),

    -- Creditor (cleaned and validated)
    creditor_name           VARCHAR(256)    NOT NULL,
    creditor_name_normalised VARCHAR(256)   NOT NULL,
    creditor_account        VARCHAR(64),
    creditor_bic            VARCHAR(16),
    creditor_country_code   VARCHAR(4)      NOT NULL,
    creditor_country_name   VARCHAR(64),
    creditor_region         VARCHAR(32),

    -- Amount (typed and standardised)
    amount                  DECIMAL(18,2)   NOT NULL,
    currency                VARCHAR(4)      NOT NULL,
    amount_zar              DECIMAL(18,2)   NOT NULL,
    fx_rate_to_zar          DECIMAL(18,8),

    -- Corridor (derived)
    corridor                VARCHAR(16)     NOT NULL,
    corridor_name           VARCHAR(128),
    is_cross_border         BOOLEAN         NOT NULL,
    is_intra_africa         BOOLEAN         NOT NULL,
    is_africa_to_world      BOOLEAN,
    is_world_to_africa      BOOLEAN,

    -- Payment classification
    payment_type            VARCHAR(32),
    payment_category        VARCHAR(64),

    -- Dates (typed)
    business_date           DATE            NOT NULL,
    value_date              DATE,
    settlement_date         DATE,
    creation_timestamp      TIMESTAMP,

    -- Data quality
    dq_score                DECIMAL(5,2)    NOT NULL,
    dq_issues               VARCHAR(512),
    is_duplicate            BOOLEAN         NOT NULL DEFAULT FALSE,
    dedup_group_id          VARCHAR(64),

    -- Lineage
    source_bronze_id        VARCHAR(64)     NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,
    dbt_run_id              VARCHAR(64),

    -- Partitioning
    business_date_partition DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (business_date_partition)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'silver'
);


CREATE TABLE IF NOT EXISTS silver_cib_trade_finance (
    facility_id             VARCHAR(64)     NOT NULL,
    facility_type           VARCHAR(32)     NOT NULL,
    client_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256)    NOT NULL,
    client_name_normalised  VARCHAR(256)    NOT NULL,

    beneficiary_name        VARCHAR(256),
    beneficiary_country     VARCHAR(4),

    facility_amount         DECIMAL(18,2)   NOT NULL,
    facility_currency       VARCHAR(4)      NOT NULL,
    facility_amount_zar     DECIMAL(18,2)   NOT NULL,
    utilised_amount         DECIMAL(18,2),
    utilisation_pct         DECIMAL(5,2),

    issue_date              DATE,
    expiry_date             DATE,
    days_to_expiry          INTEGER,

    facility_status         VARCHAR(32)     NOT NULL,

    corridor                VARCHAR(16),
    is_cross_border         BOOLEAN,

    -- Lineage
    source_bronze_id        VARCHAR(64)     NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    -- Partitioning
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'silver'
);
