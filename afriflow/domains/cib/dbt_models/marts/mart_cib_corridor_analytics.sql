{{
    config(
        materialized='table',
        tags=['cib', 'marts', 'corridor', 'analytics']
    )
}}

/*
    Mart: CIB Corridor Analytics

    We aggregate payment flows by corridor to provide:
        - Volume and transaction counts
        - Average transaction values
        - Success/failure rates
        - Trend indicators (MoM growth)
        - Risk-weighted metrics

    This mart powers the corridor intelligence dashboard
    and geographic expansion detection signals.
*/

WITH enriched_payments AS (
    SELECT * FROM {{ ref('int_cib_enriched') }}
),

-- Daily corridor aggregates
daily_corridor_stats AS (
    SELECT
        corridor,
        sender_country,
        beneficiary_country,
        payment_date,
        COUNT(*) AS daily_transactions,
        SUM(amount) AS daily_volume_usd,
        AVG(amount) AS daily_avg_transaction,
        MEDIAN(amount) AS daily_median_transaction,
        SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_count,
        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
        SUM(CASE WHEN has_fx_exposure THEN 1 ELSE 0 END) AS fx_exposure_count,
        SUM(CASE WHEN is_cross_border THEN amount ELSE 0 END) AS cross_border_volume

    FROM enriched_payments
    GROUP BY
        corridor,
        sender_country,
        beneficiary_country,
        payment_date
),

-- Add previous day for trend calculation
with_trends AS (
    SELECT
        *,
        LAG(daily_volume_usd, 1) OVER (
            PARTITION BY corridor
            ORDER BY payment_date
        ) AS prev_day_volume,
        LAG(daily_transactions, 1) OVER (
            PARTITION BY corridor
            ORDER BY payment_date
        ) AS prev_day_transactions,
        LAG(daily_avg_transaction, 1) OVER (
            PARTITION BY corridor
            ORDER BY payment_date
        ) AS prev_day_avg_transaction
    FROM daily_corridor_stats
),

-- Calculate growth rates
with_growth AS (
    SELECT
        corridor,
        sender_country,
        beneficiary_country,
        payment_date,
        daily_transactions,
        daily_volume_usd,
        daily_avg_transaction,
        daily_median_transaction,
        completed_count,
        failed_count,
        fx_exposure_count,
        cross_border_volume,
        prev_day_volume,
        prev_day_transactions,
        prev_day_avg_transaction,
        -- Volume growth rate (percentage)
        CASE
            WHEN prev_day_volume IS NULL OR prev_day_volume = 0 THEN NULL
            ELSE ROUND(
                ((daily_volume_usd - prev_day_volume) / prev_day_volume) * 100,
                2
            )
        END AS volume_growth_pct,
        -- Transaction growth rate
        CASE
            WHEN prev_day_transactions IS NULL OR prev_day_transactions = 0 THEN NULL
            ELSE ROUND(
                ((daily_transactions - prev_day_transactions) / prev_day_transactions) * 100,
                2
            )
        END AS transaction_growth_pct,
        -- Success rate
        ROUND(
            (completed_count * 100.0 / NULLIF(daily_transactions, 0)),
            2
        ) AS success_rate_pct,
        -- Failure rate
        ROUND(
            (failed_count * 100.0 / NULLIF(daily_transactions, 0)),
            2
        ) AS failure_rate_pct

    FROM with_trends
),

-- Corridor risk weighting
risk_weighted AS (
    SELECT
        *,
        -- Risk-weighted volume (higher risk = lower weight)
        CASE
            WHEN corridor IN ('NG-GH', 'KE-TZ') THEN daily_volume_usd * 0.9
            WHEN corridor IN ('ZA-NG', 'ZA-KE') THEN daily_volume_usd * 1.0
            WHEN corridor LIKE '%CI%' THEN daily_volume_usd * 0.85
            ELSE daily_volume_usd * 0.95
        END AS risk_weighted_volume

    FROM with_growth
)

SELECT
    corridor,
    sender_country,
    beneficiary_country,
    payment_date,
    daily_transactions,
    daily_volume_usd,
    daily_avg_transaction,
    daily_median_transaction,
    completed_count,
    failed_count,
    fx_exposure_count,
    cross_border_volume,
    risk_weighted_volume,
    success_rate_pct,
    failure_rate_pct,
    volume_growth_pct,
    transaction_growth_pct,
    prev_day_volume,
    prev_day_transactions,
    CURRENT_TIMESTAMP AS computed_at

FROM risk_weighted
ORDER BY payment_date DESC, daily_volume_usd DESC
