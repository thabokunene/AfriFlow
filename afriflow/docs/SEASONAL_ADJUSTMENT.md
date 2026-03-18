<!--
@file SEASONAL_ADJUSTMENT.md
@description Seasonal adjustment framework and calendars for reducing false positives in signals
@author Thabo Kunene
@created 2026-03-17
-->
<!-- docs/SEASONAL_ADJUSTMENT.md -->

# AfriFlow Seasonal Adjustment Framework

> DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
> by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
> demonstration of concept, domain knowledge, and technical skill built by
> Thabo Kunene for portfolio and learning purposes only. All data is
> simulated. No real client, transaction, or proprietary information is used.

## Why Seasonal Adjustment Is Critical in African Markets

Western financial platforms treat time as linear or quarterly. We reject that
framing entirely. African corporate cash flows are governed by agricultural
harvest cycles, religious observance windows, commodity extraction seasons,
and government fiscal calendars that do not map to standard Q1 through Q4
reporting.

If we do not account for this, our signal layer will generate catastrophic
false positives. A Ghanaian cocoa exporter whose CIB payments drop 60% in
January is not churning. They are off season. A Nigerian oil services company
whose FX hedging spikes in March is not speculating. They are preparing for
the dry season drilling window.

## Seasonal Calendar Architecture

We maintain a multi-dimensional seasonal calendar that adjusts every cross
domain signal calculation.

### Calendar Dimensions

| Dimension | Examples | Affected Domains |
|-----------|----------|------------------|
| Agricultural harvest | Maize (Apr to Jun, Southern Africa), Cocoa (Oct to Dec, West Africa), Tea (Jan to Mar, East Africa), Sugar (Jun to Nov, Mozambique) | CIB, Forex, Insurance |
| Religious observance | Ramadan (variable, 30 days), Christmas (Dec), Easter (variable) | PBB, Cell, CIB |
| Government fiscal | SA fiscal year (Apr to Mar), Nigeria (Jan to Dec), Kenya (Jul to Jun) | CIB, Forex |
| Commodity pricing | Gold (counter cyclical), Copper (cyclical with China demand), Oil (OPEC driven) | CIB, Forex, Insurance |
| Weather patterns | Rainy season (varies by region), Cyclone season (Nov to Apr, Mozambique Channel) | Insurance, Cell, CIB |
| School calendar | Term dates varies by country, university cycles | PBB, Cell |

### Configuration Format

We store seasonal configurations in YAML to allow non engineering teams
(economists, sector analysts) to update them without code changes.

```yaml
# config/seasonal_calendars/southern_africa_agriculture.yml

region: southern_africa
countries: [ZA, MZ, ZM, ZW, MW, BW]

seasons:
  maize:
    planting:
      start_month: 10
      end_month: 12
      cash_flow_impact: negative
      expected_cib_change_pct: -25
      expected_fx_demand: USD_buy
      notes: "Input purchase period. Fertilizer and seed imports peak."

    growing:
      start_month: 1
      end_month: 3
      cash_flow_impact: neutral
      expected_cib_change_pct: -40
      expected_fx_demand: minimal
      notes: "Low activity period. False attrition signals likely."

    harvest:
      start_month: 4
      end_month: 6
      cash_flow_impact: positive
      expected_cib_change_pct: +60
      expected_fx_demand: USD_sell
      notes: "Export revenue peak. FX conversion and hedging demand high."

    marketing:
      start_month: 7
      end_month: 9
      cash_flow_impact: positive_declining
      expected_cib_change_pct: +20
      expected_fx_demand: mixed
      notes: "Stored crop sales. Gradual decline in activity."

  sugar_mozambique:
    crushing:
      start_month: 6
      end_month: 11
      cash_flow_impact: positive
      expected_cib_change_pct: +80
      expected_fx_demand: USD_sell
      notes: "Sugar export revenue. MZN/USD corridor active."

    off_season:
      start_month: 12
      end_month: 5
      cash_flow_impact: negative
      expected_cib_change_pct: -50
      expected_fx_demand: USD_buy
      notes: "Equipment import and maintenance. Low export revenue."
```

### Integration with Signal Layer

Every signal detector must call the seasonal adjustment service before
calculating drift or anomaly scores.

```python
# Example integration in flow_drift_detector.py

from afriflow.seasonal import SeasonalAdjuster

adjuster = SeasonalAdjuster()

raw_drift = calculate_raw_drift(client_payments, baseline)
seasonal_factor = adjuster.get_adjustment_factor(
    client_id=client.id,
    sector=client.sector,
    country=client.country,
    date=current_date
)

adjusted_drift = raw_drift - seasonal_factor.expected_change_pct

# Only alert if the ADJUSTED drift exceeds threshold
if abs(adjusted_drift) > DRIFT_THRESHOLD:
    generate_alert(client, adjusted_drift)
```

### Sector Classification

We classify each corporate client into one or more seasonal sectors.

| Sector Code | Description | Primary Seasonal Driver |
|-------------|-------------|------------------------|
| AGR_GRAIN | Grain agriculture | Planting and harvest cycles |
| AGR_CASH | Cash crop (cocoa, coffee, tea) | Harvest and export windows |
| AGR_SUGAR | Sugar production | Crushing season |
| MIN_GOLD | Gold mining | Counter cyclical, weather affected |
| MIN_COPPER | Copper mining | Global demand cycles |
| MIN_OIL | Oil and gas | OPEC decisions, drilling seasons |
| RET_FMCG | Fast moving consumer goods | Religious holidays, school terms |
| CON_INFRA | Infrastructure construction | Dry season preference |
| TEL_MOBILE | Mobile telecommunications | Airtime peaks around holidays |
| FIN_BANK | Banking and financial services | Government payment cycles |

### Accuracy Tracking

We track seasonal model accuracy by comparing predicted seasonal adjustment
factors against actual observed patterns. Each quarter we recalibrate.

| Metric | Target | Measurement |
|--------|--------|-------------|
| False positive reduction | 60% fewer false attrition alerts | Compare alert volume before and after seasonal adjustment |
| Seasonal prediction accuracy | Within 15% of actual seasonal swing | Compare predicted vs actual payment volume change |
| Sector coverage | 90% of Top 500 clients classified | Percentage of clients with assigned seasonal profile |

### Files in This Module

| File | Purpose |
|------|---------|
| `integration/seasonal/adjuster.py` | Core seasonal adjustment engine |
| `integration/seasonal/calendar_loader.py` | Loads YAML seasonal configurations |
| `integration/seasonal/sector_classifier.py` | Assigns clients to seasonal sectors |
| `config/seasonal_calendars/*.yml` | Per region seasonal configurations |
| `tests/unit/test_seasonal_adjuster.py` | Unit tests for adjustment logic |
