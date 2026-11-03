# TASK173 Q13 correction and Full Sizing recovery R1

## Disposition

The reviewed R2A authority was not changed. The Q13 implementation mapping was
corrected in commit `c36d54d0a8c162bbb4c585acfc6ec5615ce1f6cf`: Task172 support
hashes are now replayed with `recompute_task172_support_id(request)` and bound
to `physical_support_id`; physical segment URIs are compared only with URI
fields. Q13 semantics, TASK172, tolerances, candidate space and R2A authority
remain unchanged.

Focused tests cover the captured Candidate B endpoint pair and six tampering or
cross-domain identity failures. The captured pair changes Q13 from false to
true; all other recorded Q predicates remain true. TASK172 identity tests,
TASK173 Rating/R2A tests, TASK174 tests, mypy, Ruff, format, manifest D==M,
`uv lock --check`, and `git diff --check` passed. The frozen reference TASK174
identity replay remained `ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`.

## Candidate Rating outcome

The frozen completion request and native TASK168 candidate space replayed with
their exact identities. Candidate A and Candidate B Rating request hashes also
matched their frozen values. One post-fix full Candidate Rating invocation was
performed for each candidate; the complete native request projections and
complete returned blocked-result projections are preserved in the JSON
evidence.

Both returned `Task173BlockedResult` with
`BLOCKED_TASK173_CANDIDATE_UNEXPECTED_RUNTIME_FAILURE`. The exact diagnostics
were `PydanticSerializationError` and `Unable to serialize unknown type: <class
'hexagent.exchangers.shell_tube.tube_side.owned_enums.ReferencePlanePair'>`.
The independently recomputed blocked-result hashes match the returned hashes:

- Candidate A: request `1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7`, result `1ddde455a88fdb5ab4b17c821a78395d3c624cefb215b578a4e2a1da07d3df85`.
- Candidate B: request `56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8`, result `290fca0f7e08a4f8457daa9de854a292c4332fa1f575bb4153623a48d9d4d033`.

Neither candidate completed full Rating, so the full-candidate success count is
zero. No second public Sizing invocation was authorized or performed. The first
frozen Sizing result and its invocation count remain unchanged. This is an
implementation blocker; no retry or repair was attempted in this continuation.

## Invocation and governance boundary

- Historical R4 public Sizing invocations: 2.
- Frozen completion-request public Sizing invocations: 1; this continuation: 0.
- Candidate Rating diagnostic invocations: A=1, B=1.
- R2A authority changed: false. TASK172 production/contract changed: false.
- TASK173 Sizing complete: false. TASK175 performed: false.
- PR #283 remains OPEN / Draft; Ready and Merge are not authorized.

Replay the frozen request, candidate request identities, blocked-result
preimages and runtime binding with:

```sh
uv run --locked python docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-completion-r1-replay.py
```

The diagnostic execution runner is included as evidence provenance. It has
one-shot per-candidate invocation guards and does not invoke public Sizing.
