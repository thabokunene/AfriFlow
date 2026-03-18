#!/bin/bash
# =============================================================================
# @file validation_command.sh
# @description Runs the unit-test suite for the client_briefing module and
#              prints a clear PASS/FAIL outcome to stdout.  Intended to be
#              executed from the project root after any change to the
#              client_briefing package to confirm nothing has been broken.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================

# -----------------------------------------------------------------------------
# Interpreter: .venv/Scripts/python.exe
#   Uses the project's local virtual-environment Python rather than any
#   system-wide interpreter so that the correct package versions are always
#   resolved.  On Linux/macOS this path would be .venv/bin/python instead.
#
# -m pytest: run pytest as a module entry-point (avoids PATH issues)
#
# Target: afriflow/tests/unit/test_client_briefing.py
#   Scopes the test run to client_briefing unit tests only; avoids spinning up
#   the full suite, which keeps the validation loop fast during development.
# -----------------------------------------------------------------------------
.venv/Scripts/python.exe -m pytest afriflow/tests/unit/test_client_briefing.py \
  && echo "VALIDATION SUCCESSFUL" \   # Exit code 0 from pytest → all tests passed
  || echo "VALIDATION FAILED"         # Non-zero exit code from pytest → at least one test failed
