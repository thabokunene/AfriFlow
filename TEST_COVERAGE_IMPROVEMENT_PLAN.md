# Test Coverage Improvement Plan

## Executive Summary

This document outlines a comprehensive plan to improve test coverage for critical modules in the AfriFlow data platform, focusing on:
1. **Kafka Producer Modules** (CIB, Forex) - Currently at 0-40% coverage
2. **Flink Processing Modules** (Flow Drift Detector, Expansion Detector) - Partial coverage with gaps

**Target:** Achieve minimum 80% coverage for each module.

---

## Module Analysis

### 1. CIB Kafka Producer (`domains/cib/ingestion/kafka_producer.py`)

**Current Coverage:** ~40%
**Lines of Code:** 220
**Existing Tests:** 9 tests in `tests/unit/cib/ingestion/test_cib_kafka_producer.py`

#### Identified Gaps:

| Gap Category | Missing Tests | Priority |
|-------------|---------------|----------|
| Validation - Country Codes | Invalid country code formats (lowercase, numbers, special chars) | High |
| Validation - Currency | Invalid currency codes, edge cases | High |
| Validation - Amount | Zero amount, negative amount, non-numeric | High |
| Validation - Status | Invalid status values | Medium |
| Validation - Purpose Code | Invalid purpose codes | Medium |
| Validation - Corridor | Invalid corridor formats | Medium |
| Batch Processing | Empty batch, all failures, mixed validation errors | High |
| Error Handling | Connection errors, timeout errors | High |
| Logging | Verify log messages on errors | Low |
| Close Method | Close without producer, close with producer | Medium |

#### New Tests Required: 25

---

### 2. Forex Kafka Producer (`domains/forex/ingestion/kafka_producer.py`)

**Current Coverage:** ~60%
**Lines of Code:** 380
**Existing Tests:** 28 tests in `tests/unit/forex/ingestion/test_forex_kafka_producer.py`

#### Identified Gaps:

| Gap Category | Missing Tests | Priority |
|-------------|---------------|----------|
| Trade Validation - ID Format | Invalid trade_id formats | Medium |
| Rate Tick - Edge Cases | Equal bid/mid/ask rates | High |
| Hedge Validation - Dates | Invalid date formats | Medium |
| Batch - Unknown Type | Already covered | - |
| Close Method | Already covered | - |
| Error Propagation | Exception chaining verification | Medium |
| Logging Verification | Log message assertions | Low |

#### New Tests Required: 12

---

### 3. Flow Drift Detector (`domains/cib/processing/flink/flow_drift_detector.py`)

**Current Coverage:** ~75%
**Lines of Code:** 180
**Existing Tests:** 8 tests in `tests/unit/cib/processing/flink/test_flow_drift_detector.py`

#### Identified Gaps:

| Gap Category | Missing Tests | Priority |
|-------------|---------------|----------|
| Edge Case - Zero Previous Avg | Division by zero handling | High |
| Edge Case - Empty Data | get_statistics with no data | High |
| Edge Case - Single Observation | Statistics with 1 data point | Medium |
| Threshold Boundary | Exactly at threshold (no alert) | High |
| Data Truncation | Verify old data is pruned | Medium |
| Multiple Clients | Isolation between clients | Medium |
| Multiple Corridors | Isolation between corridors | Medium |

#### New Tests Required: 10

---

### 4. Expansion Detector (`domains/cell/processing/flink/expansion_detector.py`)

**Current Coverage:** ~65%
**Lines of Code:** 160
**Existing Tests:** 5 tests in `tests/unit/cell/processing/flink/test_expansion_detector.py`

#### Identified Gaps:

| Gap Category | Missing Tests | Priority |
|-------------|---------------|----------|
| Edge Case - No Activations | Empty client data | High |
| Edge Case - Exact Threshold | Exactly at threshold | High |
| Time Window Boundary | Activations at window edge | High |
| Multiple Signals | Multiple countries expansion | High |
| Confidence Calculation | Verify formula | Medium |
| Historical Cutoff | Verify cutoff logic | Medium |
| Processor Class | RBAC validation tests | High |

#### New Tests Required: 15

---

## Implementation Plan

### Phase 1: Kafka Producer Tests (Week 1)

1. **CIB Kafka Producer** - Add 25 tests
   - Validation edge cases (10 tests)
   - Batch processing scenarios (8 tests)
   - Error handling (5 tests)
   - Lifecycle methods (2 tests)

2. **Forex Kafka Producer** - Add 12 tests
   - Additional validation (6 tests)
   - Error propagation (4 tests)
   - Edge cases (2 tests)

### Phase 2: Flink Processing Tests (Week 2)

1. **Flow Drift Detector** - Add 10 tests
   - Edge cases (5 tests)
   - Multi-client/corridor (3 tests)
   - Threshold boundaries (2 tests)

2. **Expansion Detector** - Add 15 tests
   - Edge cases (6 tests)
   - Time window tests (4 tests)
   - Processor class tests (5 tests)

### Phase 3: Integration & CI/CD (Week 3)

1. Update CI/CD pipeline for coverage reporting
2. Add coverage thresholds to pytest configuration
3. Create coverage dashboard integration

---

## Test Infrastructure Requirements

### Dependencies

```txt
# requirements-dev.txt ( additions)
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-asyncio>=0.21.0
freezegun>=1.2.0  # For time-based tests
```

### Pytest Configuration

```ini
# pyproject.toml additions
[tool.pytest.ini_options]
addopts = """
    -v
    --tb=short
    --cov=afriflow
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=80
"""
```

---

## Test Design Principles

### 1. Deterministic Tests

```python
# Use fixed seeds for random operations
import random
random.seed(42)

# Use freezegun for time-based tests
from freezegun import freeze_time
@freeze_time("2024-01-15 10:00:00")
def test_time_dependent():
    pass
```

### 2. Fast Execution

```python
# Avoid real I/O, use mocks
from unittest.mock import Mock, patch

@patch('kafka.KafkaProducer')
def test_fast(mock_producer):
    pass
```

### 3. Clear Assertions

```python
# Use descriptive assertion messages
assert result == expected, f"Expected {expected}, got {result}"

# Use pytest's parametrize for multiple scenarios
@pytest.mark.parametrize("input,expected", [...])
def test_multiple_scenarios(input, expected):
    pass
```

---

## Coverage Measurement

### Commands

```bash
# Run tests with coverage
pytest --cov=afriflow.domains.cib.ingestion.kafka_producer \
       --cov-report=term-missing \
       afriflow/tests/unit/cib/ingestion/

# Generate HTML report
pytest --cov=afriflow --cov-report=html

# Check specific module coverage
coverage report -m --include="*/cib/ingestion/kafka_producer.py"
```

### Coverage Thresholds

| Module | Current | Target | Deadline |
|--------|---------|--------|----------|
| CIB Kafka Producer | 40% | 80% | Week 1 |
| Forex Kafka Producer | 60% | 80% | Week 1 |
| Flow Drift Detector | 75% | 85% | Week 2 |
| Expansion Detector | 65% | 85% | Week 2 |

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-coverage.yml
name: Test Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run tests with coverage
        run: |
          pytest --cov=afriflow \
                 --cov-report=xml \
                 --cov-fail-under=80
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Documentation Requirements

### Test Documentation Template

```markdown
## Test: test_validation_invalid_country_code

**Purpose:** Verify that invalid country codes are rejected

**Input:** Payment with sender_country="123"

**Expected:** ValidationError raised

**Coverage:** Line 85-88 in kafka_producer.py

**Related:** test_validation_valid_country_code
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tests too slow | Use mocks, avoid I/O |
| Flaky tests | Fixed seeds, freeze time |
| False positives | Clear assertions, multiple checks |
| Coverage inflation | Focus on meaningful tests |

---

## Success Criteria

1. ✅ All modules achieve 80%+ line coverage
2. ✅ All modules achieve 70%+ branch coverage
3. ✅ All tests pass in CI/CD pipeline
4. ✅ Test execution time < 5 minutes for full suite
5. ✅ No flaky tests (100% pass rate over 10 runs)

---

## Appendix: Test File Structure

```
afriflow/tests/
├── unit/
│   ├── cib/
│   │   └── ingestion/
│   │       ├── test_cib_kafka_producer.py (existing)
│   │       └── test_cib_kafka_producer_validation.py (new)
│   └── forex/
│       └── ingestion/
│           ├── test_forex_kafka_producer.py (existing)
│           └── test_forex_kafka_producer_edge_cases.py (new)
└── integration/
    └── kafka/
        └── test_kafka_producers_integration.py (new)
```

---

*Document Version: 1.0*
*Last Updated: 2026-03-17*
*Author: AfriFlow Data Engineering Team*
