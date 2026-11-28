# V08-07 Task173 independent heavy case — supersession record

Status: `SUPERSEDED_BY_KERNEL_V1` (not a passing Task173 solver outcome)

## Superseded node

| Field | Value |
|-------|-------|
| Test | `tests/prototypes/test_v08_thermal_rating_independent_case_heavy.py::test_v08_03_independent_case_input_delta` |
| Legacy path | `run_v08_thermal_rating` + Task173 live mesh (`FIXTURE` vs `FIXTURE_ALT`) |
| Product obligation | Independent non-reference water/water case with distinct duty and tube inlet (220 kW alt / delta inputs) |

## Replacement evidence (formal PR gate)

| Field | Value |
|-------|-------|
| Authority | `V08_INDEPENDENT_KERNEL_V1` |
| Fixture | `tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json` (P2) |
| Acceptance | `test_v08_06_kernel_version_acceptance.py` → `P2_STATUS == KERNEL_JOINT_E2E_PASS` |
| Runner | `v08_06_kernel_version_acceptance.run_kernel_matrix` |

## Historical replay (not release gate)

- Workflow: `.github/workflows/v08-legacy-task173-experimental.yml` (`workflow_dispatch` only)
- Env: `HXFORGE_LEGACY_EXPERIMENTAL_V08_TASK173=1`
- Manifest shard: `v08-03-thermal-live-independent` (7200s runner budget preserved)
- Formal CI: test reports **skipped** with this document id — obligations preserved, Task173 not claimed as PASS

## Code and evidence retention

Original test body unchanged under legacy env. Prior failure logs (CI 45661307292 / 45764324314) remain valid historical attribution.