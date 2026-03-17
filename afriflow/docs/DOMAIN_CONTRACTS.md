<!-- docs/DOMAIN_CONTRACTS.md -->

# Domain Data Contracts

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## What Is a Data Contract

A data contract is a formal agreement between a data producer (domain)
and data consumers (integration layer, other domains, analytics). It
specifies:

1. **Schema**: What fields are produced, their types, and constraints
2. **Quality**: Minimum completeness, accuracy, and freshness
3. **SLA**: Maximum latency from source event to Kafka topic
4. **Volume**: Expected daily event volume (for capacity planning)
5. **Ownership**: Who is responsible for the data
6. **Change management**: How schema changes are communicated

## CIB Domain Contract

```yaml
domain: cib
owner: CIB Data Engineering
contact: cib-data-team@standardbank.co.za

schemas:
  - name: cib.payments.v2
    format: avro
    compatibility: BACKWARD
    fields:
      - name: payment_id
        type: string
        required: true
        description: Unique payment identifier
      - name: debtor_client_id
        type: string
        required: true
      - name: creditor_country
        type: string
        required: true
        quality_threshold: 99.5%
      - name: amount
        type: double
        required: true
        quality_threshold: 100%
      - name: currency
        type: string
        required: true
      - name: business_date
        type: string
        format: YYYY-MM-DD
        required: true

quality:
  completeness:
    creditor_country: ">= 99.5%"
    debtor_client_id: "100%"
    amount: "100%"
  freshness:
    max_latency: "5 minutes from source event"
  volume:
    daily_expected: "50,000 to 200,000 events"
    alert_threshold: "< 10,000 events (possible source outage)"

sla:
  availability: "99.5%"
  support_hours: "24/7 for CRITICAL, business hours for others"

change_management:
  notice_period: "14 days for schema changes"
  breaking_changes: "Not permitted under BACKWARD compatibility"
  notification_channel: "#afriflow-contracts (Slack)"
```

## Forex Domain Contract

```yaml
domain: forex
owner: Treasury Data Engineering
contact: fx-data-team@standardbank.co.za

schemas:
  - name: forex.trades.v1
    format: avro
    compatibility: BACKWARD
    fields:
      - name: trade_id
        type: string
        required: true
      - name: client_id
        type: string
        required: true
      - name: source_currency
        type: string
        required: true
      - name: target_currency
        type: string
        required: true
      - name: amount
        type: double
        required: true
      - name: rate
        type: double
        required: true
      - name: trade_type
        type: string
        required: true
        allowed_values: ["SPOT", "FORWARD", "SWAP", "OPTION"]
      - name: is_hedge
        type: boolean
        required: true
      - name: trade_date
        type: string
        format: YYYY-MM-DD
        required: true

quality:
  completeness:
    client_id: "100%"
    target_currency: "100%"
    is_hedge: ">= 98%"
  freshness:
    max_latency: "2 minutes from trade execution"

sla:
  availability: "99.9%"
```

## Insurance Domain Contract

```yaml
domain: insurance
owner: Liberty/Standard Bank Insurance Data Team
contact: insurance-data@liberty.co.za

schemas:
  - name: insurance.policies.v1
    format: avro
    fields:
      - name: policy_id
        type: string
        required: true
      - name: client_id
        type: string
        required: true
      - name: coverage_country
        type: string
        required: true
      - name: coverage_type
        type: string
        required: true
        allowed_values: ["COMMERCIAL_ASSET", "TRADE_CREDIT",
                         "GROUP_LIFE", "CREDIT_LIFE", "CARGO"]
      - name: premium_annual
        type: double
        required: true
      - name: status
        type: string
        required: true
        allowed_values: ["ACTIVE", "LAPSED", "CANCELLED", "PENDING"]

quality:
  completeness:
    coverage_country: ">= 97%"
    premium_annual: "100%"
  freshness:
    max_latency: "1 hour from policy system update"
```

## Cell Network Domain Contract

```yaml
domain: cell
owner: MTN Partnership Data Team
contact: mtn-integration@standardbank.co.za

schemas:
  - name: cell.sim_activations.v1
    format: avro
    fields:
      - name: activation_id
        type: string
        required: true
      - name: corporate_client_id
        type: string
        required: true
      - name: activation_country
        type: string
        required: true
      - name: city
        type: string
        required: false
        quality_threshold: 80%
      - name: sim_count
        type: int
        required: true
      - name: activation_date
        type: string
        format: YYYY-MM-DD
        required: true

quality:
  completeness:
    corporate_client_id: ">= 95%"
    activation_country: "100%"
    city: ">= 80%"
  freshness:
    max_latency: "24 hours (Tier 2 integration)"
    target_latency: "1 hour (Tier 1 integration)"

notes:
  - "Data availability varies by country. See docs/FEDERATED_ARCHITECTURE.md"
  - "SIM counts require deflation adjustment. See docs/SIM_DEFLATION.md"
  - "MoMo transaction data contract is separate (cell.momo.v1)"
```

## PBB Domain Contract

```yaml
domain: pbb
owner: PBB Data Engineering
contact: pbb-data-team@standardbank.co.za

schemas:
  - name: pbb.payroll.v1
    format: avro
    fields:
      - name: payroll_id
        type: string
        required: true
      - name: corporate_client_id
        type: string
        required: true
      - name: employee_country
        type: string
        required: true
      - name: employee_count
        type: int
        required: true
      - name: total_payroll_value
        type: double
        required: true
      - name: payroll_date
        type: string
        format: YYYY-MM-DD
        required: true

quality:
  completeness:
    corporate_client_id: "100%"
    employee_country: "100%"
  freshness:
    max_latency: "4 hours from payroll processing"
```

## Contract Violation Handling

When a domain violates its contract (quality threshold breached,
freshness SLA missed, unexpected volume drop), the system:

1. Logs the violation in the governance audit trail
2. Notifies the domain owner via configured channel
3. Marks downstream Gold layer records as "DEGRADED" with a reason
4. If violation persists beyond grace period, activates circuit breaker
   and serves last-known-good data with staleness warning

## Files in This Module

| File | Purpose |
|------|---------|
| `orchestration/data_contracts/cib_contract.yml` | CIB domain contract |
| `orchestration/data_contracts/forex_contract.yml` | Forex domain contract |
| `orchestration/data_contracts/insurance_contract.yml` | Insurance domain contract |
| `orchestration/data_contracts/cell_contract.yml` | Cell domain contract |
| `orchestration/data_contracts/pbb_contract.yml` | PBB domain contract |
| `governance/contract_monitor.py` | Monitors contract compliance |
