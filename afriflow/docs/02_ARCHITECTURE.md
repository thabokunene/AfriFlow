# 02 Architecture

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project. We built it as an independent
> demonstration of concept, domain knowledge, and
> skill.

## Architecture Principles

We designed AfriFlow around six principles that we
believe are essential for a cross divisional integration
platform operating across 20 African countries.

1. **Domain ownership**: Each business division owns
   its data products. We do not centralise ownership.
   We centralise integration.

2. **Federated processing, centralised intelligence**:
   Raw data stays in the country where it originates.
   Only aggregated signals and anonymised metrics flow
   to the central hub for cross domain correlation.

3. **Schema evolution without breakage**: We use Avro
   schemas with a Schema Registry. Every domain can
   evolve its schema independently as long as it
   maintains backward compatibility.

4. **Quality as infrastructure**: Data quality is not
   a testing phase. It is a runtime system with
   ingestion time scoring, circuit breakers, and
   propagated confidence metrics.

5. **Graceful degradation**: When a country feed goes
offline (submarine cable cut, power outage, telco
downtime), the platform continues operating with
reduced confidence rather than failing entirely.

6. **Regulatory compliance by design**: Data residency,
   consent, and access control are architectural
   constraints, not afterthoughts.

## High Level Data Flow

DATA SOURCES (5 DOMAINS)
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ CIB │ FOREX │INSURANCE │ CELL │ PBB │
│Payments │FX Trades │Policies │SIM Data │Accounts │
│Cash Mgmt │Hedging │Claims │MoMo │Payroll │
│Trade Fin │Forwards │Premiums │USSD │Deposits │
│ISO 20022 │FIX/SWIFT │ACORD │CDRs │Core Bank │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
│ │ │ │ │
▼ ▼ ▼ ▼ ▼
┌──────────────────────────────────────────────────────┐
│ APACHE KAFKA │
│ Schema Registry (Avro per domain) │
│ │
│ Topics per domain: │
│ cib.payments.raw forex.trades.raw │
│ insurance.policies.raw insurance.claims.raw │
│ cell.usage.raw cell.momo.raw cell.ussd.raw │
│ pbb.accounts.raw pbb.payroll.raw │
└──────────────────────┬───────────────────────────────┘
│
┌────────┴────────┐
▼ ▼
┌─────────────┐ ┌─────────────┐
│ Apache Flink │ │ Apache Spark│
│ (Real Time) │ │ (Batch) │
│ │ │ │
│ Cross domain │ │ Historical │
│ event │ │ enrichment │
│ correlation │ │ and model │
│ and alerts │ │ training │
└──────┬──────┘ └──────┬──────┘
│ │
▼ ▼
┌─────────────────────────────────┐
│ DELTA LAKE │
│ │
│ BRONZE (Raw per domain) │
│ SILVER (Cleaned per domain) │
│ GOLD (Cross domain joined) │
└──────────────┬──────────────────┘
│
┌─────────┼───────────┐
▼ ▼ ▼
┌──────────┐ ┌────────┐ ┌──────────┐
│ dbt │ │ ML │ │ Serving │
│ Models │ │ Models │ │ API │
│ │ │ │ │ (FastAPI)│
│ Golden │ │ Cross │ │ │
│ Record │ │ Domain │ │ Power BI │
│ Marts │ │ Scores │ │ CRM │
└──────────┘ └────────┘ └──────────┘

text


## Medallion Architecture

We use the Bronze, Silver, Gold medallion pattern with
clear responsibilities at each layer.

### Bronze Layer

Raw data lands here with minimal transformation. We
preserve the original payload, add ingestion metadata
(timestamp, source system, batch ID, quality score),
and store in Delta format for time travel capability.

Each domain has its own Bronze tables. We never mix
domains at the Bronze layer.

bronze_cib_payments
bronze_cib_trade_finance
bronze_forex_trades
bronze_forex_rate_ticks
bronze_insurance_policies
bronze_insurance_claims
bronze_cell_usage
bronze_cell_momo
bronze_cell_sim_activations
bronze_cell_ussd_sessions
bronze_pbb_accounts
bronze_pbb_payroll

text


### Silver Layer

Cleaned, validated, and enriched data per domain. We
apply data quality rules, standardise formats, resolve
within domain duplicates, and add derived fields.

Each Silver table carries a quality score between 0
and 100 that reflects completeness, timeliness, and
consistency of the underlying data.

silver_cib_enriched
silver_forex_enriched
silver_insurance_enriched
silver_cell_enriched
silver_pbb_enriched

text


### Gold Layer

Cross domain integrated tables. This is where entity
resolution links records across domains and where the
unified golden record lives.

gold_unified_client_record
gold_cross_sell_features
gold_risk_signals
gold_corridor_intelligence
gold_group_revenue_360
gold_data_shadow_gaps

text


## Domain Ownership Model

We follow Data Mesh principles. Each domain team owns
its simulator, ingestion, processing, and dbt models.
The integration layer consumes published data products
from each domain via well defined contracts.

domains/
├── shared/ # Shared configuration and
│ # reference data used by all
│ # domains
├── cib/ # Owned by CIB data team
├── forex/ # Owned by Treasury data team
├── insurance/ # Owned by Insurance data team
├── cell/ # Owned by Digital/Telco team
└── pbb/ # Owned by PBB data team

integration/ # Owned by AfriFlow platform team
# Consumes from all domains

text


## Key Technical Decisions

### Why Kafka and Not Direct Database Reads

We chose event streaming over batch database extraction
for three reasons.

First, we need real time cross domain correlation. When
a CIB payment event and a cell SIM activation event
happen within minutes of each other, we must correlate
them in near real time to generate timely expansion
signals.

Second, we need to decouple producers from consumers.
Each domain publishes events without knowing or caring
who consumes them. This allows the integration layer
to evolve independently.

Third, we need an immutable event log for audit and
replay. Kafka's retention policy gives us the ability
to reprocess historical events when we deploy new
signal detection logic.

### Why Delta Lake and Not Pure Parquet

We chose Delta Lake over plain Parquet files for four
reasons: ACID transactions (concurrent writes from
Flink and Spark do not corrupt data), time travel
(we can query the golden record as it existed at any
point in the past for audit purposes), schema
enforcement (we reject records that violate the
expected schema), and efficient upserts (MERGE
operations for slowly changing dimensions like client
metadata).

### Why dbt for the Gold Layer

We chose dbt for the Gold layer transformations because
it provides version controlled SQL, built in
documentation, automated testing, and lineage tracking.
The unified golden record SQL is readable by any
analyst in the group, not just engineers.

### Why a Serving API Layer

We include a FastAPI based serving layer because the
golden record must be consumable by systems beyond
Power BI. The credit engine, the CRM, the pricing
system, and the RM mobile app all need programmatic
access to client intelligence. A dashboard alone is
insufficient for platform adoption.

## Federated Country Pod Architecture

We detail this fully in
[08_FEDERATED_COUNTRY_PODS.md](08_FEDERATED_COUNTRY_PODS.md).
The summary is that raw data stays in country. Only
aggregated, anonymised signals flow to the central
South Africa hub. This satisfies data residency
requirements in Nigeria, Kenya, Ghana, and other
regulated markets.

## Local Development Environment

We provide a Docker Compose configuration that runs
the full stack locally.

```bash
make setup    # Pull images, create networks
make start    # Start Kafka, Flink, Spark, Delta Lake
make simulate # Run all domain simulators
make demo     # Run the cross domain signal demo
make test     # Run full test suite
make stop     # Shut down all services

The local environment includes Kafka (3 brokers with
Schema Registry), Apache Flink (JobManager plus 2
TaskManagers), Apache Spark (standalone mode), a
Delta Lake compatible storage layer, PostgreSQL for
Airflow metadata, Airflow (webserver plus scheduler),
and a FastAPI serving layer.
```

text
