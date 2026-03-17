# AfriFlow SQL Schema Documentation

## Overview

This document provides comprehensive documentation for all SQL schemas in the AfriFlow data platform. The schemas implement a medallion architecture (Bronze → Silver → Gold) with proper data governance, lineage tracking, and POPIA compliance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GOLD LAYER                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Unified Client  │ │ Cross-Sell      │ │ Risk Heatmap    │   │
│  │ Record          │ │ Matrix          │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Group Revenue   │ │ Corridor        │ │ Signal Tables   │   │
│  │ 360             │ │ Intelligence    │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────┐
│                       SILVER LAYER                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ CIB Payments │ │ Forex Trades │ │ Insurance    │            │
│  │              │ │              │ │ Policies     │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ Cell Usage   │ │ PBB Payroll  │                              │
│  │ (Deflated)   │ │              │                              │
│  └──────────────┘ └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────────┐
│                        BRONZE LAYER                              │
│  Raw ingested data from source systems (append-only)            │
│  - CIB: ISO 20022, MT103/MT202, FpML                           │
│  - Forex: FIX 4.4, SWIFT MT300, FpML                           │
│  - Insurance: ACORD XML, ACORD AL3                             │
│  - Cell: CDR (ASN.1), MoMo API, GSMA TAP3                      │
│  - PBB: ISO 8583, NACHA, REST API                              │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Schemas

### 1. CIB (Corporate Investment Banking)

#### Bronze Tables
- `bronze_cib_payments` - Raw ISO 20022 payment messages
- `bronze_cib_trade_finance` - Letters of credit, guarantees
- `bronze_cib_cash_management` - Sweep and pooling instructions

#### Silver Tables
- `silver_cib_payments` - Cleaned, validated payments with corridor derivation
- `silver_cib_trade_finance` - Enriched trade finance with utilisation tracking

#### Gold Marts
- `mart_cib_client_flows` - Client payment flow analytics
- `mart_cib_corridor_analytics` - Corridor-level volume and trend analysis

### 2. Forex (Foreign Exchange)

#### Bronze Tables
- `bronze_forex_trades` - Raw FX trade records (spot, forward, swap, options)
- `bronze_forex_rates` - Rate ticks including parallel market rates

#### Silver Tables
- `silver_forex_trades` - Enriched trades with hedge designation and African market flags

#### Gold Marts
- `mart_forex_exposure` - Client exposure and hedge adequacy
- `mart_hedge_analytics` - Hedge effectiveness and accounting qualification

### 3. Insurance

#### Bronze Tables
- `bronze_insurance_policies` - Raw policy administration data
- `bronze_insurance_claims` - Claims records with fraud flags

#### Silver Tables
- `silver_insurance_policies` - Cleaned policies with coverage gap analysis
- `silver_insurance_claims` - Enriched claims with loss ratios

#### Gold Marts
- `mart_policy_analytics` - Policy portfolio analytics
- `mart_claims_intelligence` - Claims frequency, severity, and fraud detection

### 4. Cell Network (MTN Partnership)

#### Bronze Tables
- `bronze_cell_usage` - SIM-level usage aggregations
- `bronze_cell_momo` - Mobile Money transactions
- `bronze_cell_sim_activations` - SIM activation events

#### Silver Tables
- `silver_cell_corporate_usage` - Corporate-level aggregations with SIM deflation

#### Gold Marts
- `mart_cell_intelligence` - Expansion signals and workforce estimates
- `mart_momo_analytics` - MoMo transaction patterns and salary detection

### 5. PBB (Personal & Business Banking)

#### Bronze Tables
- `bronze_pbb_accounts` - Account records with channel usage
- `bronze_pbb_payroll` - Payroll batch processing records

#### Silver Tables
- `silver_pbb_corporate_payroll` - Employer-level payroll aggregations

#### Gold Marts
- `mart_payroll_analytics` - Payroll health and retention metrics
- `mart_pbb_client` - Client relationship analytics

## Integration Layer

### Unified Golden Record
- `mart_unified_client` - Single client view across all 5 domains

### Cross-Domain Analytics
- `mart_group_revenue_360` - Revenue attribution across domains
- `mart_cross_sell_matrix` - Product gap analysis and NBA recommendations
- `mart_risk_heatmap` - Composite risk scoring

### Signal Tables
- `gold_signal_expansion` - Client expansion detection alerts
- `gold_signal_shadow_gap` - Data shadow gap identification
- `gold_signal_currency_event` - Currency event impact tracking

## Governance Tables

### Entity Resolution
- `entity_resolution` - Golden ID to domain ID mapping
- `entity_match_log` - Immutable match decision audit
- `entity_verification_queue` - Low-confidence matches for human review

### Reference Data
- `ref_sim_deflation` - Country-specific SIM-to-employee conversion factors
- `ref_seasonal_calendar` - Agricultural and economic seasonal patterns
- `ref_currency_country` - Currency metadata with capital control flags

### Audit & Lineage
- `governance_data_lineage` - Field-level lineage tracking
- `governance_access_log` - Access audit trail (7-year retention)
- `governance_data_quality` - Per-table quality metrics

## Data Classification

All tables include a `classification` property indicating data sensitivity:

| Classification | Description | Retention |
|---------------|-------------|-----------|
| POPIA_RESTRICTED | Contains personal information | 7 years |
| CONFIDENTIAL | Business sensitive | 5 years |
| INTERNAL | Internal use only | 3 years |
| PUBLIC | Can be shared externally | 1 year |

## Partitioning Strategy

Tables are partitioned for optimal query performance:

| Layer | Partition Column | Rationale |
|-------|-----------------|-----------|
| Bronze | `ingestion_date` | Time-based ingestion |
| Silver | `business_date` / `snapshot_date` | Business logic alignment |
| Gold | `snapshot_date` | Point-in-time analysis |
| Reference | None | Small, frequently joined tables |

## Validation Scripts

Run schema validation:
```bash
python afriflow/schemas/scripts/validate_schemas.py
```

Rollback all schemas:
```bash
spark-sql --file afriflow/schemas/scripts/rollback_schemas.sql
```

## dbt Configuration

All Gold layer tables are implemented as dbt models with:
- `materialized='table'` for performance
- Appropriate tags for job selection
- Column-level documentation
- Data tests (unique, not_null, accepted_values)

## POPIA Compliance

1. **Hashing**: All PII fields are hashed at bronze layer
2. **Minimisation**: Only necessary fields propagated to gold
3. **Access Control**: Classification-based access policies
4. **Audit Trail**: All access logged with 7-year retention
5. **Right to Erasure**: Soft delete with audit preservation

## Contact

For schema change requests or questions:
- Data Engineering Team: data-engineering@afriflow.internal
- Data Governance: data-governance@afriflow.internal
