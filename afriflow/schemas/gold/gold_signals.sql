-- =========================================================
-- AFRIFLOW: GOLD LAYER - CROSS DOMAIN SIGNAL TABLES
--
-- These tables capture every cross-domain signal that
-- AfriFlow detects. They serve as both the operational
-- alert source and the historical audit trail.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


-- ---------------------------------------------------------
-- EXPANSION SIGNALS
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_signal_expansion (
    signal_id               VARCHAR(64)     NOT NULL,
    golden_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256)    NOT NULL,
    client_tier             VARCHAR(16),
    relationship_manager    VARCHAR(128),

    expansion_country       VARCHAR(4)      NOT NULL,
    expansion_city          VARCHAR(128),
    confidence_score        DECIMAL(5,2)    NOT NULL,
    urgency                 VARCHAR(16)     NOT NULL,

    -- Evidence per domain
    cib_new_payments        INTEGER,
    cib_corridor_value_30d  DECIMAL(18,2),
    cib_new_suppliers       INTEGER,
    cell_new_sims           INTEGER,
    cell_growth_pct         DECIMAL(8,2),
    forex_new_trades        INTEGER,
    forex_hedging_in_place  BOOLEAN,
    insurance_coverage_gap  BOOLEAN,
    pbb_new_employees       INTEGER,

    -- Opportunity
    estimated_opportunity_zar DECIMAL(18,2),
    recommended_products    VARCHAR(512),

    -- Lifecycle
    detection_date          DATE            NOT NULL,
    alert_sent              BOOLEAN         NOT NULL DEFAULT FALSE,
    alert_sent_date         DATE,
    rm_acknowledged         BOOLEAN         DEFAULT FALSE,
    rm_acknowledged_date    DATE,
    outcome_recorded        BOOLEAN         DEFAULT FALSE,
    outcome                 VARCHAR(32),
    revenue_booked_zar      DECIMAL(18,2),

    -- Metadata
    model_version           VARCHAR(16),
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
-- DATA SHADOW GAP SIGNALS
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_signal_shadow_gap (
    gap_id                  VARCHAR(64)     NOT NULL,
    golden_id               VARCHAR(64)     NOT NULL,
    client_name             VARCHAR(256),

    rule_id                 VARCHAR(32)     NOT NULL,
    gap_type                VARCHAR(32)     NOT NULL,
    severity                VARCHAR(16)     NOT NULL,

    source_domain           VARCHAR(16)     NOT NULL,
    target_domain           VARCHAR(16)     NOT NULL,
    country                 VARCHAR(4),
    currency                VARCHAR(4),

    -- Evidence
    evidence_json           VARCHAR(2048),
    interpretation          VARCHAR(512),
    recommended_action      VARCHAR(512),

    -- Opportunity
    revenue_opportunity_zar DECIMAL(18,2),
    compliance_concern      BOOLEAN,

    -- Lifecycle
    gap_opened_date         DATE            NOT NULL,
    gap_closed_date         DATE,
    is_open                 BOOLEAN         NOT NULL DEFAULT TRUE,

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
-- CURRENCY EVENT IMPACT LOG
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold_signal_currency_event (
    event_id                VARCHAR(64)     NOT NULL,
    currency                VARCHAR(4)      NOT NULL,
    country                 VARCHAR(4)      NOT NULL,
    event_type              VARCHAR(32)     NOT NULL,
    magnitude_pct           DECIMAL(8,4)    NOT NULL,

    official_rate_before    DECIMAL(18,8),
    official_rate_after     DECIMAL(18,8),
    parallel_rate           DECIMAL(18,8),

    overall_severity        VARCHAR(16)     NOT NULL,
    total_affected_clients  INTEGER         NOT NULL,
    total_affected_value_zar DECIMAL(18,2)  NOT NULL,

    -- Per domain impact
    cib_affected_clients    INTEGER,
    cib_affected_value_zar  DECIMAL(18,2),
    forex_affected_clients  INTEGER,
    forex_affected_value_zar DECIMAL(18,2),
    insurance_affected_clients INTEGER,
    insurance_affected_value_zar DECIMAL(18,2),
    cell_jv_impact_zar      DECIMAL(18,2),
    pbb_advance_demand_zar  DECIMAL(18,2),

    -- Commodity context
    commodity_correlation   VARCHAR(32),
    commodity_price_change  DECIMAL(8,4),

    -- Timing
    detected_at             TIMESTAMP       NOT NULL,
    report_generated_at     TIMESTAMP,
    report_delivered_at     TIMESTAMP,
    source                  VARCHAR(32),

    -- Metadata
    snapshot_date           DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (snapshot_date)
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'integration',
    'layer' = 'gold'
);
