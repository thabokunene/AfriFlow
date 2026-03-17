{{
    config(
        materialized='table',
        tags=['cell', 'marts', 'momo', 'analytics']
    )
}}

/*
    Mart: MoMo (Mobile Money) Analytics

    Aggregated Mobile Money transaction analytics including:
        - Transaction volume and value
        - Salary disbursement tracking
        - Supplier payment identification
        - Agent network analysis
        - Cross-border flow detection

    MoMo is critical for African banking intelligence:
        - Salary disbursements reveal employer-employee relationships
        - Supplier payments reveal B2B relationships
        - Cross-border flows reveal trade corridors
        - Transaction regularity reveals business health

    This mart powers:
        - Payroll capture opportunity identification
        - Supplier network mapping
        - Cross-border payment intelligence
*/

WITH raw_momo AS (
    SELECT * FROM {{ source('cell', 'momo_raw') }}
),

-- Cleaned MoMo transactions
cleaned AS (
    SELECT
        TRIM(transaction_id) AS transaction_id,
        UPPER(TRIM(transaction_type)) AS transaction_type,
        TRIM(sender_msisdn_hash) AS sender_msisdn_hash,
        TRIM(sender_account_hash) AS sender_account_hash,
        UPPER(TRIM(sender_country)) AS sender_country,
        TRIM(sender_region) AS sender_region,
        UPPER(TRIM(sender_type)) AS sender_type,
        TRIM(receiver_msisdn_hash) AS receiver_msisdn_hash,
        TRIM(receiver_account_hash) AS receiver_account_hash,
        UPPER(TRIM(receiver_country)) AS receiver_country,
        TRIM(receiver_region) AS receiver_region,
        UPPER(TRIM(receiver_type)) AS receiver_type,
        TRIM(corporate_client_id) AS corporate_client_id,
        COALESCE(is_salary_disbursement, FALSE) AS is_salary_disbursement,
        COALESCE(is_supplier_payment, FALSE) AS is_supplier_payment,
        CAST(amount AS DECIMAL(18,2)) AS amount,
        UPPER(TRIM(currency)) AS currency,
        CAST(fee_amount AS DECIMAL(10,2)) AS fee_amount,
        CASE
            WHEN transaction_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(transaction_date AS DATE)
            ELSE NULL
        END AS transaction_date,
        TRIM(transaction_time) AS transaction_time,
        UPPER(TRIM(transaction_status)) AS transaction_status,
        UPPER(TRIM(channel)) AS channel,
        TRIM(agent_id_hash) AS agent_id_hash,
        TRIM(agent_location) AS agent_location,
        _ingested_at,
        _source_system
    FROM raw_momo
    WHERE transaction_id IS NOT NULL
      AND amount > 0
),

-- Daily aggregation per corporate
daily_corporate AS (
    SELECT
        corporate_client_id,
        sender_country,
        transaction_date,
        COUNT(*) AS transaction_count,
        SUM(amount) AS transaction_value,
        SUM(fee_amount) AS fee_revenue,
        COUNT(DISTINCT sender_account_hash) AS unique_senders,
        COUNT(DISTINCT receiver_account_hash) AS unique_receivers,
        COUNT(CASE WHEN is_salary_disbursement THEN 1 END) AS salary_count,
        SUM(CASE WHEN is_salary_disbursement THEN amount ELSE 0 END) AS salary_value,
        COUNT(CASE WHEN is_supplier_payment THEN 1 END) AS supplier_count,
        SUM(CASE WHEN is_supplier_payment THEN amount ELSE 0 END) AS supplier_value,
        COUNT(CASE WHEN sender_country != receiver_country THEN 1 END) AS cross_border_count,
        SUM(CASE WHEN sender_country != receiver_country THEN amount ELSE 0 END) AS cross_border_value,
        MAX(currency) AS currency
    FROM cleaned
    WHERE transaction_status = 'SUCCESS'
      AND corporate_client_id IS NOT NULL
    GROUP BY
        corporate_client_id,
        sender_country,
        transaction_date
),

-- Monthly aggregation with trends
monthly_corporate AS (
    SELECT
        corporate_client_id,
        sender_country,
        DATE_TRUNC('month', transaction_date) AS transaction_month,
        currency,

        -- Aggregates
        SUM(transaction_count) AS monthly_transaction_count,
        SUM(transaction_value) AS monthly_transaction_value,
        SUM(fee_revenue) AS monthly_fee_revenue,
        SUM(salary_count) AS monthly_salary_count,
        SUM(salary_value) AS monthly_salary_value,
        SUM(supplier_count) AS monthly_supplier_count,
        SUM(supplier_value) AS monthly_supplier_value,
        SUM(cross_border_count) AS monthly_cross_border_count,
        SUM(cross_border_value) AS monthly_cross_border_value,

        -- Unique counts
        COUNT(DISTINCT transaction_date) AS active_days,
        AVG(unique_senders) AS avg_daily_senders,
        AVG(unique_receivers) AS avg_daily_receivers,

        -- Previous month for trend
        LAG(SUM(transaction_value)) OVER (
            PARTITION BY corporate_client_id, sender_country
            ORDER BY DATE_TRUNC('month', transaction_date)
        ) AS prev_month_value

    FROM daily_corporate
    GROUP BY
        corporate_client_id,
        sender_country,
        DATE_TRUNC('month', transaction_date),
        currency
),

-- Calculate trends and metrics
with_metrics AS (
    SELECT
        *,
        -- Month-over-month growth
        CASE
            WHEN prev_month_value > 0
            THEN ROUND(
                (monthly_transaction_value - prev_month_value)::NUMERIC /
                prev_month_value::NUMERIC * 100, 2
            )
            ELSE NULL
        END AS mom_growth_pct,
        -- Average transaction size
        CASE
            WHEN monthly_transaction_count > 0
            THEN ROUND(
                monthly_transaction_value::NUMERIC / monthly_transaction_count::NUMERIC, 2
            )
            ELSE 0
        END AS avg_transaction_size,
        -- Salary ratio
        CASE
            WHEN monthly_transaction_count > 0
            THEN ROUND(
                monthly_salary_count::NUMERIC / monthly_transaction_count::NUMERIC * 100, 2
            )
            ELSE 0
        END AS salary_transaction_pct,
        -- Cross-border ratio
        CASE
            WHEN monthly_transaction_count > 0
            THEN ROUND(
                monthly_cross_border_count::NUMERIC / monthly_transaction_count::NUMERIC * 100, 2
            )
            ELSE 0
        END AS cross_border_pct,
        -- Convert to ZAR (simplified)
        CASE
            WHEN currency = 'ZAR' THEN monthly_transaction_value
            WHEN currency = 'USD' THEN monthly_transaction_value * 18.5
            WHEN currency = 'NGN' THEN monthly_transaction_value / 85
            WHEN currency = 'KES' THEN monthly_transaction_value / 14
            ELSE monthly_transaction_value * 10
        END AS monthly_transaction_value_zar

    FROM monthly_corporate
)

SELECT
    corporate_client_id,
    sender_country AS transaction_country,
    transaction_month,
    monthly_transaction_count,
    monthly_transaction_value,
    monthly_transaction_value_zar,
    currency,
    monthly_fee_revenue,
    monthly_salary_count,
    monthly_salary_value,
    monthly_supplier_count,
    monthly_supplier_value,
    monthly_cross_border_count,
    monthly_cross_border_value,
    active_days,
    avg_daily_senders,
    avg_daily_receivers,
    mom_growth_pct,
    avg_transaction_size,
    salary_transaction_pct,
    cross_border_pct,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM with_metrics
WHERE monthly_transaction_count > 0
ORDER BY monthly_transaction_value_zar DESC
