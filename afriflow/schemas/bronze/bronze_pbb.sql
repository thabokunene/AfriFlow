-- =========================================================
-- AFRIFLOW: BRONZE LAYER - PBB (Personal & Business Banking)
--
-- Raw ingested data from retail core banking, payroll
-- processing, digital banking, and card systems.
--
-- The PBB domain is critical for the workforce capture
-- signal: we compare cell SIM counts against PBB payroll
-- deposits to identify employees banking with competitors.
--
-- Source protocols: ISO 8583, NACHA, REST API
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS bronze_pbb_accounts (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Account identity
    account_id              VARCHAR(64),
    account_number_hash     VARCHAR(64),
    account_type            VARCHAR(32),
    product_code            VARCHAR(32),
    product_name            VARCHAR(128),

    -- Account holder (anonymised for bronze)
    customer_id_hash        VARCHAR(64),
    customer_segment        VARCHAR(32),
    customer_country        VARCHAR(4),

    -- Corporate linkage
    employer_client_id      VARCHAR(64),
    employer_name           VARCHAR(256),
    is_payroll_account      BOOLEAN,

    -- Balances
    current_balance         DECIMAL(18,2),
    available_balance       DECIMAL(18,2),
    account_currency        VARCHAR(4),

    -- Activity
    last_transaction_date   VARCHAR(16),
    transaction_count_30d   INTEGER,
    debit_turnover_30d      DECIMAL(18,2),
    credit_turnover_30d     DECIMAL(18,2),

    -- Status
    account_status          VARCHAR(16),
    opened_date             VARCHAR(16),
    closed_date             VARCHAR(16),

    -- Channel usage
    digital_active          BOOLEAN,
    card_active             BOOLEAN,
    ussd_active             BOOLEAN,
    branch_last_visit       VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'pbb',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_pbb_payroll (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Payroll batch identity
    payroll_batch_id        VARCHAR(64),
    corporate_client_id     VARCHAR(64),
    corporate_name          VARCHAR(256),

    -- Payroll details
    payroll_date            VARCHAR(16),
    payroll_country         VARCHAR(4),
    payroll_currency        VARCHAR(4),

    -- Counts
    employee_count          INTEGER,
    successful_credits      INTEGER,
    failed_credits          INTEGER,

    -- Values
    total_payroll_value     DECIMAL(18,2),
    average_salary          DECIMAL(18,2),
    max_salary              DECIMAL(18,2),
    min_salary              DECIMAL(18,2),

    -- Frequency
    payroll_frequency       VARCHAR(16),
    is_supplementary        BOOLEAN,

    -- Status
    processing_status       VARCHAR(32),
    completion_timestamp    VARCHAR(32),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'pbb',
    'layer' = 'bronze'
);
