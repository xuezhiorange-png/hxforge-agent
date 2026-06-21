# TASK-003 Engineering Review — Round 3

**PR:** #7  
**Head reviewed:** `0e4220d1966d8086ae46dbf2c2f2447d312b6267`  
**Decision:** CHANGES REQUIRED  
**CI:** Python 3.11 and 3.12 quality jobs passed.

The latest revision improves the FluidSpec adapter, PH provider signature and provenance enum fields. Five contract gaps remain.

## 1. Reference-state guard

The provider accepts the first observed fingerprint as its baseline. If CoolProp is already changed before provider construction, the changed state is accepted while provenance still says `DEF`. The fingerprint probes Water and R134a only, so an R717 change may be missed. Verification and the subsequent property call are also not protected as one atomic operation.

Required:

- establish a known `DEF` baseline during controlled initialization;
- include all supported reference-sensitive fluids or a query-specific signature;
- protect verification and property evaluation with one documented lock;
- fail closed when constructed under a non-approved baseline;
- test mutation before construction, R717 mutation and mutation between verification and evaluation.

## 2. PH public schema

The provider requires `reference_state`, but `PHStateSpec` still contains only pressure and enthalpy. Public JSON therefore cannot supply the mandatory provider input. Omitting the Python keyword produces a normal `TypeError` rather than a structured property error.

Required:

- add a required reference-state identifier to the versioned PH state schema;
- define the schema-version impact;
- add a deterministic `PHStateSpec` to provider adapter;
- reject missing, unknown and mismatched identifiers through structured errors;
- add API/schema integration tests.

## 3. Validation provenance

Dataset ID, revision and basis exist in `PropertyProvenance`, but `_provenance()` does not populate them. Validation still depends only on the fluid allowlist and does not match the actual query to a regression fixture.

Required:

- record `support_allowlist` for ordinary Tier-1 states;
- record dataset ID, revision and `backend_regression` when a query matches a fixture;
- implement documented deterministic fixture or envelope matching;
- add matching and non-matching provenance tests.

## 4. Serialization

Result versions remain pattern-constrained strings instead of `Literal["1.0"]`. Result-model phase and query fields remain plain strings. `PropertyServiceError` has no strict versioned JSON reconstruction contract.

Required:

- use literal schema versions and enum fields throughout;
- add a strict error model with `extra="forbid"`;
- implement deterministic error JSON serialization and reconstruction;
- prove canonical JSON equality after state and error round trips.

## 5. Error classification

Known state errors are still classified by searching English CoolProp message text. The exact current-version test does not make the public error code independent of backend wording.

Required:

- pre-check critical boundaries for saturation queries;
- classify known state-domain failures using explicit checks rather than message substrings;
- reserve `BACKEND_FAILURE` for unexpected backend faults;
- keep backend messages only in context;
- test different backend messages producing the same public code.

## Approval gate

After correction, rerun all CI gates and demonstrate: a known-DEF locked guard, PH reference identity from schema to provider, populated validation provenance, strict state/error JSON round trips and error codes independent of backend wording.

Keep TASK-003 `IN_PROGRESS` and PR #7 Draft. Do not begin TASK-004.
