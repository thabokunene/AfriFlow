<!--
@file 09_CURRENCY_EVENT_PROPAGATION.md
@description Rules for propagating currency events across domains and signal pipelines
@author Thabo Kunene
@created 2026-03-17
-->
# 09 Currency Event Propagation

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

Currency movements drive many of the cross domain
signals. This document describes how we propagate
currency related events through the platform.

## Event Types

- **Spot trades** (FX): immediate currency exchange
  contracts.
- **Forwards / Hedging**: contracted currency exposure
  in the future.
- **Payments**: cross border settlements and transfers.
- **FX Rates**: market rate feeds used for valuation.

## Propagation Rules

1. **Normalization**: Convert all currency amounts to a
   common reporting currency (e.g., USD) for cross
   domain analysis.
2. **Timestamp alignment**: Use event time and adjust
   for timezone differences.
3. **Correlation**: Link currency trades to payment
   corridors and client exposures.

## Signal Derivation

- **Hedge coverage ratio**: compares outstanding FX
  exposure to hedging position.
- **Currency corridor drift**: detects when payments
  shift to lower cost corridors.
- **Volatility risk**: flags clients with high currency
  rate sensitivity.

