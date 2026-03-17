{{
    config(
        materialized='table',
        tags=['cib', 'marts', 'client', 'flows']
    )
}}

/*
    Mart: CIB Client Flows

    We aggregate payment flows by client to provide:
        - Client payment statistics
        - Flow trends and patterns
        - Geographic expansion signals
        - Client health indicators

    This mart powers the expansion detector and
    client relationship management dashboards.
*/

WITH enriched_payments AS (
    SELECT * FROM {{ ref('int_cib_enriched') }}
),

-- Monthly client aggregates
monthly_client_stats AS (
    SELECT
        sender_name AS client_name,
        sender_country AS home_country,
        DATE_TRUNC('month', payment_date) AS month,
        COUNT(*) AS monthly_transactions,
        SUM(amount) AS monthly_volume_usd,
        AVG(amount) AS monthly_avg_transaction,
        COUNT(DISTINCT beneficiary_country) AS monthly_destinations,
        COUNT(DISTINCT corridor) AS monthly_corridors,
        SUM(CASE WHEN status = 'COMPLETED' THEN amount ELSE 0 END) AS completed_volume,
        SUM(CASE WHEN is_cross_border THEN 1 ELSE 0 END) AS cross_border_count,
        COUNT(DISTINCT CASE WHEN is_cross_border THEN beneficiary_country END) AS cross_border_destinations

    FROM enriched_payments
    WHERE client_segment IS NOT NULL
    GROUP BY
        sender_name,
        sender_country,
        DATE_TRUNC('month', payment_date)
),

-- Add previous month for trend analysis
with_trends AS (
    SELECT
        *,
        LAG(monthly_volume_usd, 1) OVER (
            PARTITION BY client_name, home_country
            ORDER BY month
        ) AS prev_month_volume,
        LAG(monthly_destinations, 1) OVER (
            PARTITION BY client_name, home_country
            ORDER BY month
        ) AS prev_month_destinations,
        LAG(monthly_corridors, 1) OVER (
            PARTITION BY client_name, home_country
            ORDER BY month
        ) AS prev_month_corridors,
        LAG(cross_border_destinations, 1) OVER (
            PARTITION BY client_name, home_country
            ORDER BY month
        ) AS prev_month_cross_border_destinations
    FROM monthly_client_stats
),

-- Calculate growth and expansion signals
with_signals AS (
    SELECT
        client_name,
        home_country,
        month,
        monthly_transactions,
        monthly_volume_usd,
        monthly_avg_transaction,
        monthly_destinations,
        monthly_corridors,
        completed_volume,
        cross_border_count,
        cross_border_destinations,
        prev_month_volume,
        prev_month_destinations,
        prev_month_corridors,
        prev_month_cross_border_destinations,

        -- Volume growth
        CASE
            WHEN prev_month_volume IS NULL OR prev_month_volume = 0 THEN NULL
            ELSE ROUND(
                ((monthly_volume_usd - prev_month_volume) / prev_month_volume) * 100,
                2
            )
        END AS volume_growth_pct,

        -- Destination expansion (new countries)
        CASE
            WHEN prev_month_destinations IS NULL THEN 0
            ELSE monthly_destinations - prev_month_destinations
        END AS new_destinations_count,

        -- Corridor expansion
        CASE
            WHEN prev_month_corridors IS NULL THEN 0
            ELSE monthly_corridors - prev_month_corridors
        END AS new_corridors_count,

        -- Cross-border expansion
        CASE
            WHEN prev_month_cross_border_destinations IS NULL THEN 0
            ELSE cross_border_destinations - prev_month_cross_border_destinations
        END AS new_cross_border_destinations,

        -- Expansion signal flag
        CASE
            WHEN monthly_destinations > COALESCE(prev_month_destinations, 0)
                OR monthly_corridors > COALESCE(prev_month_corridors, 0)
            THEN TRUE
            ELSE FALSE
        END AS is_expanding,

        -- Growth signal flag
        CASE
            WHEN prev_month_volume IS NOT NULL
                AND monthly_volume_usd > prev_month_volume * 1.20
            THEN TRUE
            ELSE FALSE
        END AS is_high_growth,

        -- Client health score (simplified)
        ROUND(
            (
                (CASE WHEN monthly_transactions > 10 THEN 20 ELSE monthly_transactions * 2 END) +
                (CASE WHEN monthly_volume_usd > 100000 THEN 30 ELSE monthly_volume_usd / 10000 END) +
                (CASE WHEN cross_border_destinations > 3 THEN 25 ELSE cross_border_destinations * 8 END) +
                (CASE WHEN completed_volume / NULLIF(monthly_volume_usd, 0) > 0.95 THEN 25 ELSE 20 END)
            )::NUMERIC,
            0
        ) AS client_health_score

    FROM with_trends
),

-- Add client segment from source
final AS (
    SELECT
        s.client_name,
        s.home_country,
        s.month,
        s.monthly_transactions,
        s.monthly_volume_usd,
        s.monthly_avg_transaction,
        s.monthly_destinations,
        s.monthly_corridors,
        s.completed_volume,
        s.cross_border_count,
        s.cross_border_destinations,
        s.volume_growth_pct,
        s.new_destinations_count,
        s.new_corridors_count,
        s.new_cross_border_destinations,
        s.is_expanding,
        s.is_high_growth,
        s.client_health_score,
        e.client_segment,
        e.geographic_diversification,
        CURRENT_TIMESTAMP AS computed_at

    FROM with_signals s
    LEFT JOIN (
        SELECT DISTINCT
            sender_name,
            sender_country,
            client_segment,
            geographic_diversification
        FROM enriched_payments
    ) e ON s.client_name = e.sender_name
       AND s.home_country = e.sender_country
)

SELECT * FROM final
ORDER BY month DESC, monthly_volume_usd DESC
