-- =========================================================
-- AFRIFLOW: BRONZE LAYER - CIB (Corporate Investment Banking)
--
-- Raw ingested data from CIB source systems.
-- We preserve the original data exactly as received.
-- No transformations, no deduplication, no enrichment.
-- Append only with ingestion metadata.
--
-- Source protocols: ISO 20022, MT103/MT202, FpML
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS bronze_cib_payments (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,
    raw_payload_hash        VARCHAR(64)     NOT NULL,

    -- ISO 20022 payment fields (raw)
    message_id              VARCHAR(64),
    message_type            VARCHAR(32),
    creation_date_time      VARCHAR(32),
    number_of_transactions  INTEGER,
    settlement_method       VARCHAR(16),
    settlement_date         VARCHAR(16),

    -- Debtor (payer)
    debtor_name             VARCHAR(256),
    debtor_account_iban     VARCHAR(64),
    debtor_account_other    VARCHAR(64),
    debtor_agent_bic        VARCHAR(16),
    debtor_country          VARCHAR(4),
    debtor_client_id        VARCHAR(64),

    -- Creditor (payee)
    creditor_name           VARCHAR(256),
    creditor_account_iban   VARCHAR(64),
    creditor_account_other  VARCHAR(64),
    creditor_agent_bic      VARCHAR(16),
    creditor_country        VARCHAR(4),

    -- Amount
    amount                  DECIMAL(18,2),
    currency                VARCHAR(4),
    exchange_rate           DECIMAL(18,8),
    equivalent_amount_zar   DECIMAL(18,2),

    -- Payment details
    payment_type            VARCHAR(32),
    charge_bearer           VARCHAR(8),
    remittance_info         VARCHAR(512),
    end_to_end_id           VARCHAR(64),
    instruction_id          VARCHAR(64),

    -- Business context
    business_date           VARCHAR(16),
    value_date              VARCHAR(16),
    processing_status       VARCHAR(32),

    -- Data quality (set at ingestion)
    dq_completeness_score   DECIMAL(5,2),
    dq_valid_debtor         BOOLEAN,
    dq_valid_creditor       BOOLEAN,
    dq_valid_amount         BOOLEAN,

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.logRetentionDuration' = 'interval 90 days',
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_cib_trade_finance (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Trade finance fields
    facility_id             VARCHAR(64),
    facility_type           VARCHAR(32),
    client_id               VARCHAR(64),
    client_name             VARCHAR(256),
    issuing_bank_bic        VARCHAR(16),
    advising_bank_bic       VARCHAR(16),
    beneficiary_name        VARCHAR(256),
    beneficiary_country     VARCHAR(4),

    -- Amounts
    facility_amount         DECIMAL(18,2),
    facility_currency       VARCHAR(4),
    utilised_amount         DECIMAL(18,2),
    available_amount        DECIMAL(18,2),

    -- Dates
    issue_date              VARCHAR(16),
    expiry_date             VARCHAR(16),
    last_amendment_date     VARCHAR(16),

    -- Status
    facility_status         VARCHAR(32),
    amendment_count         INTEGER,

    -- Goods and shipping
    goods_description       VARCHAR(512),
    port_of_loading         VARCHAR(128),
    port_of_discharge       VARCHAR(128),
    latest_shipment_date    VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_cib_cash_management (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Cash management fields
    account_id              VARCHAR(64),
    client_id               VARCHAR(64),
    client_name             VARCHAR(256),
    account_type            VARCHAR(32),
    account_currency        VARCHAR(4),
    account_country         VARCHAR(4),

    -- Balances
    opening_balance         DECIMAL(18,2),
    closing_balance         DECIMAL(18,2),
    available_balance       DECIMAL(18,2),
    value_date_balance      DECIMAL(18,2),

    -- Sweep / pool
    pool_id                 VARCHAR(64),
    sweep_target_account    VARCHAR(64),
    sweep_threshold         DECIMAL(18,2),
    sweep_executed          BOOLEAN,
    sweep_amount            DECIMAL(18,2),

    -- Statement
    statement_date          VARCHAR(16),
    transaction_count       INTEGER,

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'bronze'
);
