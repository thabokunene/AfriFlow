# Data Shadow Module

This module models the expected data footprint for every client across all domains (CIB, Forex, Insurance, Cell, PBB) and generates signals (shadows) from the gaps between expectation and reality.

## Architecture
- **Expectation Rules**: `ExpectationRuleEngine` (in `expectation_rules.py`) applies cross-domain inference rules to determine expected domain presence.
- **Calculator**: `ShadowCalculator` (in `shadow_calculator.py`) compares expected presence against actual presence to identify shadows.
- **Monitor**: `ShadowMonitor` (in `shadow_monitor.py`) tracks changes in shadows over time (opened/closed gaps) and generates alerts.

## Key Classes
- `DomainShadow`: Represents a detected gap (e.g., competitive leakage, coverage gap).
- `ShadowCategory`: Enum for types of shadows (e.g., `COMPETITIVE_LEAKAGE`, `PAYROLL_CAPTURE_OPPORTUNITY`).

## Usage
The `ShadowMonitor` is the primary entry point for tracking client health over time. It uses the `ShadowCalculator` to perform point-in-time analysis.

## Remediation Note
In March 2026, this module underwent a structural remediation to remove duplicate classes (`DataShadowCalculator`), fix incorrect imports, and consolidate logic into a unified rule engine.
