# TASK-005 — Correlation Registry and Applicability Engine

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #10
- Branch: `codex/task-005-correlation-registry`
- PR: #11 (Draft)
- Head SHA: `408293e`

## Scope

### In Scope

- Correlation identity and versioning (CorrelationKey, semver)
- Bibliographic source model with verification status
- Applicability envelope (geometry, phase, flow, numeric bounds)
- Pure-function applicability assessment
- Out-of-range policy (conservative defaults)
- Registry Protocol + InMemoryCorrelationRegistry
- CorrelationUsageRecord with provenance integration
- 13 new ErrorCode constants
- Documentation (CORRELATION_REGISTRY.md)

### Out of Scope

- Actual engineering formulas
- Heat balance, LMTD, ε-NTU
- Database, FastAPI
- Sizing/rating

## Test Count

568 total (457 existing + 111 new)

## Engineering Decisions

- ID format: lowercase dot-separated namespace
- Version rules: semantic versioning (major.minor.patch)
- Default out-of-range: block on absolute, warn on recommended
- Source verification: 4-level enum
- Hash format: SHA-256 of canonical JSON
- Latest-version selection: highest stable, exclude withdrawn/deprecated by default
