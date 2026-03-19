# PHASE 1: ANALYZE - Lekgotla & Corridor

## Module: lekgotla/

### Dependencies on existing modules:
- **afriflow.logging_config**: For senior-grade structured logging.
- **afriflow.exceptions**: Will define `LekgotlaError`, `ThreadNotFoundError`, etc.
- **afriflow.config.settings**: For point values, PII patterns, and matching weights.
- **integration.cross_domain_signals**: Threads anchor to `ExpansionSignal`, `ShadowGapSignal`, and `CurrencyEvent`.
- **integration.entity_resolution**: Critical for `Moderator` PII scanning and `ContextMatchingEngine` linkage.
- **currency_events.propagator**: Triggers `RegulatoryAlert` and associated threads.

### Data flow:
- **Input**: Gold layer signals, user posts/replies, regulatory circulars, Client Golden Records.
- **Output**: Threads, Posts, Knowledge Cards, Notifications, Contribution scores, Platform Analytics.

### Integration points:
- **client_briefing.briefing_generator**: Will pull "Relevant Wisdom" via `ContextMatchingEngine`.
- **alerting**: Notifications hook into existing CRM/Email channels.
- **schemas.gold**: Lekgotla tables link conceptually to gold signal records.

### African market specifics:
- **The "Lekgotla" Concept**: Digitalizing collective intelligence for African banking.
- **Regulatory Interpretation**: Handling the high velocity of CBN/SARB circulars.
- **Expertise Mapping**: Connecting regional RMs with HQ specialists on specific corridors.

### Risks:
- **PII Leakage**: High risk in free-text posts; requires aggressive automated moderation.
- **Engagement**: Platform value depends on practitioner participation.
- **Stale Knowledge**: Cards must have a validation TTL to prevent outdated advice.

---

## Module: corridor/

### Dependencies on existing modules:
- **domains.***: Consumes volume/revenue from CIB, Forex, Insurance, PBB, and Cell.
- **integration.sim_deflation**: Uses `ref_sim_deflation` for workforce estimation.
- **integration.entity_resolution**: Aggregates client flows across 5 divisions.
- **afriflow.config.settings**: For leakage and divergence thresholds.

### Data flow:
- **Input**: Raw payment records, domain revenue logs, MoMo (informal) flow data.
- **Output**: Corridor health stats, unified Revenue Attribution, Leakage Signals, Flow Divergence alerts.

### Integration points:
- **lekgotla.context_matching_engine**: Corridors are a primary matching dimension for threads.
- **dashboards.group_exco**: Primary data source for corridor analytics.
- **alerting**: Leakage signals trigger RM notifications.

### African market specifics:
- **The "MoMo Moat"**: Understanding formal vs informal flow shifts (unique African moat).
- **Corridor Growth**: Tracking Abidjan-Lagos and other intra-African trade routes.
- **SIM Deflation**: Nigeria/Kenya specific headcount estimation logic.

### Risks:
- **Data Fragmentation**: Handling varying data quality across 20 country pods.
- **Attribution Logic**: Ensuring origin vs destination revenue splits are fair.

---

# PHASE 2: ULTRATHINK DECISIONS

## Decision 1: Thread Anchoring Strategy
- **Question**: How do we link threads to signals without hardcoding table names?
- **Decision**: Use a `signal_type` (Enum) and `signal_id` (str) pattern.
- **Rationale**: Signals are stored in multiple gold tables (Expansion, Shadow, Currency). A generic anchoring pattern allows the `ContextMatchingEngine` to query the correct source based on the type.

## Decision 2: PII Moderation Rigor
- **Question**: How aggressive should the PII scanner be?
- **Decision**: Block any post containing a client name found in the `golden_record` or any string matching a 10-digit account number pattern.
- **Rationale**: Banking compliance is non-negotiable. It's better to hold a post for review (false positive) than to leak client data in a shared forum.

## Decision 3: Seasonal Knowledge Boosting
- **Question**: Should seasonality affect Knowledge Card ranking?
- **Decision**: Yes. The `ContextMatchingEngine` will boost cards with tags matching the current `african_seasons.py` state for the relevant country.
- **Rationale**: A card about "Cocoa Harvest Hedging" is 10x more valuable in October than in April.

## Decision 4: Informal Flow Interpretation
- **Question**: How do we handle "noisy" MoMo data in Tier 3 countries?
- **Decision**: Apply a `confidence_penalty` to `FlowComparison` results where the MoMo data source is marked as Tier 3.
- **Rationale**: We must avoid panicking ExCo with "Capital Flight" alerts based on stale or low-quality informal data.

## Decision 5: Revenue Attribution Logic
- **Question**: How to split corridor revenue between Source and Destination?
- **Decision**: 50/50 split for fee income; 100% to Origin for FX spread.
- **Rationale**: Aligns with Standard Bank's transfer pricing guidelines for intra-African payments.

## Decision 6: Contribution Fairness
- **Question**: How to reward Compliance/Risk practitioners who don't generate revenue?
- **Decision**: `REGULATORY_ALERT` posts earn 30 points (3x a normal post).
- **Rationale**: Prevents gamification from skewing purely toward RMs and sales, ensuring the "Wisdom" layer remains balanced.

---

# PHASE 3: IMPLEMENTATION PLAN

## Phase 3a: Data Models & Schemas
- **Task 1**: `lekgotla/` dataclasses (Thread, Post, KnowledgeCard)
- **Task 2**: `corridor/` dataclasses (Corridor, Revenue, Leakage)
- **Task 3**: `schemas/lekgotla/` SQL (4 files)
- **Acceptance**: All models importable; `pytest` verifies schema-dataclass mapping.

## Phase 3b: Core Engines
- **Task 4**: `lekgotla/thread_store.py` (In-memory + Indexing)
- **Task 5**: `lekgotla/context_matching_engine.py` (The Differentiator)
- **Task 6**: `corridor/corridor_engine.py` (Payment Mapping)
- **Task 7**: `corridor/leakage_detector.py` (The Revenue Case)
- **Acceptance**: Context engine scores correctly; Leakage detected on test payments.

## Phase 3c: Wisdom & Governance
- **Task 8**: `lekgotla/knowledge_card_store.py` (Graduation logic)
- **Task 9**: `lekgotla/moderation.py` (PII Scanner)
- **Task 10**: `lekgotla/regulatory_channel.py` (Compliance value)
- **Acceptance**: Cards graduate based on win-rate; PII blocked in tests.

## Phase 3d: Delivery & Analytics
- **Task 11**: `lekgotla/notification_engine.py` (Push logic)
- **Task 12**: `lekgotla/contribution_tracker.py` (Gamification)
- **Task 13**: `corridor/formal_vs_informal.py` (The Moat)
- **Task 14**: `lekgotla/analytics.py` (Platform Health)
- **Acceptance**: Leaderboard updates; Divergence alerts triggered.

## Phase 3e: Verification
- **Task 15**: Full test suite (10 files)
- **Acceptance**: 95%+ coverage; No circular dependencies.
