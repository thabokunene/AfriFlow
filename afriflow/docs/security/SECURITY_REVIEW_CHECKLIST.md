# Security Review Checklist for Processor Modules

Use this checklist when reviewing any Processor that implements `BaseProcessor`.

## Interface & Structure
- [ ] Class is named `Processor` and directly subclasses `BaseProcessor`
- [ ] Implements `configure`, `validate`, and `process_sync`
- [ ] Does not rely on external adapter patterns for core logic

## Access Controls
- [ ] `validate` enforces role-based access using `access_role`
- [ ] Allowed roles vary by environment (dev/test vs staging/prod)
- [ ] Unauthorized roles trigger `PermissionError`

## Input Validation
- [ ] Record type is enforced (dict required)
- [ ] `source` is required and must be a non-empty string
- [ ] Payload size is capped (e.g., 100k characters) with clear error on exceedance

## Error Handling & Logging
- [ ] `process_sync` wraps logic in try/except
- [ ] Errors are logged with appropriate severity and structured context
- [ ] Exceptions are re-raised after logging for upstream handling
- [ ] No secrets or sensitive values are logged

## Configuration
- [ ] `configure` respects environment from `AppConfig`
- [ ] No hard-coded secrets or credentials

## Testing
- [ ] Unit tests verify:
  - Accepts authorized role with valid source
  - Rejects missing `source`
  - Rejects unauthorized role
- [ ] Tests are part of the suite and run under CI

## Coding Standards
- [ ] Module follows established imports, logging usage, and lint style
- [ ] No overly long lines for added code paths
- [ ] Docstrings or references to the global hardening doc exist where appropriate

## Sign-off
- Reviewer: ____________________
- Date: ________________________
