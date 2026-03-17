# 07 Data Quality Framework

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

Our data quality framework is built as an executable
component of the pipeline. Quality is measured at
ingestion and re-evaluated at each transformation.

## Quality Dimensions

1. **Completeness** – fraction of expected fields
   present.
2. **Timeliness** – freshness compared to SLA.
3. **Accuracy** – conformance to expected formats and
   reference data.
4. **Consistency** – agreement across related
   datasets.
5. **Confidence** – an aggregate score used for
   downstream gating.

## Quality Gates

- **Ingestion Gate**: blocks records that do not meet
  minimum completeness or schema validity.
- **Transformation Gate**: prevents propagation of
  low-quality records into Silver and Gold layers.
- **Signal Gate**: suppresses signals when quality is
  below configured thresholds.

## Monitoring and Alerting

We emit quality metrics to Prometheus and display
behaviour in Grafana dashboards. Alerts are raised on
:

- sustained quality drops
- repeated schema changes
- downstream consumption failures

