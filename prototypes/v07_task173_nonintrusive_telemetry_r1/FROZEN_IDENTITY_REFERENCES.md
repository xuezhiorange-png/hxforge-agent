# Frozen identity references (documentation only — no solver execution)

## Candidate B (`e152cca9-fd5d-59ca-9b46-1df574eee841`)

| Field | Value | Evidence |
|-------|-------|----------|
| `candidate_hash` | `53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489` | `TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json` |
| **SUCCESS** `candidate_rating_result_hash` | **`1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743`** | Same file; `TASK-173-v0.7-full-sizing-reference-plane-serialization-completion-r1.json` |
| `result_id` | `urn:hxforge:task173:1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743` | completion evidence |

### Correction: `fa9030a7…` is NOT the success hash

`fa9030a7d2968d1f1d0bfc73426bebd023f73182ecf0b561d2e548c82016f88f` is the **BLOCKED** candidate-rating `result_hash` for Candidate B under the **cell-root precision-floor adjudication** fixture (`TASK-173-v0.7-cell-root-precision-floor-adjudication-r1.json`, `attempt_4.candidate_b.blocked_rating_result_hash`), with `rating_request_hash` `8771099ae4fdfa553d2d092e41e366fcb36b1b30f16822c9f0277b9a6394066e`.

Earlier telemetry summaries incorrectly cited `fa9030a7…` as the regression target for a **successful** Candidate B rating. Post-hook identity regression for **success** must use **`1cecb402…`** (reference-plane serialization completion bundle). Blocked-receipt regression remains a **separate** frozen case (`fa9030a7…`).

## Q13 correction bundle (distinct request lineage)

`docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py` lists a different `rating_request_hash` (`56ecf30c…`) for the same `candidate_id`; use the hash that matches the frozen request you replay.
