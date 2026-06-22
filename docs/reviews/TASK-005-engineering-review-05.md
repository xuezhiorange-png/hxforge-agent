# TASK-005 Engineering Review — Round 5

**PR:** #11  
**Head reviewed:** `7ebb50e05c50385007a94f0a1d393409373807bf`  
**Decision:** CHANGES REQUIRED  
**CI:** GitHub Actions run `27924695591` / run #99 passed.

Review-04 closed definition identity, full assessment hashing, UUID5 provenance identity, and SemVer-aware supersession. Three final contracts remain open.

## 1. ApplicabilityAssessment still accepts and silently rewrites caller continuation

`allows_evaluation` remains a public field with a default. The model validator overwrites the caller-provided value using `object.__setattr__` instead of rejecting contradictory direct construction. This does not satisfy the requirement that continuation be engine-derived and that inconsistent construction fail.

Required:

- remove `allows_evaluation` from public constructor input, or make it a computed/read-only property;
- provide one validated engine/factory construction path;
- reject contradictory direct construction and JSON input rather than silently correcting it;
- retain required and validated `assessment_hash`;
- add tests proving caller-provided continuation cannot alter or bypass the domain result.

## 2. CorrelationUsageRecord.create does not cross-validate assessment against inputs

The factory only checks `assessment.correlation_key == definition.key`. It then copies `inputs.values`, assessment status and assessment hash without proving that the assessment was actually produced from that definition and those inputs.

Consequently, callers can combine:

- a valid assessment for the same key but a different definition hash/policy;
- a valid assessment with different geometry, phase, flow or input values;
- an arbitrary valid assessment hash;
- a mismatched applicability status relative to the supplied inputs.

Required:

- recompute `expected_assessment = assess_applicability(definition, inputs)` inside the factory, or introduce a signed/structured assessment identity that embeds definition hash and input identity;
- require the supplied assessment to match the recomputed assessment hash, status, messages, variable results and continuation;
- derive usage fields only from the verified assessment and definition;
- add negative tests for different inputs, different definition/policy, forged assessment hash and mismatched status.

## 3. PR and task records are still stale

The actual remote head is `7ebb50e`, but the PR body and task card still report `a3c8d19`. The PR body also records CI run `27924642281`, while the verified final run is `27924695591` / run #99.

Required:

- update PR body and `docs/tasks/TASK-005-correlation-registry.md` to the exact final head and CI run after the code fix;
- retain the actual test count and Draft status until final approval.

## Final approval gate

Before approval:

1. both Python matrix jobs remain green;
2. assessment continuation is not caller-controlled or silently rewritten;
3. usage factory proves the assessment belongs to the exact definition and inputs;
4. PR body and task card match the final remote head and CI run;
5. no real formulas, database, API, heat balance, sizing/rating, or TASK-006 scope is added.
