<!--
@file INTEGRATION_PATTERNS.md
@description Catalog of integration patterns and contracts between AfriFlow modules
@author Thabo Kunene
@created 2026-03-17
-->

# Integration Patterns

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Pattern 1: Change Data Capture (CDC)

For domains with existing relational databases (CIB core banking,
PBB account systems, Insurance policy management), we use Debezium
to capture row-level changes and publish to Kafka.

```
Source DB --> Debezium Connector --> Kafka Topic --> Flink/Spark
```

**Advantages:**
- No changes to source systems required
- Captures inserts, updates, and deletes
- Low latency (seconds from commit to Kafka)

We apply this pattern to CIB, Insurance, and PBB domains.

## Pattern 2: API-Based Ingestion

For domains with REST APIs (Forex trading platform, some MTN
endpoints), we use scheduled API polling or webhook listeners.

```
Source API --> Custom Kafka Producer --> Kafka Topic
```

We apply this pattern to Forex rate feeds and MTN API endpoints where
available.

## Pattern 3: File-Based Ingestion (Batch)

For domains where real-time integration is not available (Insurance
batch extracts, MTN Tier 2/3 country data), we ingest files via
scheduled jobs.

```
SFTP/S3 --> Airflow Sensor --> Spark Ingestion --> Delta Lake Bronze
```

We apply this pattern to Insurance claims batches and MTN country
data where real-time feeds are not yet available.

## Pattern 4: Cross-Domain Event Correlation

The integration layer subscribes to enriched Kafka topics from
multiple domains and correlates events using the golden ID.

```
cib.payments.enriched -----+
forex.trades.enriched -----+--> Flink Cross-Domain Job --> signal.expansion
cell.activations.enriched -+     signal.attrition
insurance.policies.enriched -->  signal.hedge_gap
pbb.payroll.enriched -->         signal.leakage
```

This is the core pattern that enables cross-domain signal detection.

## Pattern 5: Late Arrival Handling

African data sources have variable latency. A payment processed in
DRC might arrive in our Kafka topic 4 hours after execution due to
batch processing at the local core banking system.

We handle late arrivals by:

1. Using event-time processing in Flink (not processing time)
2. Configuring watermarks with generous allowed lateness per country
3. Updating Silver and Gold layer records when late data arrives
4. Tracking late arrival rates per domain per country for SLA monitoring

| Country | Expected Latency | Allowed Lateness |
|---------|-----------------|-----------------|
| South Africa | < 5 minutes | 30 minutes |
| Nigeria | < 30 minutes | 4 hours |
| Kenya | < 15 minutes | 2 hours |
| DRC | < 4 hours | 24 hours |
| Angola | < 2 hours | 12 hours |

## Pattern 6: Circuit Breaker

When a domain feed fails quality checks or stops producing events, we
activate a circuit breaker that:

1. Stops writing new data from that domain to Silver/Gold layers
2. Serves last-known-good data with a staleness timestamp
3. Alerts the domain owner and platform team
4. Automatically reactivates when feed quality recovers

This prevents corrupt or missing data from polluting the golden record.

## Files in This Module

| File | Purpose |
|------|---------|
| `domains/*/ingestion/kafka_producer.py` | Domain-specific Kafka producers |
| `domains/*/processing/flink/late_arrival_handler.py` | Late arrival processing |
| `governance/circuit_breaker.py` | Domain feed circuit breaker |
| `infrastructure/debezium/` | CDC connector configurations |
