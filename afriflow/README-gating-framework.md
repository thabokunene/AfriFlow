# Gating Framework Extension Guide

## Overview
- Declarative configuration defines filters and gates per subtree under `domains/`.
- Changed-files detection feeds the framework to apply gates only when relevant subtrees are modified.
- Conditional branch/function gates activate via environment variables or feature flags.
- Logs include subtree, filter evaluation, condition result, and durations.

## Files
- Config: `afriflow/config/coverage_gates.json`
- Framework: `afriflow/scripts/gating_framework.py`
- Reports: written under `afriflow/coverage/`
- CI: `.github/workflows/ci-tests.yml` integrates changed-files detection and framework step.

## Add a New Subtree
1. Edit `afriflow/config/coverage_gates.json`:
   - Add a `subtrees` entry with:
     - `name`: unique subtree name
     - `path`: e.g. `domains/equities/ingestion`
     - `filters`: `file_patterns`, `file_types`, `naming_regex`, `date_range` (optional)
     - `conditions`: `branch_gate_env`, `function_gate_env` (optional)
     - `gates`: `line_min`, `branch_min`, `func_min`, artifacts, optional `include_file_pattern`
2. Ensure CI changed-files detection covers PRs and writes `afriflow/coverage/changed_files.json`.
3. The framework will detect changes and apply gates automatically per config.

## Filters
- `file_patterns`: glob patterns matched against changed files
- `file_types`: list of extensions, e.g. `["py"]`
- `naming_regex`: regex matched against basenames
- `date_range`: (optional) future enhancement; leave null to skip

## Conditions
- Set env vars for conditional gates:
  - `branch_gate_env`: e.g. `ENABLE_FOREX_BRANCH_GATE`
  - `function_gate_env`: e.g. `ENABLE_FOREX_FUNC_GATE`
- Accepted true values: `1`, `true`, `yes`, `on` (case-insensitive)

## Gates
- Coverage gate thresholds:
  - `line_min`: required minimum line coverage
  - `branch_min`: required minimum branch coverage (0 if disabled)
  - `func_min`: required minimum function coverage (0 if disabled)
- Artifacts:
  - `write_md`, `write_json` for per-subtree reports
  - Optional `include_file_pattern` to narrow files

## Logging
- Written to `afriflow/coverage/gating_log.json`:
  - `subtree`, `path`, `affected_count`, `filters_match`, `conditions`
  - durations for filter and gate steps
  - `gate_status`: `passed`, `failed`, `skipped`

## Examples
- Add `domains/commodities/ingestion` with line gate only:
```json
{
  "name": "commodities_ingestion",
  "path": "domains/commodities/ingestion",
  "filters": { "file_patterns": ["**/*.py"], "file_types": ["py"], "naming_regex": null },
  "conditions": {},
  "gates": { "line_min": 90, "branch_min": 0, "func_min": 0 }
}
```

## Validation
- Run targeted tests:
  - `pytest -q tests/unit/scripts/test_gating_framework.py`
  - `pytest -q tests/integration/gating/test_gating_pipeline.py`

## Notes
- Keep report artifacts stable for dashboards.
- Use feature flags to toggle branch/function gates per subtree.
