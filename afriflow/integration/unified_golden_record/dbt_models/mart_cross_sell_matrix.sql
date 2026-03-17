{{
    config(
        materialized='table',
        tags=['integration', 'cross_sell', 'opportunity']
    )
}}

/*
    Mart: Cross-Sell Matrix

    Identifies product gaps for every client across all domains.
    This table powers:
    - Next Best Action recommendations
    - Cross-sell prioritization
    - Product penetration analysis
    - Revenue opportunity sizing

    The matrix shows current holdings, identifies gaps, and
    prioritises the next best product to offer each client.
*/

WITH unified_clients AS (
    SELECT * FROM {{ ref('mart_unified_client') }}
),

-- CIB product holdings
cib_holdings AS (
    SELECT
        golden_id,
        MAX(CASE WHEN payment_count_90d > 0 THEN TRUE ELSE FALSE END) AS has_cib_payments,
        COUNT(DISTINCT corridor) > 0 AS has_cib_trade_finance,
        COUNT(DISTINCT CASE WHEN is_cash_management THEN 1 END) > 0 AS has_cib_cash_management
    FROM {{ ref('mart_cib_client_flows') }}
    GROUP BY golden_id
),

-- Forex product holdings
forex_holdings AS (
    SELECT
        golden_id,
        MAX(CASE WHEN trade_type = 'SPOT' THEN TRUE ELSE FALSE END) AS has_forex_spot,
        MAX(CASE WHEN trade_type = 'FORWARD' THEN TRUE ELSE FALSE END) AS has_forex_forwards,
        MAX(CASE WHEN trade_type IN ('OPTION_CALL', 'OPTION_PUT') THEN TRUE ELSE FALSE END) AS has_forex_options
    FROM {{ ref('mart_forex_exposure') }}
    GROUP BY golden_id
),

-- Insurance product holdings
insurance_holdings AS (
    SELECT
        golden_id,
        MAX(CASE WHEN policy_type IN ('asset', 'property', 'marine') THEN TRUE ELSE FALSE END) AS has_insurance_asset,
        MAX(CASE WHEN policy_type IN ('credit', 'surety', 'guarantee') THEN TRUE ELSE FALSE END) AS has_insurance_credit,
        MAX(CASE WHEN policy_type IN ('liability', 'directors', 'professional') THEN TRUE ELSE FALSE END) AS has_insurance_liability
    FROM {{ ref('mart_policy_analytics') }}
    GROUP BY golden_id
),

-- Cell product holdings
cell_holdings AS (
    SELECT
        golden_id,
        MAX(CASE WHEN active_sims > 0 THEN TRUE ELSE FALSE END) AS has_cell_corporate_sim,
        MAX(CASE WHEN momo_transaction_value > 0 THEN TRUE ELSE FALSE END) AS has_cell_momo
    FROM {{ ref('mart_cell_intelligence') }}
    GROUP BY golden_id
),

-- PBB product holdings
pbb_holdings AS (
    SELECT
        golden_id,
        MAX(CASE WHEN employee_count > 0 THEN TRUE ELSE FALSE END) AS has_pbb_payroll,
        MAX(CASE WHEN digital_adoption_pct > 0 THEN TRUE ELSE FALSE END) AS has_pbb_employee_banking
    FROM {{ ref('mart_payroll_analytics') }}
    GROUP BY golden_id
),

-- Combine holdings
combined AS (
    SELECT
        uc.golden_id,
        uc.canonical_name,
        uc.client_tier,
        uc.relationship_manager,
        uc.domains_active,

        -- Current holdings
        COALESCE(cib.has_cib_payments, FALSE) AS has_cib_payments,
        COALESCE(cib.has_cib_trade_finance, FALSE) AS has_cib_trade_finance,
        COALESCE(cib.has_cib_cash_management, FALSE) AS has_cib_cash_management,
        COALESCE(forex.has_forex_spot, FALSE) AS has_forex_spot,
        COALESCE(forex.has_forex_forwards, FALSE) AS has_forex_forwards,
        COALESCE(forex.has_forex_options, FALSE) AS has_forex_options,
        COALESCE(insurance.has_insurance_asset, FALSE) AS has_insurance_asset,
        COALESCE(insurance.has_insurance_credit, FALSE) AS has_insurance_credit,
        COALESCE(insurance.has_insurance_liability, FALSE) AS has_insurance_liability,
        COALESCE(cell.has_cell_corporate_sim, FALSE) AS has_cell_corporate_sim,
        COALESCE(cell.has_cell_momo, FALSE) AS has_cell_momo,
        COALESCE(pbb.has_pbb_payroll, FALSE) AS has_pbb_payroll,
        COALESCE(pbb.has_pbb_employee_banking, FALSE) AS has_pbb_employee_banking,

        -- Revenue data
        uc.total_relationship_value_zar,
        uc.forex_unhedged_value,
        uc.insurance_coverage_gap_value,
        uc.cell_estimated_employees,
        uc.pbb_total_employees,
        uc.pbb_dormant_pct

    FROM unified_clients uc
    LEFT JOIN cib_holdings cib ON uc.golden_id = cib.golden_id
    LEFT JOIN forex_holdings forex ON uc.golden_id = forex.golden_id
    LEFT JOIN insurance_holdings insurance ON uc.golden_id = insurance.golden_id
    LEFT JOIN cell_holdings cell ON uc.golden_id = cell.golden_id
    LEFT JOIN pbb_holdings pbb ON uc.golden_id = pbb.golden_id
),

-- Calculate product counts and gaps
with_gaps AS (
    SELECT
        *,

        -- Total products held
        (
            CASE WHEN has_cib_payments THEN 1 ELSE 0 END +
            CASE WHEN has_cib_trade_finance THEN 1 ELSE 0 END +
            CASE WHEN has_cib_cash_management THEN 1 ELSE 0 END +
            CASE WHEN has_forex_spot THEN 1 ELSE 0 END +
            CASE WHEN has_forex_forwards THEN 1 ELSE 0 END +
            CASE WHEN has_forex_options THEN 1 ELSE 0 END +
            CASE WHEN has_insurance_asset THEN 1 ELSE 0 END +
            CASE WHEN has_insurance_credit THEN 1 ELSE 0 END +
            CASE WHEN has_insurance_liability THEN 1 ELSE 0 END +
            CASE WHEN has_cell_corporate_sim THEN 1 ELSE 0 END +
            CASE WHEN has_cell_momo THEN 1 ELSE 0 END +
            CASE WHEN has_pbb_payroll THEN 1 ELSE 0 END +
            CASE WHEN has_pbb_employee_banking THEN 1 ELSE 0 END
        ) AS total_products_held,

        -- Total available products
        13 AS total_products_available,

        -- Gap identification
        NOT has_forex_forwards AND COALESCE(forex_unhedged_value, 0) > 0 AS gap_fx_hedging,
        COALESCE(forex_unhedged_value, 0) AS gap_fx_hedging_value,
        NOT has_insurance_asset AND NOT has_insurance_credit AS gap_insurance_coverage,
        'Multiple' AS gap_insurance_countries,
        NOT has_pbb_payroll AND COALESCE(cell_estimated_employees, 0) > COALESCE(pbb_total_employees, 0) AS gap_employee_banking,
        GREATEST(0, COALESCE(cell_estimated_employees, 0) - COALESCE(pbb_total_employees, 0)) AS gap_employee_count,
        NOT has_cib_trade_finance AS gap_trade_finance,
        NOT has_cib_cash_management AS gap_cash_management

    FROM combined
),

-- Calculate next best action
with_nba AS (
    SELECT
        *,

        -- Product penetration
        ROUND(total_products_held::NUMERIC / total_products_available::NUMERIC * 100, 2) AS product_penetration_pct,

        -- Next Best Action logic
        CASE
            WHEN gap_fx_hedging AND forex_unhedged_value > 1000000 THEN 'FX Forward Hedge'
            WHEN gap_employee_banking AND gap_employee_count > 50 THEN 'PBB Payroll Solution'
            WHEN gap_insurance_coverage THEN 'Asset/Credit Insurance'
            WHEN gap_trade_finance THEN 'Trade Finance Facility'
            WHEN gap_cash_management THEN 'Cash Management Sweep'
            WHEN NOT has_forex_options AND forex_unhedged_value > 5000000 THEN 'FX Options'
            WHEN NOT has_cell_momo AND cell_estimated_employees > 100 THEN 'MoMo Integration'
            ELSE 'Relationship Review'
        END AS nba_product_1,

        CASE
            WHEN gap_fx_hedging AND forex_unhedged_value > 1000000 THEN forex_unhedged_value * 0.005
            WHEN gap_employee_banking THEN gap_employee_count * 5000
            WHEN gap_insurance_coverage THEN 100000
            WHEN gap_trade_finance THEN 50000
            ELSE 25000
        END AS nba_product_1_value,

        CASE
            WHEN gap_fx_hedging AND forex_unhedged_value > 1000000 THEN 0.85
            WHEN gap_employee_banking AND gap_employee_count > 50 THEN 0.75
            WHEN gap_insurance_coverage THEN 0.65
            WHEN gap_trade_finance THEN 0.60
            ELSE 0.50
        END AS nba_product_1_confidence,

        CASE
            WHEN gap_fx_hedging AND forex_unhedged_value > 1000000 THEN 'FX Options'
            WHEN gap_employee_banking THEN 'Employee Cards'
            WHEN gap_insurance_coverage THEN 'Liability Insurance'
            ELSE 'Digital Banking'
        END AS nba_product_2,

        CASE
            WHEN gap_fx_hedging AND forex_unhedged_value > 1000000 THEN forex_unhedged_value * 0.002
            WHEN gap_employee_banking THEN gap_employee_count * 500
            ELSE 15000
        END AS nba_product_2_value,

        CASE
            WHEN gap_insurance_coverage THEN 'Credit Insurance'
            WHEN NOT has_cell_momo THEN 'MoMo Salary Disbursement'
            ELSE 'Working Capital'
        END AS nba_product_3,

        CASE
            WHEN gap_insurance_coverage THEN 75000
            WHEN NOT has_cell_momo THEN 30000
            ELSE 50000
        END AS nba_product_3_value

    FROM with_gaps
)

SELECT
    golden_id,
    canonical_name,
    client_tier,
    relationship_manager,

    -- Current holdings
    has_cib_payments,
    has_cib_trade_finance,
    has_cib_cash_management,
    has_forex_spot,
    has_forex_forwards,
    has_forex_options,
    has_insurance_asset,
    has_insurance_credit,
    has_insurance_liability,
    has_cell_corporate_sim,
    has_cell_momo,
    has_pbb_payroll,
    has_pbb_employee_banking,

    -- Product counts
    total_products_held,
    total_products_available,
    product_penetration_pct,

    -- Gap identification
    gap_fx_hedging,
    gap_fx_hedging_value,
    gap_insurance_coverage,
    gap_insurance_countries,
    gap_employee_banking,
    gap_employee_count,
    gap_trade_finance,
    gap_cash_management,

    -- Next Best Action
    nba_product_1,
    nba_product_1_value,
    nba_product_1_confidence,
    nba_product_2,
    nba_product_2_value,
    nba_product_3,
    nba_product_3_value,

    -- Total opportunity
    (
        COALESCE(nba_product_1_value, 0) +
        COALESCE(nba_product_2_value, 0) +
        COALESCE(nba_product_3_value, 0)
    ) AS total_opportunity_zar,

    -- Cross-sell priority
    CASE
        WHEN total_products_held <= 3 AND total_relationship_value_zar > 1000000 THEN 'critical'
        WHEN total_products_held <= 5 AND total_relationship_value_zar > 500000 THEN 'high'
        WHEN total_products_held <= 8 THEN 'medium'
        ELSE 'low'
    END AS cross_sell_priority,

    -- Metadata
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date

FROM with_nba
ORDER BY total_opportunity_zar DESC
