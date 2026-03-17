-- =========================================================
-- AFRIFLOW: GOLD LAYER - UNIFIED GOLDEN RECORD
--
-- The crown jewel of the entire platform.
-- A single table that combines every client's relationship
-- across all five Standard Bank domains into one row.
--
-- Freshness SLA: sub 5 minute
-- Accuracy target: 99.97%
-- Coverage target: 80%+ of Top 500 clients across 3+ domains
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


CREATE TABLE IF NOT EXISTS gold_unified_client_record (
    -- =====================================================
    -- IDENTITY
    -- =====================================================
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256)    NOT NULL,
    registration_number     VARCHAR(32),
    tax_number              VARCHAR(32),
    home_country            VARCHAR(4)      NOT NULL,
    client_tier             VARCHAR(16),
    relationship_manager    VARCHAR(128),
    client_segment          VARCHAR(32),

    -- Entity resolution metadata
    match_confidence        DECIMAL(5,2)    NOT NULL,
    match_method            VARCHAR(32)     NOT NULL,
    domains_matched         INTEGER         NOT NULL,
    human_verified          BOOLEAN         NOT NULL DEFAULT FALSE,
    verification_date       DATE,

    -- =====================================================
    -- DOMAIN PRESENCE FLAGS
    -- =====================================================
    has_cib                 BOOLEAN         NOT NULL DEFAULT FALSE,
    has_forex               BOOLEAN         NOT NULL DEFAULT FALSE,
    has_insurance           BOOLEAN         NOT NULL DEFAULT FALSE,
    has_cell                BOOLEAN         NOT NULL DEFAULT FALSE,
    has_pbb                 BOOLEAN         NOT NULL DEFAULT FALSE,
    domains_active          INTEGER         NOT NULL,

    -- Domain specific IDs
    cib_client_id           VARCHAR(64),
    forex_client_id         VARCHAR(64),
    insurance_client_id     VARCHAR(64),
    cell_client_id          VARCHAR(64),
    pbb_client_id           VARCHAR(64),

    -- =====================================================
    -- CIB METRICS
    -- =====================================================
    cib_active_corridors    INTEGER,
    cib_annual_value        DECIMAL(18,2),
    cib_payment_count_90d   INTEGER,
    cib_new_countries_90d   INTEGER,
    cib_health_status       VARCHAR(16),
    cib_last_activity       DATE,
    cib_estimated_revenue   DECIMAL(18,2),

    -- =====================================================
    -- FOREX METRICS
    -- =====================================================
    forex_currencies_traded INTEGER,
    forex_annual_volume     DECIMAL(18,2),
    forex_hedged_value      DECIMAL(18,2),
    forex_unhedged_value    DECIMAL(18,2),
    forex_hedge_ratio_pct   DECIMAL(5,2),
    forex_is_adequately_hedged BOOLEAN,
    forex_open_forwards     INTEGER,
    forex_last_activity     DATE,
    forex_estimated_revenue DECIMAL(18,2),

    -- =====================================================
    -- INSURANCE METRICS
    -- =====================================================
    insurance_active_policies INTEGER,
    insurance_annual_premium DECIMAL(18,2),
    insurance_sum_insured   DECIMAL(18,2),
    insurance_coverage_gaps INTEGER,
    insurance_coverage_gap_value DECIMAL(18,2),
    insurance_lapsing_90d   INTEGER,
    insurance_open_claims   INTEGER,
    insurance_loss_ratio    DECIMAL(8,2),
    insurance_last_activity DATE,

    -- =====================================================
    -- CELL NETWORK METRICS
    -- =====================================================
    cell_total_sims         INTEGER,
    cell_estimated_employees INTEGER,
    cell_countries_active   INTEGER,
    cell_sim_growth_pct     DECIMAL(8,2),
    cell_is_expanding       BOOLEAN,
    cell_monthly_data_gb    DECIMAL(12,2),
    cell_momo_monthly_value DECIMAL(18,2),
    cell_smartphone_pct     DECIMAL(5,2),
    cell_ussd_banking_sessions INTEGER,
    cell_last_activity      DATE,

    -- =====================================================
    -- PBB METRICS
    -- =====================================================
    pbb_employee_accounts   INTEGER,
    pbb_total_employees     INTEGER,
    pbb_monthly_payroll     DECIMAL(18,2),
    pbb_average_salary      DECIMAL(18,2),
    pbb_digital_adoption_pct DECIMAL(5,2),
    pbb_dormant_pct         DECIMAL(5,2),
    pbb_last_activity       DATE,

    -- =====================================================
    -- CROSS DOMAIN CALCULATED FIELDS
    -- =====================================================

    -- Total relationship value (all domains combined)
    total_relationship_value_zar DECIMAL(18,2) NOT NULL,

    -- Cross sell opportunity
    cross_sell_priority     VARCHAR(16)     NOT NULL,
    cross_sell_score        DECIMAL(5,2),
    missing_product_count   INTEGER,
    missing_products        VARCHAR(256),

    -- Risk signals
    primary_risk_signal     VARCHAR(32)     NOT NULL,
    risk_score              DECIMAL(5,2),

    -- Workforce capture
    cell_pbb_capture_ratio  DECIMAL(5,2),
    uncaptured_employees    INTEGER,
    payroll_capture_opportunity_zar DECIMAL(18,2),

    -- Competitive leakage
    competitive_leakage_detected BOOLEAN,
    leakage_countries       VARCHAR(128),
    leakage_estimated_value DECIMAL(18,2),

    -- Data shadow health
    shadow_health_score     DECIMAL(5,2),
    shadow_open_gaps        INTEGER,
    shadow_total_opportunity DECIMAL(18,2),

    -- Last activity across all domains
    last_activity_any_domain DATE,
    days_since_any_activity INTEGER,

    -- =====================================================
    -- GOVERNANCE
    -- =====================================================
    data_classification     VARCHAR(32)     NOT NULL DEFAULT 'POPIA_RESTRICTED',
    contains_za_pii         BOOLEAN,
    contains_ng_pii         BOOLEAN,
    contains_ke_pii         BOOLEAN,
    cross_border_flag       BOOLEAN,

    -- =====================================================
    -- METADATA
    -- =====================================================
    record_created_at       TIMESTAMP       NOT NULL,
    record_updated_at       TIMESTAMP       NOT NULL,
    dbt_run_id              VARCHAR(64),
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'gold',
    'freshness_sla' = '5_minutes',
    'accuracy_target' = '99.97'
);
