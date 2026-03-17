-- =========================================================
-- AFRIFLOW: SILVER LAYER - FOREX
--
-- Cleaned and enriched forex trade data with derived
-- hedge effectiveness metrics and African currency
-- specific annotations (parallel market flags, commodity
-- correlation, capital control status).
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS silver_forex_trades (
    trade_id                VARCHAR(64)     NOT NULL,
    trade_type              VARCHAR(32)     NOT NULL,
    trade_subtype           VARCHAR(32),
    client_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256)    NOT NULL,

    -- Currency pair (standardised)
    base_currency           VARCHAR(4)      NOT NULL,
    quote_currency          VARCHAR(4)      NOT NULL,
    currency_pair           VARCHAR(8)      NOT NULL,

    -- Amounts (validated)
    deal_amount             DECIMAL(18,2)   NOT NULL,
    contra_amount           DECIMAL(18,2)   NOT NULL,
    deal_amount_zar         DECIMAL(18,2)   NOT NULL,
    deal_rate               DECIMAL(18,8)   NOT NULL,
    market_rate_at_deal     DECIMAL(18,8),
    spread_bps              DECIMAL(10,4),

    -- Standard Bank revenue
    estimated_revenue_zar   DECIMAL(18,2),

    -- Dates (typed)
    trade_date              DATE            NOT NULL,
    value_date              DATE            NOT NULL,
    maturity_date           DATE,

    -- Hedge attributes
    is_hedge                BOOLEAN         NOT NULL,
    hedge_designation       VARCHAR(64),
    underlying_exposure_id  VARCHAR(64),

    -- Forward specific
    forward_points          DECIMAL(18,8),
    forward_rate            DECIMAL(18,8),
    days_to_maturity        INTEGER,

    -- African market enrichment
    target_country          VARCHAR(4),
    is_african_currency     BOOLEAN         NOT NULL,
    has_capital_controls    BOOLEAN,
    capital_control_severity VARCHAR(16),
    parallel_market_active  BOOLEAN,
    commodity_correlation   VARCHAR(32),
    commodity_correlation_r DECIMAL(5,2),

    -- Status
    trade_status            VARCHAR(32)     NOT NULL,

    -- Lineage
    source_bronze_id        VARCHAR(64)     NOT NULL,
    processed_timestamp     TIMESTAMP       NOT NULL,

    -- Partitioning
    trade_date_partition    DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (trade_date_partition)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'forex',
    'layer' = 'silver'
);
