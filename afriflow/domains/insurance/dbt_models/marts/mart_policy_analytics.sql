{{
    config(
        materialized='table',
        tags=['insurance', 'marts', 'policy', 'analytics']
    )
}}

/*
    Mart: Policy Analytics

    Aggregated policy-level analytics including:
        - Premium and coverage metrics
        - Lapsing policy identification
        - Coverage gap analysis
        - Claims history linkage

    This mart powers insurance dashboards and
    cross-sell opportunity identification.
*/

WITH enriched_policies AS (
    SELECT * FROM {{ ref('int_insurance_enriched') }}
),

-- Claims aggregation per policy
claims_agg AS (
    SELECT
        policy_id,
        COUNT(*) AS total_claims_count,
        SUM(claim_amount_zar) AS total_claims_value_zar,
        SUM(CASE WHEN claim_status != 'CLOSED' THEN 1 ELSE 0 END) AS open_claims_count,
        SUM(CASE WHEN claim_status != 'CLOSED' THEN claim_amount_zar ELSE 0 END) AS open_claims_value_zar,
        MAX(claim_date) AS last_claim_date
    FROM {{ source('insurance', 'claims') }}
    GROUP BY policy_id
),

-- Policy analytics
policy_analytics AS (
    SELECT
        ep.policy_id,
        ep.client_id,
        ep.client_name,
        ep.policy_type,
        ep.coverage_country,
        ep.policy_status,
        ep.sum_insured_zar,
        ep.premium_annual,
        ep.premium_annual_zar,
        ep.inception_date,
        ep.expiry_date,
        ep.days_to_expiry,
        ep.is_lapsing_90d,
        ep.coverage_gap,
        ep.coverage_gap_amount_zar,

        -- Claims metrics
        COALESCE(ca.total_claims_count, 0) AS total_claims_count,
        COALESCE(ca.total_claims_value_zar, 0) AS total_claims_value_zar,
        COALESCE(ca.open_claims_count, 0) AS open_claims_count,
        COALESCE(ca.open_claims_value_zar, 0) AS open_claims_value_zar,

        -- Loss ratio
        CASE
            WHEN ep.premium_annual_zar > 0
            THEN ROUND(
                COALESCE(ca.total_claims_value_zar, 0)::NUMERIC /
                ep.premium_annual_zar::NUMERIC * 100, 2
            )
            ELSE 0
        END AS loss_ratio_pct,

        -- Renewal probability (simplified)
        CASE
            WHEN ep.days_to_expiry > 90 THEN 0.85
            WHEN ep.days_to_expiry > 30 THEN 0.70
            WHEN ep.days_to_expiry > 0 THEN 0.50
            ELSE 0.20
        END AS renewal_probability,

        -- Cross-sell flags
        CASE
            WHEN ep.policy_type = 'ASSET' AND NOT ep.coverage_gap THEN TRUE
            ELSE FALSE
        END AS eligible_for_credit_insurance,
        CASE
            WHEN ep.policy_type = 'CREDIT' AND NOT ep.coverage_gap THEN TRUE
            ELSE FALSE
        END AS eligible_for_liability_insurance

    FROM enriched_policies ep
    LEFT JOIN claims_agg ca ON ep.policy_id = ca.policy_id
    WHERE ep.policy_status IN ('ACTIVE', 'PENDING', 'RENEWED')
)

SELECT
    'GOLD-' || policy_id AS golden_id,
    policy_id,
    client_id,
    client_name,
    policy_type,
    coverage_type AS policy_type,
    coverage_country,
    policy_status,
    sum_insured_zar,
    premium_annual,
    premium_annual_zar,
    inception_date,
    expiry_date,
    days_to_expiry,
    is_lapsing_90d,
    coverage_gap,
    coverage_gap_amount_zar,
    total_claims_count,
    total_claims_value_zar,
    open_claims_count,
    open_claims_value_zar,
    loss_ratio_pct,
    renewal_probability,
    eligible_for_credit_insurance,
    eligible_for_liability_insurance,
    CURRENT_DATE AS policy_date,
    '{{ invocation_id }}' AS dbt_run_id,
    CURRENT_DATE AS snapshot_date
FROM policy_analytics
ORDER BY premium_annual_zar DESC
