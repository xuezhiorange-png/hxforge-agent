"""TASK-025 9-stage scheduler and blocked finalization.

# mypy: ignore-errors

§12 — Nine-stage scheduler.
§9.4 — Participation invariants (stage 5).
§6.3 / §6.4 — Blocked result finalization.
"""

from __future__ import annotations

import decimal
from decimal import Decimal
from typing import Any, Final, cast

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ConstructionFamily,
    EquipmentFamily,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
)
from hexagent.exchangers.shell_tube.tube_side.blocked_result import (
    Task025BlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side.blocker_registry import (
    BlockerCode,
    Task025BlockerEntry,
    collapse_unregistered_codes,
    emit_blocker,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.tube_side.hash_dag import (
    blocked_result_hash,
    heat_transfer_authority_length_hash,
    hydraulic_authority_hash,
    internal_flow_authority_length_hash,
    layout_hash_passthrough,
    request_hash,
    result_hash,
    result_id,
)
from hexagent.exchangers.shell_tube.tube_side.hydraulic_geometry import (
    compute_hydraulic_geometry,
)
from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
    HeatTransferLengthAuthority,
    InternalFlowLengthAuthority,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    FlowPathMode,
    HydraulicAuthorityMode,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    DESIGN_CONTRACT_PATH,
    IMPLEMENTATION_SOFTWARE_VERSION,
    TASK_ID,
    FrozenIdentity,
    FrozenProvenance,
    FrozenRawProjection,
)
from hexagent.exchangers.shell_tube.tube_side.raw_projection import (
    RawProjectionError,
    project_raw_dict,
    project_raw_value,
)
from hexagent.exchangers.shell_tube.tube_side.request import (
    SUPPORTED_PROFILE_IDS,
    TASK025_REQUEST_FIELDS,
    Task025Request,
)
from hexagent.exchangers.shell_tube.tube_side.valid_result import (
    DEFERRED_CAPABILITIES_V1,
    Task025ValidResult,
)

# §12 — STAGE_RANKS (9 stages).
STAGE_RANKS: Final[int] = 9


# §4.2 — top-level token constants.
TOP_LEVEL_NOT_EXACT_DICT_TOKEN: Final[bytes] = b"task025.top-level-not-exact-dict.v1"
RAW_PROFILE_ID_MISSING_TOKEN: Final[bytes] = b"task025.profile-id-missing.v1"
RAW_PROFILE_ID_INVALID_TYPE_TOKEN: Final[bytes] = b"task025.profile-id-invalid-type.v1"


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _hash_raw_payload(payload: bytes) -> str:
    return sha256_hex_from_framed_bytes(payload)


def _raw_projection(kind: str, payload: bytes) -> FrozenRawProjection:
    return FrozenRawProjection(
        projection_kind=kind,
        canonical_bytes_hex=payload.hex(),
    )


def _build_provenance(
    evidence_refs: tuple[str, ...],
    upstream_identity_hashes: tuple[str, ...],
) -> FrozenProvenance:
    return FrozenProvenance(
        task_id=TASK_ID,
        design_contract_path=DESIGN_CONTRACT_PATH,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=tuple(evidence_refs),
        upstream_identity_hashes=tuple(upstream_identity_hashes),
    )


def _build_task020_identity(config: Any) -> FrozenIdentity:
    return FrozenIdentity(
        identity_type="task020.configuration.v1",
        identity_id=config.configuration_id,
        identity_hash=config.configuration_hash,
    )


def _build_task021_identity(layout: TubeLayout) -> FrozenIdentity:
    return FrozenIdentity(
        identity_type="task021.tube-layout.v1",
        identity_id=layout.layout_id,
        identity_hash=layout.layout_hash,
    )


# -----------------------------------------------------------------------
# §4.2 — Non-dict branch.
# -----------------------------------------------------------------------


def _build_non_dict_blocked(evidence_refs: tuple[str, ...] = ()) -> Task025BlockedResult:
    raw_request = _raw_projection("token", TOP_LEVEL_NOT_EXACT_DICT_TOKEN)
    raw_profile = _raw_projection("token", TOP_LEVEL_NOT_EXACT_DICT_TOKEN)
    blockers = (
        emit_blocker(
            BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
            "raw_input",
            "raw_input_not_dict",
            (),
        ),
    )
    return Task025BlockedResult(
        schema_version="task025.blocked-result.v1",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        resolved_profile_id=None,
        raw_profile_id_projection=raw_profile,
        raw_request_projection=raw_request,
        request_hash=None,
        blocked_result_hash=blocked_result_hash(
            Task025BlockedResult(
                schema_version="task025.blocked-result.v1",
                implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
                resolved_profile_id=None,
                raw_profile_id_projection=raw_profile,
                raw_request_projection=raw_request,
                request_hash=None,
                blocked_result_hash="0" * 64,
                blockers=blockers,
                warnings=(),
                deferred_capabilities=DEFERRED_CAPABILITIES_V1,
                stage_rank=1,
                task020_identity=None,
                task021_identity=None,
                provenance=_build_provenance(evidence_refs, ()),
            )
        ),
        blockers=blockers,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        stage_rank=1,
        task020_identity=None,
        task021_identity=None,
        provenance=_build_provenance(evidence_refs, ()),
    )


def _build_raw_projection_blocked() -> Task025BlockedResult:
    token = b"task025.raw-projection-unsupported.v1"
    raw_request = _raw_projection("raw_request_projection_unsupported", token)
    raw_profile = _raw_projection("raw_profile_projection_unsupported", token)
    blockers = [
        emit_blocker(
            BlockerCode.BL_019_RAW_PROJECTION_UNSUPPORTED,
            "raw_input",
            "raw_projection_unsupported",
            (),
        )
    ]
    return _finalize_blocked(
        raw_request,
        raw_profile,
        None,
        request_hash_value=None,
        blockers=blockers,
        stage_rank=1,
    )


def _build_evidence_refs_blocked(
    message_key: str = "evidence_refs_not_frozen_container",
) -> Task025BlockedResult:
    """Round-3/4 — public surface for evidence_refs contract violations.

    Always reports a stable ``BL_003_BLOCKED_INPUT_REJECTED`` blocker so
    consumers can match on the public contract regardless of whether the
    violation was detected before or after the raw projection boundary.

    Round-4 §8.4 — the message key distinguishes the failure mode
    (container / entry-type / entry-empty / surrogate / UTF-8) so the
    public surface is fully introspectable.
    """
    token = b"task025.raw-projection-unsupported.v1"
    raw_request = _raw_projection("raw_request_projection_unsupported", token)
    raw_profile = _raw_projection("raw_profile_projection_unsupported", token)
    blockers = [
        emit_blocker(
            BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
            "raw_input.evidence_refs",
            message_key,
            (),
        )
    ]
    return _finalize_blocked(
        raw_request,
        raw_profile,
        None,
        request_hash_value=None,
        blockers=blockers,
        stage_rank=1,
    )


def schedule(raw_input: Any) -> Task025ValidResult | Task025BlockedResult:
    """§4.2 — Top-level entry: dispatch non-dict / dict branches."""
    if type(raw_input) is not dict:
        return _build_non_dict_blocked()
    try:
        return _schedule_dict(raw_input)
    except RawProjectionError:
        return _build_raw_projection_blocked()


def _schedule_dict(raw_input: dict[str, Any]) -> Task025ValidResult | Task025BlockedResult:
    # §4.2 — raw_request_projection + raw_profile_id_projection must always exist.
    # Round-5 §4 — safe top-level key scan. Any membership, indexing, or
    # ``.get()`` on ``raw_input`` before this point would invoke the
    # caller-controlled ``__hash__`` / ``__eq__`` on untrusted keys, which
    # would leak the malicious exception before the raw projection has
    # a chance to reject the input. We iterate via ``dict.items(...)``
    # only and check ``type(key) is str`` before any string equality.
    try:
        evidence_refs_value, evidence_refs_present = _scan_top_level_request(
            cast(dict[object, object], raw_input)
        )
    except _TopLevelKeyScanError:
        return _build_raw_projection_blocked()
    # Round-4 §8.2 — evidence_refs, when present, must pass the full
    # v1 contract: exact tuple of non-empty, non-surrogate, UTF-8
    # encodable str. We validate the entire tuple before the raw
    # projection so any violation produces a stable
    # ``BL_003_BLOCKED_INPUT_REJECTED`` Stage 1 blocked result with a
    # precise message key.
    prevalidated_evidence_refs: tuple[str, ...] | None = None
    if evidence_refs_present:
        try:
            prevalidated_evidence_refs = _validate_evidence_refs(evidence_refs_value)
        except _EvidenceRefsError as exc:
            return _build_evidence_refs_blocked(exc.message_key)
    try:
        raw_request_bytes = project_raw_dict(raw_input)
    except RawProjectionError:
        return _build_raw_projection_blocked()
    raw_request_projection = _raw_projection("raw_request_dict", raw_request_bytes)

    # raw_profile_id_projection from the dict.
    if "profile_id" not in raw_input:
        raw_profile_bytes = RAW_PROFILE_ID_MISSING_TOKEN
    else:
        raw_profile = raw_input["profile_id"]
        if not isinstance(raw_profile, str) or not raw_profile:
            raw_profile_bytes = RAW_PROFILE_ID_INVALID_TYPE_TOKEN
        else:
            raw_profile_bytes = project_raw_value(raw_profile)
    raw_profile_id_projection = _raw_projection("raw_profile_id", raw_profile_bytes)

    # Resolved profile_id is None for unsupported / missing / non-string.
    raw_profile_value = raw_input.get("profile_id") if "profile_id" in raw_input else None
    if isinstance(raw_profile_value, str) and raw_profile_value in SUPPORTED_PROFILE_IDS:
        resolved_profile_id: str | None = raw_profile_value
    else:
        resolved_profile_id = None

    # §12 — Stage 1 — top-level validation: schema, profile, software-version.
    stage1_blockers: list[Task025BlockerEntry] = []

    schema_version = raw_input.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_029_UNSUPPORTED_SCHEMA,
                "raw_input.schema_version",
                "schema_version_missing_or_invalid",
                (),
            )
        )
    elif schema_version != "task025.request.v1":
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_029_UNSUPPORTED_SCHEMA,
                "raw_input.schema_version",
                "schema_version_unsupported",
                (),
            )
        )

    actual_fields = frozenset(raw_input)
    expected_fields = frozenset(TASK025_REQUEST_FIELDS)
    missing_fields = expected_fields - actual_fields
    unknown_fields = actual_fields - expected_fields
    if unknown_fields:
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
                "raw_input",
                "raw_input_unknown_field",
                tuple(sorted(unknown_fields)),
            )
        )
    if missing_fields:
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
                "raw_input",
                "raw_input_missing_field",
                tuple(f"missing_field:{field_name}" for field_name in sorted(missing_fields)),
            )
        )

    if not isinstance(resolved_profile_id, str):
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_028_UNSUPPORTED_PROFILE,
                "raw_input.profile_id",
                "profile_id_missing_or_unsupported",
                (),
            )
        )

    # Round-3 §7 — evidence_refs must be an exact tuple of non-empty str.
    # v1 contract rejects list / byte / str-subclass at Stage 1 so the raw
    # projection boundary never sees the malformed value.
    raw_evidence_refs_value: Any = raw_input.get("evidence_refs")
    if type(raw_evidence_refs_value) is not tuple:
        stage1_blockers.append(
            emit_blocker(
                BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
                "raw_input.evidence_refs",
                "evidence_refs_not_frozen_container",
                (),
            )
        )

    if stage1_blockers:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=stage1_blockers,
            stage_rank=1,
            evidence_refs=(),
            upstream_hashes=(),
        )

    # §12 — Stage 2 — TASK-020 and TASK-021 identity / construction family /
    # shell_pass_count / tube_pass_count / blockers == ().
    stage2_blockers: list[Task025BlockerEntry] = []
    config_raw = raw_input["task020_configuration"]
    layout_raw = raw_input["task021_layout"]
    config, config_blockers = _validate_task020(config_raw)
    layout, layout_blockers = _validate_task021(layout_raw)
    stage2_blockers.extend(config_blockers)
    stage2_blockers.extend(layout_blockers)
    if config is not None and layout is not None:
        if layout.task020_configuration_id != config.configuration_id:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_024_TASK020_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.task020_configuration_id",
                    "task020_configuration_id_mismatch",
                    (),
                )
            )
        if layout.task020_configuration_hash != config.configuration_hash:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.task020_configuration_hash",
                    "task020_configuration_hash_mismatch",
                    (),
                )
            )
        if layout.construction_family != config.construction_family.value:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.construction_family",
                    "construction_family_mismatch",
                    (),
                )
            )
        if layout.shell_pass_count != config.shell_pass_count:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.shell_pass_count",
                    "shell_pass_count_mismatch",
                    (),
                )
            )
        if layout.tube_pass_count != config.tube_pass_count:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.tube_pass_count",
                    "tube_pass_count_mismatch",
                    (),
                )
            )
        if layout.equipment_orientation is not config.orientation:
            stage2_blockers.append(
                emit_blocker(
                    BlockerCode.BL_025_TASK021_IDENTITY_MISMATCH,
                    "raw_input.task021_layout.equipment_orientation",
                    "orientation_mismatch",
                    (),
                )
            )

    if stage2_blockers:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=stage2_blockers,
            stage_rank=2,
            evidence_refs=(),
            upstream_hashes=(),
        )

    # §12 — Stage 3 — TASK-025 owned mode: flow_path_mode / hydraulic_authority_mode
    # membership + four-way equality.
    stage3_blockers: list[Task025BlockerEntry] = []
    flow_path_mode_raw = raw_input["flow_path_mode"]
    hydraulic_mode_raw = raw_input["hydraulic_authority_mode"]
    flow_path_mode: FlowPathMode | None = None
    hydraulic_mode: HydraulicAuthorityMode | None = None

    if type(flow_path_mode_raw) is not FlowPathMode:
        stage3_blockers.append(
            emit_blocker(
                BlockerCode.BL_017_NON_TASK025_OWNED_ENUM,
                "raw_input.flow_path_mode",
                "flow_path_mode_not_owned",
                (),
            )
        )
    elif flow_path_mode_raw in (
        FlowPathMode.U_TUBE_PARALLEL_FLOW,
        FlowPathMode.U_TUBE_COUNTER_FLOW,
    ):
        stage3_blockers.append(
            emit_blocker(
                BlockerCode.BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET,
                "raw_input.flow_path_mode",
                "flow_path_mode_u_tube_blocked",
                (),
            )
        )
    else:
        flow_path_mode = flow_path_mode_raw

    if type(hydraulic_mode_raw) is not HydraulicAuthorityMode:
        stage3_blockers.append(
            emit_blocker(
                BlockerCode.BL_017_NON_TASK025_OWNED_ENUM,
                "raw_input.hydraulic_authority_mode",
                "hydraulic_authority_mode_not_owned",
                (),
            )
        )
    elif hydraulic_mode_raw is not HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH:
        stage3_blockers.append(
            emit_blocker(
                BlockerCode.BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET,
                "raw_input.hydraulic_authority_mode",
                "hydraulic_authority_mode_v1_unsupported",
                (),
            )
        )
    else:
        hydraulic_mode = hydraulic_mode_raw

    # Inner modes from upstream authorities.
    internal_flow_auth_raw = raw_input["internal_flow_authority"]
    heat_transfer_auth_raw = raw_input["heat_transfer_authority"]
    participation_auth_raw = raw_input["hydraulic_participation_authority"]

    internal_flow_auth, ifa_blockers = _validate_internal_flow_length(internal_flow_auth_raw)
    heat_transfer_auth, hta_blockers = _validate_heat_transfer_length(heat_transfer_auth_raw)
    participation_auth, pa_blockers = _validate_participation(participation_auth_raw)

    # Stage 3 includes the mode equality contract (§5.6).
    if (
        internal_flow_auth is not None
        and heat_transfer_auth is not None
        and participation_auth is not None
        and hydraulic_mode is not None
    ):
        modes = (
            hydraulic_mode,
            internal_flow_auth.authority_mode,
            heat_transfer_auth.authority_mode,
            participation_auth.authority_mode,
        )
        if not all(m is HydraulicAuthorityMode.INTERNAL_ARITHMETIC_FROM_LENGTH for m in modes):
            stage3_blockers.append(
                emit_blocker(
                    BlockerCode.BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET,
                    "raw_input",
                    "authority_mode_consistency_failed",
                    (),
                )
            )

    stage3_blockers.extend(ifa_blockers)
    stage3_blockers.extend(hta_blockers)
    stage3_blockers.extend(pa_blockers)

    if stage3_blockers:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=stage3_blockers,
            stage_rank=3,
            evidence_refs=(),
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # §12 — Stage 4 — dual length finite / positive / pair / hash.
    stage4_blockers: list[Task025BlockerEntry] = []
    if internal_flow_auth is None or heat_transfer_auth is None:
        stage4_blockers.append(
            emit_blocker(
                BlockerCode.BL_009_FLOW_LENGTH_NON_DETERMINISTIC,
                "raw_input",
                "length_authority_missing",
                (),
            )
        )
    else:
        if (
            internal_flow_auth.start_plane.kind != "internal_flow"
            or internal_flow_auth.end_plane.kind != "internal_flow"
        ):
            stage4_blockers.append(
                emit_blocker(
                    BlockerCode.BL_004_CROSS_PAIR_REFERENCE_PLANE,
                    "raw_input.internal_flow_authority",
                    "internal_flow_pair_invalid",
                    (),
                )
            )
        if (
            heat_transfer_auth.start_plane.kind != "heat_transfer"
            or heat_transfer_auth.end_plane.kind != "heat_transfer"
        ):
            stage4_blockers.append(
                emit_blocker(
                    BlockerCode.BL_004_CROSS_PAIR_REFERENCE_PLANE,
                    "raw_input.heat_transfer_authority",
                    "heat_transfer_pair_invalid",
                    (),
                )
            )
    if stage4_blockers:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=stage4_blockers,
            stage_rank=4,
            evidence_refs=(),
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # §12 — Stage 5 — participation invariants.
    stage5_blockers: list[Task025BlockerEntry] = []
    upstream_position_ids = tuple(p.position_id for p in layout.positions)
    if participation_auth is None:
        stage5_blockers.append(
            emit_blocker(
                BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                "raw_input.hydraulic_participation_authority",
                "participation_authority_missing",
                (),
            )
        )
    else:
        all_ids = participation_auth.all_layout_position_ids
        active_ids = participation_auth.active_position_ids
        inactive_ids = participation_auth.inactive_position_ids
        # INV-01 — all_layout_position_ids == upstream ordered
        if all_ids != upstream_position_ids:
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority.all_layout_position_ids",
                    "all_layout_position_ids_not_exact",
                    (),
                )
            )
        # INV-02 — unique
        if len(set(all_ids)) != len(all_ids):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_006_DUPLICATE_AUTHORITY,
                    "raw_input.hydraulic_participation_authority.all_layout_position_ids",
                    "all_layout_position_ids_duplicate",
                    (),
                )
            )
        # INV-03 / INV-04 — subset checks
        all_set = set(all_ids)
        if not set(active_ids).issubset(all_set):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority.active_position_ids",
                    "active_ids_not_subset",
                    (),
                )
            )
        if not set(inactive_ids).issubset(all_set):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority.inactive_position_ids",
                    "inactive_ids_not_subset",
                    (),
                )
            )
        # INV-05 / INV-06 — no duplicates
        if len(set(active_ids)) != len(active_ids):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_006_DUPLICATE_AUTHORITY,
                    "raw_input.hydraulic_participation_authority.active_position_ids",
                    "active_ids_duplicate",
                    (),
                )
            )
        if len(set(inactive_ids)) != len(inactive_ids):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_006_DUPLICATE_AUTHORITY,
                    "raw_input.hydraulic_participation_authority.inactive_position_ids",
                    "inactive_ids_duplicate",
                    (),
                )
            )
        # INV-07 — disjoint
        if set(active_ids) & set(inactive_ids):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority",
                    "active_inactive_overlap",
                    (),
                )
            )
        # INV-08 — union == all
        if set(active_ids) | set(inactive_ids) != set(all_ids):
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority",
                    "active_inactive_union_mismatch",
                    (),
                )
            )
        # INV-09 — inactive = exact ordered complement
        expected_inactive = tuple(pid for pid in all_ids if pid not in set(active_ids))
        if inactive_ids != expected_inactive:
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    "raw_input.hydraulic_participation_authority.inactive_position_ids",
                    "inactive_not_exact_complement",
                    (),
                )
            )
        # INV-10 — active non-empty
        if not active_ids:
            stage5_blockers.append(
                emit_blocker(
                    BlockerCode.BL_007_EMPTY_ACTIVE_SET,
                    "raw_input.hydraulic_participation_authority.active_position_ids",
                    "active_ids_empty",
                    (),
                )
            )

    if stage5_blockers:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=stage5_blockers,
            stage_rank=5,
            evidence_refs=(),
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # §12 — Stage 6 — deterministic request projection + request_hash.
    # Round-4 §8.3 — Stage 6 reuses the prevalidated tuple. The full
    # contract was already enforced in ``_schedule_dict`` and rejected
    # with a Stage 1 ``BL_003_BLOCKED_INPUT_REJECTED`` if violated, so a
    # non-None prevalidated tuple is guaranteed here.
    if prevalidated_evidence_refs is None:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=[
                emit_blocker(
                    BlockerCode.BL_003_BLOCKED_INPUT_REJECTED,
                    "raw_input.evidence_refs",
                    "evidence_refs_not_frozen_container",
                    (),
                )
            ],
            stage_rank=6,
            evidence_refs=(),
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )
    evidence_refs_final = prevalidated_evidence_refs

    request = Task025Request(
        schema_version=schema_version,
        profile_id=resolved_profile_id or "",
        task020_configuration=config,
        task021_layout=layout,
        internal_flow_authority=internal_flow_auth,
        heat_transfer_authority=heat_transfer_auth,
        hydraulic_participation_authority=participation_auth,
        flow_path_mode=flow_path_mode,
        hydraulic_authority_mode=hydraulic_mode,
        evidence_refs=evidence_refs_final,
    )

    try:
        req_hash = request_hash(request)
    except (ValueError, TypeError):
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=None,
            blockers=[
                emit_blocker(
                    BlockerCode.BL_012_INVALID_REQUEST_HASH,
                    "request",
                    "request_hash_invalid",
                    (),
                ),
            ],
            stage_rank=6,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # §12 — Stage 7 — hydraulic authority hash match.
    try:
        ifa_hash = internal_flow_authority_length_hash(
            internal_flow_auth.length_m,
            internal_flow_auth.start_plane,
            internal_flow_auth.end_plane,
            internal_flow_auth.authority_mode,
        )
        hta_hash = heat_transfer_authority_length_hash(
            heat_transfer_auth.length_m,
            heat_transfer_auth.start_plane,
            heat_transfer_auth.end_plane,
            heat_transfer_auth.authority_mode,
        )
        expected_pha_hash = hydraulic_authority_hash(
            task020_configuration_id=config.configuration_id,
            task021_layout_id=layout.layout_id,
            internal_flow_length_hash_value=ifa_hash,
            heat_transfer_length_hash_value=hta_hash,
            all_layout_position_ids=participation_auth.all_layout_position_ids,
            active_position_ids=participation_auth.active_position_ids,
            inactive_position_ids=participation_auth.inactive_position_ids,
            hydraulic_authority_mode=hydraulic_mode,
            participation_evidence_refs=participation_auth.evidence_refs,
        )
    except (ValueError, TypeError):
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=req_hash,
            blockers=(
                emit_blocker(
                    BlockerCode.BL_011_INVALID_AUTHORITY_HASH,
                    "hydraulic_authority_hash",
                    "hash_computation_failed",
                    (),
                ),
            ),
            stage_rank=7,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    if participation_auth.hydraulic_authority_hash != expected_pha_hash:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=req_hash,
            blockers=(
                emit_blocker(
                    BlockerCode.BL_011_INVALID_AUTHORITY_HASH,
                    "hydraulic_authority_hash",
                    "hydraulic_authority_hash_mismatch",
                    (),
                ),
            ),
            stage_rank=7,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # Stage 7 — verify caller-supplied length_hash fields.
    if internal_flow_auth.length_hash != ifa_hash:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=req_hash,
            blockers=(
                emit_blocker(
                    BlockerCode.BL_011_INVALID_AUTHORITY_HASH,
                    "internal_flow_authority.length_hash",
                    "internal_flow_length_hash_mismatch",
                    (),
                ),
            ),
            stage_rank=7,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )
    if heat_transfer_auth.length_hash != hta_hash:
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=req_hash,
            blockers=(
                emit_blocker(
                    BlockerCode.BL_011_INVALID_AUTHORITY_HASH,
                    "heat_transfer_authority.length_hash",
                    "heat_transfer_length_hash_mismatch",
                    (),
                ),
            ),
            stage_rank=7,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # Round-4 §7 — Stage 8 geometry attribute reads must be controlled.
    # Any missing / inaccessible field or non-exact concrete type is
    # converted to a stable BL_026_TUBE_GEOMETRY_MISSING Stage 8 blocked
    # result with a precise message key. The raw projection already
    # validated the geometry, but the scheduler cannot depend on that
    # and must re-validate with ``object.__getattribute__``.
    try:
        geometry_snapshot = object.__getattribute__(layout, "tube_geometry")
    except (AttributeError, TypeError):
        return _stage8_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            req_hash,
            (config.configuration_hash, layout.layout_hash),
            "tube_geometry_missing_or_inaccessible",
        )
    if type(geometry_snapshot) is not ApprovedTubeGeometrySnapshot:
        return _stage8_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            req_hash,
            (config.configuration_hash, layout.layout_hash),
            "tube_geometry_not_exact_snapshot",
        )
    try:
        inner_diameter_m_raw = object.__getattribute__(geometry_snapshot, "inner_diameter_m")
    except (AttributeError, TypeError):
        return _stage8_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            req_hash,
            (config.configuration_hash, layout.layout_hash),
            "inner_diameter_missing_or_inaccessible",
        )
    try:
        inner_diameter = _parse_inner_diameter_m(inner_diameter_m_raw)
    except _InnerDiameterParseError as exc:
        return _stage8_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            req_hash,
            (config.configuration_hash, layout.layout_hash),
            exc.message_key,
        )

    active_count = len(participation_auth.active_position_ids)
    try:
        geometry = compute_hydraulic_geometry(
            tube_inner_diameter_m=inner_diameter,
            active_tube_count=active_count,
            internal_flow_length_m=internal_flow_auth.length_m,
            heat_transfer_length_m=heat_transfer_auth.length_m,
        )
    except (decimal.InvalidOperation, ValueError, TypeError):
        return _finalize_blocked(
            raw_request_projection,
            raw_profile_id_projection,
            resolved_profile_id,
            request_hash_value=req_hash,
            blockers=(
                emit_blocker(
                    BlockerCode.BL_005_DECIMAL_STRUCTURED_IDENTITY_COLLISION,
                    "geometry",
                    "geometry_compute_failed",
                    (),
                ),
            ),
            stage_rank=8,
            evidence_refs=evidence_refs_final,
            upstream_hashes=(config.configuration_hash, layout.layout_hash),
        )

    # Stage 9 — assemble the valid result.
    layout_hash_value = layout_hash_passthrough(layout.layout_hash)
    valid = Task025ValidResult(
        schema_version="task025.result.v1",
        profile_id=resolved_profile_id or "",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=req_hash,
        layout_hash=layout_hash_value,
        result_hash="0" * 64,
        result_id="0" * 36,
        internal_flow_authority=internal_flow_auth,
        heat_transfer_authority=heat_transfer_auth,
        hydraulic_authority_hash=expected_pha_hash,
        active_position_ids=participation_auth.active_position_ids,
        inactive_position_ids=participation_auth.inactive_position_ids,
        single_tube_flow_area_m2=geometry.single_tube_flow_area_m2,
        total_parallel_flow_area_m2=geometry.total_parallel_flow_area_m2,
        flow_cross_section_wetted_perimeter_m=geometry.flow_cross_section_wetted_perimeter_m,
        total_flow_cross_section_wetted_perimeter_m=geometry.total_flow_cross_section_wetted_perimeter_m,
        hydraulic_diameter_m=geometry.hydraulic_diameter_m,
        internal_volume_m3=geometry.internal_volume_m3,
        internal_heat_transfer_surface_area_m2=geometry.internal_heat_transfer_surface_area_m2,
        future_pressure_drop_length_m=None,
        warnings=(),
        blockers=(),
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        stage_rank=STAGE_RANKS,
        task020_identity=_build_task020_identity(config),
        task021_identity=_build_task021_identity(layout),
        provenance=_build_provenance(
            evidence_refs_final,
            (config.configuration_hash, layout.layout_hash),
        ),
    )

    # §10.8 — compute result_hash from the populated result, then patch it back.
    rhash = result_hash(valid)
    rid = result_id(rhash)
    valid = Task025ValidResult(**{**valid.__dict__, "result_hash": rhash, "result_id": rid})  # type: ignore[call-arg]
    return valid


# -----------------------------------------------------------------------
# Helper finalizers.
# -----------------------------------------------------------------------


def _stage8_blocked(
    raw_request_projection: FrozenRawProjection,
    raw_profile_id_projection: FrozenRawProjection,
    resolved_profile_id: str | None,
    req_hash: str | None,
    upstream_hashes: tuple[str, ...],
    message_key: str,
) -> Task025BlockedResult:
    """Round-4 §7 — Stage 8 blocked-result helper.

    Centralises the BL_026_TUBE_GEOMETRY_MISSING emission for every
    Stage 8 geometry read failure so the message key can be selected
    precisely without leaking the underlying exception.
    """
    return _finalize_blocked(
        raw_request_projection,
        raw_profile_id_projection,
        resolved_profile_id,
        request_hash_value=req_hash,
        blockers=list(
            (
                emit_blocker(
                    BlockerCode.BL_026_TUBE_GEOMETRY_MISSING,
                    "task021_layout.tube_geometry.inner_diameter_m",
                    message_key,
                    (),
                ),
            )
        ),
        stage_rank=8,
        evidence_refs=(),
        upstream_hashes=upstream_hashes,
    )


def finalize_blocked(
    *,
    raw_request_projection: FrozenRawProjection,
    raw_profile_id_projection: FrozenRawProjection,
    resolved_profile_id: str | None,
    request_hash_value: str | None,
    blockers: tuple[Task025BlockerEntry, ...],
    stage_rank: int,
    evidence_refs: tuple[str, ...] = (),
    upstream_hashes: tuple[str, ...] = (),
) -> Task025BlockedResult:
    """§6.3 — Public blocked-result finalizer (sort + dedup blockers)."""
    return _finalize_blocked(
        raw_request_projection,
        raw_profile_id_projection,
        resolved_profile_id,
        request_hash_value,
        list(blockers),
        stage_rank,
        evidence_refs,
        upstream_hashes,
    )


def _finalize_blocked(
    raw_request_projection: FrozenRawProjection,
    raw_profile_id_projection: FrozenRawProjection,
    resolved_profile_id: str | None,
    request_hash_value: str | None,
    blockers: list[Task025BlockerEntry],
    stage_rank: int,
    evidence_refs: tuple[str, ...] = (),
    upstream_hashes: tuple[str, ...] = (),
) -> Task025BlockedResult:
    sorted_blockers = collapse_unregistered_codes(blockers)
    provisional = Task025BlockedResult(
        schema_version="task025.blocked-result.v1",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        resolved_profile_id=resolved_profile_id,
        raw_profile_id_projection=raw_profile_id_projection,
        raw_request_projection=raw_request_projection,
        request_hash=request_hash_value,
        blocked_result_hash="0" * 64,
        blockers=sorted_blockers,
        warnings=(),
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        stage_rank=stage_rank,
        task020_identity=None,
        task021_identity=None,
        provenance=_build_provenance(evidence_refs, upstream_hashes),
    )
    bh = blocked_result_hash(provisional)
    return Task025BlockedResult(**{**provisional.__dict__, "blocked_result_hash": bh})  # type: ignore[call-arg]


# -----------------------------------------------------------------------
# Upstream validators (stages 2, 3, 4).
# -----------------------------------------------------------------------


def _validate_task020(raw: Any) -> tuple[Any, list[Task025BlockerEntry]]:
    from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration

    blockers: list[Task025BlockerEntry] = []
    if type(raw) is not ShellAndTubeConfiguration:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration",
                "task020_type_mismatch",
                (),
            )
        )
        return None, blockers

    if raw.schema_version != "task020.configuration.v1":
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.schema_version",
                "task020_schema_version_invalid",
                (),
            )
        )
    if raw.equipment_family is not EquipmentFamily.SHELL_AND_TUBE:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.equipment_family",
                "task020_equipment_family_not_shell_and_tube",
                (),
            )
        )
    if raw.construction_family is not ConstructionFamily.FIXED_TUBESHEET:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.construction_family",
                "task020_construction_family_not_fixed_tubesheet",
                (),
            )
        )
    if raw.shell_pass_count != 1:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.shell_pass_count",
                "task020_shell_pass_count_not_one",
                (),
            )
        )
    if raw.tube_pass_count != 1:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.tube_pass_count",
                "task020_tube_pass_count_not_one",
                (),
            )
        )
    if raw.authority_mode is not AuthorityMode.INTERNAL_GENERIC:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET,
                "raw_input.task020_configuration.authority_mode",
                "task020_authority_mode_not_internal_generic",
                (),
            )
        )
    if not isinstance(raw.configuration_id, str) or not raw.configuration_id:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.configuration_id",
                "task020_configuration_id_invalid",
                (),
            )
        )
    if not _is_64hex(raw.configuration_hash):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.configuration_hash",
                "task020_configuration_hash_invalid",
                (),
            )
        )
    # Round-4 §5.2 — read ``blockers`` defensively so a missing attribute
    # or a non-str subclass is converted to a stable blocked result
    # rather than leaking ``AttributeError``.
    try:
        blockers_value = object.__getattribute__(raw, "blockers")
    except (AttributeError, TypeError):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.blockers",
                "task020_blockers_missing_or_inaccessible",
                (),
            )
        )
        return raw, blockers
    if type(blockers_value) is not tuple:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.blockers",
                "task020_blockers_not_exact_tuple",
                (),
            )
        )
    elif len(blockers_value) != 0:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_013_INVALID_TASK020_CONFIGURATION,
                "raw_input.task020_configuration.blockers",
                "task020_upstream_blockers_non_empty",
                (),
            )
        )
    return raw, blockers


def _validate_task021(raw: Any) -> tuple[TubeLayout | None, list[Task025BlockerEntry]]:
    blockers: list[Task025BlockerEntry] = []
    if type(raw) is not TubeLayout:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout",
                "task021_type_mismatch",
                (),
            )
        )
        return None, blockers

    if raw.schema_version != "task021.tube-layout.v1":
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.schema_version",
                "task021_schema_version_invalid",
                (),
            )
        )
    if raw.construction_family != ConstructionFamily.FIXED_TUBESHEET.value:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.construction_family",
                "task021_construction_family_not_fixed_tubesheet",
                (),
            )
        )
    if raw.shell_pass_count != 1:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.shell_pass_count",
                "task021_shell_pass_count_not_one",
                (),
            )
        )
    if raw.tube_pass_count != 1:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.tube_pass_count",
                "task021_tube_pass_count_not_one",
                (),
            )
        )
    # Round-4 §5.3 — same defensive pattern as TASK-020: a missing
    # ``blockers`` attribute is converted to a stable BL_014 blocker.
    try:
        layout_blockers_value = object.__getattribute__(raw, "blockers")
    except (AttributeError, TypeError):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.blockers",
                "task021_blockers_missing_or_inaccessible",
                (),
            )
        )
        return raw, blockers
    if type(layout_blockers_value) is not tuple:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.blockers",
                "task021_blockers_not_exact_tuple",
                (),
            )
        )
    elif len(layout_blockers_value) != 0:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.blockers",
                "task021_upstream_blockers_non_empty",
                (),
            )
        )
    if not _is_64hex(raw.layout_hash):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_014_INVALID_TASK021_LAYOUT,
                "raw_input.task021_layout.layout_hash",
                "task021_layout_hash_invalid",
                (),
            )
        )
    return raw, blockers


def _validate_internal_flow_length(
    raw: Any,
) -> tuple[InternalFlowLengthAuthority | None, list[Task025BlockerEntry]]:
    blockers: list[Task025BlockerEntry] = []
    if type(raw) is not InternalFlowLengthAuthority:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_009_FLOW_LENGTH_NON_DETERMINISTIC,
                "raw_input.internal_flow_authority",
                "internal_flow_length_type_mismatch",
                (),
            )
        )
        return None, blockers
    return raw, blockers


def _validate_heat_transfer_length(
    raw: Any,
) -> tuple[HeatTransferLengthAuthority | None, list[Task025BlockerEntry]]:
    blockers: list[Task025BlockerEntry] = []
    if type(raw) is not HeatTransferLengthAuthority:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_010_HEAT_LENGTH_NON_DETERMINISTIC,
                "raw_input.heat_transfer_authority",
                "heat_transfer_length_type_mismatch",
                (),
            )
        )
        return None, blockers
    return raw, blockers


def _validate_participation(
    raw: Any,
) -> tuple[Any, list[Task025BlockerEntry]]:
    from hexagent.exchangers.shell_tube.tube_side.hydraulic_participation_authority import (
        Task025HydraulicParticipationAuthority,
    )

    blockers: list[Task025BlockerEntry] = []
    if type(raw) is not Task025HydraulicParticipationAuthority:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                "raw_input.hydraulic_participation_authority",
                "participation_authority_type_mismatch",
                (),
            )
        )
        return None, blockers
    # Round-4 §6.3 — defensive closure of the four tuple fields, the
    # authority_mode, and the hydraulic_authority_hash. The raw
    # projection already validated the value, but a race between
    # projection and the scheduler could still mutate the object; this
    # block re-reads with ``object.__getattribute__`` and converts any
    # attribute failure to a stable BL_001 blocked result.
    field_paths = {
        "all_layout_position_ids": "participation.all_layout_position_ids",
        "active_position_ids": "participation.active_position_ids",
        "inactive_position_ids": "participation.inactive_position_ids",
        "evidence_refs": "participation.evidence_refs",
    }
    for attr_name, _ in field_paths.items():
        try:
            field_value = object.__getattribute__(raw, attr_name)
        except (AttributeError, TypeError):
            blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    f"raw_input.hydraulic_participation_authority.{attr_name}",
                    "participation_member_missing_or_inaccessible",
                    (),
                )
            )
            return None, blockers
        if type(field_value) is not tuple:
            blockers.append(
                emit_blocker(
                    BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                    f"raw_input.hydraulic_participation_authority.{attr_name}",
                    "participation_member_not_exact_tuple",
                    (),
                )
            )
    try:
        authority_mode = object.__getattribute__(raw, "authority_mode")
        hydraulic_authority_hash = object.__getattribute__(raw, "hydraulic_authority_hash")
    except (AttributeError, TypeError):
        blockers.append(
            emit_blocker(
                BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                "raw_input.hydraulic_participation_authority",
                "participation_field_missing_or_inaccessible",
                (),
            )
        )
        return None, blockers
    if type(authority_mode) is not HydraulicAuthorityMode:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                "raw_input.hydraulic_participation_authority.authority_mode",
                "participation_authority_mode_not_exact_enum",
                (),
            )
        )
    if type(hydraulic_authority_hash) is not str or len(hydraulic_authority_hash) != 64:
        blockers.append(
            emit_blocker(
                BlockerCode.BL_001_ACTIVE_PARTICIPATION_MISSING,
                "raw_input.hydraulic_participation_authority.hydraulic_authority_hash",
                "participation_hydraulic_authority_hash_invalid",
                (),
            )
        )
    if blockers:
        return None, blockers
    return raw, blockers


def _is_64hex(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


class _EvidenceRefsError(Exception):
    __slots__ = ("message_key",)

    def __init__(self, message_key: str) -> None:
        super().__init__(message_key)
        self.message_key = message_key


class _TopLevelKeyScanError(Exception):
    """Round-5 §4 — internal helper signal.

    Raised by :func:`_scan_top_level_request` when the top-level dict
    contains a key whose ``type(...) is not str``. The caller converts
    this into a stable ``BL_019_RAW_PROJECTION_UNSUPPORTED`` Stage 1
    blocked result via ``_build_raw_projection_blocked``.
    """

    __slots__ = ()


def _scan_top_level_request(
    raw_input: dict[object, object],
) -> tuple[object | None, bool]:
    """Round-5 §4 — safe top-level key scan.

    Iterates ``raw_input`` via ``dict.items(raw_input)`` so any subclass
    ``items`` override is bypassed. The ``type(raw_input) is dict`` gate
    is enforced upstream by ``schedule()`` before this helper is called.

    Only keys with ``type(key) is str`` are observed; ``__hash__`` and
    ``__eq__`` on any other key are not invoked. The recognised key
    ``"evidence_refs"`` is matched by direct string equality against
    the iterated key, never via dict membership / ``get`` / indexing.
    """
    evidence_refs_value: object | None = None
    evidence_refs_present = False
    for key, value in dict.items(raw_input):
        if type(key) is not str:
            raise _TopLevelKeyScanError
        if key == "evidence_refs":
            evidence_refs_present = True
            evidence_refs_value = value
    return evidence_refs_value, evidence_refs_present


def _validate_evidence_refs(value: Any) -> tuple[str, ...]:
    """v1 contract: ``evidence_refs`` must be an exact tuple of non-empty str.

    Lists, byte strings, and str subclasses are explicitly rejected. No
    implicit conversion is performed; the round-3 v1 contract is exactly
    tuple-of-non-empty-str.

    Round-4 §8.2 — surrogate / non-UTF-8 checks are also performed here
    so the raw projection boundary never sees a malformed entry. The
    helper raises ``_EvidenceRefsError`` for every violation; the
    scheduler converts that into ``BL_003_BLOCKED_INPUT_REJECTED`` with
    a stable per-violation message key.
    """
    if type(value) is not tuple:
        raise _EvidenceRefsError("evidence_refs_not_frozen_container")
    items: list[str] = []
    for item in value:
        if type(item) is not str:
            raise _EvidenceRefsError("evidence_refs_entry_not_exact_str")
        if not item:
            raise _EvidenceRefsError("evidence_refs_entry_empty")
        if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
            raise _EvidenceRefsError("evidence_refs_entry_surrogate")
        try:
            item.encode("utf-8")
        except UnicodeEncodeError as exc:  # pragma: no cover - guard
            raise _EvidenceRefsError("evidence_refs_entry_not_utf8") from exc
        items.append(item)
    return tuple(items)


class _InnerDiameterParseError(Exception):
    __slots__ = ("message_key",)

    def __init__(self, message_key: str) -> None:
        super().__init__(message_key)
        self.message_key = message_key


def _parse_inner_diameter_m(value: Any) -> Decimal:
    """Total Decimal parser for the Stage 8 inner diameter.

    The contract is:
      * ``type(value) is str`` — no subclasses, no implicit conversion.
      * The string is non-empty, contains no surrogate code points, and
        parses as a finite, strictly-positive :class:`Decimal`.
      * ``NaN``, ``sNaN``, ``Infinity``, ``-Infinity``, ``0`` and any
        non-positive value are rejected.
    Every failure path emits a stable ``_InnerDiameterParseError`` with
    a known ``message_key`` so the caller can produce a Stage 8 blocked
    result without leaking Python builtin exceptions.
    """
    if type(value) is not str:
        raise _InnerDiameterParseError("inner_diameter_not_exact_str")
    if not value:
        raise _InnerDiameterParseError("inner_diameter_empty")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise _InnerDiameterParseError("inner_diameter_surrogate")
    try:
        parsed = Decimal(value)
    except (decimal.InvalidOperation, ValueError, UnicodeError) as exc:
        raise _InnerDiameterParseError("inner_diameter_not_parseable") from exc
    if not parsed.is_finite():
        raise _InnerDiameterParseError("inner_diameter_not_finite")
    if parsed <= Decimal(0):
        raise _InnerDiameterParseError("inner_diameter_non_positive")
    return parsed


# -----------------------------------------------------------------------
# Public top-level entry point.
# -----------------------------------------------------------------------


def evaluate_task025(raw_input: object) -> Task025ValidResult | Task025BlockedResult:
    """§4.2 — Top-level public entry."""
    return schedule(raw_input)


__all__ = [
    "STAGE_RANKS",
    "TOP_LEVEL_NOT_EXACT_DICT_TOKEN",
    "RAW_PROFILE_ID_MISSING_TOKEN",
    "RAW_PROFILE_ID_INVALID_TYPE_TOKEN",
    "schedule",
    "evaluate_task025",
    "finalize_blocked",
]
