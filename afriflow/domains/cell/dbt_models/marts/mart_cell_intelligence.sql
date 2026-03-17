{{
    config(
        materialized='table',
        tags=['cell', 'marts', 'intelligence']
    )
}}

/*
    Mart: Cell Network Intelligence

    Aggregated cell network analytics at the corporate client level
    including:
        - SIM metrics with deflation-adjusted employee estimates
        - Growth signals (expansion/contraction detection)
        - Usage patterns and device mix
        - MoMo (Mobile Money) intelligence
        - Geographic spread analysis

    This mart powers:
        - Workforce capture signals
        - Geographic expansion detection
        - Client health monitoring
*/

WITH enriched_cell AS (
    SELECT * FROM {{ ref('int_cell_enriched') }}
),

-- MoMo aggregation (would join with MoMo raw data in production)
momo_agg AS (
    SELECT
        corporate_client_id,
        sender_country AS usage_country,
        DATE_TRUNC('month', CAST(transaction_date AS DATE)) AS data_month,
        COUNT(*) AS momo_transaction_count,
        SUM(amount) AS momo_transaction_value,
        COUNT(CASE WHEN is_salary_disbursement THEN 1 END) AS momo_salary_count,
        SUM(CASE WHEN is_salary_disbursement THEN amount ELSE 0 END) AS momo_salary_value,
        COUNT(CASE WHEN is_supplier_payment THEN 1 END) AS momo_supplier_count,
        SUM(CASE WHEN is_supplier_payment THEN amount ELSE 0 END) AS momo_supplier_value
    FROM {{ source('cell', 'momo_raw') }}
    WHERE corporate_client_id IS NOT NULL
    GROUP BY
        corporate_client_id,
        sender_country,
        DATE_TRUNC('month', CAST(transaction_date AS DATE))
),

-- Combined cell + MoMo
combined AS (
    SELECT
        ec.corporate_client_id,
        ec.usage_country,
        ec.usage_month,
        ec.total_active_sims,
        ec.deflation_factor,
        ec.estimated_employees,
        ec.sim_growth_pct,
        ec.smartphone_count,
        ec.smartphone_pct,
        ec.total_voice_minutes,
        ec.total_data_usage_gb,
        ec.total_sms_count,
        ec.total_ussd_sessions,
        ec.total_ussd_banking,
        ec.total_revenue_zar,
        ec.distinct_cities,
        ec.primary_city,
        ec.integration_tier,
        COALESCE(ma.momo_transaction_count, 0) AS momo_transaction_count,
        COALESCE(ma.momo_transaction_value, 0) AS momo_transaction_value,
        COALESCE(ma.momo_salary_count, 0) AS momo_salary_count,
        COALESCE(ma.momo_salary_value, 0) AS momo_salary_value,
        COALESCE(ma.momo_supplier_count, 0) AS momo_supplier_count,
        COALESCE(ma.momo_supplier_value, 0) AS momo_supplier_value,
        -- MoMo regularity score (simplified)
        CASE
            WHEN COALESCE(ma.momo_salary_count, 0) > 0 THEN 0.9
            WHEN COALESCE(ma.momo_transaction_count, 0) > 100 THEN 0.7
            WHEN COALESCE(ma.momo_transaction_count, 0) > 10 THEN 0.5
            ELSE 0.3
        END AS momo_regularity_score
    FROM enriched_cell ec
    LEFT JOIN momo_agg ma
        ON ec.corporate_client_id = ma.corporate_client_id
        AND ec.usage_country = ma.usage_country
        AND ec.usage_month = ma.data_month
),

-- Calculate expansion signals
with_signals AS (
    SELECT
        *,
        -- Expansion flags
        CASE WHEN COALESCE(sim_growth_pct, 0) > 10 THEN TRUE ELSE FALSE END AS is_expanding,
        CASE WHEN COALESCE(sim_growth_pct, 0) < -10 THEN TRUE ELSE FALSE END AS is_contracting,
        -- Activity tracking
        CASE
            WHEN total_active_sims > 0 THEN CURRENT_DATE
            ELSE NULL
        END AS last_activity_date,
        -- Days since activity
        CASE
            WHEN total_active_sims > 0 THEN 0
            ELSE NULL
        END AS days_since_activity,
        -- Countries active (would be calculated across all countries in production)
        1 AS countries_active
    FROM combined
    WHERE total_active_sims > 0
)

SELECT
    'GOLD-' || corporate_client_id AS golden_id,
    corporate_client_id,
    usage_country,
    total_active_sims AS active_sims,
    deflation_factor,
    estimated_employees,
    sim_growth_pct AS sim_growth_pct_mom,
    0.0 AS sim_growth_pct_qoq,
    is_expanding,
    is_contracting,
    total_data_usage_gb AS monthly_data_usage_gb,
    total_voice_minutes AS monthly_voice_minutes,
    total_ussd_banking AS ussd_banking_sessions,
    smartphone_pct,
    momo_transaction_value,
    momo_transaction_count,
    momo_salary_value AS momo_salary_value,
    momo_supplier_value AS momo_supplier_value,
    momo_regularity_score,
    distinct_cities,
    primary_city,
    countries_active,
    last_activity_date,
    days_since_activity,
    usage_month AS data_month,
    integration_tier,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM with_signals
ORDER BY estimated_employees DESC
