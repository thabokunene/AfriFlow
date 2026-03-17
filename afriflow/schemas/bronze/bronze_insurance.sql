-- =========================================================
-- AFRIFLOW: BRONZE LAYER - INSURANCE (Liberty / Standard Bank)
--
-- Raw ingested data from insurance policy administration,
-- claims systems, and premium billing.
--
-- Source protocols: ACORD XML, ACORD AL3, Custom API
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS bronze_insurance_policies (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Policy identity
    policy_id               VARCHAR(64),
    policy_number           VARCHAR(64),
    policy_type             VARCHAR(64),
    product_code            VARCHAR(32),
    product_name            VARCHAR(128),

    -- Client
    client_id               VARCHAR(64),
    client_name             VARCHAR(256),
    client_registration_num VARCHAR(32),
    client_country          VARCHAR(4),

    -- Coverage
    coverage_type           VARCHAR(64),
    coverage_country        VARCHAR(4),
    sum_insured             DECIMAL(18,2),
    sum_insured_currency    VARCHAR(4),
    excess_amount           DECIMAL(18,2),

    -- Premium
    premium_annual          DECIMAL(18,2),
    premium_currency        VARCHAR(4),
    premium_frequency       VARCHAR(16),
    premium_payment_method  VARCHAR(32),
    premium_status          VARCHAR(32),

    -- Dates
    inception_date          VARCHAR(16),
    expiry_date             VARCHAR(16),
    renewal_date            VARCHAR(16),
    cancellation_date       VARCHAR(16),

    -- Status
    policy_status           VARCHAR(32),
    underwriting_status     VARCHAR(32),

    -- Beneficiary (corporate)
    beneficiary_name        VARCHAR(256),
    beneficiary_type        VARCHAR(32),

    -- Asset details (if asset policy)
    asset_description       VARCHAR(512),
    asset_location_country  VARCHAR(4),
    asset_location_city     VARCHAR(128),
    asset_value             DECIMAL(18,2),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'insurance',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_insurance_claims (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Claim identity
    claim_id                VARCHAR(64),
    claim_number            VARCHAR(64),
    policy_id               VARCHAR(64),
    client_id               VARCHAR(64),

    -- Claim details
    claim_type              VARCHAR(64),
    loss_date               VARCHAR(16),
    notification_date       VARCHAR(16),
    loss_description        VARCHAR(1024),
    loss_country            VARCHAR(4),
    loss_city               VARCHAR(128),

    -- Amounts
    claim_amount            DECIMAL(18,2),
    claim_currency          VARCHAR(4),
    reserve_amount          DECIMAL(18,2),
    paid_amount             DECIMAL(18,2),
    recovery_amount         DECIMAL(18,2),

    -- Status
    claim_status            VARCHAR(32),
    assessment_status       VARCHAR(32),
    fraud_flag              BOOLEAN,

    -- Dates
    settlement_date         VARCHAR(16),
    closed_date             VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'insurance',
    'layer' = 'bronze'
);
