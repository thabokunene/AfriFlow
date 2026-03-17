-- =========================================================
-- AFRIFLOW: BRONZE LAYER - FOREX (Foreign Exchange / Treasury)
--
-- Raw ingested data from FX trading platforms and rate feeds.
-- Covers spot, forward, swap, and option trades plus
-- real time rate ticks.
--
-- Source protocols: FIX 4.4, SWIFT MT300, FpML
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS bronze_forex_trades (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,
    schema_version          VARCHAR(16)     NOT NULL,

    -- Trade identity
    trade_id                VARCHAR(64),
    trade_type              VARCHAR(32),
    trade_subtype           VARCHAR(32),
    client_id               VARCHAR(64),
    client_name             VARCHAR(256),
    trader_id               VARCHAR(64),
    sales_person_id         VARCHAR(64),

    -- Currency pair
    base_currency           VARCHAR(4),
    quote_currency          VARCHAR(4),
    deal_currency           VARCHAR(4),
    contra_currency         VARCHAR(4),

    -- Amounts
    deal_amount             DECIMAL(18,2),
    contra_amount           DECIMAL(18,2),
    deal_rate               DECIMAL(18,8),
    market_rate_at_deal     DECIMAL(18,8),
    spread_bps              DECIMAL(10,4),

    -- ZAR equivalent
    deal_amount_zar         DECIMAL(18,2),

    -- Dates
    trade_date              VARCHAR(16),
    value_date              VARCHAR(16),
    maturity_date           VARCHAR(16),
    fixing_date             VARCHAR(16),

    -- Forward specific
    forward_points          DECIMAL(18,8),
    forward_rate            DECIMAL(18,8),

    -- Hedge flag
    is_hedge                BOOLEAN,
    hedge_designation       VARCHAR(64),
    underlying_exposure_id  VARCHAR(64),

    -- Status
    trade_status            VARCHAR(32),
    confirmation_status     VARCHAR(32),
    settlement_status       VARCHAR(32),

    -- Counterparty
    counterparty_name       VARCHAR(256),
    counterparty_bic        VARCHAR(16),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'forex',
    'layer' = 'bronze'
);


CREATE TABLE IF NOT EXISTS bronze_forex_rates (
    -- Ingestion metadata
    ingestion_id            VARCHAR(64)     NOT NULL,
    ingestion_timestamp     TIMESTAMP       NOT NULL,
    kafka_topic             VARCHAR(128)    NOT NULL,
    kafka_partition         INTEGER         NOT NULL,
    kafka_offset            BIGINT          NOT NULL,
    source_system           VARCHAR(64)     NOT NULL,

    -- Rate tick
    rate_id                 VARCHAR(64),
    base_currency           VARCHAR(4),
    quote_currency          VARCHAR(4),
    bid_rate                DECIMAL(18,8),
    ask_rate                DECIMAL(18,8),
    mid_rate                DECIMAL(18,8),
    tick_timestamp          VARCHAR(32),

    -- Source classification
    rate_type               VARCHAR(32),
    rate_source             VARCHAR(64),

    -- African market specific
    is_official_rate        BOOLEAN,
    parallel_market_rate    DECIMAL(18,8),
    parallel_divergence_pct DECIMAL(8,4),

    -- Partitioning
    ingestion_date          DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (ingestion_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'forex',
    'layer' = 'bronze'
);
