/*
 * @file stg_cell_usage.sql
 * @description dbt staging model for cell usage data, performing initial cleaning, type casting, and validation of raw MTN metrics.
 * @author Thabo Kunene
 * @created 2026-03-19
 */
{{
    config(
        materialized='view',
        tags=['cell', 'staging', 'usage']
    )
}}

/*
    Staging model for Cell Network usage data.

    We perform initial cleaning, type casting, and validation
    on raw cell network data from MTN integration.

    This is the domain that makes AfriFlow uniquely African -
    no Western or East Asian banking platform has telco data
    as a first-class banking signal.

    Columns:
        - SIM and usage identifiers (hashed for privacy)
        - Voice, data, SMS, USSD usage metrics
        - Revenue and corporate linkage
        - Geographic distribution

    Quality checks:
        - SIM hashes are valid
        - Usage metrics are non-negative
        - Country codes are valid ISO 3166-1 alpha-2
*/

-- Common Table Expression (CTE) to pull raw data from the MTN source.
WITH raw_usage AS (
    SELECT * FROM {{ source('cell', 'usage_raw') }}
),

-- CTE to clean and normalize raw fields for downstream analytics.
cleaned AS (
    SELECT
        -- Ingestion metadata for lineage and auditing.
        TRIM(ingestion_id) AS ingestion_id,
        CAST(ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp,
        TRIM(kafka_topic) AS kafka_topic,
        CAST(kafka_partition AS INTEGER) AS kafka_partition,
        CAST(kafka_offset AS BIGINT) AS kafka_offset,
        TRIM(source_system) AS source_system,
        TRIM(schema_version) AS schema_version,
        TRIM(integration_tier) AS integration_tier,

        -- Corporate client identifiers to link SIMs back to the bank's clients.
        TRIM(corporate_client_id) AS corporate_client_id,
        TRIM(corporate_account_ref) AS corporate_account_ref,

        -- SIM identity (already hashed at source for POPIA/GDPR compliance).
        TRIM(sim_hash) AS sim_hash,
        TRIM(msisdn_hash) AS msisdn_hash,
        TRIM(imsi_hash) AS imsi_hash,
        UPPER(TRIM(sim_type)) AS sim_type,
        UPPER(TRIM(device_type)) AS device_type,

        -- Usage period normalization.
        CASE
            WHEN usage_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(usage_date AS DATE)
            ELSE NULL
        END AS usage_date,
        UPPER(TRIM(usage_country)) AS usage_country,
        TRIM(usage_city) AS usage_city,
        TRIM(usage_region) AS usage_region,

        -- Voice metrics: using GREATEST(0, ...) to ensure data quality.
        GREATEST(0, CAST(voice_minutes_in AS DECIMAL(10,2))) AS voice_minutes_in,
        GREATEST(0, CAST(voice_minutes_out AS DECIMAL(10,2))) AS voice_minutes_out,
        GREATEST(0, CAST(voice_calls_in AS INTEGER)) AS voice_calls_in,
        GREATEST(0, CAST(voice_calls_out AS INTEGER)) AS voice_calls_out,

        -- Data consumption metrics in Megabytes.
        GREATEST(0, CAST(data_usage_mb AS DECIMAL(12,2))) AS data_usage_mb,
        GREATEST(0, CAST(data_sessions AS INTEGER)) AS data_sessions,

        -- SMS interaction counts.
        GREATEST(0, CAST(sms_sent AS INTEGER)) AS sms_sent,
        GREATEST(0, CAST(sms_received AS INTEGER)) AS sms_received,

        -- USSD metrics (Critical for African banking accessibility analysis).
        GREATEST(0, CAST(ussd_sessions AS INTEGER)) AS ussd_sessions,
        GREATEST(0, CAST(ussd_banking_sessions AS INTEGER)) AS ussd_banking_sessions,

        -- Revenue generated per SIM, used for business value attribution.
        GREATEST(0, CAST(revenue_voice AS DECIMAL(10,2))) AS revenue_voice,
        GREATEST(0, CAST(revenue_data AS DECIMAL(10,2))) AS revenue_data,
        GREATEST(0, CAST(revenue_sms AS DECIMAL(10,2))) AS revenue_sms,
        GREATEST(0, CAST(revenue_total AS DECIMAL(10,2))) AS revenue_total,
        UPPER(TRIM(revenue_currency)) AS revenue_currency,

        -- Operational status of the SIM.
        UPPER(TRIM(sim_status)) AS sim_status,
        CASE
            WHEN activation_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(activation_date AS DATE)
            ELSE NULL
        END AS activation_date,
        CASE
            WHEN last_activity_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(last_activity_date AS DATE)
            ELSE NULL
        END AS last_activity_date,

        -- Partitioning
        CASE
            WHEN ingestion_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(ingestion_date AS DATE)
            ELSE CURRENT_DATE
        END AS ingestion_date

    FROM raw_usage
    WHERE sim_hash IS NOT NULL
      AND corporate_client_id IS NOT NULL
),

validated AS (
    SELECT
        *,
        -- Validation flags
        CASE
            WHEN usage_country IN ('ZA', 'NG', 'KE', 'GH', 'TZ', 'UG', 'ZM', 'MZ', 'CI', 'RW', 'AO', 'CM', 'ET', 'MW', 'SS')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_country,
        CASE
            WHEN sim_type IN ('PREPAID', 'POSTPAID', 'CORPORATE', 'M2M')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_sim_type,
        CASE
            WHEN sim_status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'BARRED', 'DEACTIVATED')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_sim_status,
        CASE
            WHEN revenue_total >= 0 THEN TRUE
            ELSE FALSE
        END AS is_valid_revenue,
        -- Derived flags
        CASE
            WHEN device_type IN ('SMARTPHONE', 'IPHONE', 'ANDROID')
            THEN TRUE
            ELSE FALSE
        END AS is_smartphone,
        CASE
            WHEN ussd_banking_sessions > 0 THEN TRUE
            ELSE FALSE
        END AS uses_banking_ussd

    FROM cleaned
)

SELECT
    ingestion_id,
    ingestion_timestamp,
    kafka_topic,
    kafka_partition,
    kafka_offset,
    source_system,
    schema_version,
    integration_tier,
    corporate_client_id,
    corporate_account_ref,
    sim_hash,
    msisdn_hash,
    imsi_hash,
    sim_type,
    device_type,
    usage_date,
    usage_country,
    usage_city,
    usage_region,
    voice_minutes_in,
    voice_minutes_out,
    voice_calls_in,
    voice_calls_out,
    data_usage_mb,
    data_sessions,
    sms_sent,
    sms_received,
    ussd_sessions,
    ussd_banking_sessions,
    revenue_voice,
    revenue_data,
    revenue_sms,
    revenue_total,
    revenue_currency,
    sim_status,
    activation_date,
    last_activity_date,
    ingestion_date,
    is_valid_country,
    is_valid_sim_type,
    is_valid_sim_status,
    is_valid_revenue,
    is_smartphone,
    uses_banking_ussd
FROM validated
WHERE is_valid_country = TRUE
  AND is_valid_sim_type = TRUE
