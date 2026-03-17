

```markdown
# AfriFlow
<img width="2784" height="1536" alt="image" src="https://github.com/user-attachments/assets/f405b91d-838e-43dc-8f31-34d945fecfd8" />

**Cross-Divisional Data Integration Platform
for Standard Bank Group**

Unifying CIB, Forex, Insurance, Cell Network, and
Personal Banking data into a single client intelligence
layer across 20 African countries.

> **DISCLAIMER:** This project is not a sanctioned
> initiative of Standard Bank Group, MTN, or any
> affiliated entity. It is a demonstration of concept,
> domain knowledge, and data engineering skill by
> Thabo Kunene.

---

## The Problem

Standard Bank Group operates five major divisions.
Each has its own data lake, its own client identifiers,
and its own version of the truth.

```
┌──────────────────────────────────────────────────┐
│            STANDARD BANK GROUP                   │
│                                                  │
│  ┌───────┐  ┌───────┐  ┌─────────┐  ┌────────┐ │
│  │  CIB  │  │ FOREX │  │INSURANCE│  │  CELL  │ │
│  │       │  │       │  │         │  │NETWORK │ │
│  └───┬───┘  └───┬───┘  └────┬────┘  └───┬────┘ │
│      │          │           │            │      │
│      │    NO INTEGRATION    │            │      │
│      │          │           │            │      │
│      └──────────┴───────────┴────────────┘      │
│                      │                          │
│                 ┌────┴────┐                     │
│                 │   PBB   │                     │
│                 │Personal │                     │
│                 │Banking  │                     │
│                 └─────────┘                     │
└──────────────────────────────────────────────────┘
```

A Platinum corporate client might have a R500M cash
management relationship in CIB, a R200M forex hedging
book in Treasury, a R50M group insurance policy through
Liberty, and 15,000 employees using Standard Bank cell
phone banking through the MTN partnership.

Today, no single person at Standard Bank can see all
of that in one place.

---

## The Solution

AfriFlow creates a **Unified Golden Record** by:

1. **Ingesting** real-time event streams from all
   five domains via Apache Kafka
2. **Resolving** client entities across domains using
   deterministic and probabilistic matching
3. **Correlating** cross-domain signals that no single
   division can detect alone
4. **Generating** actionable intelligence for
   Relationship Managers before they walk into
   client meetings

---

## Architecture

![Architecture Overview](diagrams/architecture_overview_small.png)

```
  SOURCE DOMAINS          STREAMING        PROCESSING
 ┌─────┐ ┌─────┐
 │ CIB │ │FOREX│
 │     │ │     │        ┌────────┐       ┌──────────┐
 └──┬──┘ └──┬──┘        │ KAFKA  │       │  FLINK   │
    │       │     ──>   │        │  ──>  │(real-time)│
 ┌──┴──┐ ┌──┴──┐        │ Schema │       ├──────────┤
 │ INS │ │CELL │        │Registry│       │  SPARK   │
 │     │ │(MTN)│        └────────┘       │ (batch)  │
 └──┬──┘ └──┬──┘                         └────┬─────┘
    │       │                                  │
 ┌──┴──┐   │          MEDALLION LAKEHOUSE      │
 │ PBB │   │         ┌────────────────────┐    │
 └─────┘   │         │ BRONZE │ SILVER │ GOLD │
           │         └────────────────────┘    │
           │                                   │
           │         CROSS-DOMAIN INTELLIGENCE │
           │        ┌──────────────────────────┤
           └──────> │ Entity Resolution        │
                    │ Data Shadow Engine        │
                    │ Currency Propagator       │
                    │ Seasonal Calendar         │
                    │ Signal Detectors          │
                    │ Client Briefing Generator │
                    └──────────┬───────────────┘
                               │
                    ┌──────────┴───────────────┐
                    │  UNIFIED GOLDEN RECORD   │
                    │  Single client view       │
                    │  across 5 domains         │
                    │  Freshness SLA: <5 min    │
                    └──────────────────────────┘
```

---

## Cross-Domain Signals

These are the patterns that no single division can
detect alone. The power comes from correlation across
domains.

![Signal Matrix](diagrams/cross_domain_signal_matrix_small.png)

| Signal | Domains Combined | What We Detect |
|--------|-----------------|----------------|
| **Geographic Expansion** | CIB + Cell | New payment corridors plus SIM activations in a new country. Client is expanding 4 to 8 weeks before public announcement. |
| **Relationship Attrition** | CIB + Forex | FX hedging dropping while CIB payments shift to competitor corridors. Client is about to leave. |
| **Supply Chain Risk** | CIB + Insurance + Cell | Claims spiking in supplier network. MoMo payments to suppliers irregular. Concentration risk building. |
| **Workforce Capture** | Cell + PBB | 800 MTN SIMs in Nigeria but zero PBB payroll deposits. 288 employees (deflated) are banking elsewhere. |
| **Unhedged FX Exposure** | CIB + Forex | Cross-border payment seasonality not aligned with forward booking. Seasonal exposure gap. |
| **Insurance Coverage Gap** | CIB + Insurance + Cell | Active operations and employees in Ghana but zero insurance coverage. Assets unprotected. |
| **Competitive Leakage** | All 5 Domains | CIB payments growing but FX, insurance, cell, and payroll all with competitors. Quantified leakage. |
| **Currency Event Cascade** | All 5 Domains | Naira devalues 18.5%. Impact propagated across CIB facilities, FX positions, insurance coverage, MTN JV revenue, and employee purchasing power in 60 seconds. |
| **Corridor P&L Attribution** | CIB + Forex + Insurance + PBB | Total revenue per payment corridor across all domains. Shows which corridors are fully monetised and where product gaps exist. |
| **Seasonal False Alarm Filter** | CIB + Forex + Cell | Agricultural harvest cycles cause predictable payment drops. Without seasonal adjustment, the system would generate false attrition alerts. A Ghanaian cocoa exporter dropping 60% in February is normal. It is off season. |
| **Government Payment Health** | CIB + Cell + PBB | Government payment regularity as a sovereign risk proxy. When government payments slow, entire country portfolio at risk. |
| **MoMo Informal Economy Pulse** | Cell + CIB + Insurance | Mobile money patterns in supply chain reveal informal economy health invisible to formal banking data. |

---

## Data Shadow Engine

Most platforms analyse data that exists. We also
analyse data that is **missing**.

![Data Shadow](diagrams/data_shadow_diagram.png)

For every client, we model the expected data footprint
across all five domains based on known operations.
When reality diverges from expectation, the gap itself
is the signal.

```
CLIENT: Acme Corp (Platinum)

EXPECTED vs ACTUAL DATA FOOTPRINT
                ZA    KE    NG    GH    TZ
  CIB          [OK]  [OK]  [OK]  [OK]  [OK]
  FOREX        [OK]  [OK]  [GAP] [OK]   --
  INSURANCE    [OK]  [GAP] [GAP] [GAP]  --
  CELL (MTN)   [OK]  [OK]  [OK]  [GAP] [GAP]
  PBB          [OK]  [GAP] [GAP]  --    --

  GAPS DETECTED: 8
  REVENUE OPPORTUNITY: R24.3M
  COMPLIANCE CONCERNS: 2

  [GAP] = Expected but missing (signal)
  [OK]  = Data present as expected
   --   = Not expected for this client
```

Every red gap is a revenue opportunity or a compliance
concern. We generate RM alerts from the gaps, not
just from the data.

---

## Currency Event Propagation

In Africa, FX volatility is not an isolated risk. It
is a systemic event that cascades across every domain
simultaneously.

![Currency Propagation](diagrams/currency_propagation_flow_small.png)

When a major FX event occurs, AfriFlow propagates
impact across all five domains within 60 seconds:

```
EVENT: Nigerian Naira devalues 18.5%
       Official: 460 -> 561 NGN/USD
       Parallel: 620 NGN/USD

PROPAGATION (T+60 seconds):

  CIB ........... R777M facility impact
                  47 clients affected
                  Trade finance now inadequate

  FOREX ......... R148M unhedged loss
                  15 clients with ZERO hedging
                  Emergency outreach required

  INSURANCE ..... R89M coverage gap
                  Asset valuations need restatement
                  Sum insured now inadequate

  CELL (MTN) .... R45M JV revenue impact
                  MoMo recalibration needed
                  Monitor SIM churn for slowdown

  PBB ........... R32M salary advance demand
                  Employee purchasing power down 18.5%
                  Loan delinquency risk elevated 90 days

  TOTAL IMPACT:   R1,091M across 5 domains

Western banks stop at the FX desk.
We propagate everywhere. In 60 seconds.
```

---

## Entity Resolution

The hardest problem in cross-domain integration:
matching the same client across five systems that each
have their own ID, their own spelling, and their own
data quality.

![Entity Resolution](diagrams/entity_resolution_flow_small.png)

```
THE SAME CLIENT IN FIVE SYSTEMS:

  CIB .......... CIB-1234
                 "Acme Mining Corp (Pty) Ltd"

  FOREX ........ FX-ACME-ZA
                 "ACME MINING CORP"

  INSURANCE .... LIB-POL-98765
                 "Acme Mining Corporation"

  CELL ......... MTN-CORP-5678
                 "Acme Mining"

  PBB .......... PBB-ACC-112233
                 "ACME MINING (PTY) LTD"

AFTER ENTITY RESOLUTION:

  Golden ID .... GLD-A1B2C3D4E5F6
  Name ......... Acme Mining Corp (Pty) Ltd
  Confidence ... 100% (registration number match)
  Domains ...... 5 of 5 linked
```

We use a four-phase hierarchical matching algorithm:

1. **Registration number** (exact, 100% confidence)
2. **Tax number** (exact, 98% confidence)
3. **Fuzzy name + country** (probabilistic, 70 to 90%)
4. **Contact details** (supplementary, 85%)

All matches below 90% confidence go to a human
verification queue.

---

## Federated Country Pods

Nigerian data stays in Nigeria. Kenyan data stays in
Kenya. Only aggregated signals flow to the central hub.

![Federated Pods](diagrams/federated_pods_small.png)

```
TIER 1: Full Local Stack (strict data residency)
  NG  Nigeria ......... Kafka + Flink + Spark + Delta
  KE  Kenya ........... Kafka + Flink + Spark + Delta
  GH  Ghana ........... Kafka + Flink + Spark + Delta
  AO  Angola .......... Kafka + Flink + Spark + Delta

TIER 2: Lightweight Processing
  TZ  Tanzania ........ Kafka + Flink + Delta
  UG  Uganda .......... Kafka + Flink + Delta
  MZ  Mozambique ...... Kafka + Flink + Delta
  ZM  Zambia .......... Kafka + Flink + Delta

TIER 3: Batch Sync Only
  CD  DRC ............. Daily SFTP aggregated
  CI  Cote d'Ivoire ... Daily SFTP aggregated
  SN  Senegal ......... Daily SFTP aggregated
  +6  more country pods

CENTRAL HUB: South Africa
  Full compute stack
  Golden Record Master
  ML training cluster
  Cross-domain intelligence engine

FLOWS TO HUB:          STAYS LOCAL:
  Golden IDs             Customer names
  Aggregated volumes     Transaction records
  SIM counts (deflated)  Individual CDRs
  Hedge ratios           Policy beneficiaries
  Signal outputs         Payroll records
```

---

## Domain Data Flow

Each domain follows the same engineering pattern from
source to Gold layer.

![Domain Data Flow](diagrams/domain_data_flow_small.png)

---

## African Market Context

AfriFlow is built for realities that Western and East
Asian banking platforms do not model.

### SIM Deflation

In Africa, one employee commonly uses 2 to 4 SIM cards.
We apply country-specific deflation factors so that
800 MTN SIMs in Nigeria are correctly interpreted as
approximately 288 employees, not 800.

```
COUNTRY   DEFLATION   800 SIMs =
ZA        0.77        616 employees
NG        0.36        288 employees
KE        0.48        384 employees
GH        0.52        416 employees
TZ        0.42        336 employees
CD        0.40        320 employees
```

### Seasonal Adjustment

Agricultural harvest cycles drive corporate cash flows
in ways that do not align with fiscal quarters.

```
GHANA COCOA: Is a 60% payment drop in February
real attrition?

  Without seasonal calendar:
    ALERT: RELATIONSHIP AT RISK!

  With AfriFlow seasonal adjustment:
    "60% drop is consistent with expected seasonal
     pattern (50% expected drop). This is likely
     NOT attrition. Off season for cocoa."
```

### Multi-Regulatory Compliance

```
COUNTRY     DATA LAW        FX CONTROLS
ZA          POPIA           Limited
NG          NDPR (strict)   Strict
KE          DPA 2019        Moderate
GH          DPA 2012        Moderate
AO          DPA 2011        Very strict
MZ          Draft law       Strict
CD          None formal     Strict
TZ          PDPA (pending)  Moderate
```

---

## Schema Overview

40 tables across the full medallion architecture.

```
BRONZE (10 tables)
  Raw ingestion, append only, Kafka metadata
  ├── bronze_cib_payments
  ├── bronze_cib_trade_finance
  ├── bronze_cib_cash_management
  ├── bronze_forex_trades
  ├── bronze_forex_rates
  ├── bronze_insurance_policies
  ├── bronze_insurance_claims
  ├── bronze_cell_usage
  ├── bronze_cell_momo
  ├── bronze_cell_sim_activations
  ├── bronze_pbb_accounts
  └── bronze_pbb_payroll

SILVER (7 tables)
  Cleaned, validated, enriched, deduplicated
  ├── silver_cib_payments
  ├── silver_cib_trade_finance
  ├── silver_forex_trades
  ├── silver_insurance_policies
  ├── silver_insurance_claims
  ├── silver_cell_corporate_usage
  └── silver_pbb_corporate_payroll

GOLD: Domain Marts (6 tables)
  Business-ready aggregations per domain
  ├── mart_cib_client_flows
  ├── mart_cib_corridor_analytics
  ├── mart_forex_exposure
  ├── mart_policy_analytics
  ├── mart_cell_intelligence
  └── mart_payroll_analytics

GOLD: Unified (1 table)
  The crown jewel
  └── gold_unified_client_record
      Single row per client across all 5 domains
      100+ columns: identity, metrics, cross-sell,
      risk, shadow health
      Freshness SLA: sub-5-minute

GOLD: Cross-Domain (4 tables)
  Only possible through integration
  ├── gold_cross_sell_matrix
  ├── gold_corridor_intelligence
  ├── gold_group_revenue_360
  └── gold_risk_heatmap

GOLD: Signals (3 tables)
  Detection through outcome tracking
  ├── gold_signal_expansion
  ├── gold_signal_shadow_gap
  └── gold_signal_currency_event

GOVERNANCE (9 tables)
  Audit, lineage, reference data
  ├── entity_resolution
  ├── entity_match_log
  ├── entity_verification_queue
  ├── ref_sim_deflation
  ├── ref_seasonal_calendar
  ├── ref_currency_country
  ├── governance_data_lineage
  ├── governance_access_log
  └── governance_data_quality
```

---

## Repository Structure

```
afriflow/
├── README.md
├── DISCLAIMER.md
├── pyproject.toml
├── requirements.txt
├── conftest.py
│
├── .github/workflows/
│   └── ci.yml
│
├── docs/
│   ├── BUSINESS_CASE.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_CONTRACTS.md
│   ├── ENTITY_RESOLUTION.md
│   ├── COMPLIANCE.md
│   ├── INTEGRATION_PATTERNS.md
│   ├── SEASONAL_ADJUSTMENT.md
│   ├── DATA_SHADOW.md
│   ├── CURRENCY_PROPAGATION.md
│   ├── CLIENT_BRIEFING.md
│   ├── COMPETITIVE_ANALYSIS.md
│   └── FEDERATED_ARCHITECTURE.md
│
├── schemas/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── governance/
│
├── domains/
│   ├── cib/
│   │   ├── simulator/
│   │   ├── ingestion/
│   │   ├── processing/
│   │   └── dbt_models/
│   ├── forex/
│   ├── insurance/
│   ├── cell/
│   └── pbb/
│
├── integration/
│   ├── entity_resolution/
│   │   ├── client_matcher.py
│   │   ├── entity_graph.py
│   │   └── golden_id_generator.py
│   ├── cross_domain_signals/
│   │   ├── expansion_signal.py
│   │   ├── relationship_risk_signal.py
│   │   ├── supply_chain_risk_signal.py
│   │   ├── workforce_signal.py
│   │   ├── hedge_gap_signal.py
│   │   └── total_relationship_value.py
│   ├── unified_golden_record/
│   │   └── dbt_models/
│   └── ml_models/
│
├── data_shadow/
│   ├── __init__.py
│   ├── expectation_rules.py
│   └── shadow_monitor.py
│
├── currency_event/
│   ├── __init__.py
│   └── propagator.py
│
├── seasonal_calendar/
│   ├── __init__.py
│   └── african_seasons.py
│
├── client_briefing/
│   ├── __init__.py
│   └── briefing_generator.py
│
├── governance/
│   ├── popia_classifier.py
│   ├── cross_border_data_rules.py
│   ├── data_lineage_tracker.py
│   └── audit_trail_logger.py
│
├── alerting/
│   ├── rm_alert_engine.py
│   └── salesforce_integration.py
│
├── diagrams/
│   ├── generate_architecture_overview.py
│   ├── generate_signal_matrix.py
│   ├── generate_currency_propagation.py
│   ├── generate_domain_data_flow.py
│   ├── generate_entity_resolution_flow.py
│   └── generate_federated_pods.py
│
├── orchestration/
│   ├── airflow/dags/
│   └── data_contracts/
│
├── tests/
│   ├── unit/
│   │   ├── test_data_shadow.py
│   │   ├── test_currency_propagation.py
│   │   ├── test_seasonal_calendar.py
│   │   └── test_client_briefing.py
│   ├── integration/
│   │   └── test_end_to_end_pipeline.py
│   └── data_quality/
│
└── notebooks/
    ├── 01_domain_exploration.ipynb
    ├── 02_entity_resolution_demo.ipynb
    ├── 03_cross_domain_signals_demo.ipynb
    ├── 04_data_shadow_demo.ipynb
    └── 05_currency_propagation_demo.ipynb
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/Klinsh/afriflow.git
cd afriflow

# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run demonstrations
python -m data_shadow.expectation_rules
python -m currency_event.propagator
python -m seasonal_calendar.african_seasons
python -m client_briefing.briefing_generator

# Generate architecture diagrams
python diagrams/generate_architecture_overview.py
python diagrams/generate_signal_matrix.py
python diagrams/generate_currency_propagation.py
python diagrams/generate_domain_data_flow.py
python diagrams/generate_entity_resolution_flow.py
python diagrams/generate_federated_pods.py
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Streaming | Apache Kafka | Event ingestion with schema registry |
| Stream Processing | Apache Flink | Real-time cross-domain correlation |
| Batch Processing | Apache Spark | Historical enrichment and ML training |
| Storage | Delta Lake | Medallion architecture (Bronze/Silver/Gold) |
| Transformation | dbt | SQL-based Silver to Gold transformations |
| Orchestration | Apache Airflow | DAG scheduling and SLA monitoring |
| Visualisation | Power BI | Phase 1 RM and ExCo dashboards |
| Language | Python 3.10+ | All processing and ML code |
| Testing | pytest | Unit, integration, and data quality tests |
| CI/CD | GitHub Actions | Automated lint, type check, test |

---

## What This Is (and Is Not)

**This is** a reference implementation. Architectural
scaffolding that demonstrates how the pieces connect,
how the data flows, and how intelligence emerges from
cross-domain correlation. It is built to demonstrate
domain knowledge, systems thinking, and engineering
discipline.

**This is not** a production-ready system. Tooling
decisions, infrastructure choices, cloud provider
selections, and deployment patterns would all need
validation by the engineering team with access to
real infrastructure and data.

**The simulated data** demonstrates the pipeline
architecture, not model performance. ML accuracy
metrics from synthetic data are not meaningful. The
value of the architecture is validated when trained
on production data.

---

## Author

**Thabo Kunene**
Senior Data Engineer

Building the data infrastructure for Africa's
financial future.

*Motho ke motho ka batho.*

---

## License

MIT
```
