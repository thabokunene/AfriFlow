<!--
@file 10_DATA_SHADOW_MODEL.md
@description Data shadow model definition and audit/compliance footprint mapping approach
@author Thabo Kunene
@created 2026-03-17
-->
# 10 Data Shadow Model

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

The Data Shadow Model tracks where data exists in the
platform that is not part of the canonical
golden-data model. It enables us to identify
shadow copies, duplication, and uncharted data flows.

## Purpose

- Identify data stores that contain production data
  but are not governed.
- Surface redundant pipelines and transformation
  logic.
- Support audit and compliance by showing the full
  data footprint.

## Components

- **Shadow catalog**: an inventory of datasets and
  their owners.
- **Lineage maps**: graphs showing how shadow data
  flows between systems.
- **Risk scoring**: assigns risk levels based on
  sensitivity and accessibility.

## Governance

We require that any new dataset be registered in the
shadow catalog and assessed by the governance board.
Unregistered datasets are flagged for review.

