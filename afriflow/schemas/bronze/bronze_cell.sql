-- =========================================================
-- AFRIFLOW: BRONZE LAYER - CELL NETWORK (MTN Partnership)
--
-- Raw ingested data from MTN cell network systems including
-- SIM activations, mobile money transactions, usage patterns,
-- and airtime purchases.
--
-- This is the domain that makes AfriFlow uniquely African.
-- No Western or East Asian banking platform has access to
-- telco data as a first class banking signal.
--
-- Source protocols: CDR (ASN.1), MoMo API, GSMA TAP3
--
-- IMPORTANT: Cell data arrives in three integration tiers:
-- Tier 1: Real time Kafka stream (ZA, KE, NG)
-- Tier 2: Daily batch SFTP (GH, TZ, UG)
-- Tier 3: Monthly aggregated report (CD, MZ, others)
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS bronze_cell_usage (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128),
    kafka_partition         INTEGER,
    kafka_offset            BIGINT,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,
    integration_tier        VARCHAR(8)      NOT NULL,

    -- Corporate client linkage
    corporate_client_id     VARCHAR(64),
    corporate_account_ref   VARCHAR(64),

    -- SIM identity (anonymised for privacy)
    sim_hash                VARCHAR(64),
    msisdn_hash             VARCHAR(64),
    imsi_hash               VARCHAR(64),
    sim_type                VARCHAR(16),
    device_type             VARCHAR(32),

    -- Usage aggregation (per SIM per day)
    usage_date              VARCHAR(16),
    usage_country           VARCHAR(4),
    usage_city              VARCHAR(128),
    usage_region            VARCHAR(128),

    -- Voice
    voice_minutes_in        DECIMAL(10,2),
    voice_minutes_out       DECIMAL(10,2),
    voice_calls_in          INTEGER,
    voice_calls_out         INTEGER,

    -- Data
    data_usage_mb           DECIMAL(12,2),
    data_sessions           INTEGER,

    -- SMS
    sms_sent                INTEGER,
    sms_received            INTEGER,

    -- USSD (Africa specific: banking via USSD)
    ussd_sessions           INTEGER,
    ussd_banking_sessions   INTEGER,

    -- Revenue
    revenue_voice           DECIMAL(10,2),
    revenue_data            DECIMAL(10,2),
    revenue_sms             DECIMAL(10,2),
    revenue_total           DECIMAL(10,2),
    revenue_currency        VARCHAR(4),

    -- Status
    sim_status              VARCHAR(16),
    activation_date         VARCHAR(16),
    last_activity_date      VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date, usage_country)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cell',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_cell_momo (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128),
    kafka_partition         INTEGER,
    kafka_offset            BIGINT,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,
    integration_tier        VARCHAR(8)      NOT NULL,

    -- MoMo transaction identity
    transaction_id          VARCHAR(64),
    transaction_type        VARCHAR(32),

    -- Sender (anonymised)
    sender_msisdn_hash      VARCHAR(64),
    sender_account_hash     VARCHAR(64),
    sender_country          VARCHAR(4),
    sender_region           VARCHAR(128),
    sender_type             VARCHAR(16),

    -- Receiver (anonymised)
    receiver_msisdn_hash    VARCHAR(64),
    receiver_account_hash   VARCHAR(64),
    receiver_country        VARCHAR(4),
    receiver_region         VARCHAR(128),
    receiver_type           VARCHAR(16),

    -- Corporate linkage
    corporate_client_id     VARCHAR(64),
    is_salary_disbursement  BOOLEAN,
    is_supplier_payment     BOOLEAN,

    -- Amount
    amount                  DECIMAL(18,2),
    currency                VARCHAR(4),
    fee_amount              DECIMAL(10,2),

    -- Transaction details
    transaction_date        VARCHAR(16),
    transaction_time        VARCHAR(16),
    transaction_status      VARCHAR(16),
    channel                 VARCHAR(32),

    -- Agent details (for cash in/out)
    agent_id_hash           VARCHAR(64),
    agent_location          VARCHAR(128),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date, sender_country)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cell',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_cell_sim_activations (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128),
    kafka_partition         INTEGER,
    kafka_offset            BIGINT,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,
    integration_tier        VARCHAR(8)      NOT NULL,

    -- Activation details
    activation_id           VARCHAR(64),
    corporate_client_id     VARCHAR(64),
    corporate_account_ref   VARCHAR(64),

    -- SIM (anonymised)
    sim_hash                VARCHAR(64),
    msisdn_hash             VARCHAR(64),

    -- Location
    activation_country      VARCHAR(4),
    activation_city         VARCHAR(128),
    activation_region       VARCHAR(128),

    -- Type
    sim_type                VARCHAR(16),
    activation_type         VARCHAR(16),
    device_type             VARCHAR(32),
    is_smartphone           BOOLEAN,

    -- Batch (corporate bulk activations)
    batch_id                VARCHAR(64),
    batch_size              INTEGER,

    -- Dates
    activation_date         VARCHAR(16),
    deactivation_date       VARCHAR(16),

    -- Status
    activation_status       VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date, activation_country)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cell',
    'layer' = 'bronze'
);
