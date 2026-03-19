-- =============================================================================
-- @file mart_pbb_client.sql
-- @description Final analytical mart for PBB client profiles, integrating
--     account portfolio metrics, channel adoption, and relationship health scores.
-- @author Thabo Kunene
-- @created 2026-03-19
-- =============================================================================

{{
    config(
        materialized='table',
        tags=['pbb', 'marts', 'client']
    )
}}

/*
    Design intent:
    - Provide a holistic view of individual PBB customer relationships.
    - Segment customers based on product holdings and channel engagement.
    - Identify cross-sell opportunities and potential attrition risks.
    - Power customer-centric dashboards and automated marketing campaigns.
*/

WITH enriched_pbb AS (
    -- Enriched PBB data from the intermediate layer
    SELECT * FROM {{ ref('int_pbb_enriched') }}
),

-- Account-level aggregation per customer to profile the individual relationship
customer_accounts AS (
    SELECT
        customer_id_hash,
        employer_client_id,
        customer_country,
        customer_segment,

        -- Account counts: indicator of relationship depth
        COUNT(*) AS total_accounts,
        COUNT(DISTINCT CASE WHEN account_type IN ('SAVINGS', 'SALARY') THEN account_id END) AS savings_accounts,
        COUNT(DISTINCT CASE WHEN account_type IN ('CHECKING', 'CURRENT') THEN account_id END) AS checking_accounts,
        COUNT(DISTINCT CASE WHEN account_type IN ('BUSINESS') THEN account_id END) AS business_accounts,

        -- Balance summary: primary indicator of customer wealth and liquidity
        SUM(current_balance) AS total_balance,
        SUM(available_balance) AS total_available,
        AVG(current_balance) AS avg_balance,

        -- Turnover: tracks the velocity of funds through the customer's accounts
        SUM(debit_turnover_30d) AS total_debit_turnover,
        SUM(credit_turnover_30d) AS total_credit_turnover,

        -- Channel adoption: flags for digital engagement monitoring
        MAX(CASE WHEN digital_active THEN 1 ELSE 0 END) AS is_digital_active,
        MAX(CASE WHEN card_active THEN 1 ELSE 0 END) AS has_card,
        MAX(CASE WHEN ussd_active THEN 1 ELSE 0 END) AS uses_ussd,

        -- Account health: identifies signs of relationship deterioration or financial stress
        COUNT(CASE WHEN is_dormant THEN 1 END) AS dormant_count,
        COUNT(CASE WHEN is_overdrawn THEN 1 END) AS overdrawn_count,
        COUNT(CASE WHEN is_closed THEN 1 END) AS closed_count,

        -- Activity: tracks the recency of customer engagement
        MAX(last_transaction_date) AS last_activity_date

    FROM {{ ref('stg_pbb_accounts') }}
    WHERE is_valid_status = TRUE
    GROUP BY
        customer_id_hash,
        employer_client_id,
        customer_country,
        customer_segment
),

-- Enriched customer profile with derived behavioral and health scores
enriched AS (
    SELECT
        ca.customer_id_hash,
        ca.employer_client_id,
        ca.customer_country,
        ca.customer_segment,
        ca.total_accounts,
        ca.savings_accounts,
        ca.checking_accounts,
        ca.business_accounts,
        ca.total_balance,
        ca.total_available,
        ca.avg_balance,
        ca.total_debit_turnover,
        ca.total_credit_turnover,
        ca.is_digital_active,
        ca.has_card,
        ca.uses_ussd,
        ca.dormant_count,
        ca.overdrawn_count,
        ca.closed_count,
        ca.last_activity_date,

        -- Channel adoption score: measures the breadth of digital tool usage
        (
            ca.is_digital_active +
            ca.has_card +
            ca.uses_ussd
        ) AS channel_score,

        -- Relationship health score: heuristic-based risk and value assessment
        CASE
            WHEN ca.dormant_count > 0 AND ca.overdrawn_count > 0 THEN 20
            WHEN ca.dormant_count > 0 THEN 40
            WHEN ca.overdrawn_count > 0 THEN 50
            WHEN ca.total_accounts >= 3 THEN 90
            WHEN ca.total_accounts >= 2 THEN 75
            ELSE 60
        END AS health_score,

        -- Days since activity: indicator of potential churn
        CASE
            WHEN ca.last_activity_date IS NOT NULL
            THEN CURRENT_DATE - ca.last_activity_date
            ELSE NULL
        END AS days_since_activity,

        -- Cross-sell eligibility flags for automated lead generation
        CASE WHEN ca.savings_accounts = 0 THEN TRUE ELSE FALSE END AS eligible_for_savings,
        CASE WHEN ca.has_card = 0 AND ca.is_digital_active = 1 THEN TRUE ELSE FALSE END AS eligible_for_card,
        CASE WHEN ca.business_accounts = 0 AND ca.customer_segment = 'BUSINESS' THEN TRUE ELSE FALSE END AS eligible_for_business

    FROM customer_accounts ca
    WHERE ca.total_accounts > 0
)

-- Final output selection for the presentation layer with unique golden IDs
SELECT
    'GOLD-' || customer_id_hash AS golden_id,
    customer_id_hash AS client_id,
    employer_client_id AS corporate_client_id,
    customer_country AS employee_country,
    customer_segment,
    total_accounts AS employee_count,
    0 AS new_accounts_mom,
    0 AS closed_accounts_mom,
    0 AS net_employee_change,
    total_credit_turnover AS monthly_payroll_value,
    'ZAR' AS payroll_currency,
    total_credit_turnover AS monthly_payroll_zar,
    avg_balance AS average_salary_zar,
    avg_balance AS median_salary,
    channel_score AS digital_adoption_pct,
    0 AS ussd_usage_pct,
    CASE WHEN has_card = 1 THEN 100 ELSE 0 END AS card_active_pct,
    CASE
        WHEN total_accounts > 0
        THEN ROUND(dormant_count::NUMERIC / total_accounts::NUMERIC * 100, 2)
        ELSE 0
    END AS dormant_pct,
    CASE
        WHEN total_accounts > 0
        THEN ROUND(overdrawn_count::NUMERIC / total_accounts::NUMERIC * 100, 2)
        ELSE 0
    END AS overdrawn_pct,
    100.0 AS on_time_pct,
    FALSE AS missed_payment_flag,
    total_credit_turnover * 0.02 AS estimated_account_revenue_zar,
    CURRENT_DATE AS payroll_date,
    last_activity_date AS last_payroll_date,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM enriched
ORDER BY total_credit_turnover DESC
