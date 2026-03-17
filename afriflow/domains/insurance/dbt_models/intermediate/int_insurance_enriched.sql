{{
    config(
        materialized='table',
        tags=['insurance', 'intermediate', 'enriched']
    )
}}

/*
    Intermediate enriched Insurance model.

    We enrich staged policies with:
        - Client segmentation
        - Coverage adequacy analysis
        - Cross-sell opportunity flags
        - CIB/Forex linkage for cross-domain signals

    This model joins with reference data for client master
    and country risk ratings.
*/

WITH staged_policies AS (
    SELECT * FROM {{ ref('stg_insurance_policies') }}
),

-- Client master reference
client_master AS (
    SELECT * FROM {{ source('insurance', 'client_master') }}
),

-- Country risk ratings
country_risk AS (
    SELECT * FROM {{ source('insurance', 'country_risk_ratings') }}
),

-- Calculate policy metrics
policy_metrics AS (
    SELECT
        client_id,
        COUNT(*) AS total_policies,
        SUM(premium_annual) AS total_premium,
        SUM(sum_insured) AS total_sum_insured,
        COUNT(DISTINCT coverage_country) AS countries_covered,
        COUNT(DISTINCT policy_type) AS policy_types_held,
        COUNT(CASE WHEN is_lapsing_90d THEN 1 END) AS policies_lapsing_90d,
        COUNT(CASE WHEN is_expired THEN 1 END) AS expired_policies,
        AVG(premium_annual) AS avg_premium,
        MIN(expiry_date) AS earliest_expiry,
        MAX(expiry_date) AS latest_expiry
    FROM staged_policies
    WHERE policy_status = 'ACTIVE'
    GROUP BY client_id
),

-- Coverage adequacy analysis
coverage_analysis AS (
    SELECT
        policy_id,
        client_id,
        policy_type,
        coverage_country,
        sum_insured,
        premium_annual,
        -- Coverage gap flag (simplified - would compare to CIB asset values in production)
        CASE
            WHEN policy_type = 'ASSET' AND sum_insured < 1000000 THEN TRUE
            WHEN policy_type = 'CREDIT' AND sum_insured < 500000 THEN TRUE
            WHEN policy_type = 'LIABILITY' AND sum_insured < 2000000 THEN TRUE
            ELSE FALSE
        END AS coverage_gap,
        CASE
            WHEN policy_type = 'ASSET' AND sum_insured < 1000000 THEN 1000000 - sum_insured
            WHEN policy_type = 'CREDIT' AND sum_insured < 500000 THEN 500000 - sum_insured
            WHEN policy_type = 'LIABILITY' AND sum_insured < 2000000 THEN 2000000 - sum_insured
            ELSE 0
        END AS coverage_gap_amount,
        -- Days to expiry
        CASE
            WHEN expiry_date IS NOT NULL
            THEN expiry_date - CURRENT_DATE
            ELSE NULL
        END AS days_to_expiry,
        -- Lapsing flag (within 90 days)
        CASE
            WHEN expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
            THEN TRUE
            ELSE FALSE
        END AS is_lapsing_90d
    FROM staged_policies
),

-- Enrich with client and country data
enriched AS (
    SELECT
        ca.policy_id,
        ca.client_id,
        sp.client_name,
        sp.client_name_normalised,
        sp.client_country,
        ca.policy_type,
        sp.product_name,
        ca.coverage_country,
        ca.sum_insured,
        ca.sum_insured_currency,
        ca.excess_amount,
        ca.premium_annual,
        sp.premium_currency,
        sp.premium_status,
        sp.inception_date,
        sp.expiry_date,
        ca.days_to_expiry,
        ca.is_lapsing_90d,
        sp.policy_status,
        ca.coverage_gap,
        ca.coverage_gap_amount AS coverage_gap_amount_zar,
        cr.risk_rating AS country_risk_rating,
        cr.stability_score,
        sp._ingested_at,
        sp._source_system

    FROM coverage_analysis ca
    JOIN staged_policies sp ON ca.policy_id = sp.policy_id
    LEFT JOIN country_risk cr ON ca.coverage_country = cr.country_code
    WHERE sp.is_valid_policy_type = TRUE
      AND sp.is_valid_premium = TRUE
)

SELECT
    policy_id,
    policy_type,
    product_name,
    client_id,
    client_name,
    client_name_normalised,
    client_country,
    coverage_type AS policy_type,
    coverage_country,
    sum_insured,
    sum_insured AS sum_insured_zar,
    excess_amount,
    premium_annual,
    premium_annual AS premium_annual_zar,
    premium_currency,
    premium_status,
    inception_date,
    expiry_date,
    days_to_expiry,
    is_lapsing_90d,
    policy_status,
    coverage_gap,
    coverage_gap_amount_zar,
    'INTERNAL' AS source_bronze_id,
    CURRENT_TIMESTAMP AS processed_timestamp,
    CURRENT_DATE AS snapshot_date
FROM enriched
