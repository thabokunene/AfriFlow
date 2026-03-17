{{
    config(
        materialized='table',
        tags=['forex', 'marts', 'exposure']
    )
}}

/*
    Mart: Forex Exposure

    Aggregated FX exposure analytics per client per currency including:
        - Trade volume and count
        - Hedging metrics (hedged vs unhedged)
        - Forward book summary
        - Revenue attribution
        - African market context (capital controls, parallel markets)
        - Risk metrics (VaR, drawdown)

    This mart powers:
        - FX exposure dashboards
        - Hedge adequacy monitoring
        - Cross-sell opportunity identification
        - Risk heatmaps
*/

WITH enriched_trades AS (
    SELECT * FROM {{ ref('int_forex_enriched') }}
),

-- Hedge instruments (would join with hedge data in production)
hedges AS (
    SELECT
        client_id,
        target_currency,
        SUM(notional_base) AS hedged_volume,
        COUNT(*) AS hedge_count
    FROM {{ source('forex', 'hedges') }}
    WHERE status = 'ACTIVE'
    GROUP BY client_id, target_currency
),

-- Aggregate exposure per client per currency
exposure_agg AS (
    SELECT
        client_id,
        quote_currency AS target_currency,
        target_country,

        -- Volume metrics
        SUM(deal_amount) AS total_trade_volume,
        SUM(deal_amount_zar) AS trade_value_zar,
        COUNT(*) AS trade_count,

        -- Hedge metrics
        COALESCE(MAX(h.hedged_volume), 0) AS hedged_volume,
        SUM(deal_amount) - COALESCE(MAX(h.hedged_volume), 0) AS unhedged_volume,

        -- Forward book
        COUNT(CASE WHEN trade_type = 'FORWARD' AND trade_status = 'ACTIVE' THEN 1 END) AS open_forward_count,
        SUM(CASE WHEN trade_type = 'FORWARD' AND trade_status = 'ACTIVE' THEN deal_amount_zar ELSE 0 END) AS open_forward_value_zar,
        AVG(days_to_maturity) AS avg_forward_maturity_days,
        MIN(CASE WHEN trade_type = 'FORWARD' AND maturity_date > CURRENT_DATE THEN maturity_date END) AS nearest_maturity_date,

        -- Revenue
        SUM(estimated_revenue_zar) AS estimated_fx_revenue,
        AVG(spread_bps) AS avg_spread_bps,

        -- African market context
        MAX(is_african_currency) AS is_african_currency,
        MAX(capital_control_severity) AS has_capital_controls,
        MAX(parallel_market_active) AS parallel_market_active,
        MAX(commodity_correlation) AS commodity_correlation,

        -- Activity
        MAX(trade_date) AS last_trade_date

    FROM enriched_trades et
    LEFT JOIN hedges h ON et.client_id = h.client_id AND et.quote_currency = h.target_currency
    WHERE trade_status IN ('SETTLED', 'ACTIVE', 'PENDING')
    GROUP BY
        client_id,
        quote_currency,
        target_country
),

-- Calculate derived metrics
with_metrics AS (
    SELECT
        *,
        -- Hedge ratio
        CASE
            WHEN total_trade_volume > 0
            THEN ROUND(hedged_volume::NUMERIC / total_trade_volume::NUMERIC * 100, 2)
            ELSE 0
        END AS hedge_ratio_pct,
        -- Hedge adequacy flag (80%+ is considered adequate)
        CASE
            WHEN total_trade_volume > 0 AND hedged_volume::NUMERIC / total_trade_volume::NUMERIC >= 0.80
            THEN TRUE
            ELSE FALSE
        END AS is_adequately_hedged,
        -- Simplified VaR (95% 1-day, using 2% of exposure as proxy)
        ROUND(unhedged_volume::NUMERIC * 0.02, 2) AS var_95_1d_zar,
        -- Simplified max drawdown (using 10% as proxy for volatile African currencies)
        CASE
            WHEN is_african_currency = TRUE THEN 15.0
            ELSE 8.0
        END AS max_drawdown_90d_pct

    FROM exposure_agg
    WHERE total_trade_volume > 0
)

SELECT
    'GOLD-' || client_id AS golden_id,
    client_id,
    target_currency,
    target_country,
    total_trade_volume AS total_trade_volume_90d,
    trade_count AS trade_count_90d,
    trade_value_zar,
    hedged_volume,
    unhedged_volume,
    hedge_ratio_pct,
    is_adequately_hedged,
    open_forward_count,
    open_forward_value_zar,
    avg_forward_maturity_days,
    nearest_maturity_date,
    estimated_fx_revenue AS estimated_fx_revenue_90d,
    avg_spread_bps,
    is_african_currency,
    has_capital_controls,
    parallel_market_active,
    commodity_correlation,
    var_95_1d_zar,
    max_drawdown_90d_pct,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date,
    last_trade_date AS trade_date
FROM with_metrics
ORDER BY trade_value_zar DESC
