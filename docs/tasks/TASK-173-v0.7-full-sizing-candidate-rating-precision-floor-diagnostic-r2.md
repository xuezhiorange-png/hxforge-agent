# TASK173 Candidate Rating Precision-Floor Diagnostic R2

**Result:** `DIAGNOSED_TASK173_CANDIDATE_RATING_IMPLEMENTATION_DEFECT`

This was a diagnostic-only continuation. It did not rerun public Sizing, change production code, alter the completion request, or change any authority. The committed completion request replay passed at the exact execution freeze head `75a795f676e8cc3b1d2e7e0f89377684c3a78650`, whose parent is production runtime `b1da0536d34ff174c825e9862d7e29cf2d087785`. All bound production paths were byte-identical between those commits.

## Invocation and identity results

The completion request remained `5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae`; the native TASK168 candidate-space identity remained `aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea`. Public Sizing was not called.

Candidate A’s pristine Rating call returned a complete `Task173BlockedResult` whose independently recomputed hash matched both the returned hash and the frozen Sizing ledger: `acf8fd832d345a3fbc6e6fed218187ee3c98367955b3a060e01b246d42adbfbb`. Its separate observer call returned an exactly equal complete result projection. It was not the prior local diagnostic hash `1ddde455a88fdb5ab4b17c821a78395d3c624cefb215b578a4e2a1da07d3df85`.

Candidate B’s pristine result similarly matched the frozen Sizing ledger at `737ed569590d1464f990566599281a2eb3d2d31d51bddf2fa472984c5a04203f`; its separate observer result projection was byte-identical to pristine. Each candidate therefore used exactly two diagnostic Rating calls: one pristine and one observer. No observer was installed for either pristine run.

Both results failed at a cell-root precision floor on mesh `n=1`. The full request projections, result projections, ambient execution context, and observer records are embedded in the machine evidence file.

## First blocker

Both observer runs recorded the only false R2A eligibility predicate as `Q13`, and production returned `NONE`. Candidate B’s complete endpoint request/result capture identifies the exact failing comparison: the R2A Q13 code compares `Task172LocalResult.physical_support_id` to `support.physical_segment_id` in [`service.py` line 1022](../../src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py:1022).

Those fields are different identity domains. TASK172 defines `physical_support_id` as the canonical support hash (`recompute_task172_support_id(request)`), while `physical_segment_id` is the native support URI; the runtime’s own result replay checks them separately ([TASK172 service, lines 249–273 and 1154–1155](../../src/hexagent/exchangers/shell_tube/task172_local_runtime/service.py:249)). Candidate B’s captured endpoint results show the 64-character support hash on one side and the support URI on the other, while each result’s `physical_segment_id` exactly matches the request support URI. Consequently the current Q13 comparison cannot succeed for this valid endpoint pair, preventing the reviewed transient event from triggering.

This is an implementation defect in the R2A eligibility predicate, not evidence of nondeterminism and not a reason to broaden the authority. Candidate A’s observer version recorded `Q13=false` but did not serialize its endpoint request/result preimages or Q13 component breakdown. That missing A subpredicate detail is explicitly retained as an evidence limitation; the invocation cap was reached, so A was not rerun. Candidate B’s complete capture independently proves the production field mismatch.

No production correction is made in this diagnostic gate. The next gate is `OWNER_AUTHORIZATION_REQUIRED_FOR_TARGETED_TASK173_RATING_IMPLEMENTATION_CORRECTION`.

## Preservation and governance

The previous uncommitted R1 diagnostic artifacts were left unchanged; their SHA-256 values are recorded in the R2 JSON. This commit contains only the R2 diagnostic report, evidence, and runner. Public Sizing re-execution remains forbidden; TASK173 Sizing and TASK173 overall remain incomplete. TASK175, Ready, and Merge remain unauthorized.

After the four diagnostic calls, the committed runner received only mechanical Ruff import cleanup and formatting so repository lint/format checks can inspect it. The executed source hashes remain recorded separately in the JSON; no diagnostic call was repeated after this cleanup.
