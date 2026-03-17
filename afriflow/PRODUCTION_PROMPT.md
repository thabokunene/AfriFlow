# AfriFlow Production Hardening Prompt

## Context

You are a senior data engineering architect working on
AfriFlow, a cross-divisional data integration platform
for Standard Bank Group. The platform unifies CIB,
Forex, Insurance, Cell Network (MTN), and Personal
Banking data into a single client intelligence layer
across 20 African countries.

The codebase exists as a functional prototype. Your
task is to bring it to production grade (98%+ readiness
score) across all dimensions: code quality, test
coverage, error handling, observability, documentation,
deployment, and operational resilience.

## Current State

The repository contains the following implemented
modules (all Python unless noted):

### Core Modules (implemented, need hardening)
- `data_shadow/expectation_rules.py` - Shadow gap detection rules engine
- `data_shadow/shadow_monitor.py` - State tracking for shadow gaps over time
- `currency_event/propagator.py` - FX event cascade across 5 domains
- `seasonal_calendar/african_seasons.py` - Agricultural cycle false alarm filter
- `client_briefing/briefing_generator.py` - Pre-meeting RM intelligence briefs
- `integration/entity_resolution/client_matcher.py` - Cross-domain entity matching
- `integration/cross_domain_signals/expansion_signal.py` - Geographic expansion detector

### Test Suite (implemented, need expansion)
- `tests/unit/test_data_shadow.py`
- `tests/unit/test_currency_propagation.py`
- `tests/unit/test_seasonal_calendar.py`
- `tests/unit/test_client_briefing.py`
- `tests/integration/test_end_to_end_pipeline.py`

### Schema Definitions (implemented, SQL)
- `schemas/bronze/` - 5 files, 10 tables (raw ingestion)
- `schemas/silver/` - 5 files, 7 tables (cleaned enriched)
- `schemas/gold/` - 4 files, 14 tables (marts, unified, signals)
- `schemas/governance/` - 2 files, 9 tables (audit, lineage, reference)

### Diagrams (implemented, matplotlib generators)
- `diagrams/generate_architecture_overview.py`
- `diagrams/generate_signal_matrix.py`
- `diagrams/generate_currency_propagation.py`
- `diagrams/generate_domain_data_flow.py`
- `diagrams/generate_entity_resolution_flow.py`
- `diagrams/generate_federated_pods.py`

### Configuration
- `pyproject.toml`
- `requirements.txt`
- `conftest.py`
- `.github/workflows/ci.yml`

### Domain Simulators (referenced, need implementation)
- `domains/cib/simulator/payment_generator.py`
- `domains/forex/simulator/fx_trade_generator.py`
- `domains/insurance/simulator/policy_generator.py`
- `domains/cell/simulator/sim_activation_generator.py`
- `domains/cell/simulator/momo_generator.py`
- `domains/pbb/simulator/payroll_generator.py`

## Objective

Bring every module to production grade defined as:

| Dimension | Target | Measurement |
|---|---|---|
| Test coverage | 95%+ line coverage | pytest-cov report |
| Type safety | 100% public API typed | mypy --strict passes |
| Error handling | Zero unhandled exceptions | No bare except, all paths covered |
| Input validation | All public methods validate | Pydantic or manual with clear errors |
| Logging | Structured JSON logging | Every decision point logged |
| Documentation | Every public class and method | Sphinx compatible docstrings |
| Configuration | Zero hardcoded values | All thresholds in config files |
| Observability | Metrics on every operation | Timing, counts, error rates |
| Idempotency | All operations safely re-runnable | No duplicate side effects |
| Resilience | Graceful degradation | Missing data handled, not crashed |

## Execution Protocol

Follow this exact sequence. Do not skip steps.
Report progress after each phase.

### Phase 1: AUDIT (do not write code yet)

Read every file listed above in its entirety. Then
produce a structured audit report with this format:

```
AUDIT REPORT: [module_name]
  Current state: [summary of what exists]
  Production gaps:
    1. [specific gap with file and line reference]
    2. [specific gap]
    ...
  Risk level: [CRITICAL / HIGH / MEDIUM / LOW]
  Estimated effort: [hours]
  Dependencies: [what must be done first]
```

Cover every module. Rank by risk level descending.
Identify circular dependencies. Flag any architectural
issues that would block production deployment.

### Phase 2: PLAN (do not write code yet)

Based on the audit, produce a sequenced work plan:

```
WORK PLAN
  Phase 2a: Foundation (must be done first)
    Task 1: [specific task]
      Files affected: [list]
      Acceptance criteria: [measurable]
    Task 2: ...

  Phase 2b: Core hardening
    Task N: ...

  Phase 2c: Integration and testing
    Task N: ...

  Phase 2d: Operational readiness
    Task N: ...
```

Each task must have:
- Specific files to create or modify
- Measurable acceptance criteria
- Estimated line count
- Dependencies on prior tasks

### Phase 3: EXECUTE (now write code)

Execute the work plan in sequence. For each task:

1. State which task you are executing
2. Show the complete file (no truncation, no ellipsis,
   no "rest remains the same")
3. After each file, state what changed and why
4. Run the test suite mentally and confirm it passes
5. State the current production readiness score

### Phase 4: VERIFY

After all tasks complete:

1. List every file in the repository with line count
2. Show the complete test execution command and
   expected output
3. Calculate final production readiness score with
   evidence per dimension
4. List any remaining gaps with severity

## Technical Constraints

Follow these rules in all code:

### Python Standards
- Python 3.10+ (use match/case where appropriate)
- No emdashes anywhere in code or comments
- All prose uses "we" voice (not "I" or "you")
- Line length: 60 characters maximum
- Formatter: ruff
- Type checker: mypy --strict
- Every file starts with the disclaimer block

### Disclaimer Block (required in every .py file)
```python
"""
[Module description]

DISCLAIMER: This project is not a sanctioned
initiative of Standard Bank Group, MTN, or any
affiliated entity. It is a demonstration of
concept, domain knowledge, and data engineering
skill by Thabo Kunene.
"""
```

### Error Handling
- No bare `except:` clauses
- All exceptions must be specific types
- Every except block must log the error
- Use custom exception hierarchy:
  ```
  AfriFlowError
    EntityResolutionError
    SignalDetectionError
    CurrencyPropagationError
    SeasonalCalendarError
    BriefingGenerationError
    DataShadowError
    DataQualityError
    ConfigurationError
  ```

### Configuration
- All thresholds, weights, and magic numbers must
  live in YAML or TOML config files
- Config loaded once at startup, passed via dependency
  injection (not global state)
- Example: SIM deflation factors currently hardcoded
  in CellExpectsPBBRule must move to config

### Logging
- Use Python `logging` module
- Structured format: JSON lines
- Log levels used correctly:
  - DEBUG: detailed diagnostic
  - INFO: normal operations
  - WARNING: unexpected but handled
  - ERROR: operation failed
  - CRITICAL: system cannot continue

### Testing
- Every public method has at least one test
- Every error path has a test
- Use pytest fixtures for shared setup
- Use parametrize for multi-case testing
- Property based testing with hypothesis for
  entity resolution name normalisation
- Integration tests use the full pipeline
- No mocking of internal modules (only external I/O)

### Dependencies to Install
```bash
pip install \
  pytest pytest-cov pytest-mock hypothesis \
  pydantic pyyaml \
  mypy types-PyYAML \
  ruff \
  structlog \
  numpy pandas
```

## Quality Gates

Do not proceed to the next phase until the current
phase meets its gate:

| Phase | Gate |
|---|---|
| Audit | Every module assessed, no module missed |
| Plan | Every audit gap has a corresponding task |
| Execute | pytest passes, mypy passes, ruff passes |
| Verify | 95%+ coverage, zero type errors, zero lint errors |

## Progress Reporting

After each phase, report:

```
PROGRESS REPORT
  Phase: [current phase]
  Status: [COMPLETE / IN PROGRESS / BLOCKED]
  Tasks completed: [N of M]
  Test results: [pass/fail count]
  Coverage: [percentage]
  Type errors: [count]
  Lint errors: [count]
  Production readiness: [percentage]
  Blockers: [list or "none"]
  Next action: [specific next step]
```

## Priority Order

If context length becomes a constraint, prioritise
in this order:

1. `data_shadow/` (most complex, most value)
2. `currency_event/` (systemic risk, high visibility)
3. `seasonal_calendar/` (false alarm prevention)
4. `integration/entity_resolution/` (foundation)
5. `integration/cross_domain_signals/` (revenue signals)
6. `client_briefing/` (RM facing output)
7. Domain simulators (demonstration data)
8. Diagram generators (visual assets)

## What Success Looks Like

When complete, the following commands must all pass
with zero errors:

```bash
# Install
pip install -e ".[dev]"

# Lint
ruff check . --fix
ruff format .

# Type check
mypy --strict \
  data_shadow/ \
  currency_event/ \
  seasonal_calendar/ \
  client_briefing/ \
  integration/

# Test with coverage
pytest \
  --cov=data_shadow \
  --cov=currency_event \
  --cov=seasonal_calendar \
  --cov=client_briefing \
  --cov=integration \
  --cov-report=term-missing \
  --cov-fail-under=95 \
  -v

# Generate diagrams
python diagrams/generate_architecture_overview.py
python diagrams/generate_signal_matrix.py
python diagrams/generate_currency_propagation.py
python diagrams/generate_domain_data_flow.py
python diagrams/generate_entity_resolution_flow.py
python diagrams/generate_federated_pods.py

# Run demonstrations
python -m data_shadow.expectation_rules
python -m currency_event.propagator
python -m seasonal_calendar.african_seasons
python -m client_briefing.briefing_generator
```

Begin with Phase 1: AUDIT. Read everything. Report
what you find. Do not write code until the audit
and plan are approved.

---

## Why This Prompt Works

This prompt solves seven specific failure modes:

**Problem 1: "Read the context" is vague.**
The improved version lists every file that exists, its
location, and its current state. There is no ambiguity
about what the AI must read.

**Problem 2: "Production grade 98%" is undefined.**
The improved version defines a ten-dimension scoring
rubric with measurable targets for each dimension
(95%+ coverage, zero type errors, etc.).

**Problem 3: "Audit, plan, and execute" has no structure.**
The improved version defines four phases with explicit
quality gates between them. The AI cannot proceed to
code writing until the audit report structure is
complete with specific file and line references.

**Problem 4: "Install the dependencies" is ambiguous.**
The improved version provides the exact `pip install`
command and lists which tools serve which purpose
(ruff for linting, mypy for types, hypothesis for
property testing).

**Problem 5: No priority order means the AI might
start with diagrams.**
The improved version ranks all eight module groups
by priority so that if context runs out, the most
valuable work is done first.

**Problem 6: No definition of "done" means no way
to verify.**
The improved version ends with exact shell commands
that must all pass with zero errors. Success is
binary and verifiable.

**Problem 7: No constraints means inconsistent output.**
The improved version specifies line length, exception
hierarchy, logging format, configuration approach,
testing patterns, and the disclaimer block so every
file follows the same standard.

---

*Document Version: 1.0*
*Created: 2026-03-17*
*Author: Thabo Kunene*
