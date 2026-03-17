{{
    config(
        materialized='table',
        tags=['integration', 'unified', 'client_360']
    )
}}

/*
    Mart: Unified Client 360

    The crown jewel of the AfriFlow platform - a single golden record
    combining every client's relationship across all five domains:
    CIB, Forex, Insurance, Cell Network, and PBB.

    This table powers:
    - Relationship manager dashboards
    - Cross-sell opportunity identification
    - Risk heatmaps
    - Revenue attribution

    Freshness SLA: sub-5-minute
    Accuracy target: 99.97%
*/

WITH entity_resolution AS (
    SELECT * FROM {{ ref('stg_entity_resolution') }}
    WHERE is_active = TRUE
),

-- CIB domain aggregation
cib_metrics AS (
    SELECT
        golden_id,
        COUNT(DISTINCT corridor) AS cib_active_corridors,
        SUM(amount_zar) AS cib_annual_value,
        COUNT(*) AS cib_payment_count_90d,
        COUNT(DISTINCT CASE WHEN is_new_corridor THEN 1 END) AS cib_new_countries_90d,
        MAX(payment_date) AS cib_last_activity,
        SUM(estimated_fee_income_zar) AS cib_estimated_revenue
    FROM {{ ref('mart_cib_client_flows') }}
    GROUP BY golden_id
),

-- Forex domain aggregation
forex_metrics AS (
    SELECT
        golden_id,
        COUNT(DISTINCT target_currency) AS forex_currencies_traded,
        SUM(trade_value_zar) AS forex_annual_volume,
        SUM(hedged_volume) AS forex_hedged_value,
        SUM(unhedged_volume) AS forex_unhedged_value,
        AVG(hedge_ratio_pct) AS forex_hedge_ratio_pct,
        COUNT(DISTINCT CASE WHEN open_forward_count > 0 THEN 1 END) AS forex_open_forwards,
        MAX(trade_date) AS forex_last_activity,
        SUM(estimated_fx_revenue_90d) AS forex_estimated_revenue
    FROM {{ ref('mart_forex_exposure') }}
    GROUP BY golden_id
),

-- Insurance domain aggregation
insurance_metrics AS (
    SELECT
        golden_id,
        COUNT(DISTINCT policy_id) AS insurance_active_policies,
        SUM(premium_annual_zar) AS insurance_annual_premium,
        SUM(sum_insured_zar) AS insurance_sum_insured,
        COUNT(DISTINCT CASE WHEN coverage_gap THEN 1 END) AS insurance_coverage_gaps,
        SUM(coverage_gap_amount_zar) AS insurance_coverage_gap_value,
        COUNT(DISTINCT CASE WHEN is_lapsing_90d THEN 1 END) AS insurance_lapsing_90d,
        SUM(open_claims_count) AS insurance_open_claims,
        AVG(loss_ratio_pct) AS insurance_loss_ratio,
        MAX(expiry_date) AS insurance_last_activity
    FROM {{ ref('mart_policy_analytics') }}
    GROUP BY golden_id
),

-- Cell network aggregation
cell_metrics AS (
    SELECT
        golden_id,
        SUM(active_sims) AS cell_total_sims,
        SUM(estimated_employees) AS cell_estimated_employees,
        COUNT(DISTINCT usage_country) AS cell_countries_active,
        AVG(sim_growth_pct_mom) AS cell_sim_growth_pct,
        SUM(monthly_data_usage_gb) AS cell_monthly_data_gb,
        SUM(momo_transaction_value) AS cell_momo_monthly_value,
        AVG(smartphone_pct) AS cell_smartphone_pct,
        SUM(ussd_banking_sessions) AS cell_ussd_banking_sessions,
        MAX(last_activity_date) AS cell_last_activity
    FROM {{ ref('mart_cell_intelligence') }}
    GROUP BY golden_id
),

-- PBB aggregation
pbb_metrics AS (
    SELECT
        golden_id,
        SUM(employee_count) AS pbb_employee_accounts,
        SUM(employee_count) AS pbb_total_employees,
        SUM(monthly_payroll_zar) AS pbb_monthly_payroll,
        AVG(average_salary_zar) AS pbb_average_salary,
        AVG(digital_adoption_pct) AS pbb_digital_adoption_pct,
        AVG(dormant_pct) AS pbb_dormant_pct,
        MAX(payroll_date) AS pbb_last_activity
    FROM {{ ref('mart_payroll_analytics') }}
    GROUP BY golden_id
),

-- Combine all domain metrics
combined AS (
    SELECT
        er.golden_id,
        er.canonical_name,
        er.registration_number,
        er.tax_number,
        er.home_country,
        er.client_tier,
        er.relationship_manager,
        er.client_segment,
        er.match_confidence,
        er.match_method,
        er.domains_matched,
        er.human_verified,
        er.verification_date,

        -- Domain presence flags
        COALESCE(cib.golden_id IS NOT NULL, FALSE) AS has_cib,
        COALESCE(forex.golden_id IS NOT NULL, FALSE) AS has_forex,
        COALESCE(insurance.golden_id IS NOT NULL, FALSE) AS has_insurance,
        COALESCE(cell.golden_id IS NOT NULL, FALSE) AS has_cell,
        COALESCE(pbb.golden_id IS NOT NULL, FALSE) AS has_pbb,

        -- Count of active domains
        (
            CASE WHEN cib.golden_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN forex.golden_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN insurance.golden_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN cell.golden_id IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN pbb.golden_id IS NOT NULL THEN 1 ELSE 0 END
        ) AS domains_active,

        -- Domain IDs
        er.cib_client_id,
        er.forex_client_id,
        er.insurance_client_id,
        er.cell_client_id,
        er.pbb_client_id,

        -- CIB metrics
        COALESCE(cib.cib_active_corridors, 0) AS cib_active_corridors,
        COALESCE(cib.cib_annual_value, 0) AS cib_annual_value,
        COALESCE(cib.cib_payment_count_90d, 0) AS cib_payment_count_90d,
        COALESCE(cib.cib_new_countries_90d, 0) AS cib_new_countries_90d,
        cib.cib_last_activity,
        COALESCE(cib.cib_estimated_revenue, 0) AS cib_estimated_revenue,

        -- Forex metrics
        COALESCE(forex.forex_currencies_traded, 0) AS forex_currencies_traded,
        COALESCE(forex.forex_annual_volume, 0) AS forex_annual_volume,
        COALESCE(forex.forex_hedged_value, 0) AS forex_hedged_value,
        COALESCE(forex.forex_unhedged_value, 0) AS forex_unhedged_value,
        COALESCE(forex.forex_hedge_ratio_pct, 0) AS forex_hedge_ratio_pct,
        COALESCE(forex.forex_open_forwards, 0) AS forex_open_forwards,
        forex.forex_last_activity,
        COALESCE(forex.forex_estimated_revenue, 0) AS forex_estimated_revenue,

        -- Insurance metrics
        COALESCE(insurance.insurance_active_policies, 0) AS insurance_active_policies,
        COALESCE(insurance.insurance_annual_premium, 0) AS insurance_annual_premium,
        COALESCE(insurance.insurance_sum_insured, 0) AS insurance_sum_insured,
        COALESCE(insurance.insurance_coverage_gaps, 0) AS insurance_coverage_gaps,
        COALESCE(insurance.insurance_coverage_gap_value, 0) AS insurance_coverage_gap_value,
        COALESCE(insurance.insurance_lapsing_90d, 0) AS insurance_lapsing_90d,
        COALESCE(insurance.insurance_open_claims, 0) AS insurance_open_claims,
        COALESCE(insurance.insurance_loss_ratio, 0) AS insurance_loss_ratio,
        insurance.insurance_last_activity,

        -- Cell metrics
        COALESCE(cell.cell_total_sims, 0) AS cell_total_sims,
        COALESCE(cell.cell_estimated_employees, 0) AS cell_estimated_employees,
        COALESCE(cell.cell_countries_active, 0) AS cell_countries_active,
        COALESCE(cell.cell_sim_growth_pct, 0) AS cell_sim_growth_pct,
        COALESCE(cell.cell_monthly_data_gb, 0) AS cell_monthly_data_gb,
        COALESCE(cell.cell_momo_monthly_value, 0) AS cell_momo_monthly_value,
        COALESCE(cell.cell_smartphone_pct, 0) AS cell_smartphone_pct,
        COALESCE(cell.cell_ussd_banking_sessions, 0) AS cell_ussd_banking_sessions,
        cell.cell_last_activity,

        -- PBB metrics
        COALESCE(pbb.pbb_employee_accounts, 0) AS pbb_employee_accounts,
        COALESCE(pbb.pbb_total_employees, 0) AS pbb_total_employees,
        COALESCE(pbb.pbb_monthly_payroll, 0) AS pbb_monthly_payroll,
        COALESCE(pbb.pbb_average_salary, 0) AS pbb_average_salary,
        COALESCE(pbb.pbb_digital_adoption_pct, 0) AS pbb_digital_adoption_pct,
        COALESCE(pbb.pbb_dormant_pct, 0) AS pbb_dormant_pct,
        pbb.pbb_last_activity

    FROM entity_resolution er
    LEFT JOIN cib_metrics cib ON er.golden_id = cib.golden_id
    LEFT JOIN forex_metrics forex ON er.golden_id = forex.golden_id
    LEFT JOIN insurance_metrics insurance ON er.golden_id = insurance.golden_id
    LEFT JOIN cell_metrics cell ON er.golden_id = cell.golden_id
    LEFT JOIN pbb_metrics pbb ON er.golden_id = pbb.golden_id
),

-- Calculate derived fields
with_derived AS (
    SELECT
        *,

        -- Total relationship value
        (
            COALESCE(cib_annual_value, 0) +
            COALESCE(forex_annual_volume, 0) +
            COALESCE(insurance_annual_premium, 0) +
            COALESCE(cib_estimated_revenue, 0) +
            COALESCE(forex_estimated_revenue, 0)
        ) AS total_relationship_value_zar,

        -- Cross-sell score (based on product gaps)
        CASE
            WHEN domains_active = 1 THEN 95
            WHEN domains_active = 2 THEN 75
            WHEN domains_active = 3 THEN 50
            WHEN domains_active = 4 THEN 25
            ELSE 0
        END AS cross_sell_score,

        -- Missing product count
        (5 - domains_active) AS missing_product_count,

        -- Last activity across all domains
        GREATEST(
            COALESCE(cib_last_activity, DATE '1900-01-01'),
            COALESCE(forex_last_activity, DATE '1900-01-01'),
            COALESCE(insurance_last_activity, DATE '1900-01-01'),
            COALESCE(cell_last_activity, DATE '1900-01-01'),
            COALESCE(pbb_last_activity, DATE '1900-01-01')
        ) AS last_activity_any_domain,

        -- Cell-PBB capture ratio
        CASE
            WHEN COALESCE(pbb_total_employees, 0) > 0
            THEN ROUND(COALESCE(cell_estimated_employees, 0)::NUMERIC / pbb_total_employees::NUMERIC, 2)
            ELSE NULL
        END AS cell_pbb_capture_ratio

    FROM combined
)

SELECT
    golden_id,
    canonical_name,
    registration_number,
    tax_number,
    home_country,
    client_tier,
    relationship_manager,
    client_segment,
    match_confidence,
    match_method,
    domains_matched,
    human_verified,
    verification_date,

    -- Domain presence
    has_cib,
    has_forex,
    has_insurance,
    has_cell,
    has_pbb,
    domains_active,

    -- Domain IDs
    cib_client_id,
    forex_client_id,
    insurance_client_id,
    cell_client_id,
    pbb_client_id,

    -- CIB metrics
    cib_active_corridors,
    cib_annual_value,
    cib_payment_count_90d,
    cib_new_countries_90d,
    CASE
        WHEN cib_payment_count_90d = 0 THEN 'inactive'
        WHEN cib_payment_count_90d < 10 THEN 'low'
        WHEN cib_payment_count_90d < 50 THEN 'medium'
        ELSE 'high'
    END AS cib_health_status,
    cib_last_activity,
    cib_estimated_revenue,

    -- Forex metrics
    forex_currencies_traded,
    forex_annual_volume,
    forex_hedged_value,
    forex_unhedged_value,
    forex_hedge_ratio_pct,
    CASE WHEN COALESCE(forex_hedge_ratio_pct, 0) >= 80 THEN TRUE ELSE FALSE END AS forex_is_adequately_hedged,
    forex_open_forwards,
    forex_last_activity,
    forex_estimated_revenue,

    -- Insurance metrics
    insurance_active_policies,
    insurance_annual_premium,
    insurance_sum_insured,
    insurance_coverage_gaps,
    insurance_coverage_gap_value,
    insurance_lapsing_90d,
    insurance_open_claims,
    insurance_loss_ratio,
    insurance_last_activity,

    -- Cell metrics
    cell_total_sims,
    cell_estimated_employees,
    cell_countries_active,
    cell_sim_growth_pct,
    CASE WHEN COALESCE(cell_sim_growth_pct, 0) > 5 THEN TRUE ELSE FALSE END AS cell_is_expanding,
    cell_monthly_data_gb,
    cell_momo_monthly_value,
    cell_smartphone_pct,
    cell_ussd_banking_sessions,
    cell_last_activity,

    -- PBB metrics
    pbb_employee_accounts,
    pbb_total_employees,
    pbb_monthly_payroll,
    pbb_average_salary,
    pbb_digital_adoption_pct,
    pbb_dormant_pct,
    pbb_last_activity,

    -- Derived fields
    total_relationship_value_zar,

    -- Cross-sell priority
    CASE
        WHEN domains_active <= 2 AND total_relationship_value_zar > 1000000 THEN 'high'
        WHEN domains_active <= 3 AND total_relationship_value_zar > 500000 THEN 'medium'
        ELSE 'low'
    END AS cross_sell_priority,
    cross_sell_score,
    missing_product_count,

    -- Primary risk signal
    CASE
        WHEN COALESCE(forex_unhedged_value, 0) > 1000000 THEN 'fx_exposure'
        WHEN COALESCE(insurance_coverage_gaps, 0) > 0 THEN 'insurance_gap'
        WHEN COALESCE(cell_sim_growth_pct, 0) < -10 THEN 'client_attrition'
        WHEN COALESCE(pbb_dormant_pct, 0) > 30 THEN 'dormant_accounts'
        ELSE 'none'
    END AS primary_risk_signal,

    -- Risk score
    (
        CASE WHEN COALESCE(forex_unhedged_value, 0) > 1000000 THEN 25 ELSE 0 END +
        CASE WHEN COALESCE(insurance_coverage_gaps, 0) > 0 THEN 20 ELSE 0 END +
        CASE WHEN COALESCE(cell_sim_growth_pct, 0) < -10 THEN 25 ELSE 0 END +
        CASE WHEN COALESCE(pbb_dormant_pct, 0) > 30 THEN 15 ELSE 0 END +
        CASE WHEN domains_active = 1 THEN 15 ELSE 0 END
    ) AS risk_score,

    -- Workforce capture
    cell_pbb_capture_ratio,
    CASE
        WHEN COALESCE(cell_estimated_employees, 0) > COALESCE(pbb_total_employees, 0)
        THEN COALESCE(cell_estimated_employees, 0) - COALESCE(pbb_total_employees, 0)
        ELSE 0
    END AS uncaptured_employees,

    -- Data shadow health
    (100 - (missing_product_count * 20)) AS shadow_health_score,
    missing_product_count AS shadow_open_gaps,
    (missing_product_count * 50000) AS shadow_total_opportunity,

    -- Days since activity
    CASE
        WHEN last_activity_any_domain > DATE '1900-01-01'
        THEN DATE_PART('day', CURRENT_DATE - last_activity_any_domain)::INTEGER
        ELSE NULL
    END AS days_since_any_activity,

    -- Metadata
    'POPIA_RESTRICTED' AS data_classification,
    home_country IN ('ZA', 'NG', 'KE') AS contains_za_pii,
    CURRENT_TIMESTAMP AS record_created_at,
    CURRENT_TIMESTAMP AS record_updated_at,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date

FROM with_derived
WHERE domains_active >= 1
