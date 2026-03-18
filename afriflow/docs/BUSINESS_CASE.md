<!--
@file BUSINESS_CASE.md
@description Business case narrative and quantified opportunity for AfriFlow cross-domain integration
@author Thabo Kunene
@created 2026-03-17
-->
<!-- docs/BUSINESS_CASE.md -->

# AfriFlow Business Case

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Executive Summary

Standard Bank Group generates revenue from five major divisions: CIB,
Forex/Treasury, Insurance (Liberty), Cell Network (MTN JV), and
Personal and Business Banking. Today these divisions operate in data
silos. No single person can see a client's full relationship with the
Group.

AfriFlow creates a Unified Golden Record that integrates data across
all five divisions, enabling cross-domain signals that unlock an
estimated R1.5 to 2.5 billion in annual revenue from cross-sell,
competitive leakage recovery, and proactive advisory services.

## The Revenue Opportunity

### Signal 1: Geographic Expansion Detection

When CIB payments to a new country align with MTN SIM activations in
that country, we detect corporate expansion 4 to 8 weeks before
competitors. First mover advantage on working capital, FX hedging,
and payroll services in the new market.

- Estimated clients affected per year: 30 to 50
- Average revenue per expansion capture: R50 to 200M
- Total opportunity: R1.5B to R10B over 5 years

### Signal 2: Competitive Leakage Recovery

The data shadow model identifies domains where we expect presence but
see absence, indicating the client uses a competitor for that product.
Bundle pricing and proactive engagement recover 20 to 40% of leaked
revenue.

- Estimated annual leakage across top 500 clients: R2 to 5B
- Recovery rate: 20 to 40%
- Total opportunity: R400M to R2B annually

### Signal 3: Unhedged Exposure Advisory

Cross-referencing CIB payment corridors with forex hedging positions
reveals clients with significant unhedged FX exposure. Structured
product offering generates advisory and trading revenue.

- Estimated unhedged exposure in client base: R50B+
- Conversion rate to hedging products: 15 to 25%
- Average fee income per hedging relationship: R2 to 8M
- Total opportunity: R150 to 400M annually

### Signal 4: Payroll Capture

Cell SIM data reveals employee concentrations in markets where PBB
has no corresponding payroll deposits. Each captured employee account
generates approximately R2,500 in annual revenue.

- Estimated uncaptured employees: 200,000+
- Capture rate: 15 to 30%
- Total opportunity: R75 to 150M annually

### Signal 5: Insurance Cross-Sell

Clients with active CIB trade finance but no insurance coverage
represent uninsured risk and an insurance premium opportunity.

- Estimated clients with coverage gaps: 150 to 300
- Average annual premium per policy: R500K to R5M
- Total opportunity: R75 to 450M annually

### Combined Annual Revenue Opportunity

| Estimate | Annual Revenue |
|----------|---------------|
| Conservative | R800M to R1.5B |
| Optimistic | R2B to R4B |

## Investment Required

See `docs/COST_MODEL.md` for detailed phased cost model.

- Steady state annual cost: R130 to 205M
- Steady state ROI: 7x to 19x

## Strategic Value Beyond Revenue

1. **Client retention**: Cross-domain health scoring provides 4 to 6
   week early warning of attrition, enabling proactive intervention.

2. **Regulatory compliance**: Unified view enables holistic KYC/AML
   monitoring across divisions, reducing regulatory risk.

3. **Competitive positioning**: No other African bank has this
   capability. It becomes a hiring and client acquisition advantage.

4. **Data foundation**: The unified golden record becomes the
   foundation for future AI, GenAI, and advanced analytics
   initiatives across the Group.

## Success Metrics

| Metric | Year 1 Target | Year 3 Target |
|--------|--------------|--------------|
| Golden record coverage (top 500 clients) | 60% across 3+ domains | 90% across 4+ domains |
| Signal-to-revenue attribution | R80M tracked | R500M tracked |
| RM daily active usage | 40% of CIB RMs | 80% of all RMs |
| Entity resolution precision | 90% | 97% |
| Mean time to signal delivery | < 60 minutes | < 5 minutes |
| False positive rate on expansion signals | < 25% | < 10% |
