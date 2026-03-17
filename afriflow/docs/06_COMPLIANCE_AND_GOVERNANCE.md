# 06 Compliance and Governance

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

Compliance and governance are first class citizens in
AfriFlow. This document outlines the policies and
operational guardrails that ensure the platform meets
regulatory, privacy, and corporate governance
requirements.

## Data Residency & Residency Controls

- Raw country-specific data resides within the
  originating jurisdiction.
- Aggregated signals leaving a jurisdiction are
  anonymised and aggregated to comply with local data
  protection laws.
- Country pods enforce network controls and
  encryption-at-rest.

## Access Control

- Role based access control (RBAC) is enforced via
  the central identity provider.
- Sensitive attributes are masked for unauthorized
  roles.
- Audit trails are maintained for all data access
  requests.

## Data Lineage and Audit

- We use dbt lineage and Delta Lake transaction logs to
  provide end-to-end traceability.
- Every signal and dashboard includes a “Source
  Trace” that links back to the originating domain
  events.

## Policy Enforcement

- Schema changes require an approved change request.
- Quality thresholds are enforced as hard gates in the
  ingestion pipeline.
- Contract violations trigger automated alerts and
  optional consumption pauses.

