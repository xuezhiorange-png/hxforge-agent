# TASK172 fail-only dogbox fallback — narrow implementation R1

```text
TASK_ID=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_NARROW_IMPLEMENTATION_R1
LOCAL_RESULT=IMPLEMENTATION_AND_LOCAL_VALIDATION_PASS_PENDING_EXACT_HEAD_CI
SOURCE_HEAD=74221db2ab43a7d61ef2dd94a79da81a866d117b
REVIEWED_AUTHORITY_ID=V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3
REVIEWED_AUTHORITY_CANONICAL_HASH=9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b
R3_REVIEW_EVIDENCE_CANONICAL_HASH=2a6c9f398c9483d8a2e95bf10c91c540453b537b28969b602189dac3267bfc07
IMPLEMENTATION_EVIDENCE_CANONICAL_HASH=47f179ccb335158568e22ae2582b2ec48cd6237ceb18427b7c1275460f11556f
AUTHORITY_LIFECYCLE=REVIEWED_AUTHORITY
```

## Implementation

Implemented the reviewed `FAIL_ONLY_ORIGINAL_SEED_DOGBOX_FALLBACK` overlay in
`task172_local_runtime/service.py`. Each request first executes the unchanged
R94 TRF attempt. A primary `Task172LocalResult` is returned as the same object;
all non-residual blockers are returned unchanged. The exact-zero branch remains
on its existing path and does not invoke either nonlinear fallback attempt.

Dogbox runs only after the primary attempt has produced a typed
`BLOCKED_RESIDUAL_ACCEPTANCE` whose request hash and blocked-result hash both
replay. Any replay mismatch bypasses fallback. The dogbox attempt starts from
the deterministic R94 seed recomputed from the original request—not the TRF
iterate—and receives its own 6-`nfev` / 24-callback budget. Solver method is the
only changed control. A successful optimizer termination is not sufficient:
the ordinary final evaluation, original R98 bounds with `C_round=1.0`,
nonnegative-duty, wall-ordering, property/domain/correlation guards and native
result identity checks still have to pass. Any fallback failure remains a
typed blocker; no diagnostic iterate is accepted.

Fallback-only results carry solver status
`R94_TRF_RESIDUAL_FAIL_THEN_DOGBOX_FALLBACK_STATUS_<status>`, numerical profile
ID `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, and the two R3 authority/review
evidence references. Existing primary result profile, solver status, provenance
and hash projection remain unchanged. The existing string-valued
`numerical_profile_id` and `provenance_refs` fields express this path; no model,
request, result or blocked-result schema changed.

The former diagnostic-only candidate harness now observes the actual
`validate_request()` path and the independently callable single-attempt helper.
The frozen six n=32 requests, historical n=16 upper request and existing
68-request corpus are reused; no fixtures were changed and no production mesh
was run.

## Local execution evidence

Environment: CPython 3.14.5, macOS 27.2 arm64, CoolProp 8.0.0, SciPy 1.18.0.

- Six fixed n=32 residual-hole requests: primary residual blocker replayed on
  all six; dogbox fallback invoked and independently R98-validated on 6/6.
- Historical n=16 upper endpoint: primary residual blocker followed by a valid
  dogbox result; existing valid-upper classification contract is untouched.
- Frozen 68-request local corpus: 68/68 primary results were valid, fallback
  invocation on primary-valid requests was 0/68, and the original native result
  identities were preserved 68/68.
- Same-environment replay of the first fixed target reproduced the complete
  canonical result projection, result hash and result ID exactly.
- Tests assert original-seed reuse, only-method control change, per-attempt
  limits, fallback result hash replay and property snapshot identities. Guard
  cases cover seven non-residual blockers, invalid request and blocked-result
  hash replay, invalid fallback result identity, fallback failure/nonconvergence,
  resource exhaustion, domain failure, negative duty, wall ordering and R98
  failure.

Linux CPython 3.11/3.12 implementation behavior is reserved for the exact-head
PR CI run; this local receipt does not substitute historical characterization
for implementation CI evidence.

## Validation and change boundary

Focused TASK172, focused TASK173, full shell-tube suite and HTTP/API regression
passed. Ruff, format check, CI-scope mypy (450 files), manifest `D==M`
(259/259), pip-audit, `uv lock --check`, `uv sync --locked --all-extras`, and
`git diff --check` passed. `uv.lock` remained byte-identical (SHA-256
`4783f2a07cd28b5a5c46402101f0570d3060f464fe850c63fc7ad5e069e68464`);
`requests==2.34.2` and `urllib3==2.8.0` remain locked. The pre-existing
historical duplicate `access_path` key is outside the changed files and was not
edited.

Changed implementation/test files are limited to `service.py` and
`test_task172_local_runtime.py`, plus this Markdown receipt and its machine
evidence. No models, schemas, fixtures, TASK173 production code, dependencies,
lockfiles, workflows, registry or unrelated historical evidence changed.

```text
R94_CHANGED=false
R98_CHANGED=false
C_ROUND_CHANGED=false
REQUEST_SCHEMA_CHANGED=false
RESULT_SCHEMA_CHANGED=false
BLOCKED_SCHEMA_CHANGED=false
IMPLEMENTATION_VERSION_CHANGED=false
TASK173_ROOT_LOGIC_CHANGED=false
PRODUCTION_MESH_POLICY_CHANGED=false
PORTABILITY_RUNTIME_COMPARATOR_ADDED=false
PRODUCTION_MESH_REEXECUTED=false
REAL_CASE_MESH_ADMISSIBLE=false
TASK173_RESULT_ID=UNAVAILABLE
TASK173_RESULT_HASH=UNAVAILABLE
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
EXACT_HEAD_CI=PENDING
NEXT_GATE=STAGE3_TASK173_PRODUCTION_MESH_REEXECUTION_FROM_N1
NEXT_GATE_EXECUTED=false
STOP=true
```

Machine-readable evidence: [implementation evidence](evidence/TASK-172-stage3-task172-dogbox-fallback-narrow-implementation-r1.json).
