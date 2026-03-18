<!--
@file ARCHITECTURE.md
@description Technical architecture overview covering stack, data flows, and governance
@author Thabo Kunene
@created 2026-03-17
-->

# AfriFlow Technical Architecture

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Design Principles

1. **Domain ownership**: Each business division owns its data pipeline.
   We do not build a centralized ETL monolith. Each domain publishes
   data products with contracts.

2. **Federated with central governance**: Country pods process locally,
   aggregated signals flow centrally. Raw PII stays in jurisdiction.

3. **Event-driven first**: Real-time events via Kafka are the primary
   data transport. Batch processing supplements for historical
   enrichment and model training.

4. **Schema evolution without breakage**: Avro schemas with the Schema
   Registry enable backward-compatible evolution. We demonstrate v1 to
   v2 migration in the CIB domain.

5. **Bronze/Silver/Gold medallion**: Raw data lands in Bronze. Cleaned
   and validated data in Silver. Cross-domain integrated data in Gold.

6. **Graceful degradation**: When a data source is unavailable, the
   system continues operating on last-known-good data with explicit
   staleness indicators.

## Component Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Ingestion | Apache Kafka + Schema Registry | Industry standard event streaming with schema governance |
| Real-time processing | Apache Flink | True stream processing with event-time semantics |
| Batch processing | Apache Spark | Large-scale historical processing and model training |
| Storage | Delta Lake (Apache Iceberg compatible) | ACID transactions, time travel, schema enforcement |
| Transformation | dbt | SQL-based transformations with lineage and testing |
| Orchestration | Apache Airflow | DAG-based workflow orchestration |
| ML Feature Store | Feast (planned) | Centralized feature management for ML models |
| Visualization | Power BI (Phase 1), Custom app (Phase 2) | Standard Bank's current BI platform |
| API Layer | FastAPI (planned Phase 2) | Low-latency serving of golden record |
| Governance | Custom (POPIA/FAIS/RICA framework) | African regulatory specificity |

## Data Flow

```
Source Systems --> Kafka (raw topics per domain)
                    |
                    +--> Flink (real-time enrichment, cross-domain signals)
                    |     |
                    |     +--> Kafka (enriched topics, signal topics)
                    |     +--> Alert Engine (RM notifications)
                    |
                    +--> Spark (batch historical processing)
                    |
                    +--> Delta Lake Bronze (raw, partitioned by date)
                    +--> Delta Lake Silver (cleaned, per domain)
                    +--> Delta Lake Gold (cross-domain, golden record)
                          |
                          +--> dbt (transformation and testing)
                          +--> ML Models (feature extraction, scoring)
                          +--> Power BI (visualization)
                          +--> API Layer (programmatic access)
```

## Schema Governance

We use Avro schemas registered in the Confluent Schema Registry with
the following conventions:

- Subject naming: `{domain}.{entity}.{version}` (e.g., `cib.payment.v2`)
- Compatibility mode: BACKWARD (new schemas can read old data)
- Evolution rules: Fields can be added with defaults. Fields cannot be
  removed or have types changed.

## Infrastructure Topology

See `docs/FEDERATED_ARCHITECTURE.md` for the country pod design.

The Johannesburg hub runs the full compute stack. Country pods run
lightweight processing with local storage. Cross-country communication
uses encrypted Kafka Connect with TLS mutual authentication.

## Monitoring and Observability

| Concern | Tool | Metrics |
|---------|------|---------|
| Pipeline health | Airflow + custom dashboards | DAG success rate, task duration |
| Data freshness | Custom freshness monitor | Time since last record per domain per country |
| Data quality | dbt tests + Great Expectations | Row counts, null rates, referential integrity |
| Entity resolution | Custom accuracy tracker | Precision, recall, false merge rate |
| Signal quality | Outcome tracker (planned) | Alert action rate, revenue attribution |
| Infrastructure | Prometheus + Grafana | Kafka lag, Flink checkpoints, Spark job duration |

## Files in This Module

| File | Purpose |
|------|---------|
| `infrastructure/docker-compose.yml` | Local development stack |
| `infrastructure/kubernetes/` | Production deployment manifests |
| `infrastructure/terraform/` | Cloud infrastructure as code |
| `orchestration/airflow/dags/` | All pipeline orchestration |
| `orchestration/data_contracts/` | Domain data contracts |
