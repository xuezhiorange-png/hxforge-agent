# Correlation Registry and Applicability Engine

## Overview

The correlation registry provides a structured, auditable way to manage
engineering correlations (heat transfer, friction factor, etc.) with full
provenance, applicability envelopes, and version management.

## Why Anonymous Formulas Are Banned

Every correlation must have a stable **correlation ID** and **version**.
This ensures:

1. **Traceability**: Every calculation result can be traced back to the
   exact correlation version used.
2. **Reproducibility**: Two runs using the same correlation ID + version
   must produce identical results.
3. **Audit**: Regulatory and quality assurance processes require knowing
   exactly which correlation was applied.
4. **Deprecation**: Old correlations can be deprecated and replaced
   without breaking existing revision chains.

## ID Rules

- Correlation IDs must match `^[a-z0-9][a-z0-9._-]*$`
- IDs are case-sensitive but conventionally lowercase
- Dot-separated hierarchical IDs are recommended (e.g. `fixture.htc.tube`)
- IDs must not be empty

## Version Rules

- Versions must follow semver: `major.minor.patch` (at minimum)
- Optional prerelease suffix: `1.0.0-alpha`, `1.0.0-beta.1`
- Stable versions sort before prerelease of the same number
- Version `1.0.0` < `1.0.0-alpha` is NOT true; stable precedes prerelease

## Source Verification

Every correlation must have a `BibliographicSource` with:

- `source_id`: unique identifier for the source
- `title`, `publication`, `year`: bibliographic metadata
- `verification_status`: one of `unverified`, `secondary_source`,
  `primary_source_checked`, `independently_verified`
- Optional `doi`, `isbn`, `standard_id`, `equation_or_clause`

The `year` must be in range 1900-2099. DOI format is validated if provided.

## Applicability Envelope

The `ApplicabilityEnvelope` defines when a correlation can be used:

- **geometry_types**: Set of compatible geometries
- **phase_regimes**: Set of compatible phase regimes
- **flow_regimes**: Set of compatible flow regimes
- **bounds**: Numeric bounds on dimensionless/dimensional variables
- **required_inputs**: Variables that must be supplied
- **excluded_conditions**: Free-text exclusions

### Numeric Bounds

Each `NumericBound` specifies:

- `minimum` / `maximum`: absolute limits (inclusive or exclusive)
- `recommended_minimum` / `recommended_maximum`: recommended range
  (must be within absolute limits)
- `tolerance_fraction`: acceptable deviation

Validators enforce:
- `minimum < maximum` when both are set
- Recommended bounds within absolute bounds
- No NaN or Inf values
- `tolerance_fraction >= 0`

## Out-of-Range Policy

The `OutOfRangePolicy` defines what happens when limits are violated:

| Violation Type | Default Action |
|---|---|
| Absolute range exceeded | `block` |
| Recommended range exceeded | `warn` |
| Missing required input | `block` |
| Incompatible geometry | `block` |
| Incompatible phase | `block` |

Actions: `block`, `warn`, `allow_explicit_opt_in`, `fallback_required`.

## Definition Hash

The `definition_hash` is a SHA-256 content hash of the correlation
definition (excluding the hash itself). It ensures:

1. No silent modification of registered correlations
2. Tamper-evident storage
3. Quick comparison between definitions

Computed as: `sha256(canonical_json(definition.model_dump() - definition_hash))`

## Usage Record

The `CorrelationUsageRecord` captures:

- Which correlation was used (key + version)
- The definition hash at time of use
- The assessment hash from applicability check
- All input values
- Whether extrapolation was used
- Uncertainty specification

Each record can be converted to a `ProvenanceNode` for inclusion in
the provenance graph.

## Provenance Integration

`CorrelationUsageRecord.to_provenance_node()` creates a
`ProvenanceNode` with:

- `node_type = CORRELATION`
- `label = "{correlation_id} v{version}"`
- `metadata`: correlation ID, version, source ID, applicability status,
  extrapolation flag, uncertainty basis
- `payload_hash`: SHA-256 of the serialised usage record

## Real Correlation Approval Process

To add a real (non-fixture) correlation:

1. **Source verification**: Obtain primary source and verify against
   independent secondary source.
2. **Envelope definition**: Define applicability bounds based on the
   original paper's validity range.
3. **Uncertainty estimation**: Document uncertainty from original paper
   or independent validation.
4. **Implementation**: Implement the correlation as a pure function.
5. **Validation**: Test against known reference values.
6. **Review**: Engineering review by a qualified engineer.
7. **Registration**: Register in the correlation registry with full
   metadata.

## API

### InMemoryCorrelationRegistry

```python
registry = InMemoryCorrelationRegistry()

# Register
registry.register(correlation_definition)

# Get specific version
defn = registry.get(CorrelationKey(correlation_id="fixture.htc.tube", version="1.0.0"))

# Get latest stable version
latest = registry.get_latest("fixture.htc.tube")

# List all versions
versions = registry.list_versions("fixture.htc.tube")

# Search with filters
results = registry.search(
    purpose=CorrelationPurpose.heat_transfer_coefficient,
    geometry=GeometryType.circular_tube,
    implementation_status=CorrelationImplementationStatus.validated,
)

# Assess applicability
assessment = registry.assess(key, inputs)
if assessment.allows_evaluation:
    # Proceed with calculation
    pass
```

### Applicability Assessment

```python
from hexagent.correlations.applicability import assess_applicability

assessment = assess_applicability(definition, inputs)
# Returns ApplicabilityAssessment with:
# - status: overall applicability status
# - variable_results: per-variable assessments
# - warnings: non-blocking messages
# - blockers: blocking messages
# - allows_evaluation: whether calculation can proceed
# - assessment_hash: deterministic content hash
```
