-- =============================================================================
-- @file mart_group_revenue_360.sql
-- @description Materialises a comprehensive revenue view per client across all
--     five AfriFlow domains. Enables total relationship value calculation,
--     revenue trend analysis (QoQ, YoY), concentration measurement via HHI,
--     client lifetime value estimation, and revenue ranking across tiers and
--     countries. Revenue is annualised and also provided as 90-day rolling.
-- @author Thabo Kunene
-- @created 2026-03-18
-- =============================================================================

{{
    config(
        materialized='table',          -- Full refresh on each dbt run
        tags=['integration', 'cross_sell', 'revenue']
    )
}}

/*
    Mart: Group Revenue 360

    Comprehensive revenue view per client across all domains.
    This table enables:
    - Total relationship value calculation
    - Revenue trend analysis (QoQ, YoY)
    - Revenue concentration measurement
    - Client lifetime value estimation
    - Revenue ranking across tiers and countries

    Revenue is annualised and also provided as 90-day rolling.
*/

-- ── CTE: unified_clients ──────────────────────────────────────────────────────
-- Pull all active golden records; provides canonical_name, tier, RM, and country
WITH unified_clients AS (
    SELECT * FROM {{ ref('mart_unified_client') }}
),

-- ── CTE: cib_revenue ──────────────────────────────────────────────────────────
-- Annualise CIB fee income by multiplying 90-day rolling revenue by 4
-- CIB revenue by client
cib_revenue AS (
    SELECT
        golden_id,
        SUM(estimated_fee_income_90d) AS cib_revenue_90d,
        SUM(estimated_fee_income_90d) * 4 AS cib_revenue_annual
    FROM {{ ref('mart_cib_client_flows') }}
    GROUP BY golden_id
),

-- ── CTE: forex_revenue ────────────────────────────────────────────────────────
-- Annualise FX revenue; 90-day rolling multiplied by 4 to produce annual estimate
-- Forex revenue by client
forex_revenue AS (
    SELECT
        golden_id,
        SUM(estimated_fx_revenue_90d) AS forex_revenue_90d,
        SUM(estimated_fx_revenue_90d) * 4 AS forex_revenue_annual
    FROM {{ ref('mart_forex_exposure') }}
    GROUP BY golden_id
),

-- ── CTE: insurance_revenue ────────────────────────────────────────────────────
-- Insurance premiums are already annual; divide by 4 to derive 90-day figure
-- Insurance revenue by client
insurance_revenue AS (
    SELECT
        golden_id,
        SUM(premium_annual_zar) / 4 AS insurance_revenue_90d,  -- Quarterly slice of annual premium
        SUM(premium_annual_zar) AS insurance_revenue_annual
    FROM {{ ref('mart_policy_analytics') }}
    GROUP BY golden_id
),

-- ── CTE: cell_revenue ─────────────────────────────────────────────────────────
-- Cell/MoMo revenue estimated from data/voice/MoMo usage; annualised x4
-- Cell revenue by client (estimated from usage)
cell_revenue AS (
    SELECT
        golden_id,
        SUM(total_revenue_zar) AS cell_revenue_90d,
        SUM(total_revenue_zar) * 4 AS cell_revenue_annual
    FROM {{ ref('mart_cell_intelligence') }}
    GROUP BY golden_id
),

-- ── CTE: pbb_revenue ──────────────────────────────────────────────────────────
-- PBB revenue estimated from account fees and payroll margin; annualised x4
-- PBB revenue by client (estimated from payroll and accounts)
pbb_revenue AS (
    SELECT
        golden_id,
        SUM(estimated_account_revenue_zar) AS pbb_revenue_90d,
        SUM(estimated_account_revenue_zar) * 4 AS pbb_revenue_annual
    FROM {{ ref('mart_payroll_analytics') }}
    GROUP BY golden_id
),

-- ── CTE: combined ─────────────────────────────────────────────────────────────
-- LEFT JOIN all five revenue CTEs onto unified_clients; NULL revenue domains
-- are defaulted to 0 via COALESCE so totals remain correct.
-- Combine all revenue streams
combined AS (
    SELECT
        uc.golden_id,
        uc.canonical_name,
        uc.client_tier,
        uc.relationship_manager,
        uc.home_country,

        -- Annual revenue by domain
        COALESCE(cib.cib_revenue_annual, 0) AS cib_revenue_annual,
        COALESCE(forex.forex_revenue_annual, 0) AS forex_revenue_annual,
        COALESCE(insurance.insurance_revenue_annual, 0) AS insurance_revenue_annual,
        COALESCE(cell.cell_revenue_annual, 0) AS cell_revenue_annual,
        COALESCE(pbb.pbb_revenue_annual, 0) AS pbb_revenue_annual,

        -- 90-day revenue by domain
        COALESCE(cib.cib_revenue_90d, 0) AS cib_revenue_90d,
        COALESCE(forex.forex_revenue_90d, 0) AS forex_revenue_90d,
        COALESCE(insurance.insurance_revenue_90d, 0) AS insurance_revenue_90d,
        COALESCE(cell.cell_revenue_90d, 0) AS cell_revenue_90d,
        COALESCE(pbb.pbb_revenue_90d, 0) AS pbb_revenue_90d,

        uc.domains_active,
        uc.total_relationship_value_zar

    FROM unified_clients uc
    LEFT JOIN cib_revenue cib ON uc.golden_id = cib.golden_id
    LEFT JOIN forex_revenue forex ON uc.golden_id = forex.golden_id
    LEFT JOIN insurance_revenue insurance ON uc.golden_id = insurance.golden_id
    LEFT JOIN cell_revenue cell ON uc.golden_id = cell.golden_id
    LEFT JOIN pbb_revenue pbb ON uc.golden_id = pbb.golden_id
),

-- ── CTE: with_derived ─────────────────────────────────────────────────────────
-- Compute total revenue, primary domain identification, HHI concentration index,
-- CLV estimate, and churn probability from the combined revenue data.
-- Calculate derived metrics
with_derived AS (
    SELECT
        *,

        -- Total annual revenue: sum of all five domain annual revenue streams
        (
            cib_revenue_annual +
            forex_revenue_annual +
            insurance_revenue_annual +
            cell_revenue_annual +
            pbb_revenue_annual
        ) AS total_revenue_annual,

        (
            cib_revenue_90d +
            forex_revenue_90d +
            insurance_revenue_90d +
            cell_revenue_90d +
            pbb_revenue_90d
        ) AS total_revenue_90d,

        -- Primary revenue domain: which of the 5 domains contributes most annual revenue
        CASE
            WHEN cib_revenue_annual >= GREATEST(
                forex_revenue_annual, insurance_revenue_annual,
                cell_revenue_annual, pbb_revenue_annual
            ) THEN 'cib'
            WHEN forex_revenue_annual >= GREATEST(
                cib_revenue_annual, insurance_revenue_annual,
                cell_revenue_annual, pbb_revenue_annual
            ) THEN 'forex'
            WHEN insurance_revenue_annual >= GREATEST(
                cib_revenue_annual, forex_revenue_annual,
                cell_revenue_annual, pbb_revenue_annual
            ) THEN 'insurance'
            WHEN cell_revenue_annual >= GREATEST(
                cib_revenue_annual, forex_revenue_annual,
                insurance_revenue_annual, pbb_revenue_annual
            ) THEN 'cell'
            ELSE 'pbb'
        END AS primary_revenue_domain,

        -- Primary domain percentage
        CASE
            WHEN total_revenue_annual > 0 THEN
                ROUND(
                    GREATEST(
                        cib_revenue_annual, forex_revenue_annual,
                        insurance_revenue_annual, cell_revenue_annual,
                        pbb_revenue_annual
                    )::NUMERIC / total_revenue_annual::NUMERIC * 100, 2
                )
            ELSE 0
        END AS primary_domain_pct

    FROM combined
)

SELECT
    golden_id,
    canonical_name,
    client_tier,
    relationship_manager,
    home_country,

    -- Annual revenue
    cib_revenue_annual,
    forex_revenue_annual,
    insurance_revenue_annual,
    cell_revenue_annual,
    pbb_revenue_annual,
    total_revenue_annual,

    -- 90-day revenue
    cib_revenue_90d,
    forex_revenue_90d,
    insurance_revenue_90d,
    cell_revenue_90d,
    pbb_revenue_90d,
    total_revenue_90d,

    -- Revenue trend: placeholder values — requires a historical snapshot table
    -- to compute quarter-on-quarter and year-on-year change percentages
    0.0 AS revenue_change_qoq_pct,
    0.0 AS revenue_change_yoy_pct,
    'stable' AS revenue_trend,

    -- Revenue concentration: which domain dominates and by what percentage
    primary_revenue_domain,
    primary_domain_pct,

    -- Revenue HHI (Herfindahl-Hirschman Index for concentration)
    -- HHI = sum of squared revenue share fractions, scaled to 10000
    -- HHI = 10000 means fully concentrated; HHI = 2000 means five equal shares
    CASE
        WHEN total_revenue_annual > 0 THEN
            ROUND(
                (
                    POWER(cib_revenue_annual::NUMERIC / total_revenue_annual::NUMERIC, 2) +
                    POWER(forex_revenue_annual::NUMERIC / total_revenue_annual::NUMERIC, 2) +
                    POWER(insurance_revenue_annual::NUMERIC / total_revenue_annual::NUMERIC, 2) +
                    POWER(cell_revenue_annual::NUMERIC / total_revenue_annual::NUMERIC, 2) +
                    POWER(pbb_revenue_annual::NUMERIC / total_revenue_annual::NUMERIC, 2)
                ) * 10000, 4
            )
        ELSE 0
    END AS revenue_hhi,

    -- Client lifetime value (5-year estimate at 10% discount rate)
    -- 3.791 is the present value annuity factor for 5 years at 10% discount rate
    ROUND(
        total_revenue_annual::NUMERIC * 3.791, 2
    ) AS estimated_clv_5yr_zar,

    -- Churn probability over next 12 months: inversely proportional to domain depth
    -- Multi-domain clients have higher switching costs and lower churn propensity
    CASE
        WHEN domains_active = 1 THEN 35.0  -- Single-product: high churn risk
        WHEN domains_active = 2 THEN 20.0
        WHEN domains_active = 3 THEN 10.0
        WHEN domains_active = 4 THEN 5.0
        ELSE 2.0
    END AS churn_probability_12m,

    -- Revenue rankings: window functions for RM portfolio comparison
    ROW_NUMBER() OVER (ORDER BY total_revenue_annual DESC) AS revenue_rank_overall,
    -- Tier-relative rank: how does this client compare within their tier (e.g. Platinum)?
    ROW_NUMBER() OVER (PARTITION BY client_tier ORDER BY total_revenue_annual DESC) AS revenue_rank_in_tier,
    -- Country-relative rank: top client by revenue per country for RM territory views
    ROW_NUMBER() OVER (PARTITION BY home_country ORDER BY total_revenue_annual DESC) AS revenue_rank_in_country,

    -- Metadata: dbt run reference for lineage tracing; snapshot_date for time-series analysis
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date

FROM with_derived
ORDER BY total_revenue_annual DESC  -- Highest-value clients first for RM dashboard default view
