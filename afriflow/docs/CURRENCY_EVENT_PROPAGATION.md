<!-- docs/CURRENCY_EVENT_PROPAGATION.md -->

# AfriFlow Currency Event Propagation Framework

> DISCLAIMER: This project is not sanctioned by, affiliated with, or endorsed
> by Standard Bank Group, MTN Group, or any of their subsidiaries. It is a
> demonstration of concept, domain knowledge, and technical skill built by
> Thabo Kunene for portfolio and learning purposes only. All data is
> simulated. No real client, transaction, or proprietary information is used.

## The Problem Western Architectures Miss

JPMorgan treats FX risk as a standalone concern handled by the Treasury desk.
Kakao Bank barely deals with FX at all (South Korea has a single stable
currency). Neither architecture models the reality that in Africa, a major
currency event is a systemic shock that cascades across every banking domain
simultaneously.

When the Nigerian naira devalued by approximately 40% in June 2023, the impact
was not limited to the FX book. It hit:

- **CIB:** Every client importing into Nigeria saw immediate cost inflation.
  Trade finance facilities became inadequate overnight.
- **Forex:** Forward contracts booked at pre devaluation rates created massive
  mark to market gains for the bank but triggered margin calls and potential
  client defaults.
- **Insurance:** Asset values denominated in NGN required revaluation. Coverage
  became inadequate for assets priced in hard currency.
- **Cell:** MTN Nigeria revenue in ZAR terms dropped by the same percentage,
  affecting the partnership economics.
- **PBB:** Nigerian employees of South African corporates saw real purchasing
  power collapse. Salary advance demand spiked.

We model this cascade explicitly.

## Event Classification

| Event Type | Trigger Condition | Severity | Example |
|------------|-------------------|----------|---------|
| DEVALUATION | Official rate moves more than 10% in 24 hours | CRITICAL | NGN June 2023 |
| RAPID_DEPRECIATION | Market rate moves more than 5% in 7 days | HIGH | ZMW copper price drop |
| CAPITAL_CONTROL_CHANGE | New restrictions on FX access announced | HIGH | Nigeria BDC closure |
| PARALLEL_DIVERGENCE | Parallel market rate diverges more than 20% from official | MEDIUM | Angola pre 2018 |
| CENTRAL_BANK_INTERVENTION | Central bank spends more than 5% of reserves | MEDIUM | Kenya 2024 |
| BAND_WIDENING | Managed float band widens | LOW | Various |

## Propagation Logic

When we detect a currency event, we propagate impact across all five domains
using domain specific impact calculators.

### CIB Impact

- Recalculate facility adequacy for every client with exposure to the
  affected currency.
- Flag trade finance instruments (letters of credit, guarantees) that may
  need amendment.
- Identify clients whose supplier payments in the affected currency will
  increase, creating working capital pressure.

### Forex Impact

- Revalue all open forward and swap positions in the affected currency pair.
- Calculate mark to market impact per client.
- Identify clients with maturing forwards that may face delivery risk.
- Flag clients with no hedging in place for the affected currency.

### Insurance Impact

- Revalue insured assets denominated in the affected currency.
- Identify policies where coverage is now inadequate due to currency
  adjusted replacement cost.
- Flag group life policies where benefit amounts (often denominated in local
  currency) have lost real value.

### Cell Impact

- Recalculate MTN JV revenue impact in ZAR terms.
- Identify clients whose MoMo transaction volumes may spike (flight to
  mobile money during currency instability).
- Flag potential airtime pricing impacts.

### PBB Impact

- Identify employees of corporate clients who are paid in the affected
  currency.
- Predict salary advance demand spike.
- Flag payroll accounts where real value has dropped below product
  eligibility thresholds.

## Integration Points

The Currency Event Propagator sits in the Flink streaming layer and
triggers immediately when rate feed data crosses threshold boundaries.

```
Rate Feed (forex/simulator/rate_feed_generator.py)
|
v
Flink: rate_anomaly_detector.py
|
v (threshold crossed)
Flink: currency_event_propagator.py
|
+---> CIB impact calculator
+---> Forex impact calculator
+---> Insurance impact calculator
+---> Cell impact calculator
+---> PBB impact calculator
|
v
Unified Currency Event Impact Report
|
+---> RM alerts (all affected clients)
+---> ExCo dashboard (portfolio level impact)
+---> Risk committee report (concentration analysis)
```

## Files in This Module

| File | Purpose |
|------|---------|
| `integration/currency_events/propagator.py` | Core event propagation engine |
| `integration/currency_events/cib_impact.py` | CIB domain impact calculator |
| `integration/currency_events/forex_impact.py` | Forex domain impact calculator |
| `integration/currency_events/insurance_impact.py` | Insurance domain impact calculator |
| `integration/currency_events/cell_impact.py` | Cell domain impact calculator |
| `integration/currency_events/pbb_impact.py` | PBB domain impact calculator |
| `integration/currency_events/event_classifier.py` | Classifies FX moves by severity |
| `config/currency_thresholds.yml` | Configurable thresholds per currency |
| `tests/unit/test_currency_propagator.py` | Unit tests for propagation logic |
| `tests/integration/test_currency_cascade.py` | End to end cascade tests |
