# Architecture Decision Record

## ADR-001: Deterministic kernel and LLM orchestration

**Decision:** All engineering values are computed by deterministic, versioned tools. The LLM is limited to intent parsing, tool orchestration, result explanation, comparison narrative and report composition.

**Consequences:**
- Every value is traceable.
- Calculations remain reproducible without an LLM.
- The API and CLI can be used independently.
- New models can be validated before exposing them to the Agent.

## ADR-002: Modular monolith first

**Decision:** Use one Python monorepo with strict module boundaries. Run CFD/FEA workers separately.

**Reason:** The domain model and calculation contracts will change rapidly in early phases. Microservices would slow refactoring and complicate validation.

## ADR-003: SI units internally

**Decision:** Normalize all inputs to SI at the boundary. Unit-bearing values are validated by a dedicated module.

## ADR-004: Correlation registry

**Decision:** No anonymous equation is permitted in exchanger services. Correlations are selected through a registry containing source, version, validity envelope and uncertainty.

## ADR-005: Licensed standards are external rule packs

**Decision:** Copyrighted standards, proprietary catalogs and commercial property databases are not committed to the repository. The application loads licensed rule packs at runtime.
