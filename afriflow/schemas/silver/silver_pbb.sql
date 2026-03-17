-- =========================================================
-- AFRIFLOW: SILVER LAYER - PBB
--
-- Cleaned personal and business banking data aggregated
-- at the corporate employer level for cross-domain
-- workforce capture analysis.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS silver_pbb_corporate_payroll (
    -- Corporate client aggregation
    corporate_client_id     VARCHAR(64)     NOT NULL,
    payroll_country         VARCHAR(4)      NOT NULL,
    payroll_month           DATE            NOT NULL,

    -- Employee counts
    employee_count          INTEGER         NOT NULL,
    new_accounts_opened     INTEGER,
    accounts_closed         INTEGER,
    net_employee_change     INTEGER,

    -- Payroll values
    total_payroll_value     DECIMAL(18,2),
    payroll_currency        VARCHAR(4),
    total_payroll_value_zar DECIMAL(18,2),
    average_salary          DECIMAL(18,2),
    median_salary           DECIMAL(18,2),

    -- Channel adoption
    digital_active_count    INTEGER,
    card_active_count       INTEGER,
    ussd_active_count       INTEGER,
    digital_adoption_pct    DECIMAL(5,2),

    -- Account health
    active_accounts         INTEGER,
    dormant_accounts        INTEGER,
    overdrawn_accounts      INTEGER,

    -- Payroll regularity
    payroll_frequency       VARCHAR(16),
    on_time_payments        INTEGER,
    late_payments           INTEGER,
    missed_payments         INTEGER,

    -- Lineage
    source_record_count     INTEGER         NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    -- Partitioning
    payroll_month_partition DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (payroll_month_partition)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'pbb',
    'layer' = 'silver'
);
