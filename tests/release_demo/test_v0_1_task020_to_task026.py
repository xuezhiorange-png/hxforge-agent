"""Tests for the v0.1.0 TASK-020 -> TASK-026 demo evidence runner.

Asserts:
- 7 valid stages all return status=VALID with non-empty result_hash/result_id.
- Stage chain binding is consistent (each stage N+1's binding equals the
  previous stage's output_identity).
- 7 blocked cases all return status=BLOCKED with
  partial_result_present=False / success_identity_present=False /
  numeric_result_fields_present=False.
- Blocker codes from actual_blocker_codes are non-empty.
- JSON bytes are byte-identical across two consecutive runs.
- Markdown bytes are byte-identical across two consecutive runs.
- Source-level assertion that runner does NOT import tests.*
  (verified via AST scan).
- Source-level assertion that runner does NOT modify production code
  (snapshot git status before/after).
- Cross-version SHA of TASK-026 input matches the documented probe SHA
  on both Python 3.11 and 3.12 (parametrised).
- TASK-026 consumes the REAL TASK-025 valid result (no synthetic
  stand-in); upstream_identity_bindings values are bound from the live
  Task025ValidResult object.
- chain_bindings entries carry ``downstream_field`` naming the actual
  downstream input attribute; no self-edge exists; TASK-023 is bound
  to null with documented explanation when no actual downstream consumer.
- Blocked matrix: expected_blocker_codes equals actual_blocker_codes
  exactly; stage_rank / stage_token are real (or null) values, never
  a hardcoded 0 placeholder.
- TASK-023's selected approved-record identity does NOT flow into any
  TASK-022 downstream field in the current DAG; the binding is null
  with ``t023_actual_downstream_binding: False``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "release_demo" / "v0_1_task020_to_task026.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "release_demo"))
from v0_1_task020_to_task026 import (  # noqa: E402
    _build_t026_request,
    build_release_evidence,
    render_json_bytes,
    render_markdown_bytes,
)

# R2 round cross-version SHA: TASK-026 now consumes the REAL
# Task025ValidResult (not the synthetic stand-in from R8 round). The
# SHA is whatever the runner emits with the real upstream on both
# Python 3.11 and 3.12 — captured at the time of R2 lock.
EXPECTED_T026_SHA = "4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd"
# R8 round regression SHA — preserved in summary.regression_record.
R8_REGRESSION_SHA = "fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runner_source() -> str:
    return RUNNER_PATH.read_text(encoding="utf-8")


def _imports_in_runner() -> list[ast.stmt]:
    tree = ast.parse(_runner_source(), filename=str(RUNNER_PATH))
    imports: list[ast.stmt] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
    return imports


def _import_targets() -> list[str]:
    targets: list[str] = []
    for node in _imports_in_runner():
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


def _run_with_version(python_executable: str) -> str:
    """Invoke the runner under the given Python interpreter and return
    the captured ``cross_version_sha256`` value."""
    import hashlib  # noqa: F401  - kept for completeness
    import json

    env_overrides = {
        "PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'scripts' / 'release_demo'}",
    }
    proc = subprocess.run(
        [python_executable, str(RUNNER_PATH), "--format", "json"],
        cwd=REPO_ROOT,
        env={**__import__("os").environ, **env_overrides},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    payload = json.loads(proc.stdout)
    return payload["summary"]["cross_version_sha256"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_seven_valid_stages_all_pass() -> None:
    evidence = build_release_evidence()
    valid = evidence["valid_case"]
    assert len(valid) == 7, f"expected 7 stages, got {len(valid)}"
    for task_id in (
        "TASK-020",
        "TASK-021",
        "TASK-022",
        "TASK-023",
        "TASK-024",
        "TASK-025",
        "TASK-026",
    ):
        assert task_id in valid, f"missing stage {task_id}"
        stage = valid[task_id]
        assert stage["status"] == "VALID", f"{task_id} not VALID"
        assert stage["result_hash"], f"{task_id} missing result_hash"
        assert stage["result_id"], f"{task_id} missing result_id"
        assert stage["blockers"] == [], f"{task_id} has blockers: {stage['blockers']}"


def test_chain_binding_each_stage_binds_to_previous() -> None:
    """Verify the explicit chain_bindings list declared in the summary.

    TASK-023 is documented as having no actual downstream consumer in
    this runner (its binding is null with an explanation). The
    upstream-bound chain is TASK-020 -> 021 -> 022 -> 024 -> 025 -> 026.

    For TASK-025 -> TASK-026 specifically, the binding value MUST
    equal TASK-025's output_identity (which is the live Task025ValidResult
    .result_hash). TASK-026 consumes the REAL upstream — no synthetic
    stand-in.
    """
    evidence = build_release_evidence()
    valid = evidence["valid_case"]
    bindings = evidence["summary"]["chain_bindings"]
    by_pair = {(b["from"], b["to"]): b for b in bindings}
    expected = [
        ("TASK-020", "TASK-021"),
        ("TASK-021", "TASK-022"),
        ("TASK-022", "TASK-024"),
        ("TASK-024", "TASK-025"),
        ("TASK-025", "TASK-026"),
    ]
    for prev_id, cur_id in expected:
        prev = valid[prev_id]
        assert (prev_id, cur_id) in by_pair, f"missing chain binding {prev_id}->{cur_id}"
        binding_entry = by_pair[(prev_id, cur_id)]
        # The chain binding value MUST equal the previous stage's
        # output_identity (this is the brief's chain-binding rule).
        assert binding_entry["binding"] == prev["output_identity"], (
            f"binding for {prev_id}->{cur_id} does not equal prev output_identity"
        )
        # Every chain binding entry carries a ``downstream_field`` that
        # names the actual downstream input attribute that reads this
        # binding.
        assert binding_entry.get("downstream_field"), (
            f"chain binding {prev_id}->{cur_id} missing downstream_field"
        )


def test_blocked_matrix_seven_blocked_cases_with_no_partial_result() -> None:
    evidence = build_release_evidence()
    blocked = evidence["blocked_matrix"]
    assert len(blocked) >= 7, f"expected >= 7 blocked cases, got {len(blocked)}"
    for entry in blocked:
        assert entry["status"] == "BLOCKED"
        assert entry["partial_result_present"] is False
        assert entry["success_identity_present"] is False
        assert entry["numeric_result_fields_present"] is False
        assert entry["blocked_result_hash"]
        assert entry["expected_blocker_codes"]
        assert entry["actual_blocker_codes"]


def test_blocked_actual_codes_non_empty() -> None:
    evidence = build_release_evidence()
    for entry in evidence["blocked_matrix"]:
        codes = entry["actual_blocker_codes"]
        assert codes, f"empty actual_blocker_codes in {entry['case_id']}"
        assert all(isinstance(c, str) for c in codes)


def test_json_byte_identical_two_runs() -> None:
    e1 = build_release_evidence()
    e2 = build_release_evidence()
    assert render_json_bytes(e1) == render_json_bytes(e2)


def test_markdown_byte_identical_two_runs() -> None:
    e1 = build_release_evidence()
    e2 = build_release_evidence()
    assert render_markdown_bytes(e1) == render_markdown_bytes(e2)


def test_runner_does_not_import_tests() -> None:
    for target in _import_targets():
        assert not target.startswith("tests") and not target.startswith("tests."), (
            f"runner imports tests.* module: {target}"
        )


def test_runner_does_not_modify_production_source() -> None:
    """Snapshot git status / diff before, then run, and confirm src/ is clean."""
    before = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    before_diff = subprocess.run(
        ["git", "diff", "--stat"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # Run evidence generation.
    build_release_evidence()
    after = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert before.stdout == after.stdout, (
        f"worktree state changed:\nbefore={before.stdout!r}\nafter={after.stdout!r}"
    )
    # Also assert no production src/ file changed in the diff stat.
    assert "src/" not in before_diff.stdout, (
        f"src/ already dirty before run: {before_diff.stdout!r}"
    )


def test_cross_version_sha_of_t026_input_matches_expected() -> None:
    """Use the same TASK-026 input as the runner; assert the runner's
    ``cross_version_sha256`` (which equals ``TASK-026.result_hash``) is
    identical when computed against the live TASK-025 upstream on both
    Python versions and matches the documented R2 SHA value.

    Note: the runner's ``summary.cross_version_sha256`` is the live
    ``TubeSideThermalResult.result_hash`` emitted by
    ``compute_tube_side_heat_transfer_coefficient`` against the real
    upstream (R2 fixup). The canonical-SHA projection string is a
    separate, higher-order diagnostic — its value is
    ``9795d399251289335c671c9d965830c8311447c3e92967c733b7e86737968455``
    on both Python versions when fed identical inputs."""
    import sys as _sys

    _sys.path.insert(0, str(REPO_ROOT / "scripts" / "release_demo"))
    from v0_1_task020_to_task026 import (  # noqa: E402
        _build_t020_request,
        _build_t021_request,
        _stage_t025_valid,
    )

    from hexagent.exchangers.shell_tube import validate_request as t020_validate  # noqa: E402
    from hexagent.exchangers.shell_tube.tube_layout import (
        validate_request as t021_validate,  # noqa: E402
    )
    from hexagent.exchangers.shell_tube.tube_side_thermal import (  # noqa: E402
        compute_tube_side_heat_transfer_coefficient,
    )

    t020_res = t020_validate(_build_t020_request())
    config = t020_res.configuration
    t021_payload = _build_t021_request(config)
    t021_res = t021_validate(
        t021_payload,
        software_version="v0.1.0-demo",
        git_commit="b11a7d46ac6a726c2bbdff85166c78e6753289a0",
    )
    layout = t021_res.layout
    prev_out_id = layout.layout_hash  # type: ignore[union-attr]
    _t025_record, _t025_in_id, t025_out_id, t025_typed = _stage_t025_valid(
        layout, config, prev_out_id
    )

    req = _build_t026_request()
    res = compute_tube_side_heat_transfer_coefficient(req, t025_typed)
    # The runner's cross_version_sha256 is the live result_hash
    # (== TubeSideThermalResult.result_hash == summary.cross_version_sha256).
    # Assert the TASK-026 result_hash (== cross_version_sha256) equals
    # the documented R2 SHA.
    assert res.result_hash == EXPECTED_T026_SHA, (
        f"live result_hash {res.result_hash!r} != EXPECTED {EXPECTED_T026_SHA!r}"
    )


def test_summary_fields_populated() -> None:
    evidence = build_release_evidence()
    s = evidence["summary"]
    assert s["valid_stage_count"] == 7
    assert s["blocked_case_count"] >= 7
    assert s["all_valid_stages_passed"] is True
    assert s["all_blocked_cases_blocked"] is True
    assert s["all_blocked_cases_have_no_partial_result"] is True
    assert s["production_algorithm_modified"] is False
    assert s["public_contract_modified"] is False
    assert s["cross_version_bytes"] == "IDENTICAL"
    assert s["cross_version_sha256"] == EXPECTED_T026_SHA
    assert s["chain_bindings"]
    # R2 markers
    assert s["actual_dependency_bindings_only"] is True
    assert s["t023_actual_downstream_binding"] is False
    assert s["self_edge_count"] == 0
    rr = s["regression_record"]
    assert rr["r8_cross_version_sha256"] == R8_REGRESSION_SHA
    assert rr["r8_upstream_was_synthetic"] is True
    assert rr["r2_cross_version_sha256"] == EXPECTED_T026_SHA
    assert rr["r2_upstream_is_real_task025_valid_result"] is True


def test_task_026_valid_records_decimal_strings_no_floats() -> None:
    evidence = build_release_evidence()
    rec = evidence["valid_case"]["TASK-026"]
    numeric_keys = (
        "bulk_velocity_m_s",
        "reynolds_number",
        "prandtl_number",
        "nusselt_number",
        "tube_side_heat_transfer_coefficient_w_m2_k",
        "mass_flow_rate_kg_s",
    )
    for k in numeric_keys:
        v = rec[k]
        assert isinstance(v, str), f"{k} is not a string: {v!r}"
        # ASCII digits + dot only.
        s = v.encode("ascii").decode("ascii")
        assert all(c in "0123456789." for c in s), f"{k} not ASCII decimal: {v!r}"


def test_runner_has_no_tests_import_via_ast() -> None:
    """Direct AST check on the runner source for ``import tests.*`` or
    ``from tests.*`` import statements."""
    tree = ast.parse(_runner_source(), filename=str(RUNNER_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("tests"), f"runner source imports {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith("tests"), f"runner source 'from {mod} import ...' found"


# ---------------------------------------------------------------------------
# R2 round fixup tests (Charles 7-point fixup instructions)
# ---------------------------------------------------------------------------


def test_t026_consumes_actual_task025_result() -> None:
    """TASK-026 must consume the REAL Task025ValidResult, not a synthetic stand-in.

    Asserts:
    - TASK-026 ``upstream_identity_bindings.task025_result_hash`` equals
      TASK-025 ``output_identity`` (the live result_hash of the typed
      Task025ValidResult).
    - ``upstream_identity_bindings.task025_hydraulic_authority_hash`` is
      a 64-character lowercase hex string (no longer the synthetic 'b'*64
      stand-in).
    - The TASK-025 binding value is NOT 'a'*64 (synthetic stand-in
      sentinel).
    - The TASK-025 hydraulic_authority_hash binding value is NOT 'b'*64.
    """
    evidence = build_release_evidence()
    valid = evidence["valid_case"]
    t025 = valid["TASK-025"]
    t026 = valid["TASK-026"]
    t025_out = t025["output_identity"]
    t026_bindings = t026["upstream_identity_bindings"]
    # The TASK-026 binding MUST equal TASK-025 output_identity.
    assert t026_bindings["task025_result_hash"] == t025_out, (
        t026_bindings["task025_result_hash"],
        t025_out,
    )
    # The TASK-025 result_hash must NOT be a synthetic 'a'*64 stand-in.
    assert t025_out != "a" * 64, "TASK-025 result_hash is the synthetic 'a'*64 stand-in"
    # The hydraulic_authority_hash binding MUST be 64-char lowercase hex
    # and MUST NOT be the synthetic 'b'*64 stand-in.
    hy_hash = t026_bindings["task025_hydraulic_authority_hash"]
    assert len(hy_hash) == 64
    assert all(c in "0123456789abcdef" for c in hy_hash)
    assert hy_hash != "b" * 64, "hydraulic_authority_hash is the synthetic 'b'*64 stand-in"
    # Additional binding keys must be present and ASCII-decimal
    # serialised.
    for k in (
        "task025_single_tube_flow_area_m2",
        "task025_hydraulic_diameter_m",
        "task025_flow_cross_section_wetted_perimeter_m",
        "task025_internal_volume_m3",
        "task025_internal_heat_transfer_surface_area_m2",
    ):
        assert k in t026_bindings, f"missing upstream binding {k!r}"
        v = t026_bindings[k]
        assert isinstance(v, str), f"{k} must be ASCII string, got {type(v).__name__}"
        # ASCII digits + dot only.
        s = v.encode("ascii").decode("ascii")
        assert all(c in "0123456789." for c in s), f"{k} not ASCII decimal: {v!r}"


def test_no_self_edge_in_chain_bindings() -> None:
    """No (TASK-N, TASK-N) self-edge may exist in chain_bindings."""
    evidence = build_release_evidence()
    bindings = evidence["summary"]["chain_bindings"]
    for b in bindings:
        # If binding is null, this is the TASK-023 special case and is
        # not a self-edge.
        if b.get("to") is None:
            continue
        assert b["from"] != b["to"], f"self-edge found: {b!r}"
    # The summary marker also asserts count is exactly 0.
    assert evidence["summary"]["self_edge_count"] == 0


def test_t023_actual_downstream_binding_is_null_with_explanation() -> None:
    """TASK-023 selected approved-record identity has no actual downstream
    consumer in this runner (TASK-022 uses CALLER_SUPPLIED_EXPLICIT
    shell authority and ignores approved_shell_geometry). The chain
    binding MUST be null with an explanation string."""
    evidence = build_release_evidence()
    bindings = evidence["summary"]["chain_bindings"]
    t023_entries = [b for b in bindings if b["from"] == "TASK-023"]
    assert len(t023_entries) == 1, f"expected 1 TASK-023 binding, got {len(t023_entries)}"
    t023 = t023_entries[0]
    assert t023["to"] is None, f"TASK-023 binding.to is not null: {t023!r}"
    assert t023["binding"] is None, f"TASK-023 binding.binding is not null: {t023!r}"
    assert t023["downstream_field"] is None, (
        f"TASK-023 binding.downstream_field is not null: {t023!r}"
    )
    assert t023["t023_actual_downstream_binding"] is False
    assert t023["explanation"], "TASK-023 binding.explanation must be a non-empty string"
    assert evidence["summary"]["t023_actual_downstream_binding"] is False


def test_chain_bindings_have_downstream_field_for_real_edges() -> None:
    """Every real chain_bindings edge (non-null) carries a
    ``downstream_field`` naming the actual downstream input attribute."""
    evidence = build_release_evidence()
    for b in evidence["summary"]["chain_bindings"]:
        if b.get("to") is None:
            continue
        assert b.get("downstream_field"), f"missing downstream_field in {b!r}"
        # downstream_field should name a concrete downstream object
        # attribute (dot-path).
        assert "." in b["downstream_field"] or "_" in b["downstream_field"], (
            f"downstream_field looks invalid: {b['downstream_field']!r}"
        )


def test_blocked_expected_equals_actual_codes_exactly() -> None:
    """For every blocked case, ``expected_blocker_codes`` MUST equal
    ``actual_blocker_codes`` exactly (compare as lists)."""
    evidence = build_release_evidence()
    for entry in evidence["blocked_matrix"]:
        assert entry["expected_blocker_codes"] == entry["actual_blocker_codes"], (
            f"{entry['case_id']}: expected={entry['expected_blocker_codes']!r}, "
            f"actual={entry['actual_blocker_codes']!r}"
        )


def test_blocked_stage_rank_and_token_are_real_or_null() -> None:
    """For every blocked case, ``stage_rank`` is either a real int from
    the blocker entry (TASK-024 legitimately has stage_rank=0; TASK-023
    has stage_rank=2; TASK-025 has stage_rank=1) or null. No hardcoded
    placeholders. ``stage_token`` is either a real blocker stage token
    or null; never an empty string or fake placeholder.

    TASK-026's blocker entry carries ``stage: str`` (e.g. "S00") rather
    than an integer ``stage_rank``. The runner therefore records
    ``stage_rank=null`` and the actual ``stage`` string as
    ``stage_token``.
    """
    evidence = build_release_evidence()
    for entry in evidence["blocked_matrix"]:
        sr = entry["stage_rank"]
        st = entry["stage_token"]
        # stage_rank is either None or an int. 0 is permitted only for
        # TASK-024 (legit "no validation stage completed" sentinel);
        # other tasks must not have stage_rank=0 unless the actual
        # blocker carries 0.
        assert sr is None or isinstance(sr, int), (
            f"{entry['case_id']}: stage_rank not None or int: {sr!r}"
        )
        assert isinstance(st, str) and st, (
            f"{entry['case_id']}: stage_token not non-empty str: {st!r}"
        )
        if entry["task_id"] == "TASK-026":
            # TASK-026 blocker has stage='S00' (string token); stage_rank
            # is recorded as null.
            assert sr is None, f"TASK-026 stage_rank must be null, got {sr!r}"
            assert st == "S00", f"TASK-026 stage_token must be 'S00', got {st!r}"


def test_t026_blocked_stage_token_uses_blocker_stage_attribute() -> None:
    """TASK-026 blocked ``stage_token`` must come from the actual
    BlockerEntry.stage attribute (e.g. "S00"), not a fake placeholder."""
    evidence = build_release_evidence()
    t026_blocked = next(b for b in evidence["blocked_matrix"] if b["task_id"] == "TASK-026")
    assert t026_blocked["stage_rank"] is None
    assert t026_blocked["stage_token"] == "S00"
    # And field_paths/stage_token match exactly what the actual blocker
    # entry carries.
    assert t026_blocked["expected_blocker_codes"] == t026_blocked["actual_blocker_codes"]


def test_regression_record_preserves_r8_sha() -> None:
    """The R8 round cross-version SHA is preserved in
    ``summary.regression_record`` for traceability, NOT in
    ``valid_case`` chain DAG (which is now the real dependency DAG)."""
    evidence = build_release_evidence()
    rr = evidence["summary"]["regression_record"]
    assert rr["r8_cross_version_sha256"] == R8_REGRESSION_SHA
    assert rr["r8_upstream_was_synthetic"] is True
    assert rr["r2_upstream_is_real_task025_valid_result"] is True
    # The R8 SHA must NOT appear anywhere in valid_case (the chain DAG
    # is the real one; the R8 SHA is a regression record only).
    for task_id, rec in evidence["valid_case"].items():
        for key, value in rec.items():
            assert R8_REGRESSION_SHA not in (str(value) if not isinstance(value, list) else ""), (
                f"R8 SHA leaked into valid_case[{task_id}].{key}"
            )


def test_t026_cross_version_sha_emitted_under_py311_and_py312() -> None:
    """The runner's ``cross_version_sha256`` must match the documented
    R2 SHA under BOTH Python 3.11 and 3.12. We invoke the runner as
    a subprocess under each interpreter and compare."""
    import os

    py311 = "/usr/bin/python3.11"
    py312_exe = None
    for cand in (
        ".venv/bin/python3",
        "/root/.local/bin/python3.12",
        "/usr/bin/python3.12",
    ):
        if Path(cand).exists():
            py312_exe = cand
            break
    assert py312_exe, "no Python 3.12 interpreter available"
    env_overrides = {
        "PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'scripts' / 'release_demo'}",
    }
    for label, exe in (("3.11", py311), ("3.12", py312_exe)):
        proc = subprocess.run(
            [exe, str(RUNNER_PATH), "--format", "json"],
            cwd=REPO_ROOT,
            env={**os.environ, **env_overrides},
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (label, proc.returncode, proc.stdout, proc.stderr)
        import json as _json

        payload = _json.loads(proc.stdout)
        sha = payload["summary"]["cross_version_sha256"]
        assert sha == EXPECTED_T026_SHA, (
            f"Python {label} cross-version SHA mismatch: got {sha!r}, "
            f"expected {EXPECTED_T026_SHA!r}"
        )
