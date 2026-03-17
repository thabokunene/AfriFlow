-- =========================================================
-- AFRIFLOW: ENTITY RESOLUTION TABLES
--
-- Supporting tables for the entity resolution engine
-- including the match log, human verification queue,
-- and SIM deflation reference data.
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- It is a demonstration of concept, domain knowledge,
-- and data engineering skill by Thabo Kunene.
-- =========================================================


-- ---------------------------------------------------------
-- Entity Resolution Master
-- Maps golden IDs to domain specific IDs
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS entity_resolution (
    golden_id               VARCHAR(64)     NOT NULL,
    canonical_name          VARCHAR(256)    NOT NULL,
    registration_number     VARCHAR(32),
    tax_number              VARCHAR(32),
    home_country            VARCHAR(4)      NOT NULL,

    -- Domain ID mapping
    cib_client_id           VARCHAR(64),
    forex_client_id         VARCHAR(64),
    insurance_client_id     VARCHAR(64),
    cell_client_id          VARCHAR(64),
    pbb_client_id           VARCHAR(64),

    -- Match quality
    match_confidence        DECIMAL(5,2)    NOT NULL,
    match_method            VARCHAR(32)     NOT NULL,
    domains_matched         INTEGER         NOT NULL,

    -- Verification
    human_verified          BOOLEAN         NOT NULL DEFAULT FALSE,
    verified_by             VARCHAR(64),
    verification_date       DATE,
    verification_notes      VARCHAR(512),

    -- Status
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    merged_into_golden_id   VARCHAR(64),
    split_from_golden_id    VARCHAR(64),

    -- Metadata
    created_at              TIMESTAMP       NOT NULL,
    updated_at              TIMESTAMP       NOT NULL,
    last_match_run_id       VARCHAR(64),

    PRIMARY KEY (golden_id)
)
USING DELTA
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'reference'
);


-- ---------------------------------------------------------
-- Match Audit Log
-- Immutable log of every match decision
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS entity_match_log (
    match_id                VARCHAR(64)     NOT NULL,
    match_run_id            VARCHAR(64)     NOT NULL,
    match_timestamp         TIMESTAMP       NOT NULL,

    -- Entities being compared
    entity_a_domain         VARCHAR(16)     NOT NULL,
    entity_a_id             VARCHAR(64)     NOT NULL,
    entity_a_name           VARCHAR(256),
    entity_b_domain         VARCHAR(16)     NOT NULL,
    entity_b_id             VARCHAR(64)     NOT NULL,
    entity_b_name           VARCHAR(256),

    -- Match result
    match_decision          VARCHAR(16)     NOT NULL,
    match_confidence        DECIMAL(5,2)    NOT NULL,
    match_method            VARCHAR(32)     NOT NULL,
    match_phase             INTEGER         NOT NULL,

    -- Match evidence
    reg_num_match           BOOLEAN,
    tax_num_match           BOOLEAN,
    name_similarity_score   DECIMAL(5,2),
    country_match           BOOLEAN,
    email_domain_match      BOOLEAN,
    phone_match             BOOLEAN,

    -- Resulting golden ID
    resulting_golden_id     VARCHAR(64),

    -- Partitioning
    match_date              DATE            NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'audit'
);


-- ---------------------------------------------------------
-- Human Verification Queue
-- Low confidence matches awaiting human review
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS entity_verification_queue (
    queue_id                VARCHAR(64)     NOT NULL,
    golden_id               VARCHAR(64)     NOT NULL,

    -- Proposed match
    entity_a_domain         VARCHAR(16)     NOT NULL,
    entity_a_id             VARCHAR(64)     NOT NULL,
    entity_a_name           VARCHAR(256),
    entity_b_domain         VARCHAR(16)     NOT NULL,
    entity_b_id             VARCHAR(64)     NOT NULL,
    entity_b_name           VARCHAR(256),

    match_confidence        DECIMAL(5,2)    NOT NULL,
    match_method            VARCHAR(32)     NOT NULL,
    match_evidence          VARCHAR(1024),

    -- Queue management
    queue_status            VARCHAR(16)     NOT NULL DEFAULT 'PENDING',
    assigned_to             VARCHAR(64),
    assigned_date           DATE,
    reviewed_date           DATE,
    review_decision         VARCHAR(16),
    review_notes            VARCHAR(512),
    priority                VARCHAR(16)     NOT NULL,

    created_at              TIMESTAMP       NOT NULL
)
USING DELTA
TBLPROPERTIES (
    'classification' = 'POPIA_RESTRICTED',
    'domain' = 'integration',
    'layer' = 'operational'
);


-- ---------------------------------------------------------
-- SIM Deflation Reference
-- Country specific SIM to employee conversion factors
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS ref_sim_deflation (
    country_code            VARCHAR(4)      NOT NULL,
    country_name            VARCHAR(64)     NOT NULL,
    deflation_factor        DECIMAL(5,2)    NOT NULL,
    avg_sims_per_person     DECIMAL(5,2)    NOT NULL,
    data_source             VARCHAR(128),
    calibration_date        DATE            NOT NULL,
    next_calibration_date   DATE,
    sample_size             INTEGER,
    confidence_interval     VARCHAR(32),
    notes                   VARCHAR(256),

    PRIMARY KEY (country_code)
)
USING DELTA
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'reference',
    'layer' = 'reference'
);

-- Insert reference data
INSERT INTO ref_sim_deflation VALUES
('ZA', 'South Africa',     0.77, 1.30, 'ICASA 2023 report', '2024-01-15', '2024-07-15', 45000, '95% CI: 0.72-0.82', NULL),
('NG', 'Nigeria',          0.36, 2.80, 'NCC subscriber data', '2024-01-15', '2024-07-15', 82000, '95% CI: 0.31-0.41', 'High multi-SIM usage'),
('KE', 'Kenya',            0.48, 2.10, 'CA Kenya annual report', '2024-01-15', '2024-07-15', 38000, '95% CI: 0.43-0.53', NULL),
('GH', 'Ghana',            0.52, 1.90, 'NCA Ghana data', '2024-01-15', '2024-07-15', 22000, '95% CI: 0.47-0.57', NULL),
('TZ', 'Tanzania',         0.42, 2.40, 'TCRA subscriber data', '2024-01-15', '2024-07-15', 28000, '95% CI: 0.37-0.47', NULL),
('UG', 'Uganda',           0.45, 2.20, 'UCC data', '2024-01-15', '2024-07-15', 18000, '95% CI: 0.40-0.50', NULL),
('MZ', 'Mozambique',       0.53, 1.90, 'INCM subscriber data', '2024-01-15', '2024-07-15', 12000, '95% CI: 0.48-0.58', NULL),
('CD', 'DRC',              0.40, 2.50, 'ARPTC estimate', '2024-01-15', '2024-07-15', 8000,  '95% CI: 0.33-0.47', 'Low data quality'),
('CI', 'Cote d Ivoire',    0.50, 2.00, 'ARTCI data', '2024-01-15', '2024-07-15', 15000, '95% CI: 0.45-0.55', NULL),
('AO', 'Angola',           0.44, 2.30, 'INACOM estimate', '2024-01-15', '2024-07-15', 10000, '95% CI: 0.38-0.50', NULL),
('ZM', 'Zambia',           0.55, 1.80, 'ZICTA data', '2024-01-15', '2024-07-15', 14000, '95% CI: 0.50-0.60', NULL),
('BW', 'Botswana',         0.65, 1.55, 'BOCRA data', '2024-01-15', '2024-07-15', 8000,  '95% CI: 0.60-0.70', NULL),
('NA', 'Namibia',          0.70, 1.43, 'CRAN report', '2024-01-15', '2024-07-15', 6000,  '95% CI: 0.65-0.75', NULL),
('SZ', 'Eswatini',         0.60, 1.67, 'ESCCOM data', '2024-01-15', '2024-07-15', 4000,  '95% CI: 0.54-0.66', NULL),
('LS', 'Lesotho',          0.58, 1.72, 'LCA data', '2024-01-15', '2024-07-15', 3000,  '95% CI: 0.52-0.64', NULL),
('MW', 'Malawi',           0.38, 2.60, 'MACRA data', '2024-01-15', '2024-07-15', 5000,  '95% CI: 0.32-0.44', 'High multi-SIM usage'),
('SS', 'South Sudan',      0.35, 2.85, 'NCA South Sudan est.', '2024-01-15', '2024-07-15', 2000,  '95% CI: 0.28-0.42', 'Very low data quality'),
('ET', 'Ethiopia',         0.62, 1.60, 'ECA data', '2024-01-15', '2024-07-15', 20000, '95% CI: 0.57-0.67', 'Single operator market'),
('SN', 'Senegal',          0.47, 2.15, 'ARTP data', '2024-01-15', '2024-07-15', 10000, '95% CI: 0.42-0.52', NULL),
('CM', 'Cameroon',         0.43, 2.30, 'ART data', '2024-01-15', '2024-07-15', 12000, '95% CI: 0.38-0.48', NULL);


-- ---------------------------------------------------------
-- Seasonal Calendar Reference
-- Agricultural and economic seasonal patterns
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS ref_seasonal_calendar (
    pattern_id              VARCHAR(32)     NOT NULL,
    country_code            VARCHAR(4)      NOT NULL,
    commodity_or_activity   VARCHAR(64)     NOT NULL,
    season_type             VARCHAR(16)     NOT NULL,
    description             VARCHAR(512),

    -- Monthly weights (1.0 = normal)
    weight_jan              DECIMAL(5,2)    NOT NULL,
    weight_feb              DECIMAL(5,2)    NOT NULL,
    weight_mar              DECIMAL(5,2)    NOT NULL,
    weight_apr              DECIMAL(5,2)    NOT NULL,
    weight_may              DECIMAL(5,2)    NOT NULL,
    weight_jun              DECIMAL(5,2)    NOT NULL,
    weight_jul              DECIMAL(5,2)    NOT NULL,
    weight_aug              DECIMAL(5,2)    NOT NULL,
    weight_sep              DECIMAL(5,2)    NOT NULL,
    weight_oct              DECIMAL(5,2)    NOT NULL,
    weight_nov              DECIMAL(5,2)    NOT NULL,
    weight_dec              DECIMAL(5,2)    NOT NULL,

    -- Peak and off season
    peak_months             VARCHAR(32),
    off_season_months       VARCHAR(32),
    affected_sectors        VARCHAR(256),

    -- Metadata
    data_source             VARCHAR(128),
    last_calibration        DATE,

    PRIMARY KEY (pattern_id)
)
USING DELTA
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'reference',
    'layer' = 'reference'
);


-- ---------------------------------------------------------
-- Currency Country Reference
-- Maps currencies to countries with control metadata
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS ref_currency_country (
    currency_code           VARCHAR(4)      NOT NULL,
    country_code            VARCHAR(4)      NOT NULL,
    country_name            VARCHAR(64)     NOT NULL,

    -- FX controls
    capital_control_level   VARCHAR(16),
    repatriation_restrictions BOOLEAN,
    parallel_market_exists  BOOLEAN,

    -- Commodity link
    primary_commodity       VARCHAR(32),
    commodity_correlation_r DECIMAL(5,2),

    -- Central bank
    central_bank_name       VARCHAR(128),
    intervention_frequency  VARCHAR(16),

    PRIMARY KEY (currency_code)
)
USING DELTA
TBLPROPERTIES (
    'classification' = 'INTERNAL',
    'domain' = 'reference',
    'layer' = 'reference'
);
