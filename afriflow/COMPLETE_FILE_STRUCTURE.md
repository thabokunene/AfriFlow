# AfriFlow Complete File and Folder Structure

## Updated with Lekgotla and Corridor Modules

**Last Updated:** 2026-03-19  
**Version:** 2.0

---

## Summary Statistics

### Files by Category

| Category | Files | New Since Lekgotla |
|----------|-------|-------------------|
| Documentation (docs/) | 17 | +4 |
| Schema Definitions (schemas/) | 15 | +4 |
| Domain Code (domains/) | 65 | 0 |
| Integration Code | 18 | 0 |
| Core Modules | 10 | 0 |
| **Lekgotla Module** | **9** | **+9** |
| **Corridor Module** | **5** | **+5** |
| Governance | 9 | 0 |
| Alerting | 8 | +1 |
| Diagram Generators | 15 | +7 |
| Diagram Outputs | 44 | +14 |
| Orchestration | 12 | +3 |
| Infrastructure | 8 | 0 |
| Tests | 18 | +10 |
| Notebooks | 12 | +3 |
| Config / CI | 5 | 0 |
| **Total** | **270** | **+57** |

---

## Complete Module Map

```
CORE PLATFORM
  data_shadow/           Data Shadow Engine
  currency_event/        Currency Propagation
  seasonal_calendar/     African Seasonal Calendar
  client_briefing/       Client Briefing Generator
  corridor/              Corridor Intelligence *NEW*
    corridor_engine.py       Corridor identification
    revenue_attribution.py   Per-corridor revenue tracking
    leakage_detector.py      Competitive leakage detection
    formal_vs_informal.py    CIB vs MoMo flow comparison

DATA INTEGRATION
  integration/
    entity_resolution/   Cross-domain matching
    cross_domain_signals/ 12 signal detectors
    unified_golden_record/ Golden record assembly
    ml_models/           NBA, CLV, anomaly detection

COLLECTIVE INTELLIGENCE
  lekgotla/              *NEW MODULE*
    thread_store.py          Discussion management
    knowledge_card_store.py  Validated approaches
    context_matching.py      Signal-anchored matching
    notification_engine.py   Push to practitioners
    regulatory_channel.py    Compliance intelligence
    contribution_tracker.py  Gamification and scoring
    moderation.py            Content governance
    analytics.py             Platform health metrics

GOVERNANCE
  governance/            POPIA, FAIS, audit, lineage

ALERTING
  alerting/              RM, FX, Insurance, PBB alerts

DOMAINS (5)
  domains/cib/           Corporate Investment Banking
  domains/forex/         Foreign Exchange
  domains/insurance/     Insurance / Liberty
  domains/cell/          Cell Network / MTN
  domains/pbb/           Personal & Business Banking
```

---

## Screen Mockups Built

| # | Screen | Generator File | Output Files |
|---|--------|---------------|-------------|
| 1 | RM Client 360 | generate_rm_dashboard.py | rm_dashboard.png, _small.png |
| 2 | ExCo Strategic | generate_exco_dashboard.py | exco_dashboard.png, _small.png |
| 3 | Portfolio Overview | generate_portfolio_overview.py | portfolio_overview.png, _small.png |
| 4 | Signal Feed | generate_signal_feed.py | signal_feed.png, _small.png |
| 6 | Entity Resolution | generate_entity_resolution_console.py | entity_resolution_console.png, _small.png |
| 7 | Corridor Map | generate_corridor_map.py | corridor_map.png, _small.png |
| 8 | FX Exposure | generate_fx_exposure.py | fx_exposure.png, _small.png |
| 15 | Data Quality | generate_data_quality.py | data_quality.png, _small.png |
| 21 | Lekgotla Feed | generate_lekgotla_feed.py | lekgotla_feed.png, _small.png |
| 22 | Lekgotla Thread | generate_lekgotla_thread.py | lekgotla_thread.png, _small.png |
| 23 | Knowledge Cards | generate_knowledge_card_library.py | knowledge_card_library.png, _small.png |
| 24 | Regulatory Channel | generate_regulatory_channel.py | regulatory_channel.png, _small.png |
| 25 | Lekgotla Analytics | generate_lekgotla_analytics.py | lekgotla_analytics.png, _small.png |

Plus the Signal Flow architecture diagram (generate_signal_flow.py).

**14 screens built of 25 specified (56%)**  
**8 architecture diagrams built**  
**Total: 22 visual assets (44 image files including small versions)**

---

## Database Schema Summary

| Layer | Tables | New |
|-------|--------|-----|
| Bronze | 10 | 0 |
| Silver | 7 | 0 |
| Gold (Domain Marts) | 6 | 0 |
| Gold (Unified) | 1 | 0 |
| Gold (Cross-Domain) | 4 | 0 |
| Gold (Signals) | 3 | 0 |
| Governance | 9 | 0 |
| **Lekgotla** | **12** | **+12** |
| **Total** | **52** | **+12** |

---

## Test Coverage

| Test Category | Files | New |
|--------------|-------|-----|
| Unit Tests | 11 | +5 |
| Integration Tests | 7 | +3 |
| Data Quality Tests | 5 | +2 |
| **Total** | **23** | **+10** |

---

## New Files Created

### Lekgotla Module (9 files)
```
afriflow/lekgotla/
├── __init__.py
├── thread_store.py              # Thread CRUD and search
├── knowledge_card_store.py      # KC graduation and curation
├── context_matching_engine.py   # Signal-anchored thread matching
├── notification_engine.py       # Push relevant threads to RMs
├── regulatory_channel.py        # Compliance post management
├── contribution_tracker.py      # Scoring and leaderboard
├── moderation.py                # Content filtering and review
└── analytics.py                 # Lekgotla health metrics
```

### Corridor Module (5 files)
```
afriflow/corridor/
├── __init__.py
├── corridor_engine.py           # Corridor identification and mapping
├── revenue_attribution.py       # Per-corridor, per-domain revenue
├── leakage_detector.py          # Competitive leakage quantification
└── formal_vs_informal.py        # CIB vs MoMo flow comparison
```

### Schemas - Lekgotla (4 SQL files)
```
schemas/lekgotla/
├── lekgotla_threads.sql         # Thread, reply, upvote tables
├── lekgotla_knowledge_cards.sql # KC, attachment, outcome tables
├── lekgotla_regulatory.sql      # Regulatory alert tables
└── lekgotla_analytics.sql       # Contribution, cohort tables
```

### Documentation (4 new files)
```
docs/
├── LEKGOTLA.md                  # Lekgotla module documentation
├── SCREEN_INVENTORY.md          # Screen mockup inventory
├── STRATEGIC_ANALYSIS.md        # Strategic analysis document
├── CONCEPT_NOTE.md              # Platform concept note
└── DEVELOPMENT_BRIEF.md         # Development brief
```

### Orchestration (3 new files)
```
orchestration/airflow/dags/
├── daily_lekgotla_analytics.py
├── daily_corridor_analytics.py
└── weekly_model_retrain.py

orchestration/data_contracts/
├── lekgotla_contract.yml
└── corridor_contract.yml
```

### Tests (10 new files)
```
tests/unit/
├── test_lekgotla_context_matching.py
├── test_lekgotla_knowledge_cards.py
├── test_lekgotla_moderation.py
├── test_corridor_engine.py
└── test_corridor_leakage.py

tests/integration/
├── test_lekgotla_thread_lifecycle.py
├── test_lekgotla_card_graduation.py
└── test_corridor_revenue_attribution.py

tests/data_quality/
├── test_lekgotla_data_integrity.py
└── test_corridor_data_consistency.py
```

### Notebooks (3 new files)
```
notebooks/
├── 10_lekgotla_context_matching_demo.ipynb
├── 11_corridor_intelligence_demo.ipynb
└── 12_full_platform_walkthrough.ipynb
```

### Alert Templates (1 new file)
```
alerting/alert_templates/
└── lekgotla_notification.json
```

---

## Complete File Tree

```
afriflow/
│
├── README.md
├── DISCLAIMER.md
├── PRODUCTION_PROMPT.md
├── pyproject.toml
├── requirements.txt
├── conftest.py
├── LICENSE
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── docs/
│   ├── BUSINESS_CASE.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_CONTRACTS.md
│   ├── ENTITY_RESOLUTION.md
│   ├── COMPLIANCE.md
│   ├── INTEGRATION_PATTERNS.md
│   ├── SEASONAL_ADJUSTMENT.md
│   ├── DATA_SHADOW.md
│   ├── CURRENCY_PROPAGATION.md
│   ├── CLIENT_BRIEFING.md
│   ├── COMPETITIVE_ANALYSIS.md
│   ├── FEDERATED_ARCHITECTURE.md
│   ├── LEKGOTLA.md                    # NEW
│   ├── SCREEN_INVENTORY.md            # NEW
│   ├── STRATEGIC_ANALYSIS.md          # NEW
│   ├── CONCEPT_NOTE.md                # NEW
│   └── DEVELOPMENT_BRIEF.md           # NEW
│
├── schemas/
│   ├── bronze/
│   │   ├── bronze_cib.sql
│   │   ├── bronze_forex.sql
│   │   ├── bronze_insurance.sql
│   │   ├── bronze_cell.sql
│   │   └── bronze_pbb.sql
│   │
│   ├── silver/
│   │   ├── silver_cib.sql
│   │   ├── silver_forex.sql
│   │   ├── silver_insurance.sql
│   │   ├── silver_cell.sql
│   │   └── silver_pbb.sql
│   │
│   ├── gold/
│   │   ├── gold_domain_marts.sql
│   │   ├── gold_unified_record.sql
│   │   ├── gold_cross_domain.sql
│   │   └── gold_signals.sql
│   │
│   ├── governance/
│   │   ├── entity_resolution.sql
│   │   └── audit_and_lineage.sql
│   │
│   └── lekgotla/                      # NEW
│       ├── lekgotla_threads.sql
│       ├── lekgotla_knowledge_cards.sql
│       ├── lekgotla_regulatory.sql
│       └── lekgotla_analytics.sql
│
├── domains/
│   ├── cib/
│   ├── forex/
│   ├── insurance/
│   ├── cell/
│   └── pbb/
│
├── integration/
│   ├── entity_resolution/
│   ├── cross_domain_signals/
│   ├── unified_golden_record/
│   └── ml_models/
│
├── data_shadow/
├── currency_event/
├── seasonal_calendar/
├── client_briefing/
│
├── lekgotla/                          # NEW MODULE
│   ├── __init__.py
│   ├── thread_store.py
│   ├── knowledge_card_store.py
│   ├── context_matching_engine.py
│   ├── notification_engine.py
│   ├── regulatory_channel.py
│   ├── contribution_tracker.py
│   ├── moderation.py
│   └── analytics.py
│
├── corridor/                          # NEW MODULE
│   ├── __init__.py
│   ├── corridor_engine.py
│   ├── revenue_attribution.py
│   ├── leakage_detector.py
│   └── formal_vs_informal.py
│
├── governance/
├── alerting/
│   └── alert_templates/
│       └── lekgotla_notification.json # NEW
│
├── corridor/
├── dashboards/
├── diagrams/
├── orchestration/
├── infrastructure/
├── tests/
└── notebooks/
```

---

## Next Steps

1. **Complete remaining screen mockups** (11 of 25 remaining)
2. **Implement database schemas** for Lekgotla and Corridor
3. **Create orchestration DAGs** for new modules
4. **Add comprehensive tests** for new functionality
5. **Update documentation** with new module details

---

*Document generated: 2026-03-19*  
*Author: Thabo Kunene*
