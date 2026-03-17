{{
    config(
        materialized='table',
        tags=['cib', 'intermediate', 'enriched']
    )
}}

/*
    Intermediate enriched CIB payments model.

    We enrich staged payments with:
        - Client segmentation (by volume)
        - Corridor risk ratings
        - FX exposure flags
        - Repeat client indicators

    This model joins with reference data for client
    master data and corridor configurations.
*/

WITH staged_payments AS (
    SELECT * FROM {{ ref('stg_cib_payments') }}
),

-- Client master reference
client_master AS (
    SELECT * FROM {{ source('cib', 'client_master') }}
),

-- Corridor risk ratings
corridor_risk AS (
    SELECT * FROM {{ source('cib', 'corridor_risk_ratings') }}
),

-- Calculate client payment statistics
client_stats AS (
    SELECT
        sender_name,
        sender_country,
        COUNT(*) AS total_transactions,
        SUM(amount) AS total_volume_usd,
        AVG(amount) AS avg_transaction_value,
        COUNT(DISTINCT beneficiary_country) AS unique_destinations,
        COUNT(DISTINCT currency) AS unique_currencies,
        MIN(payment_date) AS first_payment_date,
        MAX(payment_date) AS last_payment_date
    FROM staged_payments
    WHERE status = 'COMPLETED'
    GROUP BY sender_name, sender_country
),

-- Client segmentation based on volume
client_segmentation AS (
    SELECT
        sender_name,
        sender_country,
        total_transactions,
        total_volume_usd,
        avg_transaction_value,
        unique_destinations,
        unique_currencies,
        first_payment_date,
        last_payment_date,
        CASE
            WHEN total_volume_usd >= 10000000 THEN 'tier_1_enterprise'
            WHEN total_volume_usd >= 1000000 THEN 'tier_2_corporate'
            WHEN total_volume_usd >= 100000 THEN 'tier_3_sme'
            ELSE 'tier_4_small'
        END AS client_segment,
        CASE
            WHEN unique_destinations >= 10 THEN 'highly_diversified'
            WHEN unique_destinations >= 5 THEN 'diversified'
            WHEN unique_destinations >= 2 THEN 'moderate'
            ELSE 'concentrated'
        END AS geographic_diversification
    FROM client_stats
),

-- Enrich payments with client and corridor data
enriched AS (
    SELECT
        p.transaction_id,
        p.timestamp,
        p.payment_date,
        p.amount,
        p.currency,
        p.sender_name,
        p.sender_country,
        p.beneficiary_name,
        p.beneficiary_country,
        p.status,
        p.purpose_code,
        p.corridor,
        p.is_cross_border,

        -- Client segmentation
        cs.client_segment,
        cs.total_transactions AS client_total_transactions,
        cs.total_volume_usd AS client_total_volume,
        cs.geographic_diversification,

        -- Corridor risk rating (default to 'medium' if not found)
        COALESCE(cr.risk_rating, 'medium') AS corridor_risk_rating,
        COALESCE(cr.compliance_level, 'standard') AS corridor_compliance_level,

        -- FX exposure flag
        CASE
            WHEN p.currency NOT IN ('USD', 'EUR', 'ZAR') THEN TRUE
            ELSE FALSE
        END AS has_fx_exposure,

        -- Repeat client indicator
        CASE
            WHEN cs.total_transactions > 1 THEN TRUE
            ELSE FALSE
        END AS is_repeat_client,

        -- Payment value band
        CASE
            WHEN p.amount >= 1000000 THEN 'mega'
            WHEN p.amount >= 100000 THEN 'large'
            WHEN p.amount >= 10000 THEN 'medium'
            ELSE 'small'
        END AS payment_value_band,

        p._ingested_at,
        p._source_system

    FROM staged_payments p
    LEFT JOIN client_segmentation cs
        ON p.sender_name = cs.sender_name
        AND p.sender_country = cs.sender_country
    LEFT JOIN corridor_risk cr
        ON p.corridor = cr.corridor
)

SELECT * FROM enriched
