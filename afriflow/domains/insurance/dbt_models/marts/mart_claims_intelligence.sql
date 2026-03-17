{{
    config(
        materialized='table',
        tags=['insurance', 'marts', 'claims', 'intelligence']
    )
}}

/*
    Mart: Claims Intelligence

    Aggregated claims-level analytics including:
        - Claims frequency and severity
        - Fraud detection flags
        - Settlement time analysis
        - Loss ratio by client and country

    This mart powers claims dashboards, fraud detection,
    and underwriting strategy optimization.
*/

WITH raw_claims AS (
    SELECT * FROM {{ source('insurance', 'claims_raw') }}
),

-- Cleaned claims
cleaned_claims AS (
    SELECT
        TRIM(claim_id) AS claim_id,
        TRIM(claim_number) AS claim_number,
        TRIM(policy_id) AS policy_id,
        TRIM(client_id) AS client_id,
        UPPER(TRIM(claim_type)) AS claim_type,
        CASE
            WHEN loss_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(loss_date AS DATE)
            ELSE NULL
        END AS loss_date,
        CASE
            WHEN notification_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(notification_date AS DATE)
            ELSE NULL
        END AS notification_date,
        UPPER(TRIM(loss_country)) AS loss_country,
        TRIM(loss_description) AS loss_description,
        CAST(claim_amount AS DECIMAL(18,2)) AS claim_amount,
        UPPER(TRIM(claim_currency)) AS claim_currency,
        CAST(reserve_amount AS DECIMAL(18,2)) AS reserve_amount,
        CAST(paid_amount AS DECIMAL(18,2)) AS paid_amount,
        CAST(recovery_amount AS DECIMAL(18,2)) AS recovery_amount,
        UPPER(TRIM(claim_status)) AS claim_status,
        UPPER(TRIM(assessment_status)) AS assessment_status,
        COALESCE(fraud_flag, FALSE) AS fraud_flag,
        CASE
            WHEN settlement_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(settlement_date AS DATE)
            ELSE NULL
        END AS settlement_date,
        CASE
            WHEN closed_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(closed_date AS DATE)
            ELSE NULL
        END AS closed_date,
        _ingested_at,
        _source_system
    FROM raw_claims
    WHERE claim_id IS NOT NULL
      AND client_id IS NOT NULL
),

-- Claims with calculated metrics
with_metrics AS (
    SELECT
        *,
        -- Days open
        CASE
            WHEN closed_date IS NOT NULL
            THEN closed_date - loss_date
            WHEN notification_date IS NOT NULL
            THEN CURRENT_DATE - notification_date
            ELSE NULL
        END AS days_open,
        -- Settlement time
        CASE
            WHEN settlement_date IS NOT NULL AND notification_date IS NOT NULL
            THEN settlement_date - notification_date
            ELSE NULL
        END AS settlement_time_days,
        -- Paid ratio
        CASE
            WHEN claim_amount > 0
            THEN ROUND(paid_amount::NUMERIC / claim_amount::NUMERIC * 100, 2)
            ELSE 0
        END AS paid_ratio_pct,
        -- Recovery ratio
        CASE
            WHEN paid_amount > 0
            THEN ROUND(recovery_amount::NUMERIC / paid_amount::NUMERIC * 100, 2)
            ELSE 0
        END AS recovery_ratio_pct,
        -- Severity classification
        CASE
            WHEN claim_amount >= 1000000 THEN 'catastrophic'
            WHEN claim_amount >= 500000 THEN 'severe'
            WHEN claim_amount >= 100000 THEN 'moderate'
            WHEN claim_amount >= 10000 THEN 'minor'
            ELSE 'negligible'
        END AS severity_class
    FROM cleaned_claims
),

-- Client claims summary
client_claims AS (
    SELECT
        client_id,
        COUNT(*) AS total_claims,
        SUM(claim_amount) AS total_claim_amount,
        SUM(paid_amount) AS total_paid_amount,
        SUM(recovery_amount) AS total_recovery_amount,
        COUNT(CASE WHEN fraud_flag THEN 1 END) AS fraud_claims_count,
        AVG(days_open) AS avg_days_open,
        MAX(loss_date) AS last_loss_date
    FROM with_metrics
    GROUP BY client_id
),

-- Enriched claims
enriched AS (
    SELECT
        wm.claim_id,
        wm.claim_number,
        wm.policy_id,
        wm.client_id,
        wm.claim_type,
        wm.loss_date,
        wm.notification_date,
        wm.loss_country,
        wm.loss_description,
        wm.claim_amount,
        wm.claim_currency,
        wm.reserve_amount,
        wm.paid_amount,
        wm.recovery_amount,
        wm.claim_status,
        wm.assessment_status,
        wm.fraud_flag,
        wm.days_open,
        wm.settlement_time_days,
        wm.paid_ratio_pct,
        wm.recovery_ratio_pct,
        wm.severity_class,
        cc.total_claims AS client_total_claims,
        cc.total_claim_amount AS client_total_claim_amount,
        cc.fraud_claims_count AS client_fraud_claims,
        cc.avg_days_open AS client_avg_days_open,
        -- Fraud risk score
        CASE
            WHEN wm.fraud_flag THEN 50
            WHEN wm.claim_amount > 500000 AND wm.days_open > 90 THEN 25
            WHEN wm.claim_type IN ('FIRE', 'THEFT') AND wm.loss_country IS NULL THEN 20
            ELSE 0
        END AS fraud_risk_score
    FROM with_metrics wm
    JOIN client_claims cc ON wm.client_id = cc.client_id
    WHERE wm.claim_status IN ('OPEN', 'PENDING', 'CLOSED', 'REJECTED')
)

SELECT
    claim_id,
    claim_number,
    policy_id,
    client_id,
    claim_type,
    loss_date,
    notification_date,
    loss_country,
    loss_description,
    claim_amount AS claim_amount,
    claim_amount AS claim_amount_zar,
    reserve_amount AS reserve_amount_zar,
    paid_amount AS paid_amount_zar,
    recovery_amount AS recovery_amount_zar,
    claim_status,
    days_open,
    fraud_flag,
    'INTERNAL' AS source_bronze_id,
    CURRENT_TIMESTAMP AS processed_timestamp,
    CURRENT_DATE AS snapshot_date
FROM enriched
ORDER BY claim_amount DESC
