# TASK-005 — Correlation Registry and Applicability Engine

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #10
- Branch: `codex/task-005-correlation-registry`
- PR: #Draft

## Scope

### In Scope

- Correlation identity and versioning (CorrelationKey, CorrelationId, CorrelationVersion)
- Bibliographic source model (BibliographicSource, SourceVerificationStatus)
- Classification enums (CorrelationPurpose, GeometryType, PhaseRegime, FlowRegime, ApplicabilityVariable)
- Applicability envelope (NumericBound, ApplicabilityEnvelope)
- Applicability assessment (CorrelationApplicabilityInput, ApplicabilityAssessment, VariableAssessment)
- Out-of-range policy (OutOfRangePolicy, OutOfRangeAction)
- CorrelationDefinition frozen model
- CorrelationRegistry Protocol
- InMemoryCorrelationRegistry implementation
- CorrelationUsageRecord
- Provenance integration (CORRELATION node type)
- New ErrorCode constants for correlation domain
- Documentation (CORRELATION_REGISTRY.md)

### Out of Scope

- Actual engineering formulas (Gnielinski, Dittus-Boelter, Sieder-Tate, etc.)
- Heat balance, LMTD, ε-NTU
- Pressure-drop calculations
- Sizing, rating, screening
- Database / PostgreSQL
- FastAPI
- Copyrighted standard text

## Acceptance Criteria

- [ ] All models are frozen/immutable
- [ ] CorrelationKey JSON round-trip stable
- [ ] Semantic version sorting deterministic
- [ ] Applicability assessment is pure function
- [ ] Out-of-range default is conservative (block)
- [ ] Registry enforces deep copy / immutability
- [ ] Usage record JSON round-trip stable
- [ ] Provenance node conversion works
- [ ] Existing 457 tests unbroken
- [ ] Ruff, mypy, pytest, pip-audit clean

## Test Count

457 existing + new TBD

## Engineering Decisions

- ID format: lowercase dot-separated namespace (e.g. `heat_transfer.circular_tube.single_phase.example`)
- Version rules: semantic versioning (major.minor.patch)
- Default out-of-range: block on absolute, warn on recommended
- Source verification: 4-level enum
- Hash format: SHA-256 of canonical JSON
