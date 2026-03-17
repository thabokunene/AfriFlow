-- =========================================================
-- AFRIFLOW: GOLD LAYER - DOMAIN SPECIFIC MARTS
--
-- Aggregated, business ready data products per domain.
-- These are the tables that each division can query
-- independently before cross-domain integration.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


-- ---------------------------------------------------------
-- CIB: Client payment flows and corridor analytics
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_cib_client_flows (
    golden_id               VARCHAR(64)     NOT NULL,
    client_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256)    NOT NULL,
    client_tier             VARCHAR(16),
    relationship_manager    VARCHAR(128),
    home_country            VARCHAR(4)      NOT NULL,

    -- Active corridors
    active_corridors        INTEGER         NOT NULL,
    corridor_list           VARCHAR(512),

    -- Volume metrics (rolling 90 days)
    total_payment_count_90d INTEGER,
    total_payment_value_90d DECIMAL(18,2),
    avg_payment_value       DECIMAL(18,2),
    max_payment_value       DECIMAL(18,2),

    -- Trend
    value_change_vs_prior_90d_pct DECIMAL(8,2),
    count_change_vs_prior_90d_pct DECIMAL(8,2),
    trend_direction         VARCHAR(16),

    -- Top corridors
    top_corridor_1          VARCHAR(16),
    top_corridor_1_value    DECIMAL(18,2),
    top_corridor_2          VARCHAR(16),
    top_corridor_2_value    DECIMAL(18,2),
    top_corridor_3          VARCHAR(16),
    top_corridor_3_value    DECIMAL(18,2),

    -- Supplier diversity
    unique_creditors_90d    INTEGER,
    new_creditors_90d       INTEGER,
    new_countries_90d       INTEGER,

    -- Health
    client_health_status    VARCHAR(16)     NOT NULL,
    health_score            DECIMAL(5,2),
    last_payment_date       DATE,
    days_since_last_payment INTEGER,

    -- Revenue
    estimated_fee_income_90d DECIMAL(18,2),

    -- Metadata
    snapshot_date           DATE            NOT NULL,
    dbt_run_id              VARCHAR(64)
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cib',
    'layer' = 'gold'
);


CREATE TABLE IF NOT EXISTS mart_cib_corridor_analytics (
    corridor                VARCHAR(16)     NOT NULL,
    corridor_name           VARCHAR(128),
    source_country          VARCHAR(4)      NOT NULL,
    destination_country     VARCHAR(4)      NOT NULL,

    -- Volume
    total_clients           INTEGER,
    total_payments_90d      INTEGER,
    total_value_90d         DECIMAL(18,2),
    avg_payment_size        DECIMAL(18,2),

    -- Trend
    value_change_pct        DECIMAL(8,2),
    client_change_count     INTEGER,

    -- Seasonal adjustment
    seasonal_factor         DECIMAL(5,2),
    seasonally_adjusted_value DECIMAL(18,2),
    is_peak_season          BOOLEAN,
    is_off_season           BOOLEAN,

    -- Revenue
    estimated_corridor_revenue DECIMAL(18,2),

    -- Metadata
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'cib',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- FOREX: Exposure and hedge analytics
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_forex_exposure (
    golden_id               VARCHAR(64)     NOT NULL,
    client_id               VARCHAR(64)     NOT NULL,
    target_currency         VARCHAR(4)      NOT NULL,
    target_country          VARCHAR(4),

    -- Exposure
    total_trade_volume_90d  DECIMAL(18,2),
    trade_count_90d         INTEGER,
    trade_value_zar         DECIMAL(18,2),

    -- Hedging
    hedged_volume           DECIMAL(18,2),
    unhedged_volume         DECIMAL(18,2),
    hedge_ratio_pct         DECIMAL(5,2),
    is_adequately_hedged    BOOLEAN,

    -- Forward book
    open_forward_count      INTEGER,
    open_forward_value_zar  DECIMAL(18,2),
    avg_forward_maturity_days INTEGER,
    nearest_maturity_date   DATE,

    -- Revenue
    estimated_fx_revenue_90d DECIMAL(18,2),
    avg_spread_bps          DECIMAL(10,4),

    -- African market context
    has_capital_controls    BOOLEAN,
    parallel_market_active  BOOLEAN,
    current_parallel_divergence_pct DECIMAL(8,4),
    commodity_correlation   VARCHAR(32),

    -- Risk
    var_95_1d_zar           DECIMAL(18,2),
    max_drawdown_90d_pct    DECIMAL(8,2),

    -- Metadata
    snapshot_date           DATE            NOT NULL,
    trade_date              DATE
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'forex',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- INSURANCE: Policy analytics
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_policy_analytics (
    golden_id               VARCHAR(64)     NOT NULL,
    policy_id               VARCHAR(64)     NOT NULL,
    client_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256),

    policy_type             VARCHAR(64),
    coverage_type           VARCHAR(64),
    coverage_country        VARCHAR(4),
    status                  VARCHAR(32)     NOT NULL,

    sum_insured_zar         DECIMAL(18,2),
    premium_annual          DECIMAL(18,2),
    premium_annual_zar      DECIMAL(18,2),

    inception_date          DATE,
    expiry_date             DATE,
    days_to_expiry          INTEGER,
    is_lapsing_90d          BOOLEAN,

    -- Coverage adequacy
    coverage_gap            BOOLEAN,
    coverage_gap_amount_zar DECIMAL(18,2),

    -- Claims history
    total_claims_count      INTEGER,
    total_claims_value_zar  DECIMAL(18,2),
    open_claims_count       INTEGER,
    open_claims_value_zar   DECIMAL(18,2),
    loss_ratio_pct          DECIMAL(8,2),

    -- Metadata
    policy_date             DATE            NOT NULL,
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'insurance',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- CELL: Cell network intelligence
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_cell_intelligence (
    golden_id               VARCHAR(64)     NOT NULL,
    corporate_client_id     VARCHAR(64)     NOT NULL,
    usage_country           VARCHAR(4)      NOT NULL,

    -- SIM metrics (with deflation)
    active_sims             INTEGER         NOT NULL,
    deflation_factor        DECIMAL(5,2)    NOT NULL,
    estimated_employees     INTEGER         NOT NULL,

    -- Growth signals
    sim_growth_pct_mom      DECIMAL(8,2),
    sim_growth_pct_qoq      DECIMAL(8,2),
    is_expanding            BOOLEAN,
    is_contracting          BOOLEAN,

    -- Usage patterns
    monthly_data_usage_gb   DECIMAL(12,2),
    monthly_voice_minutes   DECIMAL(12,2),
    ussd_banking_sessions   INTEGER,
    smartphone_pct          DECIMAL(5,2),

    -- MoMo intelligence
    momo_transaction_value  DECIMAL(18,2),
    momo_transaction_count  INTEGER,
    momo_salary_value       DECIMAL(18,2),
    momo_supplier_value     DECIMAL(18,2),
    momo_regularity_score   DECIMAL(5,2),

    -- Geographic
    distinct_cities         INTEGER,
    primary_city            VARCHAR(128),
    countries_active        INTEGER,

    -- Activity
    last_activity_date      DATE,
    days_since_activity     INTEGER,

    -- Metadata
    data_month              DATE            NOT NULL,
    integration_tier        VARCHAR(8),
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date, usage_country)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'cell',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- PBB: Payroll analytics
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_payroll_analytics (
    golden_id               VARCHAR(64)     NOT NULL,
    corporate_client_id     VARCHAR(64)     NOT NULL,
    employee_country        VARCHAR(4)      NOT NULL,

    -- Employee accounts
    employee_count          INTEGER         NOT NULL,
    new_accounts_mom        INTEGER,
    closed_accounts_mom     INTEGER,

    -- Payroll
    monthly_payroll_value   DECIMAL(18,2),
    payroll_currency        VARCHAR(4),
    monthly_payroll_zar     DECIMAL(18,2),
    average_salary_zar      DECIMAL(18,2),

    -- Channel adoption
    digital_adoption_pct    DECIMAL(5,2),
    ussd_usage_pct          DECIMAL(5,2),
    card_active_pct         DECIMAL(5,2),

    -- Account health
    dormant_pct             DECIMAL(5,2),
    overdrawn_pct           DECIMAL(5,2),

    -- Payroll regularity
    on_time_pct             DECIMAL(5,2),
    missed_payment_flag     BOOLEAN,

    -- Revenue
    estimated_account_revenue_zar DECIMAL(18,2),

    -- Activity
    payroll_date            DATE,
    last_payroll_date       DATE,

    -- Metadata
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'pbb',
    'layer' = 'gold'
);
