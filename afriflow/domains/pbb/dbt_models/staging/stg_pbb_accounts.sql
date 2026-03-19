-- =============================================================================
-- @file stg_pbb_accounts.sql
-- @description Staging model for PBB accounts, performing data cleaning,
--     type casting, and basic validation on raw ingestion data.
-- @author Thabo Kunene
-- @created 2026-03-19
-- =============================================================================

{{
    config(
        materialized='view',
        tags=['pbb', 'staging', 'accounts']
    )
}}

/*
    Design intent:
    - Standardize raw PBB account data for downstream enrichment and modeling.
    - Perform initial data quality checks (e.g., valid countries, account types).
    - Normalize text fields (UPPER, TRIM) to ensure consistent grouping and joining.
    - Prepare data for workforce capture analysis (payroll linkage).
*/

WITH raw_accounts AS (
    -- Source data from the raw ingestion layer
    SELECT * FROM {{ source('pbb', 'accounts_raw') }}
),

cleaned AS (
    SELECT
        -- Ingestion metadata for lineage and auditing
        TRIM(ingestion_id) AS ingestion_id,
        CAST(ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp,
        TRIM(kafka_topic) AS kafka_topic,
        CAST(kafka_partition AS INTEGER) AS kafka_partition,
        CAST(kafka_offset AS BIGINT) AS kafka_offset,
        TRIM(source_system) AS source_system,
        TRIM(schema_version) AS schema_version,

        -- Account identity: hashed where necessary for privacy compliance
        TRIM(account_id) AS account_id,
        TRIM(account_number_hash) AS account_number_hash,
        UPPER(TRIM(account_type)) AS account_type,
        TRIM(product_code) AS product_code,
        TRIM(product_name) AS product_name,

        -- Account holder (anonymised for POPIA/GDPR compliance)
        TRIM(customer_id_hash) AS customer_id_hash,
        UPPER(TRIM(customer_segment)) AS customer_segment,
        UPPER(TRIM(customer_country)) AS customer_country,

        -- Corporate linkage: crucial for payroll and workforce analytics
        TRIM(employer_client_id) AS employer_client_id,
        TRIM(employer_name) AS employer_name,
        COALESCE(is_payroll_account, FALSE) AS is_payroll_account,

        -- Balances: standardized for financial modeling
        CAST(current_balance AS DECIMAL(18,2)) AS current_balance,
        GREATEST(0, CAST(available_balance AS DECIMAL(18,2))) AS available_balance,
        UPPER(TRIM(account_currency)) AS account_currency,

        -- Activity metrics: used for behavioral profiling and dormancy detection
        CASE
            WHEN last_transaction_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(last_transaction_date AS DATE)
            ELSE NULL
        END AS last_transaction_date,
        GREATEST(0, CAST(transaction_count_30d AS INTEGER)) AS transaction_count_30d,
        CAST(debit_turnover_30d AS DECIMAL(18,2)) AS debit_turnover_30d,
        CAST(credit_turnover_30d AS DECIMAL(18,2)) AS credit_turnover_30d,

        -- Status and lifecycle dates
        UPPER(TRIM(account_status)) AS account_status,
        CASE
            WHEN opened_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(opened_date AS DATE)
            ELSE NULL
        END AS opened_date,
        CASE
            WHEN closed_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(closed_date AS DATE)
            ELSE NULL
        END AS closed_date,

        -- Channel usage: indicators of digital adoption and customer engagement
        COALESCE(digital_active, FALSE) AS digital_active,
        COALESCE(card_active, FALSE) AS card_active,
        COALESCE(ussd_active, FALSE) AS ussd_active,
        CASE
            WHEN branch_last_visit ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(branch_last_visit AS DATE)
            ELSE NULL
        END AS branch_last_visit,

        -- Partitioning for efficient query performance
        CASE
            WHEN ingestion_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(ingestion_date AS DATE)
            ELSE CURRENT_DATE
        END AS ingestion_date

    FROM raw_accounts
    WHERE account_id IS NOT NULL
      AND customer_id_hash IS NOT NULL
),

validated AS (
    SELECT
        *,
        -- Validation flags based on business rules and geographical presence
        CASE
            WHEN customer_country IN ('ZA', 'NG', 'KE', 'GH', 'TZ', 'UG', 'ZM', 'MZ', 'CI', 'RW', 'AO', 'CM', 'ET', 'MW', 'SS')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_country,
        CASE
            WHEN account_type IN ('SAVINGS', 'CHECKING', 'CURRENT', 'BUSINESS', 'PAYROLL', 'SALARY')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_account_type,
        CASE
            WHEN account_status IN ('ACTIVE', 'DORMANT', 'CLOSED', 'FROZEN', 'RESTRICTED')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_status,
        CASE
            WHEN customer_segment IN ('RETAIL', 'PREMIUM', 'BUSINESS', 'CORPORATE', 'PRIVATE')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_segment,
        -- Derived flags for operational reporting
        CASE
            WHEN closed_date IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS is_closed,
        CASE
            WHEN last_transaction_date < CURRENT_DATE - INTERVAL '90 days' THEN TRUE
            ELSE FALSE
        END AS is_dormant,
        CASE
            WHEN current_balance < 0 THEN TRUE
            ELSE FALSE
        END AS is_overdrawn,
        -- Combined channel adoption score for customer value segmentation
        (
            CASE WHEN digital_active THEN 1 ELSE 0 END +
            CASE WHEN card_active THEN 1 ELSE 0 END +
            CASE WHEN ussd_active THEN 1 ELSE 0 END
        ) AS channel_adoption_score

    FROM cleaned
)

-- Final selection filters out records that fail critical validation criteria
SELECT
    ingestion_id,
    ingestion_timestamp,
    kafka_topic,
    kafka_partition,
    kafka_offset,
    source_system,
    schema_version,
    account_id,
    account_number_hash,
    account_type,
    product_code,
    product_name,
    customer_id_hash,
    customer_segment,
    customer_country,
    employer_client_id,
    employer_name,
    is_payroll_account,
    current_balance,
    available_balance,
    account_currency,
    last_transaction_date,
    transaction_count_30d,
    debit_turnover_30d,
    credit_turnover_30d,
    account_status,
    opened_date,
    closed_date,
    digital_active,
    card_active,
    ussd_active,
    branch_last_visit,
    ingestion_date,
    is_valid_country,
    is_valid_account_type,
    is_valid_status,
    is_valid_segment,
    is_closed,
    is_dormant,
    is_overdrawn,
    channel_adoption_score
FROM validated
WHERE is_valid_country = TRUE
  AND is_valid_account_type = TRUE
  AND is_valid_status = TRUE
