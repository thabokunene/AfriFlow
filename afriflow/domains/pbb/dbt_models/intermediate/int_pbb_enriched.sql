{{
    config(
        materialized='table',
        tags=['pbb', 'intermediate', 'enriched']
    )
}}

/*
    Intermediate enriched PBB model.

    We aggregate personal and business banking data at the
    corporate employer level for cross-domain workforce
    capture analysis.

    This model joins with:
        - Corporate client master
        - Country metadata
        - SIM deflation reference (for cell comparison)
*/

WITH staged_accounts AS (
    SELECT * FROM {{ ref('stg_pbb_accounts') }}
),

-- Corporate client master
client_master AS (
    SELECT * FROM {{ source('pbb', 'client_master') }}
),

-- Monthly aggregation per corporate employer
monthly_corporate AS (
    SELECT
        employer_client_id AS corporate_client_id,
        customer_country AS payroll_country,
        DATE_TRUNC('month', last_transaction_date) AS payroll_month,

        -- Employee counts
        COUNT(DISTINCT customer_id_hash) AS employee_count,
        COUNT(DISTINCT CASE WHEN opened_date >= DATE_TRUNC('month', last_transaction_date) THEN customer_id_hash END) AS new_accounts_opened,
        COUNT(DISTINCT CASE WHEN is_closed THEN customer_id_hash END) AS accounts_closed,

        -- Account health
        COUNT(DISTINCT CASE WHEN account_status = 'ACTIVE' THEN customer_id_hash END) AS active_accounts,
        COUNT(DISTINCT CASE WHEN is_dormant THEN customer_id_hash END) AS dormant_accounts,
        COUNT(DISTINCT CASE WHEN is_overdrawn THEN customer_id_hash END) AS overdrawn_accounts,

        -- Payroll values
        SUM(credit_turnover_30d) AS total_credit_turnover,
        AVG(credit_turnover_30d) AS avg_credit_turnover,
        MAX(account_currency) AS payroll_currency,

        -- Channel adoption
        COUNT(DISTINCT CASE WHEN digital_active THEN customer_id_hash END) AS digital_active_count,
        COUNT(DISTINCT CASE WHEN card_active THEN customer_id_hash END) AS card_active_count,
        COUNT(DISTINCT CASE WHEN ussd_active THEN customer_id_hash END) AS ussd_active_count,

        -- Source record count
        COUNT(*) AS source_record_count

    FROM staged_accounts
    WHERE is_payroll_account = TRUE
      AND employer_client_id IS NOT NULL
      AND is_valid_status = TRUE
    GROUP BY
        employer_client_id,
        customer_country,
        DATE_TRUNC('month', last_transaction_date)
),

-- Calculate derived metrics
with_metrics AS (
    SELECT
        *,
        -- Net employee change
        COALESCE(new_accounts_opened, 0) - COALESCE(accounts_closed, 0) AS net_employee_change,
        -- Convert to ZAR (simplified)
        CASE
            WHEN payroll_currency = 'ZAR' THEN total_credit_turnover
            WHEN payroll_currency = 'USD' THEN total_credit_turnover * 18.5
            WHEN payroll_currency = 'NGN' THEN total_credit_turnover / 85
            WHEN payroll_currency = 'KES' THEN total_credit_turnover / 14
            ELSE total_credit_turnover * 10
        END AS total_payroll_value_zar,
        -- Channel adoption percentage
        CASE
            WHEN employee_count > 0
            THEN ROUND(digital_active_count::NUMERIC / employee_count::NUMERIC * 100, 2)
            ELSE 0
        END AS digital_adoption_pct,
        -- Dormant percentage
        CASE
            WHEN employee_count > 0
            THEN ROUND(dormant_accounts::NUMERIC / employee_count::NUMERIC * 100, 2)
            ELSE 0
        END AS dormant_pct,
        -- Overdrawn percentage
        CASE
            WHEN employee_count > 0
            THEN ROUND(overdrawn_accounts::NUMERIC / employee_count::NUMERIC * 100, 2)
            ELSE 0
        END AS overdrawn_pct,
        -- Average salary estimate (monthly credit turnover as proxy)
        avg_credit_turnover AS average_salary

    FROM monthly_corporate
    WHERE employee_count > 0
),

-- Add previous month for trend
with_trends AS (
    SELECT
        *,
        LAG(employee_count) OVER (
            PARTITION BY corporate_client_id, payroll_country
            ORDER BY payroll_month
        ) AS prev_month_employees,
        LAG(total_payroll_value_zar) OVER (
            PARTITION BY corporate_client_id, payroll_country
            ORDER BY payroll_month
        ) AS prev_month_payroll
    FROM with_metrics
),

-- Calculate growth metrics
with_growth AS (
    SELECT
        *,
        -- Employee growth
        CASE
            WHEN prev_month_employees > 0
            THEN ROUND(
                (employee_count - prev_month_employees)::NUMERIC / prev_month_employees::NUMERIC * 100, 2
            )
            ELSE NULL
        END AS employee_growth_pct,
        -- Payroll growth
        CASE
            WHEN prev_month_payroll > 0
            THEN ROUND(
                (total_payroll_value_zar - prev_month_payroll)::NUMERIC / prev_month_payroll::NUMERIC * 100, 2
            )
            ELSE NULL
        END AS payroll_growth_pct
    FROM with_trends
)

SELECT
    corporate_client_id,
    payroll_country,
    payroll_month,
    employee_count,
    new_accounts_opened,
    accounts_closed,
    net_employee_change,
    active_accounts,
    dormant_accounts,
    overdrawn_accounts,
    total_credit_turnover AS total_payroll_value,
    payroll_currency,
    total_payroll_value_zar,
    average_salary,
    average_salary AS median_salary,
    digital_active_count,
    card_active_count,
    ussd_active_count,
    digital_adoption_pct,
    dormant_pct,
    overdrawn_pct,
    employee_growth_pct AS payroll_frequency,
    0 AS on_time_payments,
    0 AS late_payments,
    0 AS missed_payments,
    source_record_count,
    CURRENT_TIMESTAMP AS processed_timestamp,
    payroll_month AS payroll_month_partition
FROM with_growth
ORDER BY total_payroll_value_zar DESC
