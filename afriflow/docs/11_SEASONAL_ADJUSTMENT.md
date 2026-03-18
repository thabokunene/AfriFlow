<!--
@file 11_SEASONAL_ADJUSTMENT.md
@description Seasonal adjustment methodology to avoid false signals from cyclical behavior
@author Thabo Kunene
@created 2026-03-17
-->
# 11 Seasonal Adjustment

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project.

Seasonal patterns are important in financial data
(holidays, fiscal year ends, harvest seasons). We apply
seasonal adjustment to ensure signals are not driven by
expected cyclical behavior.

## Approach

- Detect recurring patterns in time series data.
- Apply seasonal decomposition (e.g., STL) to separate
  trend, seasonality, and residuals.
- Use residuals for anomaly detection and signal
  generation.

## Use Cases

- Adjusting payroll and transaction volumes during
  holiday seasons.
- Normalising call volume in mobile networks across
  weekends and public holidays.

