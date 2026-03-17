-- =========================================================
-- AFRIFLOW: SILVER LAYER - INSURANCE
--
-- Cleaned insurance policy and claims data with derived
-- coverage gap analysis per country.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS silver_insurance_policies (
    policy_id               VARCHAR(64)     NOT NULL,
    policy_type             VARCHAR(64)     NOT NULL,
    product_name            VARCHAR(128),

    client_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256)    NOT NULL,
    client_name_normalised  VARCHAR(256)   NOT NULL,
    client_country          VARCHAR(4)      NOT NULL,

    coverage_type           VARCHAR(64),
    coverage_country        VARCHAR(4),
    sum_insured             DECIMAL(18,2),
    sum_insured_zar         DECIMAL(18,2),
    excess_amount           DECIMAL(18,2),

    premium_annual          DECIMAL(18,2),
    premium_annual_zar      DECIMAL(18,2),
    premium_currency        VARCHAR(4),
    premium_status          VARCHAR(32),

    inception_date          DATE,
    expiry_date             DATE,
    days_to_expiry          INTEGER,
    is_expired              BOOLEAN,
    is_lapsing_90d          BOOLEAN,

    policy_status           VARCHAR(32)     NOT NULL,

    -- Coverage adequacy (derived by comparing
    -- sum insured against known CIB asset values)
    coverage_gap            BOOLEAN,
    coverage_gap_amount_zar DECIMAL(18,2),

    -- Lineage
    source_bronze_id        VARCHAR(64)     NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'insurance',
    'layer' = 'silver'
);


CREATE TABLE IF NOT EXISTS silver_insurance_claims (
    claim_id                VARCHAR(64)     NOT NULL,
    policy_id               VARCHAR(64)     NOT NULL,
    client_id               VARCHAR(64)     NOT NULL,

    claim_type              VARCHAR(64),
    loss_date               DATE,
    notification_date       DATE,
    loss_country            VARCHAR(4),
    loss_description        VARCHAR(1024),

    claim_amount            DECIMAL(18,2),
    claim_amount_zar        DECIMAL(18,2),
    reserve_amount_zar      DECIMAL(18,2),
    paid_amount_zar         DECIMAL(18,2),
    recovery_amount_zar     DECIMAL(18,2),

    claim_status            VARCHAR(32)     NOT NULL,
    days_open               INTEGER,
    fraud_flag              BOOLEAN,

    source_bronze_id        VARCHAR(64)     NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'insurance',
    'layer' = 'silver'
);
