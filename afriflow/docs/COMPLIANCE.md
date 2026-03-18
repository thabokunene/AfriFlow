<!--
@file COMPLIANCE.md
@description Regulatory compliance framework across jurisdictions and domain constraints
@author Thabo Kunene
@created 2026-03-17
-->

# Regulatory Compliance Framework

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Multi-Jurisdictional Challenge

AfriFlow operates across 20 African countries, each with its own data
protection, banking, telecommunications, and financial advisory
regulations. We do not treat compliance as a checkbox. We treat it as
a first-class architectural constraint.

## South Africa (Primary Jurisdiction)

### POPIA (Protection of Personal Information Act, 2013)

| Requirement | AfriFlow Implementation |
|------------|------------------------|
| Lawful processing basis | Legitimate interest for existing client relationship; consent for cell data |
| Purpose limitation | Each domain's data used only for documented purposes in data contracts |
| Minimization | Gold layer contains aggregated metrics, not raw PII |
| Storage limitation | Bronze layer data retention: 7 years (banking regulatory minimum) |
| Data subject rights | API endpoint to retrieve all data for a given client (right of access) |
| Cross-border transfer | Federated architecture ensures PII stays in jurisdiction |
| Information Officer notification | Documented in governance framework |

### FAIS (Financial Advisory and Intermediary Services Act)

When AfriFlow generates product recommendations (e.g., "offer FX
hedging"), these may constitute financial advice under FAIS. We
mitigate by:

1. Framing outputs as "intelligence signals" not "advice"
2. Requiring RM to apply professional judgment before acting
3. Logging all generated recommendations for audit purposes
4. Including FAIS disclaimer on all client-facing materials derived
   from AfriFlow signals

### Banks Act and SARB Prudential Standards

- Client data used for risk assessment must meet SARB data quality
  standards
- Cross-domain risk signals that inform credit decisions must be
  documented and auditable
- We maintain complete data lineage from source to signal

## Nigeria

### NDPR (Nigeria Data Protection Regulation, 2019)

| Requirement | AfriFlow Implementation |
|------------|------------------------|
| Data localization | Nigeria country pod with local Delta Lake |
| Consent | Double opt-in for cell data processing |
| DPO appointment | Required for Standard Bank Nigeria entity |
| Annual audit | Data protection audit of NG pod |

### CBN Regulations

- FX transaction data must be reported per CBN guidelines
- Our forex domain maintains CBN-compliant reporting views
- Capital control status tracked in currency event propagator

## Kenya

### DPA 2019 (Data Protection Act)

| Requirement | AfriFlow Implementation |
|------------|------------------------|
| Registration with ODPC | Required for data processing activities |
| Data localization | Kenya country pod for KE client data |
| Cross-border transfer | Adequacy assessment required for each destination |

### CBK Prudential Guidelines

- Client data used for credit assessment must meet CBK standards
- We document all data sources contributing to credit-related signals

## Cell Network Specific Compliance

### RICA (South Africa)

- SIM registration data is RICA-regulated
- We do not store raw RICA registration details
- We use only aggregate SIM count and activation metadata

### NCC (Nigeria)

- Nigerian telecom data subject to NCC oversight
- MTN Nigeria data sharing agreement must comply with NCC guidelines
- We process only corporate SIM metadata, not individual subscriber data

### General Telecom Data Principles

Across all 20 countries, we apply these principles to cell domain data:

1. We process corporate SIM aggregates, not individual subscriber CDRs
2. We do not store voice call content, SMS content, or browsing history
3. We use MoMo transaction aggregates, not individual transaction details
4. All cell data is classified as "RESTRICTED" in our access control matrix

## Insurance Act Compliance

- Insurance recommendation signals must comply with the Insurance Act
  and FAIS requirements for intermediary services
- We do not provide insurance quotes or bind coverage through AfriFlow
- We generate "coverage gap signals" that route to licensed brokers

## Audit Trail

Every data access, every signal generation, and every RM action is
logged in an immutable audit trail:

```sql
CREATE TABLE audit_trail (
    audit_id        VARCHAR(50) PRIMARY KEY,
    event_timestamp TIMESTAMP NOT NULL,
    user_id         VARCHAR(100) NOT NULL,
    action_type     VARCHAR(50) NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     VARCHAR(100),
    golden_id       VARCHAR(50),
    domain          VARCHAR(20),
    country_code    VARCHAR(2),
    details         TEXT,
    ip_address      VARCHAR(45),
    session_id      VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Access Control Matrix

| Role | CIB Detail | Forex Detail | Insurance Detail | Cell Detail | PBB Detail | Golden Record |
|------|-----------|-------------|-----------------|------------|-----------|---------------|
| CIB RM | Full | Summary | Summary | Summary | Summary | Full |
| FX Advisor | Summary | Full | None | None | None | Partial |
| Insurance Broker | None | None | Full | None | None | Partial |
| Cell Partnership Manager | None | None | None | Full | None | Partial |
| PBB Branch Manager | None | None | None | None | Full | Partial |
| Group ExCo | Summary | Summary | Summary | Summary | Summary | Full (aggregated) |
| Data Engineer | Schema only | Schema only | Schema only | Schema only | Schema only | Schema only |

## Files in This Module

| File | Purpose |
|------|---------|
| `governance/popia_classifier.py` | PII detection and classification |
| `governance/fais_compliance.py` | Financial advisory compliance checks |
| `governance/insurance_act_compliance.py` | Insurance regulatory checks |
| `governance/cell_privacy_compliance.py` | Telecom data privacy rules |
| `governance/cross_border_data_rules.py` | Country-level data residency |
| `governance/access_control_matrix.py` | Role-based access enforcement |
| `governance/audit_trail_logger.py` | Immutable audit logging |
| `governance/data_lineage_tracker.py` | Field-level lineage tracking |
