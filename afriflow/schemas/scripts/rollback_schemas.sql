-- =========================================================
-- AFRIFLOW: SCHEMA MIGRATION ROLLBACK SCRIPT
-- 
-- This script provides rollback capabilities for all
-- AfriFlow schema changes. Use with caution - rolling back
-- will DROP tables and potentially lose data.
--
-- Usage:
--   1. Review the rollback statements carefully
--   2. Ensure you have a backup before proceeding
--   3. Execute: spark-sql --file rollback_schemas.sql
--
-- DISCLAIMER: This project is not a sanctioned initiative
-- of Standard Bank Group, MTN, or any affiliated entity.
-- =========================================================

-- =========================================================
-- ROLLBACK: GOLD LAYER
-- =========================================================

-- Unified Golden Record
DROP TABLE IF EXISTS gold_unified_client_record;
DROP TABLE IF EXISTS gold_cross_sell_matrix;
DROP TABLE IF EXISTS gold_corridor_intelligence;
DROP TABLE IF EXISTS gold_group_revenue_360;
DROP TABLE IF EXISTS gold_risk_heatmap;

-- Signal Tables
DROP TABLE IF EXISTS gold_signal_expansion;
DROP TABLE IF EXISTS gold_signal_shadow_gap;
DROP TABLE IF EXISTS gold_signal_currency_event;

-- Domain Marts
DROP TABLE IF EXISTS mart_cib_client_flows;
DROP TABLE IF EXISTS mart_cib_corridor_analytics;
DROP TABLE IF EXISTS mart_forex_exposure;
DROP TABLE IF EXISTS mart_policy_analytics;
DROP TABLE IF EXISTS mart_cell_intelligence;
DROP TABLE IF EXISTS mart_payroll_analytics;

-- =========================================================
-- ROLLBACK: SILVER LAYER
-- =========================================================

-- CIB Silver
DROP TABLE IF EXISTS silver_cib_payments;
DROP TABLE IF EXISTS silver_cib_trade_finance;

-- Forex Silver
DROP TABLE IF EXISTS silver_forex_trades;

-- Insurance Silver
DROP TABLE IF EXISTS silver_insurance_policies;
DROP TABLE IF EXISTS silver_insurance_claims;

-- Cell Silver
DROP TABLE IF EXISTS silver_cell_corporate_usage;

-- PBB Silver
DROP TABLE IF EXISTS silver_pbb_corporate_payroll;

-- =========================================================
-- ROLLBACK: BRONZE LAYER
-- =========================================================

-- CIB Bronze
DROP TABLE IF EXISTS bronze_cib_payments;
DROP TABLE IF EXISTS bronze_cib_trade_finance;
DROP TABLE IF EXISTS bronze_cib_cash_management;

-- Forex Bronze
DROP TABLE IF EXISTS bronze_forex_trades;
DROP TABLE IF EXISTS bronze_forex_rates;

-- Insurance Bronze
DROP TABLE IF EXISTS bronze_insurance_policies;
DROP TABLE IF EXISTS bronze_insurance_claims;

-- Cell Bronze
DROP TABLE IF EXISTS bronze_cell_usage;
DROP TABLE IF EXISTS bronze_cell_momo;
DROP TABLE IF EXISTS bronze_cell_sim_activations;

-- PBB Bronze
DROP TABLE IF EXISTS bronze_pbb_accounts;
DROP TABLE IF EXISTS bronze_pbb_payroll;

-- =========================================================
-- ROLLBACK: GOVERNANCE TABLES
-- =========================================================

DROP TABLE IF EXISTS entity_resolution;
DROP TABLE IF EXISTS entity_match_log;
DROP TABLE IF EXISTS entity_verification_queue;
DROP TABLE IF EXISTS ref_sim_deflation;
DROP TABLE IF EXISTS ref_seasonal_calendar;
DROP TABLE IF EXISTS ref_currency_country;

-- Audit and Lineage
DROP TABLE IF EXISTS governance_data_lineage;
DROP TABLE IF EXISTS governance_access_log;
DROP TABLE IF EXISTS governance_data_quality;

-- =========================================================
-- ROLLBACK: DBT MODELS (Integration Layer)
-- =========================================================

-- These are typically views/tables created by dbt
-- Drop in reverse dependency order

DROP TABLE IF EXISTS mart_risk_heatmap;
DROP TABLE IF EXISTS mart_cross_sell_matrix;
DROP TABLE IF EXISTS mart_group_revenue_360;
DROP TABLE IF EXISTS mart_unified_client;

-- =========================================================
-- ROLLBACK: DBT MODELS (Domain Layers)
-- =========================================================

-- Insurance
DROP TABLE IF EXISTS mart_claims_intelligence;
DROP TABLE IF EXISTS mart_policy_analytics;
DROP TABLE IF EXISTS int_insurance_enriched;
DROP TABLE IF EXISTS stg_insurance_policies;

-- Cell
DROP TABLE IF EXISTS mart_momo_analytics;
DROP TABLE IF EXISTS mart_cell_intelligence;
DROP TABLE IF EXISTS int_cell_enriched;
DROP TABLE IF EXISTS stg_cell_usage;

-- PBB
DROP TABLE IF EXISTS mart_payroll_analytics;
DROP TABLE IF EXISTS mart_pbb_client;
DROP TABLE IF EXISTS int_pbb_enriched;
DROP TABLE IF EXISTS stg_pbb_accounts;

-- Forex
DROP TABLE IF EXISTS mart_hedge_analytics;
DROP TABLE IF EXISTS mart_forex_exposure;
DROP TABLE IF EXISTS int_forex_enriched;
DROP TABLE IF EXISTS stg_forex_trades;

-- =========================================================
-- VERIFICATION QUERIES
-- =========================================================

-- Verify all tables have been dropped
SELECT 
    'Tables remaining' as check_type,
    COUNT(*) as count
FROM information_schema.tables
WHERE table_schema = 'afriflow';

-- =========================================================
-- POST-ROLLBACK CLEANUP
-- =========================================================

-- Note: Delta Lake tables may leave data files behind
-- To fully clean up, you may need to:
-- 1. Run VACUUM on Delta tables (if any remain)
-- 2. Clean up underlying storage locations
-- 3. Remove checkpoint files

-- Example VACUUM command (use with extreme caution):
-- VACUUM table_name RETAIN 0 HOURS;

-- =========================================================
-- END OF ROLLBACK SCRIPT
-- =========================================================
