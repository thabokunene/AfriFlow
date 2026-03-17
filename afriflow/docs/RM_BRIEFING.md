<!-- docs/RM_BRIEFING.md -->

# RM Pre-Meeting Briefing System

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## Purpose

The RM Pre-Meeting Briefing is a single-page intelligence summary
auto-generated 30 minutes before any calendar event with a client.
It is the most visible product feature of AfriFlow and the artifact
most likely to drive ExCo sponsorship.

When an RM walks into a meeting with a client CFO, they should have
everything they need on one screen. No switching between CIB systems,
Forex platforms, Insurance portals, and MTN dashboards. One briefing.
Two minutes to read. Full cross-domain intelligence.

## Briefing Structure

```
============================================================
CLIENT BRIEFING: [Client Name] | Meeting: [Time]

RELATIONSHIP SNAPSHOT
  Total Value: R[X]B across [N] domains
  Health: [Status Indicator] [Summary]
  Domains Active: CIB [Y/N] | Forex [Y/N] | Insurance [Y/N]
                  Cell [Y/N] | PBB [Y/N]
  Cross-Sell Priority: [CRITICAL / HIGH / STANDARD]

CHANGES SINCE LAST MEETING ([Date])
  - [Domain]: [Change description]
  - [Domain]: [Change description]
  - [Domain]: [Change description]

TOP OPPORTUNITIES (Ranked by estimated revenue)
  1. [Opportunity] -- est. R[X]M
  2. [Opportunity] -- est. R[X]M
  3. [Opportunity] -- est. R[X]M

RISK ALERTS
  - [Risk description and recommended action]
  - [Risk description and recommended action]

COMPETITIVE INTELLIGENCE
  - [Leakage detection or competitor activity signal]

TALKING POINTS
  - "[Suggested conversation opener based on signals]"
  - "[Suggested question based on detected patterns]"

SEASONAL CONTEXT
  [Industry] [Country]: Currently in [peak/off] season
  Expected cash flow pattern: [Description]
```

## Data Sources Per Section

| Briefing Section | Data Sources | Refresh Frequency |
|-----------------|-------------|-------------------|
| Relationship Snapshot | Unified Golden Record | Sub-5-minute |
| Changes Since Last | Delta between current and snapshot at last meeting date | On-demand |
| Top Opportunities | Cross-domain signal library + data shadow model | Hourly |
| Risk Alerts | Currency event propagator + flow drift detector | Real-time for CRITICAL tier |
| Competitive Intelligence | Data shadow model leakage estimator | Daily |
| Talking Points | Template engine with signal-specific language | On-demand |
| Seasonal Context | Seasonal calendar | Static, quarterly refresh |

## Calendar Integration

We integrate with the RM's calendar system (Outlook/Exchange) to:

1. Detect upcoming meetings with known clients (matching meeting
   attendee email domains to golden record contact information)
2. Trigger briefing generation 30 minutes before meeting start
3. Deliver briefing via email, push notification, and in-platform
   cached view (for offline access)

## Delivery Channels

| Channel | Use Case | Technical Approach |
|---------|----------|-------------------|
| Email | Default delivery | HTML email via Exchange API |
| Push notification | Mobile RM | Firebase Cloud Messaging |
| Power BI embedded | Desktop RM | Parameterized report page |
| Cached PDF | Offline / low connectivity | Pre-generated, synced to device |
| Salesforce card | CRM integration | Lightning Web Component |

## Feedback Collection

After each meeting, we prompt the RM with three quick questions:

1. Was the briefing accurate? (Yes / Partially / No)
2. Did you discuss any of the recommended opportunities? (Yes / No)
3. Did the client confirm any detected signals? (Expansion / Attrition
   risk / Other / None)

This feedback feeds back into:
- Entity resolution accuracy tracking
- Signal confidence calibration
- Seasonal factor adjustment
- Next-best-action model retraining

## Files in This Module

| File | Purpose |
|------|---------|
| `integration/client_briefing/briefing_generator.py` | Core briefing generation engine |
| `integration/client_briefing/calendar_integration.py` | Outlook/Exchange calendar detection |
| `integration/client_briefing/briefing_templates/` | HTML and text templates |
| `integration/client_briefing/feedback_collector.py` | Post-meeting feedback capture |
| `tests/unit/test_client_briefing.py` | Tests for briefing content accuracy |
