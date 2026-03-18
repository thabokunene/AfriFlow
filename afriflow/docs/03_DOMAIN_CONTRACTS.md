<!--
@file 03_DOMAIN_CONTRACTS.md
@description Domain data contracts specification: formats, frequencies, quality, and SLAs
@author Thabo Kunene
@created 2026-03-17
-->
# 03 Domain Contracts

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

## Purpose

We define data contracts between each business domain
and the integration layer. These contracts specify
what data each domain publishes, in what format, at
what frequency, and with what quality guarantees.

We treat contracts as enforceable agreements. If a
domain violates its contract (schema change without
notice, quality below threshold, feed offline beyond
SLA), the integration layer activates circuit breakers
and notifies the domain owner.

## Contract Structure

Every contract specifies the following.

```yaml
domain: [domain name]
version: [semantic version]
owner: [team or individual]
description: [what this data product represents]

schema:
  format: avro
  registry: [schema registry URL]
  compatibility: BACKWARD

delivery:
  method: kafka | sftp | api
  topic_or_path: [kafka topic or file path]
  frequency: real_time | hourly | daily | weekly
  timezone: [IANA timezone]

quality:
  completeness_threshold: [0 to 100]
  freshness_sla_minutes: [integer]
  uniqueness_key: [field or composite key]
  critical_fields:
    - field_name: [name]
      null_rate_max: [percentage]
      format_regex: [optional regex]

  circuit_breaker:
    consecutive_failures: [integer]
    action: pause_consumption | alert_only

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals
  - integration.unified_golden_record
```

CIB Contract

YAML

domain: cib
version: 2.1.0
owner: CIB Data Engineering
description: >
  Corporate and Investment Banking payment events
  including cross border payments, cash management
  transactions, and trade finance instruments.
  All payments conform to ISO 20022 message standards.

schema:
  format: avro
  registry: schema-registry:8081
  compatibility: BACKWARD

delivery:
  method: kafka
  topic: cib.payments.raw
  frequency: real_time
  timezone: Africa/Johannesburg

quality:
  completeness_threshold: 98
  freshness_sla_minutes: 5
  uniqueness_key: payment_id
  critical_fields:
    - field_name: debtor_client_id
      null_rate_max: 0.1
    - field_name: creditor_country
      null_rate_max: 0.5
      format_regex: "^[A-Z]{2}$"
    - field_name: amount
      null_rate_max: 0.0
    - field_name: currency
      null_rate_max: 0.0
      format_regex: "^[A-Z]{3}$"
    - field_name: business_date
      null_rate_max: 0.0

  circuit_breaker:
    consecutive_failures: 3
    action: pause_consumption

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals.expansion_signal
  - integration.cross_domain_signals.relationship_risk
  - integration.unified_golden_record

Forex Contract

YAML

domain: forex
version: 1.3.0
owner: Treasury Data Engineering
description: >
  Foreign exchange trade events including spot,
  forward, swap, and option transactions.
  Includes hedging classification flags.

schema:
  format: avro
  registry: schema-registry:8081
  compatibility: BACKWARD

delivery:
  method: kafka
  topic: forex.trades.raw
  frequency: real_time
  timezone: Africa/Johannesburg

quality:
  completeness_threshold: 99
  freshness_sla_minutes: 2
  uniqueness_key: trade_id
  critical_fields:
    - field_name: client_id
      null_rate_max: 0.0
    - field_name: base_currency
      null_rate_max: 0.0
    - field_name: target_currency
      null_rate_max: 0.0
    - field_name: amount
      null_rate_max: 0.0
    - field_name: trade_type
      null_rate_max: 0.0
    - field_name: is_hedge
      null_rate_max: 1.0

  circuit_breaker:
    consecutive_failures: 2
    action: pause_consumption

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals.hedge_gap
  - integration.currency_propagation
  - integration.unified_golden_record

Insurance Contract

YAML

domain: insurance
version: 1.1.0
owner: Insurance Data Engineering
description: >
  Insurance policy and claims events including group
  life, credit life, commercial asset, and trade
  credit products.

schema:
  format: avro
  registry: schema-registry:8081
  compatibility: BACKWARD

delivery:
  method: kafka
  topic: insurance.policies.raw
  frequency: real_time
  timezone: Africa/Johannesburg

quality:
  completeness_threshold: 95
  freshness_sla_minutes: 30
  uniqueness_key: policy_id
  critical_fields:
    - field_name: client_id
      null_rate_max: 0.0
    - field_name: coverage_country
      null_rate_max: 2.0
    - field_name: status
      null_rate_max: 0.0
    - field_name: premium_annual
      null_rate_max: 0.5

  circuit_breaker:
    consecutive_failures: 5
    action: alert_only

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals.supply_chain_risk
  - integration.unified_golden_record

Cell Network Contract

We define three tiers of integration to accommodate
varying data maturity across countries. See
08_FEDERATED_COUNTRY_PODS.md
for country specific details.

YAML

domain: cell
version: 1.0.0
owner: Digital and Telco Partnerships
description: >
  Cell network data including SIM activations, usage
  patterns, mobile money transactions, and USSD
  session data. Data arrives via one of three
  integration tiers depending on country maturity.

schema:
  format: avro
  registry: schema-registry:8081
  compatibility: BACKWARD

delivery:
  tier_1:
    method: kafka
    topic: cell.usage.raw
    frequency: real_time
    countries: [ZA, KE, NG]
  tier_2:
    method: sftp
    path: /data/cell/daily/{country_code}/
    frequency: daily
    countries: [GH, TZ, UG, ZM]
  tier_3:
    method: manual_upload
    path: /data/cell/monthly/{country_code}/
    frequency: monthly
    countries: [MZ, CD, AO, CI, SN]

quality:
  completeness_threshold: 80
  freshness_sla_minutes: 1440  # 24 hours for Tier 2
  uniqueness_key: sim_event_id
  critical_fields:
    - field_name: corporate_client_id
      null_rate_max: 5.0
    - field_name: activation_country
      null_rate_max: 0.0
    - field_name: sim_count
      null_rate_max: 0.0

  circuit_breaker:
    consecutive_failures: 10
    action: alert_only

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals.expansion_signal
  - integration.cross_domain_signals.workforce_signal
  - integration.unified_golden_record

notes: >
  Cell data quality varies significantly by country.
  We apply SIM to employee deflation factors per
  country (see domains/shared/sim_deflation_factors.py)
  to correct for multi SIM culture. We flag the
  confidence level of cell derived metrics in the
  golden record based on the integration tier.

PBB Contract

YAML

domain: pbb
version: 1.2.0
owner: PBB Data Engineering
description: >
  Personal and Business Banking data including
  current accounts, savings accounts, loan accounts,
  corporate payroll deposits, and digital banking
  transaction events.

schema:
  format: avro
  registry: schema-registry:8081
  compatibility: BACKWARD

delivery:
  method: kafka
  topic: pbb.accounts.raw
  frequency: real_time
  timezone: Africa/Johannesburg

quality:
  completeness_threshold: 97
  freshness_sla_minutes: 10
  uniqueness_key: account_id
  critical_fields:
    - field_name: corporate_client_id
      null_rate_max: 3.0
    - field_name: employee_country
      null_rate_max: 1.0
    - field_name: payroll_value
      null_rate_max: 0.0

  circuit_breaker:
    consecutive_failures: 3
    action: pause_consumption

consumers:
  - integration.entity_resolution
  - integration.cross_domain_signals.workforce_signal
  - integration.unified_golden_record
