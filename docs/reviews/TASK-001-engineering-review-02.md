# TASK-001 Engineering Review — Round 2

**PR:** #2  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

The revision resolves most findings from Round 1. TASK-001 is not yet approved because the following baseline-model issues affect downstream schemas.

## 1. Separate workflow state, verification maturity, and review requirement

`status` and `verification_level` are now separate, which is correct. However, `VERIFIED` exists in both enums and `REVIEW_REQUIRED` is an action requirement rather than a maturity level.

Required revision:

- Rename the workflow stage `VERIFIED` to `VERIFICATION_COMPLETED` (or another unambiguous workflow-stage name).
- Define `verification_level` as evidence maturity, recommended values:
  - `UNVERIFIED`
  - `PRELIMINARY`
  - `BENCHMARK_VALIDATED`
  - `ENGINEERING_APPROVED`
  - `N/A`
- Represent required human action separately, for example `requires_review: bool`, derived from warnings/assumptions, or a dedicated `review_state`.
- Update PRODUCT_REQUIREMENTS, INPUT_OUTPUT_DICTIONARY, WORKFLOW_MATRIX, DEC-006 and all baseline cases consistently.

## 2. Correct DEC-014 convergence semantics

A universal residual threshold of `0.01 K` is dimensionally invalid for solvers whose primary unknown is pressure, enthalpy, mass flow, U-value, area or another variable.

Required revision:

- Keep heat-balance acceptance separate from numerical solver convergence.
- Each solver must declare typed `absolute_tolerance`, dimensionless `relative_tolerance`, residual definition and scaling quantity.
- Use a combined criterion such as `abs(delta_x) <= atol + rtol * scale` where applicable.
- Define the heat-balance denominator safely using absolute values and a non-zero reference floor.
- Keep `max_iterations` configurable and traceable.
- On failure, terminate with `NON_CONVERGED` and a structured blocker; do not publish the last iterate as a valid result.

Do not assign one temperature tolerance to all iterative solvers.

## 3. Correct DEC-016 task dependency

Fluid validation is a TASK-003 property-service responsibility, not a TASK-002 unit-system completion criterion.

Required revision:

- Change “Tier 1 must pass before TASK-002 completes” to “Tier 1 must pass before TASK-003 completes” or before dependent thermal solvers are released.
- TASK-002 is unblocked by approved DEC-005 plus the final quantity/status data contracts; it does not require CoolProp fluid validation.

## 4. Move roughness out of StreamSpec

Surface roughness belongs to a wetted flow passage, geometry catalog entry or material/surface specification. It is not an intrinsic stream property.

Required revision:

- Remove `roughness` from Stream inputs.
- Add side-specific roughness to exchanger geometry/flow-passage data, with source and applicability.
- If roughness is resolved from a material/catalog entry, store the resolved value and catalog provenance in the run trace.

## 5. Fix baseline cases and representation claims

The claim that all five cases are fixed and fully representable is not yet true.

Required revision:

- CASE-001: `PRELIMINARY` and `REVIEW_REQUIRED` must not be described as `status` values after the state split.
- CASE-002: replace generic “user-specified” inputs with one complete fixed Water/Water rating case and a concrete versioned geometry object.
- CASE-003: convert fouling references to the structured DEC-017 object.
- CASE-004:
  - do not use a Tier-3 MPG solution as a mandatory baseline case for the v0.1 core unless the exact incompressible-fluid identifier, concentration basis and validation scope are defined;
  - preferably use a fixed Water/Water sanitary screening case for TASK-001;
  - treat EPDM compatibility as a constraint requiring verification against specified CIP chemistry, temperature and concentration, not as an unconditional fact;
  - convert fouling references to structured objects.
- CASE-005: choose one workflow, one exact refrigerant state and one exact secondary-fluid case. The current I/O dictionary cannot represent pressure/enthalpy or vapor-quality state specifications. Either add a versioned state-specification union or define the request as rejected before calculation. Do not claim full representability until this is resolved.

## 6. Define deterministic result hashing precisely

`result_hash` cannot hash an object that includes its own hash, random `run_id`, timestamps or other non-deterministic metadata.

Required revision:

- Define the canonical hash payload explicitly.
- Exclude `result_hash`, random IDs, timestamps, display formatting and non-deterministic ordering.
- State numeric canonicalization and unit normalization rules.
- Include input revision, resolved engineering inputs, deterministic outputs, formula/property versions and software commit/version.

## Additional editorial corrections

- In PRODUCT_REQUIREMENTS, replace “Only validated capabilities may return PRELIMINARY or above.” Implemented but not benchmark-validated calculations may legitimately be `PRELIMINARY`; validation maturity is represented by `verification_level`.
- Replace ambiguous `standard_basis: list/string` with one versioned structured schema.
- Exact standard/table references in example cases must be verified through the licensed rule-pack process. Until verified, use clearly marked placeholder references rather than presenting them as approved data.
- Keep ADR-006 as the software-format decision; DEC-013 correctly remains format-neutral.

## Approval gate

After these revisions:

1. update the TASK-001 acceptance checklist;
2. report final enums and fixed five-case summaries;
3. confirm DEC-005 and DEC-006 are ready for owner approval;
4. rerun CI;
5. keep the PR Draft until owner approval is recorded.

No unit-system, property, heat-balance or exchanger calculation code should be added in this PR.
