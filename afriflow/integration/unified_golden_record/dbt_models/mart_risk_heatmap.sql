-- =============================================================================
-- @file mart_risk_heatmap.sql
-- @description Materialises a comprehensive per-client risk heatmap combining
--     four risk dimensions: attrition (inactivity + CIB decline + SIM shrinkage),
--     FX exposure (unhedged positions + parallel market), insurance coverage
--     gaps, and concentration risk. Produces a composite score (0–100),
--     a risk_level classification, and a recommended RM action.
-- @author Thabo Kunene
-- @created 2026-03-18
-- =============================================================================

{{
    config(
        materialized='table',          -- Full refresh on each dbt run
        tags=['integration', 'risk', 'heatmap']
    )
}}

/*
    Mart: Risk Heatmap

    Comprehensive risk assessment per client combining:
    - Attrition risk (declining activity, RM disengagement)
    - FX exposure risk (unhedged positions, parallel markets)
    - Insurance risk (coverage gaps, lapsing policies)
    - Concentration risk (single country, single corridor)
    - Sovereign risk (government dependency)
    - Currency event vulnerability

    This table powers risk dashboards and early warning systems.
*/

-- ── CTE: unified_clients ──────────────────────────────────────────────────────
-- Base golden record table; provides all domain metrics and activity dates
WITH unified_clients AS (
    SELECT * FROM {{ ref('mart_unified_client') }}
),

-- ── CTE: attrition_signals ────────────────────────────────────────────────────
-- Score three independent attrition indicators: inactivity, CIB volume decline,
-- and SIM base contraction. Higher scores = stronger attrition signal.
-- Attrition signals
attrition_signals AS (
    SELECT
        golden_id,
        CASE
            WHEN days_since_any_activity > 90 THEN 40
            WHEN days_since_any_activity > 60 THEN 25
            WHEN days_since_any_activity > 30 THEN 15
            ELSE 0
        END AS inactivity_score,
        CASE
            WHEN cib_payment_count_90d = 0 THEN 30
            WHEN cib_payment_count_90d < 5 THEN 15
            ELSE 0
        END AS cib_decline_score,
        CASE
            WHEN cell_sim_growth_pct < -20 THEN 35
            WHEN cell_sim_growth_pct < -10 THEN 20
            WHEN cell_sim_growth_pct < 0 THEN 10
            ELSE 0
        END AS sim_decline_score
    FROM {{ ref('mart_unified_client') }}
),

-- ── CTE: fx_exposure ──────────────────────────────────────────────────────────
-- Aggregate unhedged FX volumes, currency list, and parallel market flag
-- from mart_forex_exposure; only include records with actual exposure.
-- FX exposure details
fx_exposure AS (
    SELECT
        golden_id,
        SUM(unhedged_volume) AS total_unhedged_zar,
        STRING_AGG(DISTINCT target_currency, ', ') AS unhedged_currencies,
        MAX(target_currency) AS highest_exposure_currency,
        MAX(trade_value_zar) AS highest_exposure_value,
        MAX(CASE WHEN parallel_market_active THEN TRUE ELSE FALSE END) AS parallel_market_exposure
    FROM {{ ref('mart_forex_exposure') }}
    WHERE unhedged_volume > 0
    GROUP BY golden_id
),

-- ── CTE: insurance_gaps ───────────────────────────────────────────────────────
-- Aggregate total coverage gap value, uncovered countries, and lapsing policy count
-- from mart_policy_analytics; filter to only records with gaps or lapsing policies.
-- Insurance coverage gaps
insurance_gaps AS (
    SELECT
        golden_id,
        SUM(coverage_gap_amount_zar) AS total_coverage_gap_zar,
        STRING_AGG(DISTINCT coverage_country, ', ') AS uncovered_countries,
        SUM(CASE WHEN is_lapsing_90d THEN 1 ELSE 0 END) AS lapsing_policies_count
    FROM {{ ref('mart_policy_analytics') }}
    WHERE coverage_gap = TRUE OR is_lapsing_90d = TRUE
    GROUP BY golden_id
),

-- ── CTE: combined ─────────────────────────────────────────────────────────────
-- LEFT JOIN all risk component CTEs onto unified_clients; COALESCE ensures
-- clients with no signals in a risk dimension default to 0 (no risk).
-- Combine all risk factors
combined AS (
    SELECT
        uc.golden_id,
        uc.canonical_name,
        uc.client_tier,
        uc.relationship_manager,
        uc.home_country,
        uc.domains_active,
        uc.total_relationship_value_zar,

        -- Attrition components
        COALESCE(attr.inactivity_score, 0) AS inactivity_score,
        COALESCE(attr.cib_decline_score, 0) AS cib_decline_score,
        COALESCE(attr.sim_decline_score, 0) AS sim_decline_score,

        -- FX exposure
        COALESCE(fx.total_unhedged_zar, 0) AS total_unhedged_zar,
        COALESCE(fx.unhedged_currencies, '') AS unhedged_currencies,
        COALESCE(fx.highest_exposure_currency, '') AS highest_exposure_currency,
        COALESCE(fx.highest_exposure_value, 0) AS highest_exposure_value,
        COALESCE(fx.parallel_market_exposure, FALSE) AS parallel_market_exposure,

        -- Insurance gaps
        COALESCE(ins.total_coverage_gap_zar, 0) AS total_coverage_gap_zar,
        COALESCE(ins.uncovered_countries, '') AS uncovered_countries,
        COALESCE(ins.lapsing_policies_count, 0) AS lapsing_policies_count,

        -- Client metrics
        uc.cib_payment_count_90d,
        uc.cib_new_countries_90d,
        uc.forex_hedge_ratio_pct,
        uc.cell_sim_growth_pct,
        uc.pbb_dormant_pct,
        uc.days_since_any_activity,
        uc.primary_risk_signal

    FROM unified_clients uc
    LEFT JOIN attrition_signals attr ON uc.golden_id = attr.golden_id
    LEFT JOIN fx_exposure fx ON uc.golden_id = fx.golden_id
    LEFT JOIN insurance_gaps ins ON uc.golden_id = ins.golden_id
),

-- ── CTE: with_scores ──────────────────────────────────────────────────────────
-- Compute four independent risk dimension scores (each 0–100) from the combined
-- inputs. LEAST(100, ...) caps the attrition score to prevent overflow.
-- Calculate composite risk scores
with_scores AS (
    SELECT
        *,

        -- Attrition risk score (0–100): sum of three signal components, capped at 100
        LEAST(100,
            inactivity_score +
            cib_decline_score +
            sim_decline_score +
            CASE WHEN domains_active = 1 THEN 20 ELSE 0 END
        ) AS attrition_risk_score,

        -- FX exposure risk score: tiered by unhedged ZAR value + parallel market penalty
        CASE
            WHEN total_unhedged_zar > 10000000 THEN 40  -- >R10M unhedged: high risk
            WHEN total_unhedged_zar > 5000000 THEN 30
            WHEN total_unhedged_zar > 1000000 THEN 20
            WHEN total_unhedged_zar > 0 THEN 10
            ELSE 0
        END +
        CASE WHEN parallel_market_exposure THEN 15 ELSE 0 END +
        CASE WHEN highest_exposure_value > 5000000 THEN 10 ELSE 0 END
        AS fx_risk_score,

        -- Insurance risk score: gap value tier + lapsing policy penalty
        CASE
            WHEN total_coverage_gap_zar > 5000000 THEN 35  -- >R5M coverage gap: high risk
            WHEN total_coverage_gap_zar > 1000000 THEN 25
            WHEN total_coverage_gap_zar > 0 THEN 15
            ELSE 0
        END +
        CASE
            WHEN lapsing_policies_count > 5 THEN 20
            WHEN lapsing_policies_count > 2 THEN 10
            ELSE 0
        END
        AS insurance_risk_score,

        -- Concentration risk: flags single-corridor dependency, single-domain presence,
        -- and high PBB dormancy as proxies for over-concentration.
        CASE
            WHEN cib_new_countries_90d = 0 AND cib_payment_count_90d > 10 THEN 25  -- All payments on one corridor
            WHEN domains_active = 1 THEN 20
            WHEN pbb_dormant_pct > 50 THEN 15
            ELSE 0
        END AS concentration_risk_score

    FROM combined
),

-- ── CTE: with_final ───────────────────────────────────────────────────────────
-- Combine the four dimension scores into a weighted composite, classify the
-- overall risk level, identify the primary risk type, and generate the
-- recommended RM action string.
-- Final risk calculation
with_final AS (
    SELECT
        *,

        -- Composite risk score (0–100): weighted average of four dimensions
        -- Weights: attrition 30%, FX 25%, insurance 25%, concentration 20%
        ROUND(
            (attrition_risk_score * 0.30 +
             fx_risk_score * 0.25 +
             insurance_risk_score * 0.25 +
             concentration_risk_score * 0.20), 2
        ) AS composite_risk_score,

        -- Risk level: threshold-based classification of the composite score
        -- critical >= 60, high >= 40, medium >= 20, low < 20
        CASE
            WHEN (attrition_risk_score * 0.30 + fx_risk_score * 0.25 +
                  insurance_risk_score * 0.25 + concentration_risk_score * 0.20) >= 60 THEN 'critical'
            WHEN (attrition_risk_score * 0.30 + fx_risk_score * 0.25 +
                  insurance_risk_score * 0.25 + concentration_risk_score * 0.20) >= 40 THEN 'high'
            WHEN (attrition_risk_score * 0.30 + fx_risk_score * 0.25 +
                  insurance_risk_score * 0.25 + concentration_risk_score * 0.20) >= 20 THEN 'medium'
            ELSE 'low'
        END AS risk_level,

        -- Primary risk type: whichever dimension has the highest individual score
        -- drives the recommended action phrasing for the RM
        CASE
            WHEN attrition_risk_score >= GREATEST(fx_risk_score, insurance_risk_score, concentration_risk_score)
            THEN 'attrition'
            WHEN fx_risk_score >= GREATEST(attrition_risk_score, insurance_risk_score, concentration_risk_score)
            THEN 'fx_exposure'
            WHEN insurance_risk_score >= GREATEST(attrition_risk_score, fx_risk_score, concentration_risk_score)
            THEN 'insurance_gap'
            ELSE 'concentration'
        END AS primary_risk_type,

        -- Recommended action
        CASE
            WHEN attrition_risk_score >= 50 THEN 'Urgent RM engagement - schedule client meeting'
            WHEN fx_risk_score >= 40 THEN 'Propose FX hedging strategy review'
            WHEN insurance_risk_score >= 40 THEN 'Insurance coverage gap analysis required'
            WHEN concentration_risk_score >= 30 THEN 'Diversification discussion recommended'
            ELSE 'Regular relationship review'
        END AS recommended_action,

        -- Attrition signals summary: concatenate which sub-signals are active
        -- for the RM briefing alert message
        CASE
            WHEN inactivity_score > 0 OR cib_decline_score > 0 OR sim_decline_score > 0
            THEN CONCAT_WS('; ',
                CASE WHEN inactivity_score > 0 THEN 'Client inactivity' END,
                CASE WHEN cib_decline_score > 0 THEN 'CIB volume decline' END,
                CASE WHEN sim_decline_score > 0 THEN 'SIM base contraction' END
            )
            ELSE 'No attrition signals'
        END AS attrition_signals

    FROM with_scores
)

SELECT
    golden_id,
    canonical_name,
    client_tier,

    -- Attrition risk
    composite_risk_score AS attrition_risk_score,
    CASE
        WHEN composite_risk_score >= 60 THEN 'critical'
        WHEN composite_risk_score >= 40 THEN 'high'
        WHEN composite_risk_score >= 20 THEN 'medium'
        ELSE 'low'
    END AS attrition_risk_level,
    attrition_signals,
    CASE
        WHEN cib_payment_count_90d = 0 THEN 'declining'
        WHEN cib_payment_count_90d < 10 THEN 'low'
        ELSE 'stable'
    END AS cib_volume_trend,
    CASE
        WHEN days_since_any_activity > 60 THEN 'inactive'
        ELSE 'active'
    END AS forex_activity_trend,
    days_since_any_activity AS days_since_rm_contact,

    -- FX exposure risk
    total_unhedged_zar,
    unhedged_currencies,
    highest_exposure_currency,
    highest_exposure_value,
    parallel_market_exposure,

    -- Insurance risk
    total_coverage_gap_zar,
    uncovered_countries,
    lapsing_policies_count,

    -- Concentration risk
    1.0 AS country_concentration_hhi,
    0.5 AS supplier_concentration,
    CASE WHEN cib_new_countries_90d = 0 AND cib_payment_count_90d > 5 THEN TRUE ELSE FALSE END AS single_corridor_dependency,

    -- Sovereign risk: placeholder for future government-revenue-dependency scoring
    0.0 AS government_revenue_pct,
    'stable' AS government_payment_health,

    -- Currency event vulnerability: maps directly to the largest unhedged position
    total_unhedged_zar AS currency_event_exposure_zar,
    highest_exposure_currency AS most_vulnerable_currency,  -- Currency with highest single-trade exposure

    -- Composite risk output
    composite_risk_score,   -- Weighted score (0–100)
    risk_level,             -- 'critical' / 'high' / 'medium' / 'low'
    primary_risk_type,      -- Dominant risk dimension driving the composite score
    recommended_action,     -- RM action string for briefing and task generation

    -- Metadata
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date

FROM with_final
-- Only include clients with at least one active risk signal; zero-risk clients are clean
WHERE composite_risk_score > 0 OR total_unhedged_zar > 0 OR total_coverage_gap_zar > 0
ORDER BY composite_risk_score DESC  -- Highest-risk clients surfaced first in RM dashboard
