<!--
@file 01_BUSINESS_CASE.md
@description Business case for AfriFlow: problem statement, value thesis, and outcomes
@author Thabo Kunene
@created 2026-03-17
-->
# 01 Business Case

> **Disclaimer**: Please read
> [DISCLAIMER.md](../DISCLAIMER.md). This is not a
> sanctioned project. We built it as an independent
> demonstration of concept, domain knowledge, and
> skill.

## Executive Summary

We present AfriFlow as a cross divisional data
integration platform that unifies five major business
divisions into a single client intelligence layer. The
core thesis is straightforward: when we combine signals
across CIB, Forex, Insurance, Cell Network, and
Personal Banking, we unlock intelligence that no
individual division can produce alone, and that no
competitor without the same multi domain footprint can
replicate.

## The Silo Problem

Large pan African financial services groups typically
operate five or more divisions. Each division maintains
its own data lake, its own client identifiers, its own
data schemas, and its own version of the truth about
any given client.

Division | Client ID Format | Primary System
--- | --- | ---
CIB | CIB-XXXX | Core Banking
Forex/Treasury | FX-NAME-CC | Trading Platform
Insurance | LIB-POL-XXXXX | Policy Admin
Cell Network | MTN-CORP-XXXX | Telco CRM
PBB | PBB-ACC-XXXXXXXX | Retail Banking

text


The same corporate client appears in all five systems
under different identifiers, different name spellings,
and different data models. Nobody in the group sees the
full picture.

## Revenue Opportunity

We estimate the revenue opportunity across five
categories of cross domain signal.

### Signal 1: Geographic Expansion Detection

When CIB payment data shows a client opening new
corridors to a country, and cell network data
simultaneously shows new SIM activations in that
country, we detect geographic expansion 4 to 8 weeks
before any competitor bank becomes aware.

Being first to offer working capital, FX hedging, and
payroll services in the new market wins R50M to R200M
per client in new revenue.

We estimate 20 to 40 detectable expansions per year
across the Top 500 client base.

### Signal 2: Relationship Attrition Warning

When CIB payment volumes decline and forex hedging
volumes shift to competitor bank corridors
simultaneously, we identify relationship attrition
before the client formally moves.

Early intervention recovers R100M+ per relationship.

We estimate 15 to 25 at risk relationships per year
that we can intercept.

### Signal 3: Supply Chain Risk Advisory

When CIB trade finance data shows supplier
concentration risk and insurance claims data shows
rising claims in that supply chain, we identify
systemic supply chain vulnerability.

We can upsell supply chain diversification advisory
and trade credit insurance.

### Signal 4: Workforce Payroll Capture

When cell network data shows a client's employee count
growing (via SIM activations) but PBB payroll deposits
remain flat, we identify that the client's employees
are banking with competitors.

Each employee account is worth approximately R2,500
per year in revenue. A single large corporate payroll
capture of 5,000 employees generates R12.5M annually.

### Signal 5: Unhedged Exposure Advisory

When CIB payment seasonality patterns do not align
with forex forward booking patterns, we identify that
the client is not hedging their seasonal FX exposure
properly.

## Total Estimated Opportunity

We model the total opportunity conservatively at R800M
to R2.4B in annual revenue acceleration across all
five signal categories applied to the Top 500 corporate
clients.

We present the detailed assumptions and sensitivity
analysis in the notebooks directory at
`notebooks/05_revenue_impact_analysis.ipynb`.

## Cost Considerations

We are transparent about the investment required. See
[12_COST_MODEL_AND_PHASING.md](12_COST_MODEL_AND_PHASING.md)
for the full cost model. We estimate R110M to R220M
per year in steady state operating costs, yielding a
strong ROI even under conservative revenue assumptions.

## Strategic Context

This platform creates competitive advantages that are
difficult to replicate. The combination of a 20 country
banking footprint with exclusive telco partnership data
and deep informal economy signals constitutes a moat
that we detail in
[13_RETENTION_AND_MOAT.md](13_RETENTION_AND_MOAT.md).
