# TASK-005 — Correlation Registry and Applicability Engine

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #10
- Branch: `codex/task-005-correlation-registry`
- PR: #11 (Draft)
- Head SHA: `99b2e96`

## Scope

### In Scope

- Correlation identity and versioning (CorrelationKey, SemVer)
- Bibliographic source model with verification status
- Applicability envelope (geometry, phase, flow, numeric bounds)
- Pure-function applicability assessment
- OutOfRangePolicy as sole authority for continuation
- Registry Protocol + InMemoryCorrelationRegistry
- CorrelationUsageRecord with deterministic provenance
- 13 new ErrorCode constants
- Documentation

### Out of Scope

- Actual engineering formulas
- Heat balance, LMTD, ε-NTU
- Database, FastAPI
- Sizing/rating

## Test Count

696 total (457 existing + 239 new)

## Engineering Decisions

- ID format: lowercase dot-separated namespace
- Version rules: SemVer with numeric prerelease precedence
- Default out-of-range: block on absolute, warn on recommended
- Source verification: 4-level enum
- Hash format: SHA-256 of canonical JSON
- Latest-version selection: highest stable, exclude withdrawn/deprecated
- Tolerance fraction: applied to bounds, ≤1.0

## Review-01 Status

- Item 1: mypy ✅
- Item 2: SemVer ✅
- Item 3: Envelope ✅
- Item 4: Policy ✅
- Item 5: Input immutability ✅
- Item 6: Hash contracts ✅
- Item 7: Error consolidation ✅
- Item 8: Usage record ✅
- Item 9: Fixtures ✅
