# CIB Import Convention

This project standardizes all CIB module imports to **absolute imports from the project root package `afriflow`**.

## Rationale
Absolute imports:
- Avoid dependence on the current working directory or PYTHONPATH quirks.
- Improve readability and tooling (navigation, refactors, static analysis).
- Provide a single, unambiguous import style across modules and tests.

## Convention
- Domain code: `from afriflow.domains.<domain>.<...> import ...`
- Shared code: `from afriflow.domains.shared.<...> import ...`
- Project utilities: `from afriflow.<module> import ...`

Examples:
- `from afriflow.domains.shared.interfaces import BaseProcessor`
- `from afriflow.domains.cib.processing.flink.flow_drift_detector import FlowDriftDetector`
- `from afriflow.logging_config import get_logger`

## Migration Guidelines
1. Replace:
   - `from domains...` → `from afriflow.domains...`
   - `import domains...` → `import afriflow.domains...`
2. Update tests and utilities that reference CIB modules to the new paths.
3. Verify via:
   - `python afriflow/scripts/check_imports.py --check`
   - `python -m pytest -q`

## Tooling & Enforcement
- CI step runs `afriflow/scripts/check_imports.py --check` for CIB modules.
- Optional: install pre-commit and run `pre-commit install` to enforce locally.

## Notes
- Backward compatibility: Only CIB code and CIB tests were migrated; other domains may continue using legacy paths until migrated.
- External integrations should import via `afriflow.domains...` for stability.
