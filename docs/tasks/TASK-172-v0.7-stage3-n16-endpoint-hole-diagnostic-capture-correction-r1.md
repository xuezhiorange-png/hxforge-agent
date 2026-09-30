# TASK172 Stage-3 n=16 endpoint-hole diagnostic capture correction R1

TASK_ID=TASK172_V0_7_STAGE3_N16_ENDPOINT_HOLE_DIAGNOSTIC_CAPTURE_CORRECTION_R1
MODE=OBSERVABILITY_ONLY_AND_TARGETED_N16_FAILURE_REPLAY
RESULT=PASS
PREDECESSOR_HEAD=f970a4a7a8d562a6c894ed31a30ecfbdea67393d
PR_NUMBER=283
PR_STATE=OPEN_DRAFT

## Outcome

The requested n=16 failure path was replayed at the authorized target cell. Instrumentation captured the endpoint classification and all 12 recovery levels without adding TASK172 evaluations or changing the solver outcome. The target still fails closed with:

`BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED`

This task records diagnostics only. It does not solve the cell, admit a production mesh, or authorize a full mesh rerun.

## Target identity

- Mesh subdivisions per physical interval: 16
- Outer iteration: 2
- Shooting enthalpy: 106853.814770607445 J/kg
- Physical support: `urn:hxforge:r119a:physical-segment:45e63641026ad06bba7d2ab1c7220b6f24d9d54d894eec3837f0188d70cbaf20`
- Axial support: [3.600, 3.675] m
- Tube cell: `urn:hxforge:task172:real-case-cell-tube:7cd5963f2c670fd72b72053cb9f9f5c277e7917bd5a34b93d8cf56ce495cd806`
- Shell cell: `urn:hxforge:task172:real-case-cell-shell:b99a9270a354baad036a456eff7c6267ad36c336ad7bc9a3f2c360c06bfa3084`
- Wall interface used by the authorized target and reconstructed support: `urn:hxforge:task172:real-case-wall-interface:a0a32e756da8310ad90ab25f6483c6a31f052809b5c83917b44004bf644710a9`

The predecessor execution JSON records a wall-interface ID containing `a0a32a...`; this is preserved as historical data and differs by one character from the authorized target/reconstructed support `a0a32e...`. The predecessor diagnostic string `physical_interval=[0.0,111.3949198456]` is also preserved verbatim; those values match the q bracket, not the axial support extent.

## Endpoint-hole finding

- Hole location: upper endpoint
- Hole q: 111.3949198456 W
- Failure: `BLOCKED_RESIDUAL_ACCEPTANCE`
- Request hash: `22be7911da59d0cfd54d922142570ad9f15b2dca2aeb36f415a9d3859ab16970`
- Blocked result hash: `16b34aac7500e1b661a520f6df5a30858b1d3b64b0ec27fcf346172e5e202ad5`
- Initial valid anchor: q=0.0 W, F(q)=-703.9832527970411 W
- Initial valid result hash: `f06720f4ce63eddbfe877acb89868d23a88223f5015eeff6b09b99c2131834fd`
- Recovery probes: 12 valid, 0 holes, 0 other blockers
- Last valid point: q=111.36772382024708 W, F(q)=-592.31714789397702 W
- Distance from last valid point to hole endpoint: 0.02719602535292 W
- Sign change: none; eligible root: none

All 12 F(q) values are negative and move monotonically toward zero, but the last remains -592.31714789397702 W. This is an observed trend only; it does not alter root-search behavior or imply an accepted root.

## Valid recovery probes

| Level | q (W) | F(q) (W) | TASK172 result hash | Classification |
|---:|---:|---:|---|---|
| 1 | 55.6974599228 | -648.1365648279828 | `657d7dcdbcbb118bdd4c5d008f7cf5b8638cb83193040d68b85f16810aa9b253` | VALID_CELL_EVALUATION |
| 2 | 83.5461898842 | -620.2132216999765 | `43310b956ee0083ffbf867431c85723ead88b566dbd97c798a6e2dee30a005fe` | VALID_CELL_EVALUATION |
| 3 | 97.47055486490001 | -606.25155038815149 | `f4d979d34144644bb02a39599616346496856244e41a30a688a3a741aba426a2` | VALID_CELL_EVALUATION |
| 4 | 104.43273735525 | -599.2707146633976 | `93af60015c9fc6e3beb7b44e02a37d090f431307bb6027daac49e9226d1ae4df` | VALID_CELL_EVALUATION |
| 5 | 107.913828600425 | -595.7802970676265 | `8b1a9bc0b18884c8d533bce859cf9dbe56cb79c2f5a8edb909328b8b2bd49fac` | VALID_CELL_EVALUATION |
| 6 | 109.6543742230125 | -594.0350878882451 | `831fdc4110d387f8985283f3e2011d7afc2718628714debece0dd8f3a380533e` | VALID_CELL_EVALUATION |
| 7 | 110.52464703430624 | -593.16248359513506 | `ed66db8c661f6212b306927895372025237a7be3cb9c9a698f120192b9b81c1b` | VALID_CELL_EVALUATION |
| 8 | 110.95978343995313 | -592.72618139160837 | `446a9f56b1fc7276c34bb21f99622cb25e180d9c21bf5a93459e24e068f36b89` | VALID_CELL_EVALUATION |
| 9 | 111.17735164277656 | -592.50803033206304 | `c961754c9c311bc92c5b2eaab5a820c9d354f8099c7cd691f39ab6854c644249` | VALID_CELL_EVALUATION |
| 10 | 111.28613574418827 | -592.39895460976943 | `e0a30dde00e9d4e03012e9f6113458ebdf7075662088e818907ec3415da5e474` | VALID_CELL_EVALUATION |
| 11 | 111.34052779489414 | -592.34441698873146 | `2451d8a0c8b55e0222d6348405bf2ab804525a1ceaed3b5ab9e126e4ab4a4b71` | VALID_CELL_EVALUATION |
| 12 | 111.36772382024708 | -592.31714789397702 | `ac7bec0e950ee99f0d8c4388a11f9cf208566264106799e090c87011d24a0b91` | VALID_CELL_EVALUATION |

The complete trial trajectory, including the valid physical lower endpoint and blocked upper endpoint (with no residual/sign/result fields), is in the [machine evidence](evidence/TASK-172-stage3-n16-endpoint-hole-diagnostic-capture-correction-r1.json).

## Change and validation boundary

- Diagnostic capture code changed; four TASK173 tests added.
- Capture-on/off regression confirmed identical native call identities and solver outcome.
- Multiple-hole retention and maximum recovery-depth capture regressions passed.
- TASK172 acceptance, R98/C_round, cell-root decisions/order/depth/resource limits, production mesh policy, TASK171 and TASK174 were unchanged.
- No n=1→64 mesh sequence was run. No TASK173 production result was created; mesh admission remains false.
- Local validation passed: focused TASK173 suite (40 passed), full shell-tube suite, Ruff and format, mypy CI scope (450 source files), manifest D==M (259=259), lock check, pip-audit (no known vulnerabilities; local unpublished distribution is not queried through PyPI).
- Duplicate-key audit found no duplicates in the new evidence or extension. The historical registry retains its two pre-existing duplicate `canonical_hash` collisions (three root occurrences); they are unchanged and were not repaired because historical registry rewriting is outside scope.
- Exact-head CI for the candidate is required after commit and is recorded in the final task closeout receipt.

Machine evidence canonical hash: `0ef440faa32279b1b7d06821bb58d77e0cee2ed6e71705e360b97008e15bc467`.

Next gate: `STAGE3_N16_ENDPOINT_HOLE_TRAJECTORY_ADJUDICATION`.

No self-approval. PR remains OPEN_DRAFT; Ready, Merge, full production mesh, and TASK175 remain unauthorized.
