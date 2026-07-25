"""§A10 — Valid-result identity tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a10_task025_supported_identity_surfaces() -> None:
    """§10 — the eight identity surface entry points exist."""
    fns = [
        ts.internal_flow_authority_length_hash,
        ts.heat_transfer_authority_length_hash,
        ts.layout_hash_passthrough,
        ts.hydraulic_authority_hash,
        ts.request_hash,
        ts.result_hash,
        ts.result_id,
        ts.blocked_result_hash,
    ]
    for fn in fns:
        assert callable(fn)


def test_a10_result_id_uuid_v5_format() -> None:
    rid = ts.result_id("a" * 64)
    assert len(rid) == 36
    # UUIDv5 starts with version "5" in canonical form.
    assert rid[14] == "5"
    # Same hash → same UUID.
    assert rid == ts.result_id("a" * 64)
    assert ts.result_id("b" * 64) != rid


def test_a10_layout_hash_passthrough_byte_for_byte() -> None:
    h = "c" * 64
    assert ts.layout_hash_passthrough(h) == h


def test_a10_layout_hash_passthrough_invalid_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        ts.layout_hash_passthrough("XYZ")


def test_a10_blocked_result_hash_64hex() -> None:
    from hexagent.exchangers.shell_tube.tube_side.provenance import (
        FrozenProvenance,
    )

    blocked = ts.Task025BlockedResult(
        schema_version="task025.blocked-result.v1",
        implementation_software_version="0.1.0",
        resolved_profile_id=None,
        raw_profile_id_projection=ts.FrozenRawProjection(
            projection_kind="token",
            canonical_bytes_hex=ts.TOP_LEVEL_NOT_EXACT_DICT_TOKEN.hex(),
        ),
        raw_request_projection=ts.FrozenRawProjection(
            projection_kind="token",
            canonical_bytes_hex=ts.TOP_LEVEL_NOT_EXACT_DICT_TOKEN.hex(),
        ),
        request_hash=None,
        blocked_result_hash="0" * 64,
        blockers=(),
        warnings=(),
        deferred_capabilities=ts.DEFERRED_CAPABILITIES_V1,
        stage_rank=1,
        task020_identity=None,
        task021_identity=None,
        provenance=FrozenProvenance(
            task_id="TASK-025",
            design_contract_path="docs/tasks/TASK-025-shell-and-tube-tube-side-hydraulic-geometry.md",
            implementation_software_version="0.1.0",
            input_evidence_refs=(),
            upstream_identity_hashes=(),
        ),
    )
    bh = ts.blocked_result_hash(blocked)
    assert len(bh) == 64