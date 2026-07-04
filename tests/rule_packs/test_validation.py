"""End-to-end tests for the rule-pack validator CLI and orchestrator.

These tests use a fixture builder so each test constructs a self-contained
rule-pack on disk, runs the validator, and asserts behavior. We deliberately
do NOT depend on the seed rule-pack at ``rule_packs/internal_seed/`` — those
tests live in ``test_seed_rule_pack.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hexagent.canonical_json import canonical_sha256
from hexagent.rule_packs.validation import validate_rule_pack

REPO = Path(__file__).resolve().parents[2]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def _hash_in_place(obj: dict) -> dict:
    """Recompute and inject canonical_hash for a single object."""
    obj["canonical_hash"] = canonical_sha256(obj)
    return obj


def _make_internal_rule(rid: str, *, missing_license: bool = False) -> dict:
    r: dict = {
        "rule_id": rid,
        "rule_version": "1.0.0",
        "rule_title": f"Internal rule {rid}",
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "jurisdiction": "INTL",
        "standard_family": "INTERNAL",
        "bibliographic_reference": f"internal://test/{rid}",
        "license_evidence": "project_internal_authority",
        "source_evidence": {
            "source_class": "INTERNAL_ENGINEERING_RULE",
            "source_reference": f"internal://test/{rid}",
            "source_title_or_identifier": "Test Internal",
            "source_locator_or_citation": "Chapter 1",
            "source_jurisdiction": "INTL",
            "license_evidence": "project_internal_authority",
        },
        "human_entered_evidence": {
            "author_identity": "eng@test.invalid",
            "author_role": "internal engineer",
            "entry_timestamp_utc": "2026-07-04T09:00:00Z",
            "review": {
                "reviewer_identity": "rev@test.invalid",
                "review_thread_reference": "review_test",
                "review_timestamp_utc": "2026-07-04T09:15:00Z",
            },
        },
        "rule_body": {"statement": "ok"},
        "forbidden_content_marker_check": [],
        "applicability_envelope": {"scope": "test", "units": "dimensionless"},
        "uncertainty": {"type": "structural", "note": "exact"},
        "review_status": "accepted",
        "approval_status": "approved",
        "provenance_edges": [f"{rid}_edge"],
    }
    if missing_license:
        r.pop("license_evidence")
    return _hash_in_place(r)


# All four required VENDOR_PERMISSIONED scope tokens
# (Section 4.2 / Section 16.3a).
_ALL_VENDOR_SCOPE_TOKENS = [
    "repository_storage",
    "repository_redistribution",
    "usage_scope",
    "public_artifact_allowed",
]


def _make_vendor_rule(
    rid: str,
    *,
    permission_scope: list[str] | None = None,
    missing_permission_scope: bool = False,
) -> dict:
    """Build a VENDOR_PERMISSIONED rule with full license boundary fields.

    ``permission_scope`` defaults to all four required tokens (passes).
    ``missing_permission_scope=True`` removes the scope list entirely.
    """
    scope = None if missing_permission_scope else list(permission_scope or _ALL_VENDOR_SCOPE_TOKENS)
    r: dict = {
        "rule_id": rid,
        "rule_version": "1.0.0",
        "rule_title": f"Vendor rule {rid}",
        "source_class": "VENDOR_PERMISSIONED",
        "jurisdiction": "INTL",
        "standard_family": "VENDOR",
        "bibliographic_reference": f"vendor://test/{rid}",
        "license_evidence": "permission-evidence://vendor/test",
        "source_evidence": {
            "source_class": "VENDOR_PERMISSIONED",
            "source_reference": f"vendor://test/{rid}",
            "source_title_or_identifier": "Test Vendor Catalog",
            "source_locator_or_citation": "section 1.0",
            "source_jurisdiction": "INTL",
            "license_evidence": "permission-evidence://vendor/test",
        },
        "human_entered_evidence": {
            "author_identity": "eng@test.invalid",
            "author_role": "vendor liaison",
            "entry_timestamp_utc": "2026-07-04T09:00:00Z",
            "review": {
                "reviewer_identity": "rev@test.invalid",
                "review_thread_reference": "review_vendor_test",
                "review_timestamp_utc": "2026-07-04T09:15:00Z",
            },
            "vendor_permission_evidence": {
                "permission_scope": scope,
                "vendor_identity": "vendor_acme",
                "permission_grant_reference": "grant_001",
            },
        },
        "rule_body": {"statement": "vendor-provided selection rule"},
        "forbidden_content_marker_check": [],
        "applicability_envelope": {"scope": "test", "units": "dimensionless"},
        "uncertainty": {"type": "structural", "note": "exact"},
        "review_status": "accepted",
        "approval_status": "approved",
        "provenance_edges": [f"{rid}_edge"],
    }
    if missing_permission_scope:
        # Remove the entire vendor_permission_evidence block so the
        # permission_scope field is genuinely missing, not just empty.
        r["human_entered_evidence"].pop("vendor_permission_evidence", None)
    return _hash_in_place(r)


def _make_manifest(rule_ids: list[str]) -> dict:
    m = {
        "rule_pack_id": "rp_test",
        "rule_pack_version": "1.0.0",
        "rule_count": len(rule_ids),
        "rules": rule_ids,
        "target_jurisdiction": "INTL",
        "target_standard_family": "INTERNAL",
        "creation_timestamp_utc": "2026-07-04T09:30:00Z",
        "review_id": "review_test",
    }
    return _hash_in_place(m)


def _make_edge(eid: str, to_rule_id: str) -> dict:
    return {
        "edge_id": eid,
        "from_rule_id": "external:INTERNAL_ENGINEERING_RULE:test-handbook",
        "to_rule_id": to_rule_id,
        "relation": "paraphrases",
        "evidence_ref": "internal://test/handbook",
    }


def _build_valid_rule_pack(tmp_path: Path) -> Path:
    rp = tmp_path / "rp"
    _write_json(rp / "manifest.json", _make_manifest(["r1", "r2"]))
    _write_json(rp / "rules" / "r1.json", _make_internal_rule("r1"))
    _write_json(rp / "rules" / "r2.json", _make_internal_rule("r2"))
    _write_json(rp / "provenance" / "r1_edge.json", _make_edge("r1_edge", "r1"))
    _write_json(rp / "provenance" / "r2_edge.json", _make_edge("r2_edge", "r2"))
    return rp


def test_validate_rule_pack_valid_returns_ok(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    report = validate_rule_pack(rp)
    assert report["status"] == "ok"
    assert report["rule_count"] == 2
    assert report["errors"] == []


def test_validate_rule_pack_missing_license_evidence(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    # Overwrite r1.json with a rule that omits license_evidence.
    _write_json(rp / "rules" / "r1.json", _make_internal_rule("r1", missing_license=True))
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    assert any("license_evidence" in p for p in paths)


def test_validate_rule_pack_unknown_source_class(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    bad_rule = _make_internal_rule("r1")
    bad_rule["source_class"] = "FOO_BAR"
    _hash_in_place(bad_rule)
    _write_json(rp / "rules" / "r1.json", bad_rule)
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"


def test_validate_rule_pack_forbidden_marker_rejected(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    bad_rule = _make_internal_rule("r1")
    bad_rule["forbidden_content_marker_check"] = ["standard_full_text"]
    _hash_in_place(bad_rule)
    _write_json(rp / "rules" / "r1.json", bad_rule)
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"


def test_validate_rule_pack_canonical_hash_mismatch(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    bad_rule = _make_internal_rule("r1")
    bad_rule["canonical_hash"] = "f" * 64
    _write_json(rp / "rules" / "r1.json", bad_rule)
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    assert any("canonical_hash" in e["path"] for e in report["errors"])


def test_validate_rule_pack_provenance_cycle(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    # Cycle: r1 -> r2 -> r1 (must also satisfy per-rule edge requirement)
    _write_json(
        rp / "provenance" / "r1_edge.json",
        {
            "edge_id": "r1_edge",
            "from_rule_id": "r2",
            "to_rule_id": "r1",
            "relation": "derived_from",
            "evidence_ref": "e",
        },
    )
    _write_json(
        rp / "provenance" / "r2_edge.json",
        {
            "edge_id": "r2_edge",
            "from_rule_id": "r1",
            "to_rule_id": "r2",
            "relation": "derived_from",
            "evidence_ref": "e",
        },
    )
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    assert any("cycle" in e["message"].lower() for e in report["errors"])


def test_validate_rule_pack_manifest_approves_only_approved(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    # Demote r1 from approved to under_review.
    r1 = _make_internal_rule("r1")
    r1["approval_status"] = "under_review"
    _hash_in_place(r1)
    _write_json(rp / "rules" / "r1.json", r1)
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    assert any("approval_status" in e["message"] for e in report["errors"])


def _cli_env() -> dict[str, str]:
    return {
        "PYTHONPATH": "src",
        "PATH": "/root/hxforge-agent/.venv/bin:/usr/bin:/bin",
    }


def test_cli_returns_zero_on_valid_seed(tmp_path: Path) -> None:
    # Use the in-repo seed rule-pack which we already verified is valid.
    seed = REPO / "rule_packs" / "internal_seed"
    proc = subprocess.run(
        [sys.executable, "-m", "hexagent.rule_packs.validate", str(seed), "--strict"],
        cwd=str(REPO),
        env=_cli_env(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK" in proc.stdout


def test_cli_returns_zero_on_valid_seed_json(tmp_path: Path) -> None:
    seed = REPO / "rule_packs" / "internal_seed"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "hexagent.rule_packs.validate",
            str(seed),
            "--strict",
            "--json",
        ],
        cwd=str(REPO),
        env=_cli_env(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["status"] == "ok"
    assert report["rule_count"] == 2


def test_cli_returns_nonzero_on_invalid_rule_pack(tmp_path: Path) -> None:
    rp = _build_valid_rule_pack(tmp_path)
    # Corrupt r1 rule to be invalid (unknown approval_status).
    bad_rule = _make_internal_rule("r1")
    bad_rule["approval_status"] = "unknown_state"
    _hash_in_place(bad_rule)
    _write_json(rp / "rules" / "r1.json", bad_rule)
    proc = subprocess.run(
        [sys.executable, "-m", "hexagent.rule_packs.validate", str(rp), "--strict"],
        cwd=str(REPO),
        env=_cli_env(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "FAIL" in proc.stdout


# ---------------------------------------------------------------------------
# P0-1: VENDOR_PERMISSIONED scope enforcement is wired into the main
# validator path. These tests go end-to-end through validate_rule_pack so
# helper-only coverage cannot mask the gap.
# ---------------------------------------------------------------------------


def _build_vendor_rule_pack(tmp_path: Path, vendor_rule: dict) -> Path:
    rp = tmp_path / "rp"
    rid = vendor_rule["rule_id"]
    edge_id = f"{rid}_edge"
    _write_json(rp / "manifest.json", _make_manifest([rid]))
    _write_json(rp / "rules" / f"{rid}.json", vendor_rule)
    _write_json(
        rp / "provenance" / f"{edge_id}.json",
        _make_edge(edge_id, rid),
    )
    return rp


def test_validate_rule_pack_vendor_full_scope_passes(tmp_path: Path) -> None:
    """VENDOR rule with all four required scope tokens passes validation."""
    rp = _build_vendor_rule_pack(tmp_path, _make_vendor_rule("vr1"))
    report = validate_rule_pack(rp)
    assert report["status"] == "ok", report["errors"]
    assert report["rule_count"] == 1


def test_validate_rule_pack_vendor_missing_permission_scope_rejected(tmp_path: Path) -> None:
    """VENDOR rule with vendor_permission_evidence absent entirely is rejected."""
    rp = _build_vendor_rule_pack(
        tmp_path,
        _make_vendor_rule("vr1", missing_permission_scope=True),
    )
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    assert any("permission_scope" in p for p in paths), report["errors"]


def test_validate_rule_pack_vendor_missing_repository_storage_rejected(tmp_path: Path) -> None:
    """VENDOR rule missing repository_storage is rejected at validator level."""
    scope = [t for t in _ALL_VENDOR_SCOPE_TOKENS if t != "repository_storage"]
    rp = _build_vendor_rule_pack(tmp_path, _make_vendor_rule("vr1", permission_scope=scope))
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    messages = [e["message"] for e in report["errors"]]
    assert any("permission_scope" in p for p in paths)
    assert any("repository_storage" in m for m in messages)


def test_validate_rule_pack_vendor_missing_repository_redistribution_rejected(
    tmp_path: Path,
) -> None:
    """VENDOR rule missing repository_redistribution is rejected at validator level."""
    scope = [t for t in _ALL_VENDOR_SCOPE_TOKENS if t != "repository_redistribution"]
    rp = _build_vendor_rule_pack(tmp_path, _make_vendor_rule("vr1", permission_scope=scope))
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    messages = [e["message"] for e in report["errors"]]
    assert any("permission_scope" in p for p in paths)
    assert any("repository_redistribution" in m for m in messages)


def test_validate_rule_pack_vendor_missing_usage_scope_rejected(tmp_path: Path) -> None:
    """VENDOR rule missing usage_scope is rejected.

    The validator declares VENDOR_PERMISSIONED rules require
    ``usage_scope`` (Section 4.2 — runtime loading is part of the
    contract), so a VENDOR rule-pack missing this token cannot pass.
    """
    scope = [t for t in _ALL_VENDOR_SCOPE_TOKENS if t != "usage_scope"]
    rp = _build_vendor_rule_pack(tmp_path, _make_vendor_rule("vr1", permission_scope=scope))
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    messages = [e["message"] for e in report["errors"]]
    assert any("permission_scope" in p for p in paths)
    assert any("usage_scope" in m for m in messages)


def test_validate_rule_pack_vendor_missing_public_artifact_allowed_rejected(
    tmp_path: Path,
) -> None:
    """VENDOR rule missing public_artifact_allowed is rejected.

    The validator declares VENDOR_PERMISSIONED rules require
    ``public_artifact_allowed`` (Section 4.2 — public artifact
    emission is part of the contract), so a VENDOR rule-pack missing
    this token cannot pass.
    """
    scope = [t for t in _ALL_VENDOR_SCOPE_TOKENS if t != "public_artifact_allowed"]
    rp = _build_vendor_rule_pack(tmp_path, _make_vendor_rule("vr1", permission_scope=scope))
    report = validate_rule_pack(rp)
    assert report["status"] == "fail"
    paths = [e["path"] for e in report["errors"]]
    messages = [e["message"] for e in report["errors"]]
    assert any("permission_scope" in p for p in paths)
    assert any("public_artifact_allowed" in m for m in messages)


def test_validate_rule_pack_non_vendor_without_vendor_scope_passes(tmp_path: Path) -> None:
    """NON-VENDOR rules do not require vendor_permission_evidence at all.

    The new VENDOR scope enforcement is a no-op for non-VENDOR source
    classes. This guards against regressions where the no-op branch
    starts rejecting rules that have no permission_scope field.
    """
    rp = _build_valid_rule_pack(tmp_path)
    report = validate_rule_pack(rp)
    assert report["status"] == "ok"
    assert report["rule_count"] == 2
