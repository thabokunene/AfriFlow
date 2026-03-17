{{
    config(
        materialized='view',
        tags=['insurance', 'staging', 'policies']
    )
}}

/*
    Staging model for Insurance policies.

    We perform initial cleaning, type casting, and validation
    on raw insurance policy data from the ingestion layer.

    Columns:
        - policy_id: Unique policy identifier
        - policy_number: Human-readable policy number
        - policy_type: Type of insurance (asset, credit, liability)
        - client_id: Client identifier
        - coverage details and premiums
        - Status and dates

    Quality checks:
        - Policy numbers are unique
        - Premiums are positive
        - Dates are valid
        - Status is one of the valid values
*/

WITH raw_policies AS (
    SELECT * FROM {{ source('insurance', 'policies_raw') }}
),

cleaned AS (
    SELECT
        -- Primary key
        TRIM(policy_id) AS policy_id,
        TRIM(policy_number) AS policy_number,

        -- Policy type
        UPPER(TRIM(policy_type)) AS policy_type,
        UPPER(TRIM(product_code)) AS product_code,
        TRIM(product_name) AS product_name,

        -- Client (trimmed and normalised)
        TRIM(client_id) AS client_id,
        TRIM(client_name) AS client_name,
        INITCAP(TRIM(client_name)) AS client_name_normalised,
        UPPER(TRIM(client_country)) AS client_country,

        -- Coverage
        UPPER(TRIM(coverage_type)) AS coverage_type,
        UPPER(TRIM(coverage_country)) AS coverage_country,
        CAST(sum_insured AS DECIMAL(18,2)) AS sum_insured,
        UPPER(TRIM(sum_insured_currency)) AS sum_insured_currency,
        CAST(excess_amount AS DECIMAL(18,2)) AS excess_amount,

        -- Premium
        CAST(premium_annual AS DECIMAL(18,2)) AS premium_annual,
        UPPER(TRIM(premium_currency)) AS premium_currency,
        UPPER(TRIM(premium_frequency)) AS premium_frequency,
        UPPER(TRIM(premium_payment_method)) AS premium_payment_method,
        UPPER(TRIM(premium_status)) AS premium_status,

        -- Dates (cast to date type)
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

        -- Status
        UPPER(TRIM(policy_status)) AS policy_status,
        UPPER(TRIM(underwriting_status)) AS underwriting_status,

        -- Beneficiary
        TRIM(beneficiary_name) AS beneficiary_name,
        UPPER(TRIM(beneficiary_type)) AS beneficiary_type,

        -- Asset details
        TRIM(asset_description) AS asset_description,
        UPPER(TRIM(asset_location_country)) AS asset_location_country,
        TRIM(asset_location_city) AS asset_location_city,
        CAST(asset_value AS DECIMAL(18,2)) AS asset_value,

        -- Metadata
        _ingested_at,
        _source_system

    FROM raw_policies
    WHERE policy_id IS NOT NULL
      AND client_id IS NOT NULL
),

validated AS (
    SELECT
        *,
        -- Validation flags
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
