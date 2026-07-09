# TASK-019 Slice 3B-B — case_02 Material Chain Implementation 指令

Repository: `xuezhiorange-png/hxforge-agent`

Base: `main @ 6a1a2990163a5c91d070b3bb71a05c2dac00a13a`  
Base includes PR #106 Slice 3B-A and PR #107 Amendment 002-F.

Current states:

- case_01: `WIRED_VIA_CHAIN`
- case_02: `WIRED_VIA_CHAIN_PARTIAL`
- case_03: `WIRED_VIA_CHAIN_PARTIAL`

## Authorization

Authorized:

`TASK019_SLICE3B_B_CASE02_MATERIAL_CHAIN_IMPLEMENTATION_AUTHORIZED`

Goal: wire `TASK-019-GOLDEN-02` through real production material / mass / preliminary-mechanical chain using Amendment 002-F `input.material_catalog_bridge`.

Target branch:

`codex/task-019-slice3b-b-case02-material-chain`

Draft PR title:

`TASK-019 Slice 3B-B: case02 material chain`

## Strict scope

Allowed files only:

- `src/hexagent/validation_report/chain_adapter.py`
- `src/hexagent/validation_report/double_pipe_validation_report.py`
- `tests/validation_report/test_chain_wiring_adapter.py`
- `tests/validation_report/test_double_pipe_validation_report.py`
- `ci-shard-manifest.yml` only if shard inclusion is truly required; explain why.

Forbidden files:

- `tests/golden/**`
- `tests/support/**`
- `tests/unit/**`
- `tests/benchmark/**`
- `src/hexagent/exchangers/**`
- `src/hexagent/material_mass_mechanical/**`
- `src/hexagent/material_costs/**`
- `src/hexagent/costing/**`
- `src/hexagent/properties/**`
- `.github/**`
- `docs/**`
- `pyproject.toml`
- `uv.lock`
- TASK-020+ files

Forbidden actions:

- no case_03 implementation
- no pressure drop
- no TASK-020+
- no cost records / SelectionFilters / discount / salvage
- no golden fixture change
- no expected_output change
- no tolerance change
- no provenance metadata change
- no production material/mass/mechanical module change
- no runtime catalog resolver
- no material fallback
- no hardcoded SS304 properties
- no deriving engineering properties from `material_selection.*`
- no fabricated non-null MaterialRecord fields
- no Ready / no Merge / no Issue mutation / no Feishu

## Required preflight probe

Before modifying files, verify read-only:

1. `tests/golden/double_pipe_rating/case_02_materials_mass_mechanical.json` contains `input.material_catalog_bridge`.
2. Bridge contains `shell.identity`, `shell.physical_properties`, `shell.mechanical_properties`, `shell.provenance`, `tube.identity`, `tube.physical_properties`, `tube.mechanical_properties`, `tube.provenance`.
3. Root `amendment_id == TASK-019-DESIGN-AMENDMENT-002-F`.
4. `input.material_catalog_bridge.amendment_id == TASK-019-DESIGN-AMENDMENT-002-F`.
5. `shell.provenance.amendment_id` and `tube.provenance.amendment_id` both equal `TASK-019-DESIGN-AMENDMENT-002-F`.
6. case_02 `expected_output` is unchanged.
7. `input.case_01_input_reference_case_id == TASK-019-GOLDEN-01` still exists.

If any fail, stop with:

`TASK019_SLICE3B_B_BLOCKED_002F_BRIDGE_CONTRACT_NOT_AVAILABLE_OR_INCONSISTENT_NO_MUTATION`

## Required production path

The successful case_02 path must be real:

```text
material_catalog_bridge
  -> MaterialRecord / MaterialResolutionRequest
  -> resolve_material
  -> MaterialResolutionResult
  -> calculate_mass_breakdown
  -> preliminary_check
  -> validation_report actual_output
```

### Bridge consumption

Use only `input.material_catalog_bridge` for material engineering inputs.

`input.material_selection` is descriptive/audit metadata only. Do not infer engineering properties from `SS304`, material IDs, standards, grade, or strings.

### MaterialRecord construction

All non-null fields must come from bridge. Optional nullable metadata may be `None` only if production schema permits it.

Do not auto-complete values from material name, grade, standard, or hidden defaults.

If any mandatory `MaterialRecord` field cannot be supplied by bridge and cannot be `None`, stop with:

`TASK019_SLICE3B_B_BLOCKED_BRIDGE_INCOMPLETE_FOR_MATERIAL_RECORD_NO_FABRICATION`

### MaterialResolutionRequest construction

Use case-bound data only:

- `component_role`: `bridge.shell.component_role` / `bridge.tube.component_role`
- `material_record_id`: `bridge.{shell,tube}.identity.material_record_id`
- `design_temperature_c`: `case_02.input.design_conditions.design_temperature_K - 273.15`
- `design_pressure_mpa`: `case_02.input.design_conditions.design_pressure_Pa / 1_000_000`
- `applicable_standard_id`: `bridge.{shell,tube}.identity.standard_or_spec_reference`
- `corrosion_allowance_mm`: must be `None`; do not fabricate a default.

### resolve_material

Call real production `resolve_material(...)` once for shell and once for tube. If it returns blocker or raises, fail closed partial; do not synthesize success.

### geometry source

Mass and preliminary check geometry must come from the case_01 cross-reference:

`case_02.input.case_01_input_reference_case_id = TASK-019-GOLDEN-01`

Do not synthesize geometry in case_02. Do not reverse-engineer geometry from expected_output. Do not hardcode geometry.

### calculate_mass_breakdown

Call real production `calculate_mass_breakdown(...)` using case_01 geometry and bridge-driven material resolutions. `actual_output.mass_kg.*` must come only from the production result. Do not copy expected_output.

### preliminary_check

Call real production `preliminary_check(...)` using material resolution, case_02 design conditions, and case_01 geometry. `actual_output.preliminary_mechanical_check.status` must come only from production result. Do not copy expected_output.

## Successful case_02 requirements

If full chain succeeds:

- `status = WIRED_VIA_CHAIN`
- `comparison_overall_status = NOT_COMPUTABLE`
- `blocked_fields = []`

`produced_fields` must be an exact set and must not treat bridge static fields as produced fields.

Expected minimum produced fields:

- `mass_kg.fluid_mass_kg`
- `mass_kg.shell_mass_kg`
- `mass_kg.tube_mass_kg`
- `mass_kg.total_mass_kg`
- `preliminary_mechanical_check.status`
- `selected_material_ids.shell_material_id`
- `selected_material_ids.tube_material_id`

## Regression boundaries

case_01 must remain `WIRED_VIA_CHAIN` with exact produced_fields:

1. `heat_duty_W`
2. `LMTD_derived_values.LMTD_counterflow_K`
3. `heat_transfer_coefficients.annulus_side_W_m2_K`
4. `heat_transfer_coefficients.tube_side_W_m2_K`
5. `outlet_temperatures_K.cold_side`
6. `outlet_temperatures_K.hot_side`

case_03 must remain `WIRED_VIA_CHAIN_PARTIAL` with `produced_fields = []`. Do not add cost/lifecycle/pressure-drop fields.

## Fail-closed conditions

Stop or fail closed partial without fabrication if:

1. bridge is missing
2. amendment IDs mismatch
3. shell/tube bridge field missing
4. MaterialRecord mandatory field cannot be provided by bridge
5. case_01 geometry cannot be read safely
6. `resolve_material` fails
7. `calculate_mass_breakdown` fails
8. `preliminary_check` fails
9. upstream provenance/run ID cannot be generated
10. golden fixture changes are needed

Blocked verdicts:

- `TASK019_SLICE3B_B_BLOCKED_RUNTIME_MATERIAL_CHAIN_REQUIRES_NEW_CATALOG_RESOLVER_OR_FIXTURE_CHANGE_NO_FABRICATION`
- `TASK019_SLICE3B_B_BLOCKED_002F_BRIDGE_CONTRACT_NOT_AVAILABLE_OR_INCONSISTENT_NO_MUTATION`
- `TASK019_SLICE3B_B_BLOCKED_BRIDGE_INCOMPLETE_FOR_MATERIAL_RECORD_NO_FABRICATION`

## Tests required

Success path tests:

- case_02 with 002-F bridge returns `WIRED_VIA_CHAIN`
- case_02 produced_fields exact set
- `mass_kg.*` comes from `calculate_mass_breakdown`
- preliminary status comes from `preliminary_check`
- selected material IDs come from production material resolution, not expected_output copy
- canonical actual output hash stable
- repeated run deterministic
- upstream_calculation_run_ids non-empty
- upstream_provenance_digests non-empty

No-fabrication tests:

- remove `material_catalog_bridge` -> fail closed partial
- change bridge amendment_id -> fail closed partial
- remove shell physical property -> fail closed partial
- remove tube mechanical property -> fail closed partial
- remove case_01 geometry reference -> fail closed partial
- adapter does not use expected_output.mass_kg as actual_output source
- adapter does not use hardcoded SS304 fallback

Regression tests:

- case_01 remains `WIRED_VIA_CHAIN`
- case_01 produced_fields exact set unchanged
- case_03 remains `WIRED_VIA_CHAIN_PARTIAL`
- case_03 produced_fields remains empty
- no cost/lifecycle/pressure-drop fields newly produced

## Required checks

Run:

```bash
python -m json.tool tests/golden/double_pipe_rating/case_01_heat_balance_rating.json >/dev/null
python -m json.tool tests/golden/double_pipe_rating/case_02_materials_mass_mechanical.json >/dev/null
python -m json.tool tests/golden/double_pipe_rating/case_03_cost_lifecycle_envelope.json >/dev/null
python -m json.tool tests/golden/double_pipe_rating/_provenance_metadata.json >/dev/null
python -m json.tool tests/golden/double_pipe_rating/_tolerance_metadata.json >/dev/null

git diff --check

uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src/hexagent tests/support/property_provider_doubles.py tests/support/test_property_provider_doubles.py
uv run --locked pytest tests/validation_report/
uv run --locked pytest tests/golden/double_pipe_rating/
```

Suggested if time permits:

```bash
uv run --locked pytest
```

If not run, report why.

## Commit / PR

Only commit if implementation succeeds.

Commit message:

`feat(task-019): enable slice3b-b case02 material chain`

If blocked, do not commit.

If successful, push branch and create Draft PR:

- Base: `main`
- Head: `codex/task-019-slice3b-b-case02-material-chain`
- Title: `TASK-019 Slice 3B-B: case02 material chain`
- Draft: YES

Do not Ready. Do not Merge.

## PR body must include

- baseline SHA
- branch
- changed files
- diff stat
- case_01 unchanged confirmation
- case_02 status
- case_02 produced_fields exact set
- case_02 actual values
- case_02 provenance / upstream run ids
- case_03 unchanged confirmation
- expected_output unchanged confirmation
- tolerance unchanged confirmation
- golden fixture unchanged confirmation
- no fabrication confirmation
- Ready not authorized
- Merge not authorized
- CI status

## Final report must include

- branch
- base SHA
- head SHA
- PR number and URL
- PR state / draft / merged
- changed files
- diff stat
- case_01 status
- case_01 produced_fields exact set
- case_02 status
- case_02 produced_fields exact set
- case_02 actual values
- case_02 canonical_actual_output_sha256
- case_02 upstream_calculation_run_ids
- case_02 upstream_provenance_digests
- case_03 status
- case_03 produced_fields
- all checks result
- CI run ID and status
- forbidden-action ledger

Success verdict if Draft PR created:

`TASK019_SLICE3B_B_CASE02_MATERIAL_CHAIN_DRAFT_PR_CREATED_CI_PENDING_READY_NOT_AUTHORIZED_MERGE_NOT_AUTHORIZED`

Success verdict if commit/push succeeds but PR creation fails:

`TASK019_SLICE3B_B_CASE02_MATERIAL_CHAIN_LOCAL_COMMIT_READY_PR_CREATION_REQUIRED_READY_NOT_AUTHORIZED_MERGE_NOT_AUTHORIZED`

Stop after Draft PR + CI status report. Do not Ready, do not Merge, do not enter case_03.
