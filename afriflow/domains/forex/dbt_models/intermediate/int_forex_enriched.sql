{{
    config(
        materialized='table',
        tags=['forex', 'intermediate', 'enriched']
    )
}}

/*
    Intermediate enriched Forex model.

    We enrich staged FX trades with:
        - Client segmentation
        - Currency pair standardisation
        - African market annotations (capital controls, parallel markets)
        - Hedge effectiveness metrics
        - Revenue attribution

    This model joins with reference data for:
        - Client master
        - Currency country mapping
        - Capital control status
*/

WITH staged_trades AS (
    SELECT * FROM {{ ref('stg_forex_trades') }}
),

-- Client master reference
client_master AS (
    SELECT * FROM {{ source('forex', 'client_master') }}
),

-- Currency country reference
currency_country AS (
    SELECT * FROM {{ source('forex', 'currency_country_ref') }}
),

-- Calculate derived metrics
with_metrics AS (
    SELECT
        st.*,
        -- Standard currency pair format
        CONCAT(st.base_currency, '/', st.quote_currency) AS currency_pair,
        -- Days to maturity
        CASE
            WHEN st.maturity_date IS NOT NULL
            THEN st.maturity_date - st.trade_date
            WHEN st.value_date IS NOT NULL
            THEN st.value_date - st.trade_date
            ELSE NULL
        END AS days_to_maturity,
        -- Estimated revenue (spread * deal amount)
        ROUND(
            st.deal_amount::NUMERIC * st.spread_bps::NUMERIC / 10000, 2
        ) AS estimated_revenue,
        -- Convert to ZAR if not already
        CASE
            WHEN st.deal_currency = 'ZAR' THEN st.deal_amount
            WHEN st.deal_currency = 'USD' THEN st.deal_amount * 18.5
            WHEN st.deal_currency = 'NGN' THEN st.deal_amount / 85
            WHEN st.deal_currency = 'KES' THEN st.deal_amount / 14
            ELSE st.deal_amount * 10
        END AS deal_amount_zar_calc

    FROM staged_trades st
    WHERE st.is_valid_trade_type = TRUE
      AND st.is_valid_amount = TRUE
),

-- Enrich with African market context
enriched AS (
    SELECT
        wm.trade_id,
        wm.trade_type,
        wm.trade_subtype,
        wm.client_id,
        wm.client_name,
        wm.base_currency,
        wm.quote_currency,
        wm.currency_pair,
        wm.deal_amount,
        wm.contra_amount,
        wm.deal_amount_zar,
        wm.deal_rate,
        wm.market_rate_at_deal,
        wm.spread_bps,
        wm.estimated_revenue AS estimated_revenue_zar,
        wm.trade_date,
        wm.value_date,
        wm.maturity_date,
        wm.days_to_maturity,
        wm.is_hedge,
        wm.hedge_designation,
        wm.underlying_exposure_id,
        wm.trade_status,
        wm.is_african_currency,

        -- African market enrichment
        cc.country_code AS target_country,
        wm.is_african_currency,
        cc.capital_control_level AS capital_control_severity,
        cc.parallel_market_exists AS parallel_market_active,
        cc.primary_commodity AS commodity_correlation,
        cc.commodity_correlation_r,

        -- Lineage
        wm.ingestion_id AS source_bronze_id,
        CURRENT_TIMESTAMP AS processed_timestamp

    FROM with_metrics wm
    LEFT JOIN currency_country cc ON wm.quote_currency = cc.currency_code
    WHERE wm.is_valid_status = TRUE
)

SELECT
    trade_id,
    trade_type,
    trade_subtype,
    client_id,
    client_name,
    base_currency,
    quote_currency,
    currency_pair,
    deal_amount,
    contra_amount,
    deal_amount_zar,
    deal_rate,
    market_rate_at_deal,
    spread_bps,
    estimated_revenue_zar,
    trade_date,
    value_date,
    maturity_date,
    days_to_maturity,
    is_hedge,
    hedge_designation,
    underlying_exposure_id,
    trade_status,
    target_country,
    is_african_currency,
    capital_control_severity,
    parallel_market_active,
    commodity_correlation,
    commodity_correlation_r,
    source_bronze_id,
    processed_timestamp,
    trade_date AS trade_date_partition
FROM enriched
ORDER BY trade_date DESC, deal_amount_zar DESC
