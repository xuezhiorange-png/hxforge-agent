"""General sizing adapter fail-closed contract (no live rating success claimed)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_live_compact_rating as glcr,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    general_sizing_adapter as gsa,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_experimental_sizing_requirement as scer,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    test_general_live_compact_contract as tglcc,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    load_request_from_snapshot_file,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    geometry_summary_from_request,
)
from prototypes.v07_fast_solver_rating_sizing_bridge_r20.r19_full_file_audit import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def test_general_adapter_blocks_missing_full_file() -> None:
    full, sha = tglcc._r21_full_from_r19_codec_fixture()
    request = load_request_from_snapshot_file(ROOT / dict(full.provenance)["snapshot_rel_path"])
    geom = geometry_summary_from_request(request)
    compact = glcr.build_general_live_compact_from_full(
        full,
        trajectory_artifact_path="bogus/missing.json",
        trajectory_file_sha256=sha,
        geometry_summary=geom,
    )
    outcome = gsa.experimental_general_sizing_rating_adapter(
        ROOT,
        compact,
        scer.second_candidate_experimental_sizing_requirement(),
        full_rel_path="bogus/missing.json",
    )
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "GENERAL_FULL_RATING_FILE_MISSING"


def test_general_adapter_requirement_hash_bypass_blocked(tmp_path: Path) -> None:
    full, _sha = tglcc._r21_full_from_r19_codec_fixture()
    full_rel = "tmp-r21b-general-full.json"
    full_path = tmp_path / full_rel
    full_path.write_text(
        json.dumps(full.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sha = file_sha256(full_path)
    request = load_request_from_snapshot_file(ROOT / dict(full.provenance)["snapshot_rel_path"])
    geom = geometry_summary_from_request(request)
    compact = glcr.build_general_live_compact_from_full(
        full,
        trajectory_artifact_path=full_rel,
        trajectory_file_sha256=sha,
        geometry_summary=geom,
    )
    compact = compact.model_copy(
        update={"compact_result_hash": glcr.general_live_compact_rating_hash(compact)}
    )
    req = scer.second_candidate_experimental_sizing_requirement()
    bypass = req.model_copy(update={"required_duty_w": Decimal("999999")})
    outcome = gsa.experimental_general_sizing_rating_adapter(
        tmp_path,
        compact,
        bypass,
        full_rel_path=full_rel,
    )
    assert outcome.status == "BLOCKED"
    assert outcome.blocked_code == "SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH"
