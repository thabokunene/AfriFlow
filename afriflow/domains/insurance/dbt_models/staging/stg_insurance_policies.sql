-- =============================================================================
-- @file stg_insurance_policies.sql
-- @description Staging model for insurance policies, performing data cleaning,
--     type casting, and basic validation on raw ingestion data.
-- @author Thabo Kunene
-- @created 2026-03-19
-- =============================================================================

{{
    config(
        materialized='view',
        tags=['insurance', 'staging', 'policies']
    )
}}

/*
    Design intent:
    - Standardize raw insurance policy data for downstream enrichment.
    - Perform initial data quality checks (e.g., positive premiums, valid dates).
    - Normalize text fields (UPPER, TRIM) to ensure consistent grouping and joining.
*/

WITH raw_policies AS (
    -- Source data from the raw ingestion layer
    SELECT * FROM {{ source('insurance', 'policies_raw') }}
),

cleaned AS (
    SELECT
        -- Primary key normalization to ensure reliable joins
        TRIM(policy_id) AS policy_id,
        TRIM(policy_number) AS policy_number,

        -- Policy and product categorization
        UPPER(TRIM(policy_type)) AS policy_type,
        UPPER(TRIM(product_code)) AS product_code,
        TRIM(product_name) AS product_name,

        -- Client information normalization
        TRIM(client_id) AS client_id,
        TRIM(client_name) AS client_name,
        -- INITCAP provides a readable format for reporting while preserving uniqueness
        INITCAP(TRIM(client_name)) AS client_name_normalised,
        UPPER(TRIM(client_country)) AS client_country,

        -- Coverage and financial metrics casting for mathematical operations
        UPPER(TRIM(coverage_type)) AS coverage_type,
        UPPER(TRIM(coverage_country)) AS coverage_country,
        CAST(sum_insured AS DECIMAL(18,2)) AS sum_insured,
        UPPER(TRIM(sum_insured_currency)) AS sum_insured_currency,
        CAST(excess_amount AS DECIMAL(18,2)) AS excess_amount,

        -- Premium details: standardized for actuarial calculations
        CAST(premium_annual AS DECIMAL(18,2)) AS premium_annual,
        UPPER(TRIM(premium_currency)) AS premium_currency,
        UPPER(TRIM(premium_frequency)) AS premium_frequency,
        UPPER(TRIM(premium_payment_method)) AS premium_payment_method,
        UPPER(TRIM(premium_status)) AS premium_status,

        -- Date parsing with regex validation to avoid casting errors
        CASE
            WHEN inception_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(inception_date AS DATE)
            ELSE NULL
        END AS inception_date,
        CASE
            WHEN expiry_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(expiry_date AS DATE)
            ELSE NULL
        END AS expiry_date,
        CASE
            WHEN renewal_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(renewal_date AS DATE)
            ELSE NULL
        END AS renewal_date,
        CASE
            WHEN cancellation_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(cancellation_date AS DATE)
            ELSE NULL
        END AS cancellation_date,

        -- Operational status fields
        UPPER(TRIM(policy_status)) AS policy_status,
        UPPER(TRIM(underwriting_status)) AS underwriting_status,

        -- Beneficiary details
        TRIM(beneficiary_name) AS beneficiary_name,
        UPPER(TRIM(beneficiary_type)) AS beneficiary_type,

        -- Insured asset attributes for risk location analysis
        TRIM(asset_description) AS asset_description,
        UPPER(TRIM(asset_location_country)) AS asset_location_country,
        TRIM(asset_location_city) AS asset_location_city,
        CAST(asset_value AS DECIMAL(18,2)) AS asset_value,

        -- Audit metadata for lineage tracking
        _ingested_at,
        _source_system

    FROM raw_policies
    -- Basic filter to remove broken records at the entry point
    WHERE policy_id IS NOT NULL
      AND client_id IS NOT NULL
),

validated AS (
    SELECT
        *,
        -- Validation flags to facilitate data quality reporting
        CASE
            WHEN policy_type IN ('ASSET', 'CREDIT', 'LIABILITY', 'MARINE', 'AVIATION', 'ENGINEERING')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_policy_type,
        CASE
            WHEN premium_annual >= 0 THEN TRUE
            ELSE FALSE
        END AS is_valid_premium,
        CASE
            WHEN sum_insured > 0 THEN TRUE
            ELSE FALSE
        END AS is_valid_sum_insured,
        CASE
            WHEN policy_status IN ('ACTIVE', 'PENDING', 'LAPSED', 'CANCELLED', 'EXPIRED', 'RENEWED')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_status,
        -- Temporal consistency check
        CASE
            WHEN expiry_date > inception_date THEN TRUE
            ELSE FALSE
        END AS is_valid_date_range,
        CASE
            WHEN expiry_date < CURRENT_DATE THEN TRUE
            ELSE FALSE
        END AS is_expired

    FROM cleaned
)

-- Final selection filters out records that fail critical business rules
SELECT
    policy_id,
    policy_number,
    policy_type,
    product_code,
    product_name,
    client_id,
    client_name,
    client_name_normalised,
    client_country,
    coverage_type,
    coverage_country,
    sum_insured,
    sum_insured_currency,
    excess_amount,
    premium_annual,
    premium_currency,
    premium_frequency,
    premium_payment_method,
    premium_status,
    inception_date,
    expiry_date,
    renewal_date,
    cancellation_date,
    policy_status,
    underwriting_status,
    beneficiary_name,
    beneficiary_type,
    asset_description,
    asset_location_country,
    asset_location_city,
    asset_value,
    is_valid_policy_type,
    is_valid_premium,
    is_valid_sum_insured,
    is_valid_status,
    is_valid_date_range,
    is_expired,
    _ingested_at,
    _source_system
FROM validated
WHERE is_valid_policy_type = TRUE
  AND is_valid_premium = TRUE
  AND is_valid_status = TRUE
