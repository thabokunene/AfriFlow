# 05 Cross Domain Signals

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

This document defines the set of signals derived by
correlating events across the five core domains (CIB,
Forex, Insurance, Cell Network, and PBB). The goal is
to generate actionable insights for relationship
management, risk, and expansion strategies.

## Signal Categories

1. **Expansion Signal** - Detects when a client is
   expanding into a new country or business line.
   Uses cell SIM activations, forex corridors, and
   trade finance volumes.

2. **Attrition Signal** - Identifies clients at risk of
   leaving by observing declining transaction volumes
   and migration of payments to competitor corridors.

3. **Supply Chain Risk Signal** - Uses trade finance,
   insurance claims, and supplier payment patterns to
   surface concentration and counterparty risks.

4. **Workforce Signal** - Leverages cell network SIM
   growth versus payroll deposit patterns to identify
   workforce banking leakage.

5. **Exposure Signal** - Detects unhedged foreign
   currency exposure by comparing cash flows and FX
   hedge coverage.

## Signal Scoring and Confidence

Each signal is scored 0-100 based on:

- Data quality of underlying feeds
- Number of distinct domains contributing
- Recency of contributing events
- Historical validation against known outcomes

Signals are labeled with a confidence tier:

- High (>= 80): actionable without review
- Medium (60-79): requires analyst review
- Low (< 60): exploratory only

## Delivery and Consumption

Signals are published to Kafka topics under
afriﬂow.signals.* and are consumed by:

- CRM systems (for RM workflows)
- Risk systems (for limit allocation)
- Analytics dashboards (for monitoring)
- Export pipelines (for downstream models)

