{{
    config(
        materialized='table',
        tags=['forex', 'marts', 'hedge', 'analytics']
    )
}}

/*
    Mart: Hedge Analytics

    Aggregated hedge instrument analytics including:
        - Hedge effectiveness metrics
        - Mark-to-market valuation
        - Maturity profile
        - Hedge accounting qualification
        - Gap analysis vs underlying exposure

    This mart powers:
        - Treasury dashboards
        - Hedge accounting reports
        - Risk management monitoring
        - Hedge optimization recommendations
*/

WITH raw_hedges AS (
    SELECT * FROM {{ source('forex', 'hedges_raw') }}
),

-- Cleaned hedges
cleaned AS (
    SELECT
        TRIM(hedge_id) AS hedge_id,
        TRIM(client_id) AS client_id,
        UPPER(TRIM(currency_pair)) AS currency_pair,
        UPPER(TRIM(hedge_type)) AS hedge_type,
        UPPER(TRIM(direction)) AS direction,
        CAST(notional_base AS DECIMAL(18,2)) AS notional_base,
        CAST(strike_rate AS DECIMAL(18,8)) AS strike_rate,
        CAST(current_rate AS DECIMAL(18,8)) AS current_rate,
        CAST(mark_to_market_usd AS DECIMAL(18,2)) AS mark_to_market_usd,
        CAST(hedge_effectiveness_pct AS DECIMAL(5,2)) AS hedge_effectiveness_pct,
        CASE
            WHEN inception_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(inception_date AS DATE)
            ELSE NULL
        END AS inception_date,
        CASE
            WHEN maturity_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(maturity_date AS DATE)
            ELSE NULL
        END AS maturity_date,
        UPPER(TRIM(status)) AS status,
        TRIM(underlying_exposure_id) AS underlying_exposure_id,
        _ingested_at,
        _source_system
    FROM raw_hedges
    WHERE hedge_id IS NOT NULL
      AND client_id IS NOT NULL
),

-- Calculate derived metrics
with_metrics AS (
    SELECT
        *,
        -- Days to maturity
        CASE
            WHEN maturity_date IS NOT NULL
            THEN maturity_date - CURRENT_DATE
            ELSE NULL
        END AS days_to_maturity,
        -- Maturity bucket
        CASE
            WHEN maturity_date < CURRENT_DATE THEN 'expired'
            WHEN maturity_date <= CURRENT_DATE + INTERVAL '30 days' THEN '0-30d'
            WHEN maturity_date <= CURRENT_DATE + INTERVAL '90 days' THEN '30-90d'
            WHEN maturity_date <= CURRENT_DATE + INTERVAL '180 days' THEN '90-180d'
            WHEN maturity_date <= CURRENT_DATE + INTERVAL '365 days' THEN '180-365d'
            ELSE '1y+'
        END AS maturity_bucket,
        -- Hedge accounting qualification (80-125% effectiveness)
        CASE
            WHEN hedge_effectiveness_pct BETWEEN 80 AND 125 THEN TRUE
            ELSE FALSE
        END AS qualifies_for_hedge_accounting,
        -- Ineffectiveness (for P&L recognition)
        CASE
            WHEN hedge_effectiveness_pct IS NOT NULL
            THEN ROUND(ABS(100 - hedge_effectiveness_pct), 2)
            ELSE NULL
        END AS ineffectiveness_pct,
        -- MTM as percentage of notional
        CASE
            WHEN notional_base > 0
            THEN ROUND(mark_to_market_usd::NUMERIC / notional_base::NUMERIC * 100, 4)
            ELSE 0
        END AS mtm_pct

    FROM cleaned
    WHERE status IN ('ACTIVE', 'SETTLED', 'TERMINATED')
),

-- Aggregate by client
client_hedge_summary AS (
    SELECT
        client_id,
        currency_pair,

        -- Counts
        COUNT(*) AS hedge_count,
        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) AS active_count,

        -- Notional
        SUM(notional_base) AS total_notional,
        SUM(CASE WHEN status = 'ACTIVE' THEN notional_base ELSE 0 END) AS active_notional,

        -- MTM
        SUM(mark_to_market_usd) AS total_mtm_usd,
        SUM(CASE WHEN status = 'ACTIVE' THEN mark_to_market_usd ELSE 0 END) AS active_mtm_usd,

        -- Effectiveness
        AVG(hedge_effectiveness_pct) AS avg_effectiveness,
        MIN(hedge_effectiveness_pct) AS min_effectiveness,
        MAX(hedge_effectiveness_pct) AS max_effectiveness,

        -- Hedge accounting
        COUNT(CASE WHEN qualifies_for_hedge_accounting THEN 1 END) AS qualifying_count,

        -- Maturity profile
        MIN(maturity_date) AS earliest_maturity,
        MAX(maturity_date) AS latest_maturity,
        AVG(days_to_maturity) AS avg_days_to_maturity

    FROM with_metrics
    GROUP BY client_id, currency_pair
),

-- Enrich with exposure data
enriched AS (
    SELECT
        chs.client_id,
        chs.currency_pair,
        SPLIT_PART(chs.currency_pair, '/', 1) AS base_currency,
        SPLIT_PART(chs.currency_pair, '/', 2) AS quote_currency,
        chs.hedge_count,
        chs.active_count,
        chs.total_notional,
        chs.active_notional,
        chs.total_mtm_usd,
        chs.active_mtm_usd,
        chs.avg_effectiveness,
        chs.min_effectiveness,
        chs.max_effectiveness,
        chs.qualifying_count,
        chs.earliest_maturity,
        chs.latest_maturity,
        chs.avg_days_to_maturity,

        -- Hedge ratio vs exposure (would join with exposure data)
        0.0 AS exposure_hedge_ratio,

        -- Concentration
        CASE
            WHEN chs.hedge_count > 10 THEN 'diversified'
            WHEN chs.hedge_count > 5 THEN 'moderate'
            ELSE 'concentrated'
        END AS hedge_concentration

    FROM client_hedge_summary chs
)

SELECT
    'GOLD-' || client_id AS golden_id,
    client_id,
    currency_pair,
    base_currency,
    quote_currency,
    hedge_count,
    active_count,
    total_notional,
    active_notional,
    total_mtm_usd,
    active_mtm_usd,
    avg_effectiveness,
    min_effectiveness,
    max_effectiveness,
    qualifies_for_hedge_accounting AS hedge_accounting_eligible,
    earliest_maturity,
    latest_maturity,
    avg_days_to_maturity AS avg_forward_maturity_days,
    exposure_hedge_ratio,
    hedge_concentration,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM enriched
ORDER BY active_notional DESC
