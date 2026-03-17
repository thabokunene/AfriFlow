{{
    config(
        materialized='table',
        tags=['pbb', 'marts', 'payroll', 'analytics']
    )
}}

/*
    Mart: Payroll Analytics

    Aggregated payroll-level analytics including:
        - Employee account metrics
        - Payroll value and frequency
        - Channel adoption
        - Account health indicators
        - Payroll regularity tracking

    This mart powers:
        - Workforce capture analysis
        - Payroll retention monitoring
        - Cross-sell opportunity identification
        - Competitive leakage detection
*/

WITH enriched_payroll AS (
    SELECT * FROM {{ ref('int_pbb_enriched') }}
),

-- Payroll batch tracking (would join with payroll_raw in production)
payroll_batches AS (
    SELECT
        employer_client_id AS corporate_client_id,
        payroll_country,
        DATE_TRUNC('month', payroll_date) AS payroll_month,
        COUNT(*) AS batch_count,
        SUM(employee_count) AS total_employees,
        SUM(total_payroll_value_zar) AS total_payroll_value,
        AVG(average_salary) AS avg_salary,
        COUNT(CASE WHEN processing_status = 'COMPLETED' THEN 1 END) AS completed_batches,
        COUNT(CASE WHEN processing_status = 'FAILED' THEN 1 END) AS failed_batches
    FROM {{ source('pbb', 'payroll_raw') }}
    WHERE employer_client_id IS NOT NULL
    GROUP BY
        employer_client_id,
        payroll_country,
        DATE_TRUNC('month', payroll_date)
),

-- Combined payroll metrics
combined AS (
    SELECT
        ep.corporate_client_id,
        ep.payroll_country,
        ep.payroll_month,
        ep.employee_count,
        ep.new_accounts_opened,
        ep.accounts_closed,
        ep.net_employee_change,
        ep.active_accounts,
        ep.dormant_accounts,
        ep.overdrawn_accounts,
        ep.total_payroll_value,
        ep.payroll_currency,
        ep.total_payroll_value_zar,
        ep.average_salary,
        ep.digital_active_count,
        ep.card_active_count,
        ep.ussd_active_count,
        ep.digital_adoption_pct,
        ep.dormant_pct,
        ep.overdrawn_pct,
        ep.source_record_count,
        COALESCE(pb.batch_count, 0) AS batch_count,
        COALESCE(pb.completed_batches, 0) AS completed_batches,
        COALESCE(pb.failed_batches, 0) AS failed_batches,
        COALESCE(pb.avg_salary, ep.average_salary) AS avg_salary,

        -- Payroll regularity
        CASE
            WHEN COALESCE(pb.failed_batches, 0) = 0 THEN 100.0
            ELSE ROUND(
                pb.completed_batches::NUMERIC / NULLIF(pb.batch_count, 0)::NUMERIC * 100, 2
            )
        END AS on_time_pct,
        CASE WHEN COALESCE(pb.failed_batches, 0) > 0 THEN TRUE ELSE FALSE END AS missed_payment_flag,

        -- Estimated revenue (2% of payroll value as proxy)
        ep.total_payroll_value_zar * 0.02 AS estimated_account_revenue_zar,

        -- Previous month for trend
        LAG(ep.employee_count) OVER (
            PARTITION BY ep.corporate_client_id, ep.payroll_country
            ORDER BY ep.payroll_month
        ) AS prev_month_employees,
        LAG(ep.total_payroll_value_zar) OVER (
            PARTITION BY ep.corporate_client_id, ep.payroll_country
            ORDER BY ep.payroll_month
        ) AS prev_month_payroll

    FROM enriched_payroll ep
    LEFT JOIN payroll_batches pb
        ON ep.corporate_client_id = pb.corporate_client_id
        AND ep.payroll_country = pb.payroll_country
        AND ep.payroll_month = pb.payroll_month
),

-- Calculate trends
with_trends AS (
    SELECT
        *,
        -- Employee growth
        CASE
            WHEN prev_month_employees > 0
            THEN employee_count - prev_month_employees
            ELSE 0
        END AS employee_change,
        -- Payroll growth
        CASE
            WHEN prev_month_payroll > 0
            THEN ROUND(
                (total_payroll_value_zar - prev_month_payroll)::NUMERIC / prev_month_payroll::NUMERIC * 100, 2
            )
            ELSE 0
        END AS payroll_growth_pct
    FROM combined
)

SELECT
    'GOLD-' || corporate_client_id AS golden_id,
    corporate_client_id,
    payroll_country AS employee_country,
    employee_count,
    new_accounts_opened AS new_accounts_mom,
    accounts_closed AS closed_accounts_mom,
    net_employee_change,
    total_payroll_value AS monthly_payroll_value,
    payroll_currency,
    total_payroll_value_zar AS monthly_payroll_zar,
    average_salary AS average_salary_zar,
    average_salary AS median_salary_zar,
    digital_active_count,
    card_active_count,
    ussd_active_count,
    digital_adoption_pct,
    0.0 AS ussd_usage_pct,
    CASE
        WHEN employee_count > 0
        THEN ROUND(card_active_count::NUMERIC / employee_count::NUMERIC * 100, 2)
        ELSE 0
    END AS card_active_pct,
    dormant_pct,
    overdrawn_pct,
    on_time_pct,
    missed_payment_flag,
    estimated_account_revenue_zar,
    payroll_month AS payroll_date,
    payroll_month AS last_payroll_date,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM with_trends
WHERE employee_count > 0
ORDER BY total_payroll_value_zar DESC
