<!--
@file ENTITY_RESOLUTION.md
@description Deep dive into entity resolution strategy, hierarchy, and normalization
@author Thabo Kunene
@created 2026-03-17
-->

# Entity Resolution Deep Dive

## Disclaimer

This document is not a sanctioned Standard Bank Group project. It is a
demonstration of concept, domain knowledge, and data engineering skill
by Thabo Kunene. All data, client names, and financial figures are
simulated. No proprietary information from any institution is used.

## The Hardest Problem in the Platform

Entity resolution across five divisions in 20 African countries is not
a feature. It is the foundation upon which every signal, every alert,
and every revenue claim depends. If entity resolution is wrong,
everything downstream is wrong.

We face challenges that entity resolution systems at JPMorgan or Kakao
Bank never encounter:

1. **Multi-lingual company names**: The same entity appears as
   "Societe Nationale d'Electricite" in CIB, "SNEL" in Insurance,
   "National Electric Company" in an English-language Cell contract,
   and "SNEL SARL" in Forex. Four domains, four names, zero common
   tokens in some pairs.

2. **Holding company fragmentation**: A Nigerian conglomerate with 40+
   subsidiaries where "Dangote Salt Ltd" and "Dangote Industries Plc"
   share a parent but have different registration numbers, different
   addresses, and different tax identifiers.

3. **Cross-border identity**: A Kenyan company registered as
   "Safari Logistics Ltd" in Kenya appears as
   "Safari Logistics (Tanzania) Ltd" in TZ and
   "Safari Logistique SARL" in DRC. Each country registration is
   a separate legal entity but economically they are one client.

4. **Informal naming conventions**: In some markets, company names
   in official registrations differ from trade names used in day to
   day banking. "ABC Mining Corp" officially but "ABC Gold" in CIB
   payment references.

## Matching Hierarchy

We apply matching rules in priority order:

| Priority | Method | Confidence | Coverage |
|----------|--------|-----------|----------|
| 1 | Company registration number (exact) | 100% | 40% of entities |
| 2 | Tax identification number (exact) | 98% | 55% of entities |
| 3 | SWIFT BIC or LEI code (exact) | 99% | 20% of entities (CIB/Forex only) |
| 4 | Normalized name + country (fuzzy) | 70-90% | 85% of entities |
| 5 | Contact email domain (exact) | 85% | 30% of entities |
| 6 | Contact phone prefix (partial) | 60% | 25% of entities |
| 7 | Address similarity (fuzzy) | 50-70% | 40% of entities |

## Multi-Lingual Name Normalization

We extend the standard normalization with language-specific rules:

### French Normalization (CI, SN, CD, CM, CG)

| Original | Normalized |
|----------|-----------|
| SOCIETE | SOC |
| COMPAGNIE | CIE |
| ETABLISSEMENTS | ETS |
| SARL | (removed) |
| SA | (removed) |
| D' | DE |
| L' | LE |

### Portuguese Normalization (MZ, AO)

| Original | Normalized |
|----------|-----------|
| SOCIEDADE | SOC |
| COMPANHIA | CIA |
| LIMITADA / LDA | (removed) |
| COMERCIAL | COM |

### Arabic/Swahili Considerations (TZ, KE, NG northern)

For entities with Arabic or Swahili trade names, we maintain a manual
alias table curated by regional operations teams.

## Human Verification Queue

All matches below 90% confidence route to a verification queue where
a data steward can:

1. Confirm the match (merges the entities under one golden ID)
2. Reject the match (separates the entities permanently)
3. Flag for investigation (holds the match pending additional evidence)

We target processing 50 to 100 verification decisions per day during
the initial 90-day calibration period.

## Accuracy Tracking

We track entity resolution accuracy over time:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Precision (correct matches / total matches) | > 95% | Sampled human review |
| Recall (found matches / actual matches) | > 85% | Cross-reference with RM client lists |
| False merge rate | < 3% | RM feedback on incorrect cross-domain signals |
| False split rate | < 10% | Periodic full-population audit |

## Files in This Module

| File | Purpose |
|------|---------|
| `integration/entity_resolution/client_matcher.py` | Core matching engine |
| `integration/entity_resolution/entity_graph.py` | Relationship graph construction |
| `integration/entity_resolution/golden_id_generator.py` | Deterministic golden ID creation |
| `integration/entity_resolution/name_normalizer.py` | Multi-lingual name normalization |
| `integration/entity_resolution/verification_queue.py` | Human-in-the-loop verification |
| `integration/entity_resolution/accuracy_tracker.py` | Precision/recall monitoring |
| `tests/unit/test_name_normalizer.py` | Tests for multi-lingual normalization |
| `tests/unit/test_client_matcher.py` | Tests for matching logic |
| `tests/integration/test_entity_resolution.py` | End-to-end resolution tests |
