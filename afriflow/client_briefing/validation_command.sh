#!/bin/bash
# Validation command for client_briefing
.venv/Scripts/python.exe -m pytest afriflow/tests/unit/test_client_briefing.py && echo "VALIDATION SUCCESSFUL" || echo "VALIDATION FAILED"
