/*
 * @file int_cell_enriched.sql
 * @description dbt intermediate model for enriched cell data, applying SIM deflation factors and aggregating metrics by corporate client.
 * @author Thabo Kunene
 * @created 2026-03-19
 */
{{
    config(
        materialized='table',
        tags=['cell', 'intermediate', 'enriched']
    )
}}

/*
    Intermediate enriched Cell Network model.

    We aggregate individual SIM records to corporate summaries
    and apply the SIM deflation model per country.

    The SIM deflation model is Africa-specific: in many African
    markets, individuals hold multiple SIMs (2-3 on average),
    so raw SIM counts overstate actual employee counts.

    This model joins with:
        - SIM deflation reference data
        - Corporate client master
        - Country metadata
*/

-- Pulling cleaned usage data from the staging model.
WITH staged_usage AS (
    SELECT * FROM {{ ref('stg_cell_usage') }}
),

-- Reference table for SIM deflation factors per country.
sim_deflation AS (
    SELECT * FROM {{ source('cell', 'sim_deflation_ref') }}
),

-- Master registry of corporate clients.
client_master AS (
    SELECT * FROM {{ source('cell', 'client_master') }}
),

-- Aggregate SIM metrics at the corporate level per country and month.
monthly_corporate AS (
    SELECT
        corporate_client_id,
        usage_country,
        DATE_TRUNC('month', usage_date) AS usage_month,
        integration_tier,

        -- SIM lifecycle metrics.
        COUNT(DISTINCT sim_hash) AS total_active_sims,
        COUNT(DISTINCT CASE WHEN sim_status = 'ACTIVE' THEN sim_hash END) AS active_sims,
        COUNT(DISTINCT CASE WHEN activation_date >= DATE_TRUNC('month', usage_date) THEN sim_hash END) AS new_activations,
        COUNT(DISTINCT CASE WHEN sim_status IN ('DEACTIVATED', 'BARRED') THEN sim_hash END) AS deactivations,

        -- Breakdown by device capability (proxy for income and digital maturity).
        COUNT(DISTINCT CASE WHEN is_smartphone THEN sim_hash END) AS smartphone_count,
        COUNT(DISTINCT CASE WHEN NOT is_smartphone THEN sim_hash END) AS feature_phone_count,

        -- Aggregated usage volumes across various channels.
        SUM(voice_minutes_in + voice_minutes_out) AS total_voice_minutes,
        SUM(data_usage_mb) / 1024 AS total_data_usage_gb,
        SUM(sms_sent + sms_received) AS total_sms_count,
        SUM(ussd_sessions) AS total_ussd_sessions,
        SUM(ussd_banking_sessions) AS total_ussd_banking,

        -- Aggregated revenue attribution.
        SUM(revenue_total) AS total_revenue,
        MAX(revenue_currency) AS revenue_currency,

        -- Spatial distribution metrics.
        COUNT(DISTINCT usage_city) AS distinct_cities,
        MODE(usage_city) AS primary_city,

        -- Metadata for data lineage tracking.
        COUNT(*) AS source_record_count

    FROM staged_usage
    WHERE is_valid_country = TRUE
      AND is_valid_sim_status = TRUE
    GROUP BY
        corporate_client_id,
        usage_country,
        DATE_TRUNC('month', usage_date),
        integration_tier
),

-- Enrich corporate aggregates with country-specific SIM deflation logic.
with_deflation AS (
    SELECT
        mc.*,
        sd.deflation_factor,
        sd.avg_sims_per_person,
        sd.data_source AS deflation_source,
        -- Calculate estimated actual employee headcount based on multi-SIM behavior.
        ROUND(mc.active_sims::NUMERIC / NULLIF(sd.deflation_factor, 0))::INTEGER AS estimated_employees,
        -- Window function to track month-on-month growth.
        LAG(mc.active_sims) OVER (
            PARTITION BY mc.corporate_client_id, mc.usage_country
            ORDER BY mc.usage_month
        ) AS prev_month_sims

    FROM monthly_corporate mc
    LEFT JOIN sim_deflation sd ON mc.usage_country = sd.country_code
),

-- Calculate growth metrics
with_growth AS (
    SELECT
        *,
        -- Net SIM change
        COALESCE(new_activations, 0) - COALESCE(deactivations, 0) AS net_sim_change,
        -- SIM growth percentage
        CASE
            WHEN prev_month_sims > 0
            THEN ROUND(
                (active_sims - prev_month_sims)::NUMERIC / prev_month_sims::NUMERIC * 100, 2
            )
            ELSE NULL
        END AS sim_growth_pct,
        -- Smartphone percentage
        CASE
            WHEN total_active_sims > 0
            THEN ROUND(
                smartphone_count::NUMERIC / total_active_sims::NUMERIC * 100, 2
            )
            ELSE 0
        END AS smartphone_pct,
        -- Convert revenue to ZAR (simplified - would use FX rates in production)
        CASE
            WHEN revenue_currency = 'ZAR' THEN total_revenue
            WHEN revenue_currency = 'USD' THEN total_revenue * 18.5
            WHEN revenue_currency = 'NGN' THEN total_revenue / 85
            WHEN revenue_currency = 'KES' THEN total_revenue / 14
            ELSE total_revenue * 10
        END AS total_revenue_zar

    FROM with_deflation
)

SELECT
    corporate_client_id,
    usage_country,
    usage_month AS usage_month,
    total_active_sims,
    new_activations,
    deactivations,
    net_sim_change,
    sim_growth_pct,
    deflation_factor,
    estimated_employees,
    'v1.0' AS deflation_model_version,
    smartphone_count,
    feature_phone_count,
    smartphone_pct,
    total_voice_minutes,
    total_data_usage_gb,
    total_sms_count,
    total_ussd_sessions,
    total_ussd_banking,
    total_revenue,
    revenue_currency,
    total_revenue_zar,
    0 AS momo_transaction_count,
    0 AS momo_transaction_value,
    0 AS momo_salary_count,
    0 AS momo_salary_value,
    0 AS momo_supplier_count,
    0 AS momo_supplier_value,
    distinct_cities,
    primary_city,
    source_record_count,
    integration_tier,
    CURRENT_TIMESTAMP AS processed_timestamp,
    usage_month AS usage_month_partition
FROM with_growth
WHERE active_sims > 0
