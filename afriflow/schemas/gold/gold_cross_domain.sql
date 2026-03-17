-- =========================================================
-- AFRIFLOW: GOLD LAYER - CROSS DOMAIN ANALYTICS
--
-- Tables that exist only because of cross-domain
-- integration. These cannot be built by any single
-- division operating in isolation.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


-- ---------------------------------------------------------
-- CROSS SELL MATRIX
-- Shows product gaps for every client across all domains
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_cross_sell_matrix (
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256)    NOT NULL,
    client_tier             VARCHAR(16),
    relationship_manager    VARCHAR(128),

    -- Current product holdings
    has_cib_payments        BOOLEAN,
    has_cib_trade_finance   BOOLEAN,
    has_cib_cash_management BOOLEAN,
    has_forex_spot          BOOLEAN,
    has_forex_forwards      BOOLEAN,
    has_forex_options       BOOLEAN,
    has_insurance_asset     BOOLEAN,
    has_insurance_credit    BOOLEAN,
    has_insurance_liability BOOLEAN,
    has_cell_corporate_sim  BOOLEAN,
    has_cell_momo           BOOLEAN,
    has_pbb_payroll         BOOLEAN,
    has_pbb_employee_banking BOOLEAN,

    -- Product count
    total_products_held     INTEGER         NOT NULL,
    total_products_available INTEGER        NOT NULL,
    product_penetration_pct DECIMAL(5,2)    NOT NULL,

    -- Gap identification
    gap_fx_hedging          BOOLEAN,
    gap_fx_hedging_value    DECIMAL(18,2),
    gap_insurance_coverage  BOOLEAN,
    gap_insurance_countries VARCHAR(64),
    gap_employee_banking    BOOLEAN,
    gap_employee_count      INTEGER,
    gap_trade_finance       BOOLEAN,
    gap_cash_management     BOOLEAN,

    -- Prioritised next best action
    nba_product_1           VARCHAR(128),
    nba_product_1_value     DECIMAL(18,2),
    nba_product_1_confidence DECIMAL(5,2),
    nba_product_2           VARCHAR(128),
    nba_product_2_value     DECIMAL(18,2),
    nba_product_3           VARCHAR(128),
    nba_product_3_value     DECIMAL(18,2),

    -- Total cross sell opportunity
    total_opportunity_zar   DECIMAL(18,2),
    cross_sell_priority     VARCHAR(16),

    -- Metadata
    snapshot_date           DATE            NOT NULL,
    dbt_run_id              VARCHAR(64)
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- CORRIDOR INTELLIGENCE
-- Revenue attribution per corridor across all domains
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_corridor_intelligence (
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256),
    corridor                VARCHAR(16)     NOT NULL,
    source_country          VARCHAR(4)      NOT NULL,
    destination_country     VARCHAR(4)      NOT NULL,

    -- CIB revenue on this corridor
    cib_payment_value_90d   DECIMAL(18,2),
    cib_fee_income_90d      DECIMAL(18,2),
    cib_payment_count_90d   INTEGER,

    -- Forex revenue on this corridor
    forex_volume_90d        DECIMAL(18,2),
    forex_revenue_90d       DECIMAL(18,2),
    forex_hedge_ratio       DECIMAL(5,2),

    -- Insurance revenue on this corridor
    insurance_premium_annual DECIMAL(18,2),
    insurance_coverage_active BOOLEAN,

    -- PBB on this corridor
    pbb_employee_count      INTEGER,
    pbb_payroll_value       DECIMAL(18,2),

    -- Cell on this corridor
    cell_sim_count          INTEGER,
    cell_momo_value         DECIMAL(18,2),

    -- Total corridor revenue
    total_corridor_revenue_90d DECIMAL(18,2),
    total_corridor_annual   DECIMAL(18,2),

    -- Leakage
    expected_revenue        DECIMAL(18,2),
    actual_revenue          DECIMAL(18,2),
    leakage_amount          DECIMAL(18,2),
    leakage_pct             DECIMAL(5,2),
    leakage_products        VARCHAR(256),

    -- Seasonal context
    seasonal_factor         DECIMAL(5,2),
    is_peak_season          BOOLEAN,

    -- Metadata
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- GROUP REVENUE 360
-- Total revenue per client across all domains
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_group_revenue_360 (
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256)    NOT NULL,
    client_tier             VARCHAR(16),
    relationship_manager    VARCHAR(128),
    home_country            VARCHAR(4),

    -- Revenue by domain (annualised)
    cib_revenue_annual      DECIMAL(18,2),
    forex_revenue_annual    DECIMAL(18,2),
    insurance_revenue_annual DECIMAL(18,2),
    cell_revenue_annual     DECIMAL(18,2),
    pbb_revenue_annual      DECIMAL(18,2),
    total_revenue_annual    DECIMAL(18,2)   NOT NULL,

    -- Revenue by domain (90 day)
    cib_revenue_90d         DECIMAL(18,2),
    forex_revenue_90d       DECIMAL(18,2),
    insurance_revenue_90d   DECIMAL(18,2),
    cell_revenue_90d        DECIMAL(18,2),
    pbb_revenue_90d         DECIMAL(18,2),
    total_revenue_90d       DECIMAL(18,2),

    -- Revenue trend
    revenue_change_qoq_pct  DECIMAL(8,2),
    revenue_change_yoy_pct  DECIMAL(8,2),
    revenue_trend           VARCHAR(16),

    -- Revenue concentration
    primary_revenue_domain  VARCHAR(16),
    primary_domain_pct      DECIMAL(5,2),
    revenue_hhi             DECIMAL(8,4),

    -- Client lifetime value
    estimated_clv_5yr_zar   DECIMAL(18,2),
    churn_probability_12m   DECIMAL(5,2),

    -- Ranking
    revenue_rank_overall    INTEGER,
    revenue_rank_in_tier    INTEGER,
    revenue_rank_in_country INTEGER,

    -- Metadata
    snapshot_date           DATE            NOT NULL,
    dbt_run_id              VARCHAR(64)
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'gold'
);


-- ---------------------------------------------------------
-- RISK HEATMAP
-- Concentration and attrition risk per client
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_risk_heatmap (
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256)    NOT NULL,
    client_tier             VARCHAR(16),

    -- Attrition risk
    attrition_risk_score    DECIMAL(5,2),
    attrition_risk_level    VARCHAR(16),
    attrition_signals       VARCHAR(512),
    cib_volume_trend        VARCHAR(16),
    forex_activity_trend    VARCHAR(16),
    days_since_rm_contact   INTEGER,

    -- FX exposure risk
    total_unhedged_zar      DECIMAL(18,2),
    unhedged_currencies     VARCHAR(128),
    highest_exposure_currency VARCHAR(4),
    highest_exposure_value  DECIMAL(18,2),
    parallel_market_exposure BOOLEAN,

    -- Insurance risk
    total_coverage_gap_zar  DECIMAL(18,2),
    uncovered_countries     VARCHAR(64),
    lapsing_policies_count  INTEGER,

    -- Concentration risk
    country_concentration_hhi DECIMAL(8,4),
    supplier_concentration  DECIMAL(5,2),
    single_corridor_dependency BOOLEAN,

    -- Sovereign risk
    government_revenue_pct  DECIMAL(5,2),
    government_payment_health VARCHAR(16),

    -- Currency event vulnerability
    currency_event_exposure_zar DECIMAL(18,2),
    most_vulnerable_currency VARCHAR(4),

    -- Overall risk
    composite_risk_score    DECIMAL(5,2)    NOT NULL,
    risk_level              VARCHAR(16)     NOT NULL,
    primary_risk_type       VARCHAR(32),
    recommended_action      VARCHAR(256),

    -- Metadata
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'gold'
);
