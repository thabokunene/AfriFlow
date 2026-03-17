{{
    config(
        materialized='view',
        tags=['forex', 'staging', 'trades']
    )
}}

/*
    Staging model for Forex trades.

    We perform initial cleaning, type casting, and validation
    on raw FX trade data from trading platforms.

    Covers spot, forward, swap, and option trades for
    African currency pairs.

    Columns:
        - Trade identifiers and type
        - Currency pair and amounts
        - Rates and spreads
        - Dates (trade, value, maturity)
        - Hedge designation
        - Counterparty details

    Quality checks:
        - Trade IDs are unique
        - Rates are positive
        - Currency pairs are valid
        - Dates are in valid format
*/

WITH raw_trades AS (
    SELECT * FROM {{ source('forex', 'trades_raw') }}
),

cleaned AS (
    SELECT
        -- Ingestion metadata
        TRIM(ingestion_id) AS ingestion_id,
        CAST(ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp,
        TRIM(kafka_topic) AS kafka_topic,
        CAST(kafka_partition AS INTEGER) AS kafka_partition,
        CAST(kafka_offset AS BIGINT) AS kafka_offset,
        TRIM(source_system) AS source_system,
        TRIM(schema_version) AS schema_version,

        -- Trade identity
        TRIM(trade_id) AS trade_id,
        UPPER(TRIM(trade_type)) AS trade_type,
        UPPER(TRIM(trade_subtype)) AS trade_subtype,
        TRIM(client_id) AS client_id,
        TRIM(client_name) AS client_name,
        TRIM(trader_id) AS trader_id,
        TRIM(sales_person_id) AS sales_person_id,

        -- Currency pair
        UPPER(TRIM(base_currency)) AS base_currency,
        UPPER(TRIM(quote_currency)) AS quote_currency,
        UPPER(TRIM(deal_currency)) AS deal_currency,
        UPPER(TRIM(contra_currency)) AS contra_currency,

        -- Amounts (non-negative)
        GREATEST(0, CAST(deal_amount AS DECIMAL(18,2))) AS deal_amount,
        GREATEST(0, CAST(contra_amount AS DECIMAL(18,2))) AS contra_amount,
        CAST(deal_rate AS DECIMAL(18,8)) AS deal_rate,
        CAST(market_rate_at_deal AS DECIMAL(18,8)) AS market_rate_at_deal,
        CAST(spread_bps AS DECIMAL(10,4)) AS spread_bps,

        -- ZAR equivalent
        CAST(deal_amount_zar AS DECIMAL(18,2)) AS deal_amount_zar,

        -- Dates
        CASE
            WHEN trade_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(trade_date AS DATE)
            ELSE NULL
        END AS trade_date,
        CASE
            WHEN value_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(value_date AS DATE)
            ELSE NULL
        END AS value_date,
        CASE
            WHEN maturity_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(maturity_date AS DATE)
            ELSE NULL
        END AS maturity_date,
        CASE
            WHEN fixing_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(fixing_date AS DATE)
            ELSE NULL
        END AS fixing_date,

        -- Forward specific
        CAST(forward_points AS DECIMAL(18,8)) AS forward_points,
        CAST(forward_rate AS DECIMAL(18,8)) AS forward_rate,

        -- Hedge flag
        COALESCE(is_hedge, FALSE) AS is_hedge,
        TRIM(hedge_designation) AS hedge_designation,
        TRIM(underlying_exposure_id) AS underlying_exposure_id,

        -- Status
        UPPER(TRIM(trade_status)) AS trade_status,
        UPPER(TRIM(confirmation_status)) AS confirmation_status,
        UPPER(TRIM(settlement_status)) AS settlement_status,

        -- Counterparty
        TRIM(counterparty_name) AS counterparty_name,
        UPPER(TRIM(counterparty_bic)) AS counterparty_bic,

        -- Partitioning
        CASE
            WHEN ingestion_date ~ '^\d{4}-\d{2}-\d{2}$'
            THEN CAST(ingestion_date AS DATE)
            ELSE CURRENT_DATE
        END AS ingestion_date

    FROM raw_trades
    WHERE trade_id IS NOT NULL
      AND client_id IS NOT NULL
),

validated AS (
    SELECT
        *,
        -- Validation flags
        CASE
            WHEN trade_type IN ('SPOT', 'FORWARD', 'SWAP', 'OPTION')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_trade_type,
        CASE
            WHEN base_currency IS NOT NULL AND quote_currency IS NOT NULL
            THEN TRUE
            ELSE FALSE
        END AS is_valid_currency_pair,
        CASE
            WHEN deal_rate > 0 THEN TRUE
            ELSE FALSE
        END AS is_valid_rate,
        CASE
            WHEN deal_amount > 0 THEN TRUE
            ELSE FALSE
        END AS is_valid_amount,
        CASE
            WHEN trade_status IN ('PENDING', 'SETTLED', 'FAILED', 'CANCELLED', 'ACTIVE', 'MATURED')
            THEN TRUE
            ELSE FALSE
        END AS is_valid_status,
        CASE
            WHEN value_date >= trade_date THEN TRUE
            ELSE FALSE
        END AS is_valid_value_date,
        -- Derived flags
        CASE
            WHEN base_currency IN ('ZAR', 'NGN', 'KES', 'GHS', 'TZS', 'UGX', 'ZMW', 'MZN', 'AOA', 'XOF', 'XAF', 'RWF', 'ETB')
            THEN TRUE
            ELSE FALSE
        END AS is_african_currency,
        CASE
            WHEN is_hedge AND hedge_designation IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS is_designated_hedge

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
    trade_id,
    trade_type,
    trade_subtype,
    client_id,
    client_name,
    trader_id,
    sales_person_id,
    base_currency,
    quote_currency,
    deal_currency,
    contra_currency,
    deal_amount,
    contra_amount,
    deal_rate,
    market_rate_at_deal,
    spread_bps,
    deal_amount_zar,
    trade_date,
    value_date,
    maturity_date,
    fixing_date,
    forward_points,
    forward_rate,
    is_hedge,
    hedge_designation,
    underlying_exposure_id,
    trade_status,
    confirmation_status,
    settlement_status,
    counterparty_name,
    counterparty_bic,
    ingestion_date,
    is_valid_trade_type,
    is_valid_currency_pair,
    is_valid_rate,
    is_valid_amount,
    is_valid_status,
    is_valid_value_date,
    is_african_currency,
    is_designated_hedge
FROM validated
WHERE is_valid_trade_type = TRUE
  AND is_valid_currency_pair = TRUE
  AND is_valid_rate = TRUE
  AND is_valid_status = TRUE
