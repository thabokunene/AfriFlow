<!--
@file COST_MODEL.md
@description Cost model assumptions and phased rollout plan for AfriFlow implementation
@author Thabo Kunene
@created 2026-03-17
-->
<!-- docs/COST_MODEL.md -->

# AfriFlow Cost Model and Phased Rollout

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Why We Must Present Both Sides

We claim R2B+ in revenue opportunity. ExCo will immediately ask
"what does this cost?" and "what is the phased investment plan?"
We present a credible cost model to demonstrate financial maturity,
not just technical ambition.

## Phase 1: Foundation (Months 1 to 6)

**Scope**: South Africa + Nigeria + Kenya. CIB + Forex domains only.

| Cost Category | Annual Estimate (ZAR) |
|--------------|----------------------|
| Kafka cluster (3 countries) | R4-6M |
| Flink/Spark compute | R6-10M |
| Delta Lake storage | R3-5M |
| Data engineering team (8 people) | R12-16M |
| Compliance and legal | R3-5M |
| Infrastructure (country pods NG, KE) | R6-8M |
| **Phase 1 Total** | **R34-50M** |

**Revenue target**: R80-120M from CIB corridor intelligence and forex
cross-sell signals in top 50 clients.

**ROI**: 1.6x to 3.5x in first year.

## Phase 2: Expansion (Months 7 to 12)

**Scope**: Add Ghana, Tanzania, Uganda, Mozambique. Add Insurance and
Cell domains.

| Cost Category | Incremental Annual (ZAR) |
|--------------|-------------------------|
| Additional Kafka/compute for 4 countries | R8-12M |
| MTN data licensing (estimated) | R15-30M |
| Insurance domain integration (Liberty) | R5-8M |
| Cell domain processing infrastructure | R6-10M |
| Additional data engineers (5 people) | R8-12M |
| Additional compliance (4 new jurisdictions) | R4-6M |
| **Phase 2 Incremental** | **R46-78M** |
| **Cumulative Annual** | **R80-128M** |

**Revenue target**: R300-500M from full cross-domain signals across
top 200 clients in 7 countries.

## Phase 3: Scale (Months 13 to 24)

**Scope**: All 20 countries. Add PBB domain. ML models in production.
Mobile RM app. Salesforce integration.

| Cost Category | Incremental Annual (ZAR) |
|--------------|-------------------------|
| Remaining 13 country pods | R10-20M |
| PBB domain integration | R5-8M |
| ML infrastructure (feature store, serving) | R6-10M |
| Mobile app development | R4-6M |
| Salesforce integration | R3-5M |
| Additional team growth (7 people) | R10-15M |
| **Phase 3 Incremental** | **R38-64M** |
| **Cumulative Annual** | **R118-192M** |

**Revenue target**: R800M-1.5B from full platform across all 20
countries and all 5 domains.

## Steady State (Year 3+)

| Cost Category | Annual (ZAR) |
|--------------|-------------|
| Infrastructure and compute | R50-80M |
| Team (25 people) | R40-55M |
| MTN data licensing | R20-40M |
| Compliance and legal | R10-15M |
| Maintenance and enhancements | R10-15M |
| **Steady State Total** | **R130-205M** |

**Revenue target**: R1.5-2.5B annually.

**Steady state ROI**: 7x to 19x.

## Risk Factors

| Risk | Mitigation |
|------|-----------|
| MTN data licensing cost exceeds estimate | Negotiate value-sharing model tied to revenue generated |
| Regulatory delays in Tier 1 countries | Begin with Tier 2/3 countries, add Tier 1 when approved |
| Entity resolution accuracy below 80% | Human-in-the-loop verification for top 500 clients |
| RM adoption below 50% | Embed in existing Salesforce workflow, not separate platform |
| Competitor launches similar capability | Accelerate Phase 1 to establish data network effects |
