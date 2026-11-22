# Engineering shortlist robustness r1 supersession (r2)

**Preserves** `V08-03-engineering-shortlist-robustness-r1.json` on disk; conclusions below are superseded.

## Historical defect (r1)

- Non-baseline sensitivity used full `Task168._execute_candidate_chain` on `candidate_spec_id`, re-running Task021 and drifting to foreign layouts (Re≈3427–3530).
- Failures were mislabeled via `TUBE_SIDE_REPLAY_FAILED` wrapper without separating raw Task027 codes.
- Worst-case high-K margins incorporated missing non-baseline dp as if computed.

## Corrected method (r2)

- **Fixed geometry replay:** freeze enumeration `task021_layout_hash` / Task025; rerun Task026 only when tube mass or inlet temperature changes.
- **Shell-only perturbations:** Task026/Re unchanged from canonical bundle.
- **Attribution:** record `task027_raw_blocker_code`; wrapper codes not equated to `BL_T027_UNSUPPORTED_REYNOLDS_REGIME`.
- **High-K sweep:** only scenarios with `high_k_dp_computed=true` count toward hydraulic robustness statistics (non-baseline blocked by Task173 mass binding until extended).

## Current authoritative artifact

`V08-03-engineering-shortlist-robustness-r2.json`