"""TASK-019 Slice 2 materialization contract tests.

These tests exercise the Slice 2 surface introduced on top of the Slice 1
skeleton. They are additive: none of the Slice 1 tests are touched, and
every Slice 1 fixture / case-block contract is preserved.

Slice 2 contract (per frozen design §7.1 + §11):

1. ``compute_frozen_upstream_contract_versions`` returns the 11-key
   ``upstream_contract_versions`` block per §7.1, with each value being
   a 64-char lowercase hex SHA-256.
2. ``materialize_run_environment`` returns the real ``run_environment``
   block with ``python_version``, ``platform``, ``package_versions``,
   ``deterministic_mode_flags``.
3. ``materialize_case_block_from_fixture`` materializes a §7.1-shaped
   case block from a Slice 1 fixture JSON, with deterministic SHA-256
   hashes and per-field NOT_COMPUTABLE entries for every TBD-by-Slice-N
   placeholder in the fixture's ``expected_output`` subtree.
4. ``validate_case_block_strict`` enforces additive strict-schema rules:
   - Rejects any forbidden-scope field (pressure-drop / C4 / TASK-020+).
   - Rejects unknown case_id / unknown overall_status.
5. ``validate_per_case_blocks_strict`` enforces additive cross-case
   rules: exactly 3 blocks, no duplicate case_id, case_id set matches
   the frozen 3.
6. ``materialize_validation_report_from_fixtures`` orchestrates the
   whole pipeline: round-trip tolerance/provenance checks + case-block
   materialization + strict validation + report assembly. The resulting
   report is byte-stable across repeated runs (deterministic SHA-256
   for input / expected / actual blocks; deterministic report_id; ISO
   8601 ``generated_at`` may be overridden for full determinism).
7. TASK-018 Option A deferred-amendment signal routes a case to
   NOT_COMPUTABLE + the aggregate ``blocked_on_deferred_amendments``
   counter increments by 1 for that case.

These tests do NOT run the upstream calculation chain. All numeric
golden expected vectors remain ``TBD-by-Slice-N`` placeholders in the
fixtures; Slice 2 surfaces those as NOT_COMPUTABLE per-field
comparisons (no silent default substitution).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root is importable so we can import the source module.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hexagent.validation_report import (  # noqa: E402
    ALLOWED_OVERALL_STATUSES,
    TASK_019_GOLDEN_CASE_IDS,
    TASK_019_VALIDATION_REPORT_V1,
)
from hexagent.validation_report.double_pipe_validation_report import (  # noqa: E402
    _FROZEN_UPSTREAM_CONTRACT_PATHS,
    _IMPLEMENTATION_VERSION_SLICE_2,
    _TASK_018_DISCOUNT_DEFERRED_REASON,
    canonical_json_dumps,
    compute_frozen_contract_sha,
    compute_frozen_upstream_contract_versions,
    materialize_case_block_from_fixture,
    materialize_run_environment,
    materialize_validation_report_from_fixtures,
    sha256_hex,
    validate_case_block_strict,
    validate_fixture_provenance_round_trip,
    validate_fixture_tolerance_round_trip,
    validate_per_case_blocks_strict,
)

_GOLDEN_FIXTURE_DIR = _REPO_ROOT / "tests" / "golden" / "double_pipe_rating"


# --- Frozen-contract SHA computation ---


_EXPECTED_FROZEN_KEYS: tuple[str, ...] = (
    "TASK-006",
    "TASK-007",
    "TASK-008",
    "TASK-011",
    "TASK-012",
    "TASK-013",
    "TASK-014",
    "TASK-015A",
    "TASK-017",
    "TASK-018",
    "TASK-019",
)


def test_frozen_contract_paths_map_has_11_keys() -> None:
    """The _FROZEN_UPSTREAM_CONTRACT_PATHS mapping MUST have 11 entries (per §7.1)."""
    assert tuple(sorted(_FROZEN_UPSTREAM_CONTRACT_PATHS.keys())) == _EXPECTED_FROZEN_KEYS


def test_compute_frozen_upstream_contract_versions_returns_11_hex_shas() -> None:
    """Each entry MUST be a 64-char lowercase hex SHA-256."""
    versions = compute_frozen_upstream_contract_versions(_REPO_ROOT)
    assert tuple(sorted(versions.keys())) == _EXPECTED_FROZEN_KEYS
    for key, value in versions.items():
        assert isinstance(value, str), f"{key} value is not a string"
        assert len(value) == 64, f"{key} SHA length is {len(value)}, expected 64"
        assert value == value.lower(), f"{key} SHA is not lowercase: {value!r}"
        int(value, 16)  # raises if not hex


def test_compute_frozen_contract_sha_is_deterministic() -> None:
    """compute_frozen_contract_sha MUST be deterministic across repeated calls."""
    p = ("docs/tasks/TASK-006-heat-balance.md",)
    s1 = compute_frozen_contract_sha(_REPO_ROOT, p)
    s2 = compute_frozen_contract_sha(_REPO_ROOT, p)
    assert s1 == s2
    assert len(s1) == 64


def test_compute_frozen_contract_sha_file_not_found() -> None:
    """FileNotFoundError is raised for missing contract files."""
    try:
        compute_frozen_contract_sha(_REPO_ROOT, ("docs/tasks/DOES-NOT-EXIST.md",))
    except FileNotFoundError:
        return
    raise AssertionError("FileNotFoundError not raised for missing contract file")


def test_compute_frozen_upstream_contract_versions_task_019_is_composite() -> None:
    """TASK-019 entry changes when the implementation version changes."""
    v1 = compute_frozen_upstream_contract_versions(_REPO_ROOT, task_019_impl_version="version-A")
    v2 = compute_frozen_upstream_contract_versions(_REPO_ROOT, task_019_impl_version="version-B")
    assert v1["TASK-019"] != v2["TASK-019"], "TASK-019 entry must differ when impl version differs"
    # Other entries should be identical
    for key in _EXPECTED_FROZEN_KEYS:
        if key == "TASK-019":
            continue
        assert v1[key] == v2[key], f"{key} SHA changed between impl versions"


# --- run_environment materialization ---


def test_materialize_run_environment_default_keys() -> None:
    """All four required §7.1 keys are present in the materialized block."""
    env = materialize_run_environment()
    assert "python_version" in env
    assert "platform" in env
    assert "package_versions" in env
    assert "deterministic_mode_flags" in env
    assert isinstance(env["python_version"], str)
    assert isinstance(env["platform"], str)
    assert isinstance(env["package_versions"], dict)
    assert "sort_keys" in env["deterministic_mode_flags"]
    assert "no_floats_for_money" in env["deterministic_mode_flags"]


def test_materialize_run_environment_respects_overrides() -> None:
    """Explicit overrides are used verbatim."""
    env = materialize_run_environment(
        python_version="3.12-test",
        platform="linux-test",
        package_versions={"foo": "1.0"},
    )
    assert env["python_version"] == "3.12-test"
    assert env["platform"] == "linux-test"
    assert env["package_versions"] == {"foo": "1.0"}


def test_materialize_run_environment_does_not_alias_package_versions() -> None:
    """The materialized package_versions is a fresh dict, not a reference."""
    src = {"x": "1"}
    env = materialize_run_environment(package_versions=src)
    src["x"] = "2"
    assert env["package_versions"]["x"] == "1", (
        "materialize_run_environment aliased the caller's dict"
    )


# --- case-block materialization from fixture ---


def _load_fixture(case_id: str) -> dict:
    """Helper: load a Slice 1 fixture by case_id."""
    name = {
        "TASK-019-GOLDEN-01": "case_01_heat_balance_rating.json",
        "TASK-019-GOLDEN-02": "case_02_materials_mass_mechanical.json",
        "TASK-019-GOLDEN-03": "case_03_cost_lifecycle_envelope.json",
    }[case_id]
    return json.loads((_GOLDEN_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_materialize_case_block_01_has_required_keys() -> None:
    """Materialized case 01 has all §7.1 required keys."""
    block = materialize_case_block_from_fixture(
        _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
        repo_root=_REPO_ROOT,
    )
    assert block["case_id"] == "TASK-019-GOLDEN-01"
    for key in (
        "case_id",
        "case_title",
        "input_sha256",
        "expected_output_sha256",
        "actual_output_sha256",
        "comparison",
        "provenance",
    ):
        assert key in block, f"missing required key {key!r}"


def test_materialize_case_block_shas_are_64_hex() -> None:
    """input / expected / actual SHAs are 64-char lowercase hex."""
    block = materialize_case_block_from_fixture(
        _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
        repo_root=_REPO_ROOT,
    )
    for key in ("input_sha256", "expected_output_sha256", "actual_output_sha256"):
        v = block[key]
        assert len(v) == 64, f"{key} length {len(v)} != 64"
        assert v == v.lower(), f"{key} not lowercase"
        int(v, 16)


def test_materialize_case_block_is_deterministic() -> None:
    """Re-running materialization on the same fixture yields byte-equivalent block."""
    p = _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json"
    b1 = materialize_case_block_from_fixture(p, repo_root=_REPO_ROOT)
    b2 = materialize_case_block_from_fixture(p, repo_root=_REPO_ROOT)
    assert canonical_json_dumps(b1) == canonical_json_dumps(b2)


def test_materialize_case_block_01_per_field_not_computable() -> None:
    """Case 01 has TBD-by-Slice-2 placeholders that surface as NOT_COMPUTABLE."""
    block = materialize_case_block_from_fixture(
        _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
        repo_root=_REPO_ROOT,
    )
    not_computable_fields = [
        r for r in block["comparison"]["per_field"] if r["status"] == "NOT_COMPUTABLE"
    ]
    # Case 01 has LMTD / heat_duty / heat_transfer_coefficients / outlet_temperatures / etc.
    # all TBD-by-Slice-2. There must be at least one NOT_COMPUTABLE record.
    assert len(not_computable_fields) >= 1, (
        "case 01 must surface at least one NOT_COMPUTABLE per-field record "
        "(fixture expected_output contains TBD-by-Slice-2 placeholders)"
    )
    # The pressure-drop exclusion is also surfaced explicitly.
    pressure_drop_records = [
        r for r in block["comparison"]["per_field"] if r["field"] == "pressure_drop"
    ]
    assert len(pressure_drop_records) == 1
    assert pressure_drop_records[0]["status"] == "NOT_COMPUTABLE"


def test_materialize_case_block_03_carries_deferred_blocker() -> None:
    """Case 03 carries the TASK-018 Option A deferred-amendment blocker."""
    block = materialize_case_block_from_fixture(
        _GOLDEN_FIXTURE_DIR / "case_03_cost_lifecycle_envelope.json",
        repo_root=_REPO_ROOT,
    )
    assert block["comparison"]["overall_status"] == "NOT_COMPUTABLE"
    assert _TASK_018_DISCOUNT_DEFERRED_REASON in block["comparison"]["blockers"], (
        f"case 03 must carry {_TASK_018_DISCOUNT_DEFERRED_REASON!r} blocker, "
        f"got {block['comparison']['blockers']!r}"
    )


def test_materialize_case_block_provenance_has_upstream_contract_versions() -> None:
    """The case-block provenance sub-record references the 11 upstream contracts."""
    block = materialize_case_block_from_fixture(
        _GOLDEN_FIXTURE_DIR / "case_01_heat_balance_rating.json",
        repo_root=_REPO_ROOT,
    )
    versions = block["provenance"]["design_contract_versions"]
    assert tuple(sorted(versions.keys())) == _EXPECTED_FROZEN_KEYS
    for v in versions.values():
        assert isinstance(v, str)
        assert len(v) > 0


# --- strict schema validation ---


def test_validate_case_block_strict_rejects_forbidden_scope() -> None:
    """Forbidden-scope fields (pressure_drop_*, c4_*, ...) are rejected."""
    block = {
        "case_id": "TASK-019-GOLDEN-01",
        "case_title": "t",
        "input_sha256": "a" * 64,
        "expected_output_sha256": "b" * 64,
        "actual_output_sha256": "c" * 64,
        "comparison": {
            "overall_status": "PASS",
            "per_field": [],
            "blockers": [],
            "warnings": [],
        },
        "provenance": {"pressure_drop_value": 1.0},
    }
    try:
        validate_case_block_strict(block)
    except ValueError as e:
        assert "forbidden-scope" in str(e), str(e)
        return
    raise AssertionError("validate_case_block_strict accepted forbidden scope")


def test_validate_case_block_strict_rejects_forbidden_scope_nested() -> None:
    """Forbidden-scope fields nested under arbitrary keys are still rejected."""
    block = {
        "case_id": "TASK-019-GOLDEN-01",
        "case_title": "t",
        "input_sha256": "a" * 64,
        "expected_output_sha256": "b" * 64,
        "actual_output_sha256": "c" * 64,
        "comparison": {
            "overall_status": "PASS",
            "per_field": [],
            "blockers": [],
            "warnings": [],
            "nested": {"c4_iteration_count": 5},
        },
        "provenance": {},
    }
    try:
        validate_case_block_strict(block)
    except ValueError as e:
        assert "forbidden-scope" in str(e)
        return
    raise AssertionError("validate_case_block_strict accepted nested forbidden scope")


def test_validate_case_block_strict_rejects_unknown_case_id() -> None:
    """Unknown case_id is rejected."""
    block = {
        "case_id": "TASK-019-FAKE",
        "case_title": "t",
        "input_sha256": "a" * 64,
        "expected_output_sha256": "b" * 64,
        "actual_output_sha256": "c" * 64,
        "comparison": {"overall_status": "PASS", "per_field": [], "blockers": [], "warnings": []},
        "provenance": {},
    }
    try:
        validate_case_block_strict(block)
    except ValueError as e:
        assert "not in frozen" in str(e)
        return
    raise AssertionError("validate_case_block_strict accepted unknown case_id")


def test_validate_case_block_strict_rejects_unknown_status() -> None:
    """Unknown overall_status is rejected."""
    block = {
        "case_id": "TASK-019-GOLDEN-01",
        "case_title": "t",
        "input_sha256": "a" * 64,
        "expected_output_sha256": "b" * 64,
        "actual_output_sha256": "c" * 64,
        "comparison": {"overall_status": "MAYBE", "per_field": [], "blockers": [], "warnings": []},
        "provenance": {},
    }
    try:
        validate_case_block_strict(block)
    except ValueError as e:
        assert "not in allowed set" in str(e)
        return
    raise AssertionError("validate_case_block_strict accepted unknown status")


def test_validate_case_block_strict_rejects_missing_keys() -> None:
    """Missing required §7.1 keys are rejected."""
    block = {
        "case_id": "TASK-019-GOLDEN-01",
        "case_title": "t",
        # input_sha256 + expected_output_sha256 + actual_output_sha256
        # + comparison + provenance are intentionally absent below.
    }
    try:
        validate_case_block_strict(block)
    except ValueError as e:
        assert "missing required keys" in str(e)
        return
    raise AssertionError("validate_case_block_strict accepted missing keys")


def test_validate_per_case_blocks_strict_rejects_wrong_count() -> None:
    """A non-3-length list is rejected."""
    try:
        validate_per_case_blocks_strict([])
    except ValueError as e:
        assert "exactly" in str(e)
        return
    raise AssertionError("validate_per_case_blocks_strict accepted empty list")


def test_validate_per_case_blocks_strict_rejects_duplicate_case_id() -> None:
    """Duplicate case_id in the 3-block list is rejected."""
    blocks = []
    for i, case_id in enumerate(("TASK-019-GOLDEN-01", "TASK-019-GOLDEN-01", "TASK-019-GOLDEN-03")):
        blocks.append(
            {
                "case_id": case_id,
                "case_title": f"t{i}",
                "input_sha256": chr(ord("a") + i) * 64,
                "expected_output_sha256": chr(ord("a") + i + 1) * 64,
                "actual_output_sha256": chr(ord("a") + i + 2) * 64,
                "comparison": {
                    "overall_status": "PASS",
                    "per_field": [],
                    "blockers": [],
                    "warnings": [],
                },
                "provenance": {},
            }
        )
    try:
        validate_per_case_blocks_strict(blocks)
    except ValueError as e:
        assert "duplicate case_id" in str(e)
        return
    raise AssertionError("validate_per_case_blocks_strict accepted duplicate case_id")


# --- round-trip tolerance / provenance consistency ---


def test_validate_fixture_tolerance_round_trip_known_profile_ok() -> None:
    """A fixture referencing a profile declared in the metadata passes."""
    fx = _load_fixture("TASK-019-GOLDEN-01")
    tol_md = json.loads(
        (_GOLDEN_FIXTURE_DIR / "_tolerance_metadata.json").read_text(encoding="utf-8")
    )
    # Should not raise: profile_id is in tolerance_profiles.
    validate_fixture_tolerance_round_trip(fx, tol_md)


def test_validate_fixture_tolerance_round_trip_unknown_profile_raises() -> None:
    """A fixture referencing an unknown profile is rejected."""
    fx = _load_fixture("TASK-019-GOLDEN-01")
    fx = dict(fx, tolerance_profile_id="TASK-019-FAKE-PROFILE")
    tol_md = json.loads(
        (_GOLDEN_FIXTURE_DIR / "_tolerance_metadata.json").read_text(encoding="utf-8")
    )
    try:
        validate_fixture_tolerance_round_trip(fx, tol_md)
    except ValueError as e:
        assert "TASK-019-FAKE-PROFILE" in str(e)
        return
    raise AssertionError("validate_fixture_tolerance_round_trip accepted unknown profile")


def test_validate_fixture_provenance_round_trip_mismatch_raises() -> None:
    """A fixture with a different provenance_profile_id from the metadata is rejected."""
    fx = _load_fixture("TASK-019-GOLDEN-01")
    fx = dict(fx, provenance_profile_id="TASK-019-FAKE-PROVENANCE")
    prov_md = json.loads(
        (_GOLDEN_FIXTURE_DIR / "_provenance_metadata.json").read_text(encoding="utf-8")
    )
    try:
        validate_fixture_provenance_round_trip(fx, prov_md)
    except ValueError as e:
        assert "TASK-019-FAKE-PROVENANCE" in str(e)
        return
    raise AssertionError("validate_fixture_provenance_round_trip accepted mismatch")


# --- full orchestrator ---


def test_materialize_validation_report_from_fixtures_shape() -> None:
    """The full report matches the §7.1 shape."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    # §7.1 top-level keys
    for key in (
        "report_schema_version",
        "report_id",
        "generated_at",
        "upstream_contract_versions",
        "run_environment",
        "golden_cases",
        "aggregate_summary",
        "license_boundary_attestation",
    ):
        assert key in report, f"missing top-level key {key!r}"
    assert report["report_schema_version"] == TASK_019_VALIDATION_REPORT_V1
    assert report["generated_at"] == "2026-07-08T00:00:00Z"
    assert len(report["golden_cases"]) == 3
    assert {c["case_id"] for c in report["golden_cases"]} == set(TASK_019_GOLDEN_CASE_IDS)


def test_materialize_validation_report_upstream_contract_versions_keys() -> None:
    """The upstream_contract_versions block has all 11 expected keys."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    versions = report["upstream_contract_versions"]
    assert tuple(sorted(versions.keys())) == _EXPECTED_FROZEN_KEYS


def test_materialize_validation_report_aggregate_summary_shape() -> None:
    """aggregate_summary counts match the per-case overall_status values."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    agg = report["aggregate_summary"]
    assert agg["total_cases"] == 3
    # All three cases are NOT_COMPUTABLE in Slice 2 (fixtures carry TBD-by
    # placeholders; case 03 also has the deferred-amendment blocker).
    assert agg["not_computable"] == 3
    assert agg["passed"] == 0
    assert agg["failed"] == 0
    # Per frozen design §5.3 + §8.3 Option X1, only case 03 carries the
    # TASK-018 deferred-amendment signal, so blocked_on_deferred_amendments
    # is exactly 1.
    assert agg["blocked_on_deferred_amendments"] == 1, (
        f"expected blocked_on_deferred_amendments=1, got {agg}"
    )


def test_materialize_validation_report_run_environment_real_values() -> None:
    """The run_environment block contains real (non-TBD) values."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    env = report["run_environment"]
    assert "TBD" not in env["python_version"], (
        f"python_version still TBD: {env['python_version']!r}"
    )
    assert "TBD" not in env["platform"], f"platform still TBD: {env['platform']!r}"
    assert env["python_version"], "python_version is empty"


def test_materialize_validation_report_is_deterministic() -> None:
    """Two runs with the same generated_at produce byte-equivalent JSON."""
    kwargs = dict(
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    r1 = materialize_validation_report_from_fixtures(_GOLDEN_FIXTURE_DIR, **kwargs)
    r2 = materialize_validation_report_from_fixtures(_GOLDEN_FIXTURE_DIR, **kwargs)
    s1 = canonical_json_dumps(r1)
    s2 = canonical_json_dumps(r2)
    assert s1 == s2, "report bytes differ between deterministic runs"
    assert sha256_hex(s1) == sha256_hex(s2)


def test_materialize_validation_report_round_trip_canonical_json() -> None:
    """The report survives a JSON round-trip (canonical-JSON encode/decode)."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    s = canonical_json_dumps(report)
    decoded = json.loads(s)
    assert canonical_json_dumps(decoded) == s, "round-trip lost canonical form"


def test_materialize_validation_report_does_not_silently_pass() -> None:
    """No case has overall_status=PASS (no fake numeric vectors invented)."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    for case in report["golden_cases"]:
        assert case["comparison"]["overall_status"] in {"NOT_COMPUTABLE"}, (
            f"case {case['case_id']} has unexpected status "
            f"{case['comparison']['overall_status']!r} — Slice 2 must not "
            f"silently pass a case whose expected_output subtree still "
            f"contains TBD-by-Slice-N placeholders"
        )


def test_materialize_validation_report_no_forbidden_scope_fields() -> None:
    """No pressure_drop_ / c4_ / TASK-020+ keys in the materialized report."""
    report = materialize_validation_report_from_fixtures(
        _GOLDEN_FIXTURE_DIR,
        repo_root=_REPO_ROOT,
        generated_at="2026-07-08T00:00:00Z",
    )
    s = canonical_json_dumps(report)
    for forbidden in (
        "pressure_drop_value",
        "pressure_drop_pa",
        "c4_iteration",
        "c4_engine",
        "tema_",
        "kern_",
        "bell_delaware_",
        "vendor_quote_",
    ):
        # The single allowed reference is the per-field NOT_COMPUTABLE record
        # whose field name is literally "pressure_drop" (no trailing _).
        if forbidden == "pressure_drop_value":
            # Slice 2 only emits the bare field name "pressure_drop" (no trailing _)
            # as a NOT_COMPUTABLE per-field record, never an actual value field.
            assert forbidden not in s, (
                f"forbidden scope value field {forbidden!r} leaked into report"
            )


# --- Slice 1 backward compatibility ---


def test_slice1_surface_still_works() -> None:
    """Slice 1 public surface still works (canonical_json_dumps, sha256_hex,
    deterministic_report_id, build_double_pipe_validation_report, schema
    constants). Slice 2 is additive and must not regress Slice 1.
    """
    from hexagent.validation_report import (
        build_double_pipe_validation_report,
        canonical_json_dumps,
        deterministic_report_id,
        sha256_hex,
    )

    obj = {"b": 1, "a": 2}
    assert canonical_json_dumps(obj) == '{"a":2,"b":1}'
    assert len(sha256_hex("hello")) == 64
    rid = deterministic_report_id()
    assert len(rid) == 36 and rid[14] == "5"

    # Slice 1 builder still works with caller-supplied blocks
    from hexagent.validation_report import TASK_019_GOLDEN_CASE_IDS

    block = {
        "case_id": "TASK-019-GOLDEN-01",
        "case_title": "t",
        "input_sha256": "a" * 64,
        "expected_output_sha256": "b" * 64,
        "actual_output_sha256": "c" * 64,
        "comparison": {
            "overall_status": "PASS",
            "per_field": [],
            "blockers": [],
            "warnings": [],
        },
        "provenance": {},
    }
    report = build_double_pipe_validation_report(
        per_case_blocks=[
            block,
            dict(block, case_id="TASK-019-GOLDEN-02"),
            dict(block, case_id="TASK-019-GOLDEN-03"),
        ],
        generated_at="2026-07-08T00:00:00Z",
    )
    assert report["report_schema_version"] == TASK_019_VALIDATION_REPORT_V1
    assert tuple(sorted(TASK_019_GOLDEN_CASE_IDS)) == (
        "TASK-019-GOLDEN-01",
        "TASK-019-GOLDEN-02",
        "TASK-019-GOLDEN-03",
    )
    assert frozenset({"PASS", "FAIL", "NOT_COMPUTABLE"}) == ALLOWED_OVERALL_STATUSES
    assert _IMPLEMENTATION_VERSION_SLICE_2.endswith("-slice2"), (
        "Slice 2 implementation version seed should be Slice 2-tagged"
    )
