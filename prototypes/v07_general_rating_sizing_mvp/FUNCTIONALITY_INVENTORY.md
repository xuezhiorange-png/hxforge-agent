# Functionality inventory (V07_GENERAL_RATING_SIZING_END_TO_END_MVP_R1)

| Area | Status | Notes |
|------|--------|-------|
| Task168 candidate enumeration | **REUSABLE** | `manufacturable_candidates.service.validate_request` — live, input-driven |
| Task171 topology materialization | **REUSABLE** | Via Task168 chain + sizing `materialize_candidate_task171` |
| Task172 coupled cell / fast solver | **REUSABLE** | Inside `task173_integrated_rating.validate_candidate_rating` |
| Task173 integrated rating | **REUSABLE** | Full mesh ladder + R2A path per candidate |
| Task174 hydraulic binding | **REUSABLE** | Part of sizing candidate chain |
| Task173 integrated sizing + ranking | **REUSABLE** | `validate_sizing_request` — live multi-candidate |
| R19/R21E frozen live rating artifacts | **BLOCKED for MVP** | Not used; no golden JSON replay |
| R22 experimental multi-candidate consumer | **REUSABLE pattern** | MVP uses Task173 sizing ranking instead of R22 pinned IDs |
| R23–R27 production admission | **BLOCKED** | Intentionally out of scope; WARN in reports |
| General JSON case input | **IMPLEMENTED** | `GeneralEngineeringCaseV1` |
| Arbitrary fluid / flow service envelope | **MISSING** | Task173 `SizingServiceAuthority` literals; MVP validates envelope |
| Web UI for this workflow | **MISSING** | CLI + reports only |
| Production design approval | **BLOCKED** | `PRODUCTION_DESIGN_APPROVED=false` |

## Hardcoded candidate IDs

The MVP **does not** import R22 `FROZEN_Q13` identities. Candidate IDs and hashes are produced from Task168 for each case.

## Performance

Full `validate_sizing_request` runs the production mesh profile per rated candidate. Use `--preflight-only` for fast geometry enumeration; budget defaults to 3600 s in the case file.
