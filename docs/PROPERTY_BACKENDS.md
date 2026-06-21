# HXForge Property Backend Policy

## v0.1 Reference-State Policy

**Policy:** `DEF` (CoolProp default — IIR for refrigerants, NIST-JANAF for others)

The reference-state policy is fixed at provider construction time. The
provider recomputes a per-fluid enthalpy-based configuration fingerprint
before every query. If the fingerprint changes (e.g. external code calls
`set_reference_state()`), the provider:

1. clears the cache;
2. raises `property_configuration_changed`.

## Validation Tiers (DEC-016)

| Level | Meaning | v0.1 status |
|---|---|---|
| `BENCHMARK_VALIDATED` | Validated against independently sourced reference data | Not available — all current fixtures are same-backend regressions |
| `SUPPORTED_TIER_1` | Approved name allowlist; same-backend regression tests pass | **Active** for Water, Air, R134a, R717 |
| `UNVALIDATED` | Not in the approved set | Requires `allow_unvalidated_fluids=True` |

### Validation Matrix

Backend regression fixtures are recorded in `VALIDATION_MATRIX` with:

- `dataset_id` — unique identifier (e.g. `HXFORGE-V01-WATER-TP-REGRESSION-001`)
- `validation_basis` — `backend_regression` for fixture matches
- `source` — identifies the CoolProp version and backend
- `revision` — dataset version date

These fixtures are NOT independent benchmarks. They verify that the
same CoolProp HEOS backend produces consistent results across runs.

### Validation Basis (Provenance)

Every property query records a `validation_basis` in its provenance:

| Basis | Meaning | When |
|---|---|---|
| `backend_regression` | Matches a fixture in VALIDATION_MATRIX | Fluid + query type + inputs match |
| `support_allowlist` | Fluid is in the approved Tier-1 allowlist | Non-fixture Tier-1 state |
| `unvalidated_opt_in` | Fluid allowed via `allow_unvalidated_fluids` | Non-Tier-1 fluid with flag |
| `None` | No validation claim | Fluid not in any approved set |

The `validation_level` field distinguishes `SUPPORTED_TIER_1` from
`BENCHMARK_VALIDATED` (not available in v0.1) and `UNVALIDATED`.

## Mixture Capability (v0.1)

**Policy:** Mixture identifiers are representable, but all mixture
property calculations return `property_unsupported_query`.

- `FluidIdentifier` can represent mixtures with mole-fraction composition.
- TP, PH, saturation-at-pressure, and saturation-at-temperature queries
  on mixture identifiers are rejected with `UNSUPPORTED_QUERY`.
- The `allow_unvalidated_fluids` flag does NOT enable mixture calculations.
- Actual mixture support requires validated mixing rules and is planned
  for a future milestone.

## PH Reference-State Semantics

PH queries require an explicit `reference_state` field in the public
`PHStateSpec` schema.  The field has **no default value** — omitting it
causes a Pydantic validation error (HTTP 422 in API mode).  The value
must match the provider's `reference_state_policy` (currently `DEF`);
mismatched identifiers are rejected with `property_invalid_input`.

The `PHStateSpec.to_provider_args()` adapter converts the schema to
deterministic keyword arguments for `PropertyProvider.state_ph()`.
omitted reference states are rejected with `property_invalid_input`.

The `PropertyProvider` protocol declares `reference_state` as a mandatory
keyword-only argument on `state_ph()`.

## Provider vs. EOS Backend Identity

| Concept | Field | v0.1 value | Example |
|---|---|---|---|
| Property provider | `FluidSpec.backend` / `provider_id` | `CoolProp` | `CoolProp` |
| Equation-of-state backend | `FluidIdentifier.equation_of_state_backend` | `HEOS` | `HEOS` |

The `FluidIdentifier.from_fluid_spec()` adapter:

- Accepts `provider_id` (must be `CoolProp`)
- Accepts `equation_of_state_backend` (default `HEOS`)
- Rejects unsupported provider/EOS combinations
- Documents composition basis (v0.1: `mole_fraction` only)

## Error Codes

| Code | Meaning | Classification method |
|---|---|---|
| `property_configuration_changed` | CoolProp global state changed since provider construction | Fingerprint comparison |
| `property_state_out_of_range` | State is outside the valid fluid domain | Explicit pre-check (TP limits) |
| `property_saturation_unavailable` | Saturation properties unavailable (e.g. above critical) | Explicit pre-check (critical points) |
| `property_near_saturation` | State is too close to a saturation boundary | Explicit enthalpy/pressure check |
| `property_two_phase_state` | State lies in the two-phase region | CoolProp PhaseSI or explicit check |
| `property_unsupported_query` | Query type not implemented (e.g. mixture calculations) | Mixture rejection guard |
| `property_unsupported_backend` | Non-HEOS backend in v0.1 | Backend validation |
| `property_backend_failure` | Unexpected CoolProp exception | Fallback for all unclassified exceptions |

**Note:** Message-token classification (searching CoolProp English error
text) was removed in Review-04.  All known boundary cases are now handled
by explicit pre-checks.  Any CoolProp exception that reaches the
classification path is classified as `property_backend_failure`.

## Serialization

Property results serialize to strict versioned JSON:

- `FluidStateModel` and `SaturationStateModel` use `extra="forbid"`
- `result_schema_version` is constrained to `Literal["1.0"]`
- `PropertyProvenanceModel` includes all provenance fields
- `FluidState.from_json()` returns a domain `FluidState`, not a model
