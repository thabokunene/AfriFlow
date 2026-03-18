<!--
@file DATA_SHADOW_MODEL.md
@description Defines data shadow model, expectation rules, and monitoring approach
@author Thabo Kunene
@created 2026-03-17
-->

# AfriFlow Data Shadow Model

> DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
> by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
> demonstration of concept, domain knowledge, and technical skill built by
> Thabo Kunene for portfolio and learning purposes only. All data is
> simulated. No real client, transaction, or proprietary information is used.

## Core Concept

In developed markets, missing data is treated as an engineering problem to
fix. In Africa, we treat the absence of data as a signal.

The Data Shadow Model maintains an expected data footprint for every client
across all five domains. We compare what we expect to see against what we
actually see. The gaps, which we call shadows, are themselves valuable
intelligence.

## How It Works

For every resolved client in the golden record, we compute an Expected
Domain Presence (EDP) based on what we know about them from other domains.

### Example

| What We Know | What We Expect | What We See | Shadow Signal |
|--------------|----------------|-------------|---------------|
| Client has R500M CIB activity in Nigeria | Cell data showing Nigerian SIM activations | Zero cell data for Nigeria | Client uses a competitor telco in Nigeria, or MTN feed is incomplete |
| Client has 2,000 employees per cell SIM data in Kenya | PBB payroll deposits for those employees | Zero PBB payroll from this client in Kenya | Employees are banking with a competitor. R5M per year revenue opportunity |
| Client has active CIB corridors to Ghana and Senegal | Forex hedging for GHS and XOF exposure | No GHS or XOF trades on record | Client is either unhedged (risk) or hedging with a competitor (leakage) |
| Client has construction operations in Mozambique | Insurance coverage for assets and workers | No insurance policies for Mozambique | Coverage gap creates both risk and sales opportunity |

## Shadow Categories

| Category | Description | Action |
|----------|-------------|--------|
| COMPETITIVE_LEAKAGE | Client uses a competitor for this domain in this market | Cross sell opportunity |
| COVERAGE_GAP | Client has operational exposure without corresponding coverage | Risk alert plus sales opportunity |
| DATA_FEED_ISSUE | We expect data but our feed is not delivering it | Engineering investigation |
| DORMANT_RELATIONSHIP | Client had activity in this domain but it stopped | Attrition investigation |
| NOT_APPLICABLE | Client genuinely does not need this domain in this market | No action, suppress alerts |

## Expected Domain Presence Rules

We derive EDP from cross domain inference rules.

```yaml
# config/data_shadow_rules.yml

rules:
  - name: cib_implies_forex
    description: >
      If a client has CIB payments in a foreign currency,
      we expect corresponding forex activity.
    source_domain: cib
    expected_domain: forex
    condition: "cib.corridors contains foreign currency payments"
    confidence: 0.85
    shadow_category_if_missing: COMPETITIVE_LEAKAGE

  - name: cib_implies_cell
    description: >
      If a client has CIB activity in a country where MTN operates,
      we expect cell data showing corporate SIM presence.
    source_domain: cib
    expected_domain: cell
    condition: "cib.active_countries intersects mtn.coverage_countries"
    confidence: 0.70
    shadow_category_if_missing: COMPETITIVE_LEAKAGE

  - name: cell_implies_pbb
    description: >
      If a client has corporate SIMs (employees), we expect
      payroll deposits in PBB.
    source_domain: cell
    expected_domain: pbb
    condition: "cell.corporate_sim_count > 50"
    confidence: 0.75
    shadow_category_if_missing: COMPETITIVE_LEAKAGE

  - name: cib_implies_insurance
    description: >
      If a client has significant CIB activity indicating
      physical operations, we expect insurance coverage.
    source_domain: cib
    expected_domain: insurance
    condition: "cib.annual_value > 10000000 and cib.payment_types contains SUPPLIER"
    confidence: 0.65
    shadow_category_if_missing: COVERAGE_GAP

  - name: forex_implies_hedge
    description: >
      If a client trades FX spot regularly, we expect
      corresponding forward or option hedges.
    source_domain: forex
    expected_domain: forex
    condition: "forex.spot_volume_90d > 50000000 and forex.forward_volume_90d < forex.spot_volume_90d * 0.3"
    confidence: 0.80
    shadow_category_if_missing: COVERAGE_GAP
```

## Revenue Attribution

Every shadow with category COMPETITIVE_LEAKAGE gets an estimated revenue
value based on the expected product penetration rate and average revenue
per product.

| Shadow Type | Estimation Method | Typical Value |
|-------------|-------------------|---------------|
| Missing forex hedging | 0.3% of estimated unhedged exposure | R500K to R10M per client |
| Missing insurance coverage | 0.2% of estimated asset value in country | R200K to R5M per client |
| Missing payroll capture | R2,500 per employee per year | R125K to R50M per client |
| Missing cell partnership | Estimated telco revenue share | R50K to R2M per client |

## Files in This Module

| File | Purpose |
|------|---------|
| `integration/data_shadow/shadow_calculator.py` | Core shadow computation engine |
| `integration/data_shadow/edp_rules_engine.py` | Expected Domain Presence rule evaluation |
| `integration/data_shadow/shadow_reporter.py` | Generates shadow reports for RMs |
| `integration/data_shadow/revenue_estimator.py` | Estimates revenue from shadow opportunities |
| `config/data_shadow_rules.yml` | Configurable shadow detection rules |
| `tests/unit/test_shadow_calculator.py` | Unit tests for shadow logic |
