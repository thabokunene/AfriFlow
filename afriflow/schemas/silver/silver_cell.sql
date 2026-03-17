-- =========================================================
-- AFRIFLOW: SILVER LAYER - CELL NETWORK
--
-- Cleaned and aggregated cell network data at the
-- corporate client level. We aggregate individual SIM
-- records to corporate summaries and apply the SIM
-- deflation model per country.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS silver_cell_corporate_usage (
    -- Corporate client aggregation
    corporate_client_id     VARCHAR(64)     NOT NULL,
    usage_country           VARCHAR(4)      NOT NULL,
    usage_month             DATE            NOT NULL,

    -- SIM counts
    total_active_sims       INTEGER         NOT NULL,
    new_activations         INTEGER,
    deactivations           INTEGER,
    net_sim_change          INTEGER,
    sim_growth_pct          DECIMAL(8,2),

    -- SIM deflation (Africa specific)
    deflation_factor        DECIMAL(5,2)    NOT NULL,
    estimated_employees     INTEGER         NOT NULL,
    deflation_model_version VARCHAR(16),

    -- Device mix
    smartphone_count        INTEGER,
    feature_phone_count     INTEGER,
    smartphone_pct          DECIMAL(5,2),

    -- Aggregated usage
    total_voice_minutes     DECIMAL(12,2),
    total_data_usage_gb     DECIMAL(12,2),
    total_sms_count         INTEGER,
    total_ussd_sessions     INTEGER,
    total_ussd_banking      INTEGER,

    -- Revenue
    total_revenue           DECIMAL(18,2),
    revenue_currency        VARCHAR(4),
    total_revenue_zar       DECIMAL(18,2),

    -- MoMo summary
    momo_transaction_count  INTEGER,
    momo_transaction_value  DECIMAL(18,2),
    momo_salary_count       INTEGER,
    momo_salary_value       DECIMAL(18,2),
    momo_supplier_count     INTEGER,
    momo_supplier_value     DECIMAL(18,2),

    -- Geographic spread
    distinct_cities         INTEGER,
    primary_city            VARCHAR(128),

    -- Lineage
    source_record_count     INTEGER         NOT NULL,
    integration_tier        VARCHAR(8)      NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    -- Partitioning
    usage_month_partition   DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (usage_month_partition, usage_country)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cell',
    'layer' = 'silver'
);
