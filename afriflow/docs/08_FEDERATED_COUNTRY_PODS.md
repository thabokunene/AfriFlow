# 08 Federated Country Pods

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

AfriFlow is designed to operate in a federated mode.
Each country pod owns its raw data and initial
processing pipeline, while the centralized platform
orchestrates cross-country intelligence and shared
components.

## Pod Responsibilities

Each country pod is responsible for:

- Ingesting local data sources (banking, telco, trade,
  insurance).
- Applying local compliance rules (data residency,
  consent, privacy).
- Publishing standardized domain events to Kafka.
- Monitoring local infrastructure and quality.

## Centralized Services

The central AfriFlow hub provides:

- Schema registry and contract governance.
- Cross-country correlation and aggregation.
- Global entity resolution and Golden ID service.
- Shared metadata and reference data (e.g., country
  codes, risk categories).

## Data Residency Model

- Raw data remains in the country of origin.
- Only pseudonymised and aggregated signals leave the
  country pod.
- Access to raw data is restricted to local pod
  operators.

## Deployment Patterns

We support two deployment patterns:

1. **Cloud native**: Each country pod runs in a managed
   VPC or subscription with dedicated compute and
   storage.
2. **Hybrid**: Some pods run on-premise, while the
   central hub runs in the cloud.


