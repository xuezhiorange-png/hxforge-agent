# TASK173 Supplemental Functional Acceptance R2 — Independent Review Erratum 1

```text
ERRATUM_ID=V07-T173-SUPPLEMENTAL-FUNCTIONAL-ACCEPTANCE-R2-INDEPENDENT-REVIEW-R1-ERRATUM-1
BASE_REVIEW_COMMIT=fd725fafb005014e82bcd24526524fb0bc58a315
ERRATUM_SCOPE=CORRECT_ONE_MALFORMED_AUTHORITY_HASH_AND_REPLAY_FILE_HASH_ONLY
ORIGINAL_REVIEW_VERDICT_RETAINED=PASS
```

This additive erratum preserves the original review receipt and its bytes. It
does not rewrite the historical review record. It corrects one malformed
63-character value in the review receipt and records the replay file's SHA-256
after the authorized Ruff I001 import-order-only repair.

## R2 Sizing authority hash correction

The original review receipt at `fd725fafb005014e82bcd24526524fb0bc58a315`
contains this malformed value in both its Markdown table and JSON identity:

```text
750c1f76953f46b63de90f2c21302160746e8904fc61227538397e69b8501a9
```

It is 63 hexadecimal characters and is retained above as the historical
mistake. The authoritative 64-character hash is:

```text
750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9
```

This corrected value is read from the committed R2 package evidence
`docs/tasks/evidence/TASK-173-v0.7-sizing-authority-closure-package-r2.json`
(`authority_package_hash`) and agrees with
`docs/tasks/TASK-173-v0.7-sizing-authority-closure-package-r2.md`
(`AUTHORITY_PACKAGE_CANONICAL_HASH`). The source files at the base review head
have Git blob IDs `f682e84584b4f651cd0143c040d755d1a7fa4297` and
`114692d1fad7e992d30ada1b0c0bcf20edf4c101`, respectively. Their SHA-256 values
are recorded in the machine-readable erratum.

Only the malformed identity field is superseded. The original review verdict,
review scope, and all other conclusions remain unchanged. The correction does
not alter the frozen request, requirement, candidate space, candidates, or any
R2/R2A authority.

## Replay import-order correction

The authorized Ruff I001 fix and the CI-required Ruff formatting pass modify only
formatting in
`docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2-replay.py`.
Its SHA-256 changed from
`69a1438d0340beb997849ce48148c6bd8acb511ef0b9495d524c02ba6e038f38` at the
reviewed freeze commit to
`0527379c37d5b03f124fda52c12fa7b420c8043c8732f69c395d6897e5d15685` after the
I001 repair and formatting pass. The source diff is limited to import
organization and formatter line wrapping/blank-line normalization. Import
bindings and the non-import AST are mechanically identical; no executable
statements, literals, branches, or calls changed. The frozen-input replay is
rerun on the P0 commit before any production Sizing call.

```text
REPLAY_SCRIPT_FORMAT_ONLY_CHANGE=true
REPLAY_SCRIPT_SEMANTICS_CHANGED=false
```

## Independent scope review status

This erratum and the changed replay script require narrow independent review
of the corrected hash's lineage and the import-only diff. The re-review is
limited to those corrections and does not reopen the already-passed functional
acceptance design unless it finds a related identity or behavior discrepancy.
