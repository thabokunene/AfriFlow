# Currency Events Module

This module provides logic for detecting and classifying currency events (e.g., devaluations, rapid depreciation) and propagating their impact across different business domains.

## Architecture
- **Constants**: Centralized mappings for currencies, countries, and domain identifiers.
- **Classifier**: Analyzes exchange rate movements and parallel market divergence to determine event severity (CRITICAL, HIGH, MEDIUM, LOW).
- **Propagator**: Calculates the impact of classified events on clients across CIB, Forex, Insurance, Cell (Mobile Money), and PBB (Personal & Business Banking) domains.

## Key Classes
- `CurrencyEventClassifier`: High-level API for event classification.
- `CurrencyEventPropagator`: Orchestrates impact propagation across domains.
- `CurrencyEvent`: Dataclass representing a classified FX move.
- `DomainImpact`: Represents the specific impact on a client in a single domain.

## Configuration
Thresholds are loaded from `afriflow/config/currency_thresholds.yml`.

## Remediation Note
In March 2026, this module underwent a major structural remediation to:
1. Fix duplicate/conflicting class definitions.
2. Resolve singular/plural directory naming inconsistencies.
3. Decouple logic from hardcoded constants.
4. Repair broken method structures in the propagator.
5. Standardize imports and enhance testing coverage.
