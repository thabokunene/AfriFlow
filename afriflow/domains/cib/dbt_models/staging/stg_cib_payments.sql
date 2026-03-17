{{
    config(
        materialized='view',
        tags=['cib', 'staging', 'payments']
    )
}}

/*
    Staging model for CIB payments.

    We perform initial cleaning, type casting, and validation
    on raw payment data from the Kafka ingestion layer.

    Columns:
        - transaction_id: Unique payment identifier
        - timestamp: Payment timestamp (UTC)
        - amount: Payment amount
        - currency: ISO 4217 currency code
        - sender_name: Debtor company name
        - sender_country: ISO 3166-1 alpha-2 country code
        - beneficiary_name: Creditor company name
        - beneficiary_country: ISO 3166-1 alpha-2 country code
        - status: Payment status (COMPLETED, PENDING, FAILED)
        - purpose_code: ISO 20022 purpose code
        - corridor: Derived payment corridor (sender-beneficiary)

    Quality checks:
        - Country codes are 2 uppercase letters
        - Currency codes are 3 uppercase letters
        - Amounts are positive
        - Status is one of the valid values
*/

WITH raw_payments AS (
    SELECT * FROM {{ source('cib', 'payments_raw') }}
),

cleaned AS (
    SELECT
        -- Primary key
        TRIM(transaction_id) AS transaction_id,

        -- Timestamp casting
        CAST(timestamp AS TIMESTAMP) AS timestamp,
        CAST(DATE(timestamp) AS DATE) AS payment_date,

        -- Amount validation
        CAST(amount AS DECIMAL(18, 2)) AS amount,

        -- Currency normalization
        UPPER(TRIM(currency)) AS currency,

        -- Entity names (trimmed)
        TRIM(sender_name) AS sender_name,
        TRIM(beneficiary_name) AS beneficiary_name,

        -- Country codes (uppercase, validated)
        UPPER(TRIM(sender_country)) AS sender_country,
        UPPER(TRIM(beneficiary_country)) AS beneficiary_country,

        -- Status normalization
        UPPER(TRIM(status)) AS status,

        -- Purpose code
        UPPER(TRIM(purpose_code)) AS purpose_code,

        -- Corridor derivation
        CONCAT(
            UPPER(TRIM(sender_country)),
            '-',
            UPPER(TRIM(beneficiary_country))
        ) AS corridor,

        -- Metadata
        _ingested_at,
        _source_system

    FROM raw_payments
    WHERE transaction_id IS NOT NULL
      AND amount > 0
),

validated AS (
    SELECT
        *,
        -- Validation flags
        CASE
            WHEN sender_country ~ '^[A-Z]{2}$' THEN TRUE
            ELSE FALSE
        END AS is_valid_sender_country,
        CASE
            WHEN beneficiary_country ~ '^[A-Z]{2}$' THEN TRUE
            ELSE FALSE
        END AS is_valid_beneficiary_country,
        CASE
            WHEN currency ~ '^[A-Z]{3}$' THEN TRUE
            ELSE FALSE
        END AS is_valid_currency,
        CASE
            WHEN status IN ('COMPLETED', 'PENDING', 'FAILED') THEN TRUE
            ELSE FALSE
        END AS is_valid_status,
        CASE
            WHEN sender_country != beneficiary_country THEN TRUE
            ELSE FALSE
        END AS is_cross_border

    FROM cleaned
)

SELECT
    transaction_id,
    timestamp,
    payment_date,
    amount,
    currency,
    sender_name,
    sender_country,
    beneficiary_name,
    beneficiary_country,
    status,
    purpose_code,
    corridor,
    is_cross_border,
    _ingested_at,
    _source_system
FROM validated
WHERE is_valid_sender_country = TRUE
  AND is_valid_beneficiary_country = TRUE
  AND is_valid_currency = TRUE
  AND is_valid_status = TRUE
