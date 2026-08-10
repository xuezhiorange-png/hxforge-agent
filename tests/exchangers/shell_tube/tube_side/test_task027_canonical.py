"""§19.1 — TASK-027 frozen determinism tests.

6 frozen TEST_IDs requiring canonical byte / hash / vector replay verification.
These tests use production framing primitives and frozen field values.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    BLOCKED_RESULT_HASH_NAMESPACE,
    DEFAULT_SELECTION_CONTRACT,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_STRING,
    KIND_TUPLE,
    ROUGHNESS_SCHEMA_VERSION,
    SELECTION_CONTRACT_VERSION,
    TASK027_BLOCKED_RESULT_SCHEMA_VERSION,
    TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
    AbsoluteRoughnessAuthority,
    BlockerCode,
    RoughnessMode,
    SmoothRoughnessAuthority,
    Task027BlockedResult,
    _encode_tuple,
    _frame_blocked_result_semantics,
    compute_request_hash,
    compute_result_hash,
    compute_selection_contract_hash,
    derive_result_id,
    finalize_turbulent_solver_failure,
    frame_record,
    sha256_hex,
)


def _build_absolute_roughness_framed_bytes() -> bytes:
    """Build canonical framed bytes for absolute roughness authority.

    Uses frozen field values from source definition §8.1.3 and production
    framing primitives. The production _compute_roughness_authority_hash
    excludes authority_hash from hash input; this helper mirrors that.
    """
    auth = AbsoluteRoughnessAuthority(
        schema_version=ROUGHNESS_SCHEMA_VERSION,
        authority_id="roughness-example-001",
        roughness_mode=RoughnessMode.EXPLICIT_ABSOLUTE_ROUGHNESS,
        absolute_roughness_m=Decimal("0.00004500"),
        source_type="MANUFACTURER_DATA",
        source_id="mfr-tube-ss304-001",
        source_version="2024-01",
        source_location="https://example.com/spec-001",
        permission_status="PASS",
        evidence_refs=("ref:spec-page-12",),
        authority_hash="placeholder",
    )
    fields = [
        ("schema_version", KIND_STRING, auth.schema_version.encode("utf-8")),
        ("authority_id", KIND_STRING, auth.authority_id.encode("utf-8")),
        ("roughness_mode", KIND_ENUM, auth.roughness_mode.value.encode("ascii")),
        (
            "absolute_roughness_m",
            KIND_DECIMAL,
            str(auth.absolute_roughness_m).encode("utf-8"),
        ),
        ("source_type", KIND_ENUM, auth.source_type.encode("ascii")),
        ("source_id", KIND_STRING, auth.source_id.encode("utf-8")),
        ("source_version", KIND_STRING, auth.source_version.encode("utf-8")),
        ("source_location", KIND_STRING, auth.source_location.encode("utf-8")),
        ("permission_status", KIND_ENUM, auth.permission_status.encode("ascii")),
        ("evidence_refs", KIND_TUPLE, _encode_tuple(auth.evidence_refs)),
    ]
    return frame_record(ROUGHNESS_SCHEMA_VERSION, fields)


def _build_smooth_roughness_framed_bytes() -> bytes:
    """Build canonical framed bytes for smooth roughness authority.

    Uses frozen field values from source definition §8.1.2 and production
    framing primitives.
    """
    auth = SmoothRoughnessAuthority(
        schema_version=ROUGHNESS_SCHEMA_VERSION,
        authority_id="roughness-smooth-001",
        roughness_mode=RoughnessMode.EXPLICIT_SMOOTH_PIPE_ASSERTION,
        source_type="EXPLICIT_PROJECT_ASSUMPTION",
        source_id="assumption-smooth-001",
        source_version="2026-01",
        source_location="TASK-027 selection contract",
        permission_status="PASS",
        evidence_refs=("ref:task027-selection-r1",),
        authority_hash="placeholder",
    )
    fields = [
        ("schema_version", KIND_STRING, auth.schema_version.encode("utf-8")),
        ("authority_id", KIND_STRING, auth.authority_id.encode("utf-8")),
        ("roughness_mode", KIND_ENUM, auth.roughness_mode.value.encode("ascii")),
        ("source_type", KIND_ENUM, auth.source_type.encode("ascii")),
        ("source_id", KIND_STRING, auth.source_id.encode("utf-8")),
        ("source_version", KIND_STRING, auth.source_version.encode("utf-8")),
        ("source_location", KIND_STRING, auth.source_location.encode("utf-8")),
        ("permission_status", KIND_ENUM, auth.permission_status.encode("ascii")),
        ("evidence_refs", KIND_TUPLE, _encode_tuple(auth.evidence_refs)),
    ]
    return frame_record(ROUGHNESS_SCHEMA_VERSION, fields)


def _build_selection_contract_framed_bytes() -> bytes:
    """Build canonical framed bytes for selection contract.

    Uses frozen field values from source definition §8.3 and production
    framing primitives.
    """
    c = DEFAULT_SELECTION_CONTRACT
    fields = [
        (
            "selection_contract_version",
            KIND_STRING,
            c.selection_contract_version.encode("utf-8"),
        ),
        ("selected_correlation_id", KIND_ENUM, c.selected_correlation_id.encode("ascii")),
        (
            "selected_correlation_source_refs",
            KIND_TUPLE,
            _encode_tuple(c.selected_correlation_source_refs),
        ),
        (
            "friction_factor_convention",
            KIND_ENUM,
            c.friction_factor_convention.value.encode("ascii"),
        ),
        ("re_min", KIND_DECIMAL, str(c.re_min).encode("utf-8")),
        ("re_max", KIND_DECIMAL, str(c.re_max).encode("utf-8")),
        (
            "relative_roughness_variable",
            KIND_STRING,
            c.relative_roughness_variable.encode("utf-8"),
        ),
        ("relative_roughness_min", KIND_DECIMAL, str(c.relative_roughness_min).encode("utf-8")),
        ("relative_roughness_max", KIND_DECIMAL, str(c.relative_roughness_max).encode("utf-8")),
        ("unsupported_gap_policy", KIND_ENUM, c.unsupported_gap_policy.encode("ascii")),
        ("out_of_envelope_policy", KIND_ENUM, c.out_of_envelope_policy.encode("ascii")),
        (
            "roughness_authority_contract_version",
            KIND_STRING,
            c.roughness_authority_contract_version.encode("utf-8"),
        ),
    ]
    return frame_record(SELECTION_CONTRACT_VERSION, fields)


def _build_blocked_result_bytes(
    schema_version: str,
    profile_id: str,
    request_hash: str | None,
    result_hash: str,
    result_id: str,
    task025_hydraulic_authority_hash: str | None,
    task025_result_hash: str | None,
    task026_result_hash: str | None,
    property_snapshot_hash: str | None,
    raw_request_projection: str | None,
    raw_upstream_blocked_projection: str | None,
    warnings: tuple[str, ...],
    blockers_str: str,
    deferred_capabilities: tuple[str, ...],
    provenance: str,
) -> bytes:
    """Build canonical framed bytes for a blocked result.

    Uses the frozen 15-field blocked result schema with production framing.
    """
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("request_hash", KIND_STRING, (request_hash or "").encode("utf-8")),
        ("result_hash", KIND_STRING, result_hash.encode("utf-8")),
        ("result_id", KIND_STRING, result_id.encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            (task025_hydraulic_authority_hash or "").encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, (task025_result_hash or "").encode("utf-8")),
        ("task026_result_hash", KIND_STRING, (task026_result_hash or "").encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, (property_snapshot_hash or "").encode("utf-8")),
        (
            "raw_request_projection",
            KIND_STRING,
            (raw_request_projection or "").encode("utf-8"),
        ),
        (
            "raw_upstream_blocked_projection",
            KIND_STRING,
            (raw_upstream_blocked_projection or "").encode("utf-8"),
        ),
        ("warnings", KIND_STRING, _encode_tuple(warnings)),
        ("blockers", KIND_STRING, blockers_str.encode("utf-8")),
        ("deferred_capabilities", KIND_STRING, _encode_tuple(deferred_capabilities)),
        ("provenance", KIND_STRING, provenance.encode("utf-8")),
    ]
    return frame_record(BLOCKED_RESULT_HASH_NAMESPACE, fields)


# ===========================================================================
# §5.1 — T027_ROUGHNESS_ABSOLUTE_FRAMED_VECTOR
# ===========================================================================


class TestT027RoughnessAbsoluteFramedVector:
    """T027_ROUGHNESS_ABSOLUTE_FRAMED_VECTOR — absolute roughness vector replay identity."""

    def test_absolute_roughness_vector_replay(self) -> None:
        """Verify canonical framed bytes for absolute roughness authority.

        Uses production frame_record + _encode_tuple with frozen field values.
        """
        canonical_bytes = _build_absolute_roughness_framed_bytes()
        assert len(canonical_bytes) == 577
        assert sha256_hex(canonical_bytes) == (
            "81e659672789ceac03478491068df95dbb7df3c59ab911ae3d198083810b6b0d"
        )
        # Deterministic replay
        assert _build_absolute_roughness_framed_bytes() == canonical_bytes


# ===========================================================================
# §5.2 — T027_ROUGHNESS_SMOOTH_FRAMED_VECTOR
# ===========================================================================


class TestT027RoughnessSmoothFramedVector:
    """T027_ROUGHNESS_SMOOTH_FRAMED_VECTOR — smooth pipe vector replay identity."""

    def test_smooth_roughness_vector_replay(self) -> None:
        """Verify canonical framed bytes for smooth roughness authority."""
        canonical_bytes = _build_smooth_roughness_framed_bytes()
        assert len(canonical_bytes) == 546
        assert sha256_hex(canonical_bytes) == (
            "a76c13e932cb3a41c9fe6d650e598357c9cbcb9a66107182d667d99473115b5a"
        )
        assert _build_smooth_roughness_framed_bytes() == canonical_bytes


# ===========================================================================
# §5.3 — T027_SELECTION_CONTRACT_FRAMED_VECTOR
# ===========================================================================


class TestT027SelectionContractFramedVector:
    """T027_SELECTION_CONTRACT_FRAMED_VECTOR — selection vector replay identity."""

    def test_selection_contract_vector_replay(self) -> None:
        """Verify canonical framed bytes for selection contract."""
        canonical_bytes = _build_selection_contract_framed_bytes()
        assert len(canonical_bytes) == 769
        assert sha256_hex(canonical_bytes) == (
            "514ca93b716c37504d8a3196354d245f03b44bf93636495ea8ae358fe9b6f05b"
        )
        assert _build_selection_contract_framed_bytes() == canonical_bytes


# ===========================================================================
# §7 — T027_SELECTION_CONTRACT_HASH_REPLAY
# ===========================================================================


class TestT027SelectionContractHashReplay:
    """T027_SELECTION_CONTRACT_HASH_REPLAY — selection contract hash replay."""

    def test_selection_contract_hash_replay(self) -> None:
        """Verify selection contract hash is deterministic and matches frozen identity."""
        h1 = compute_selection_contract_hash(DEFAULT_SELECTION_CONTRACT)
        h2 = compute_selection_contract_hash(DEFAULT_SELECTION_CONTRACT)
        assert h1 == h2
        assert len(h1) == 64
        # The selection contract hash equals the framed-vector SHA256
        # (same framing, same fields)
        assert h1 == sha256_hex(_build_selection_contract_framed_bytes())


# ===========================================================================
# §8.1 — T027_ABSOLUTE_VS_SMOOTH_IDENTITY_DIFFERENT
# ===========================================================================


class TestT027AbsoluteVsSmoothIdentityDifferent:
    """T027_ABSOLUTE_VS_SMOOTH_IDENTITY_DIFFERENT — full success result identity."""

    # Shared frozen semantic inputs (identical for both roughness modes)
    _PROFILE = "test-profile"
    _T025_HASH = "a" * 64
    _T026_HASH = "b" * 64
    _PROP_HASH = "c" * 64
    _FRICTION_LEN = "2.5"
    _UPSTREAM = "shell-inlet"
    _DOWNSTREAM = "shell-outlet"

    def _compute_request_hash(self, roughness_hash: str) -> str:
        return compute_request_hash(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id=self._PROFILE,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
            constant_density_assertion="TRUE",
            zero_elevation_assertion="TRUE",
            flow_direction_assertion="START_TO_END",
            roughness_authority_hash=roughness_hash,
        )

    def test_absolute_vs_smooth_result_identity(self) -> None:
        """Verify absolute and smooth roughness produce different result identity.

        Chains: roughness authority hash → request hash → result hash → result id.
        Uses production compute_request_hash, compute_result_hash, derive_result_id.
        """
        abs_rh = sha256_hex(_build_absolute_roughness_framed_bytes())
        smooth_rh = sha256_hex(_build_smooth_roughness_framed_bytes())

        # Frozen vector replay preserved
        assert len(_build_absolute_roughness_framed_bytes()) == 577
        assert len(_build_smooth_roughness_framed_bytes()) == 546

        # Different roughness authority hashes
        assert abs_rh != smooth_rh

        # Step 1: Different request hashes
        abs_req = self._compute_request_hash(abs_rh)
        smooth_req = self._compute_request_hash(smooth_rh)
        assert abs_req != smooth_req
        assert len(abs_req) == 64
        assert len(smooth_req) == 64

        # Step 2: Different success result hashes
        # Use same engineering values; only request_hash differs
        abs_rhsh = compute_result_hash(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id=self._PROFILE,
            request_hash=abs_req,
            darcy_friction_factor="0.032",
            friction_length_m=self._FRICTION_LEN,
            upstream_reference_plane=self._UPSTREAM,
            downstream_reference_plane=self._DOWNSTREAM,
            straight_tube_friction_pressure_drop_pa="15.36",
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
        )
        smooth_rhsh = compute_result_hash(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id=self._PROFILE,
            request_hash=smooth_req,
            darcy_friction_factor="0.032",
            friction_length_m=self._FRICTION_LEN,
            upstream_reference_plane=self._UPSTREAM,
            downstream_reference_plane=self._DOWNSTREAM,
            straight_tube_friction_pressure_drop_pa="15.36",
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
        )
        assert abs_rhsh != smooth_rhsh
        assert len(abs_rhsh) == 64
        assert len(smooth_rhsh) == 64

        # Step 3: Different result IDs
        abs_rid = derive_result_id(abs_rhsh)
        smooth_rid = derive_result_id(smooth_rhsh)
        assert abs_rid != smooth_rid

        # Canonical byte evidence: re-derive and verify determinism
        abs_rhsh_2 = compute_result_hash(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id=self._PROFILE,
            request_hash=abs_req,
            darcy_friction_factor="0.032",
            friction_length_m=self._FRICTION_LEN,
            upstream_reference_plane=self._UPSTREAM,
            downstream_reference_plane=self._DOWNSTREAM,
            straight_tube_friction_pressure_drop_pa="15.36",
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
        )
        assert abs_rhsh == abs_rhsh_2
        assert derive_result_id(abs_rhsh_2) == abs_rid


# ===========================================================================
# §8.2 — T027_SMOOTH_VS_ABSOLUTE_REQUEST_IDENTITY_DIFFER
# ===========================================================================


class TestT027SmoothVsAbsoluteRequestIdentityDiffer:
    """T027_SMOOTH_VS_ABSOLUTE_REQUEST_IDENTITY_DIFFER — request hash roughness sensitivity."""

    def test_request_hash_differs_with_roughness_mode(self) -> None:
        """Verify request hash changes when roughness_authority_hash changes."""
        base_kwargs = dict(
            schema_version=TASK027_SUCCESS_RESULT_SCHEMA_VERSION,
            profile_id="test-profile",
            task025_result_hash="a" * 64,
            task026_result_hash="b" * 64,
            property_snapshot_hash="c" * 64,
            constant_density_assertion="TRUE",
            zero_elevation_assertion="TRUE",
            flow_direction_assertion="START_TO_END",
        )
        h_absolute = compute_request_hash(
            roughness_authority_hash=sha256_hex(_build_absolute_roughness_framed_bytes()),
            **base_kwargs,
        )
        h_smooth = compute_request_hash(
            roughness_authority_hash=sha256_hex(_build_smooth_roughness_framed_bytes()),
            **base_kwargs,
        )
        assert h_absolute != h_smooth
        assert len(h_absolute) == 64
        assert len(h_smooth) == 64


# ===========================================================================
# §9.2 — T027_TURBULENT_SOLVER_FAILURE_FAIL_CLOSED
# ===========================================================================


class TestT027TurbulentSolverFailureFailClosed:
    """T027_TURBULENT_SOLVER_FAILURE_FAIL_CLOSED — blocked result canonical identity.

    Frozen requirement:
      TEST_EXPECTED_VARIANT=blocked
      TEST_BLOCKER_CODES=(BL_T027_TURBULENT_SOLVER_FAILURE,)
      TEST_CANONICAL_BYTE_ASSERTION=required
    """

    # Frozen semantic inputs for blocked result
    _PROFILE = "test-profile"
    _REQUEST_HASH = "d" * 64
    _T025_HASH = "e" * 64
    _T026_HASH = "f" * 64
    _PROP_HASH = "g" * 64

    def _build_independent_canonical_bytes(
        self,
        schema_version: str,
        profile_id: str,
        request_hash: str | None,
        t025_hash: str | None,
        t025_result_hash: str | None,
        t026_result_hash: str | None,
        prop_hash: str | None,
        raw_req_proj_none: bool,
        raw_upstream_proj_none: bool,
        warnings: tuple[str, ...],
        blocker_code_value: str,
        blocker_field_path: tuple[str, ...],
        blocker_message_key: str,
        blocker_evidence_refs: tuple[str, ...],
        deferred_capabilities: tuple[str, ...],
        provenance_none: bool,
    ) -> bytes:
        """Build canonical bytes independently from production hash helper.

        This reconstructs the frozen 13-field named record using raw framing
        primitives, proving the canonical byte assertion is not circular.
        """
        import struct as _struct

        def _u32(n: int) -> bytes:
            return _struct.pack(">I", n)

        def _u64(n: int) -> bytes:
            return _struct.pack(">Q", n)

        def _fv(kind: bytes, payload: bytes) -> bytes:
            return _u32(len(kind)) + kind + _u64(len(payload)) + payload

        def _fr(ns: str, fields: list[tuple[str, bytes, bytes]]) -> bytes:
            ns_b = ns.encode("utf-8")
            out = _u32(len(ns_b)) + ns_b + _u32(len(fields))
            for name, kind, payload in fields:
                out += _u32(len(name)) + name.encode("utf-8") + _fv(kind, payload)
            return out

        def _encode_tuple(items: tuple[str, ...]) -> bytes:
            out = _u32(len(items))
            for item in items:
                out += _u32(len(item)) + item.encode("utf-8")
            return out

        def _encode_blocker_entry(
            code_val: str,
            field_path: tuple[str, ...],
            msg_key: str,
            evidence: tuple[str, ...],
        ) -> bytes:
            fields = [
                ("code", b"STRING", code_val.encode("utf-8")),
                ("field_path", b"TUPLE", _encode_tuple(field_path)),
                ("message_key", b"STRING", msg_key.encode("utf-8")),
                ("evidence_refs", b"TUPLE", _encode_tuple(evidence)),
            ]
            return _fr("task027.blocker-entry.v1", fields)

        # Build the 13-field record
        req_proj_kind = b"NONE" if raw_req_proj_none else b"RAW_PROJECTION"
        upstream_kind = b"NONE" if raw_upstream_proj_none else b"RAW_PROJECTION"
        prov_kind = b"NONE" if provenance_none else b"RECORD"

        blocker_payload = _encode_blocker_entry(
            blocker_code_value,
            blocker_field_path,
            blocker_message_key,
            blocker_evidence_refs,
        )

        fields: list[tuple[str, bytes, bytes]] = [
            ("schema_version", b"STRING", schema_version.encode("utf-8")),
            ("profile_id", b"STRING", profile_id.encode("utf-8")),
            ("request_hash", b"STRING", (request_hash or "").encode("utf-8")),
            ("task025_hydraulic_authority_hash", b"STRING", (t025_hash or "").encode("utf-8")),
            ("task025_result_hash", b"STRING", (t025_result_hash or "").encode("utf-8")),
            ("task026_result_hash", b"STRING", (t026_result_hash or "").encode("utf-8")),
            ("property_snapshot_hash", b"STRING", (prop_hash or "").encode("utf-8")),
            ("raw_request_projection", req_proj_kind, b""),
            ("raw_upstream_blocked_projection", upstream_kind, b""),
            ("warnings", b"TUPLE", _encode_tuple(warnings)),
            ("blockers", b"TUPLE", blocker_payload),
            ("deferred_capabilities", b"TUPLE", _encode_tuple(deferred_capabilities)),
            ("provenance", prov_kind, b""),
        ]
        return _fr("task027.blocked-result.v1", fields)

    def test_blocked_result_full_identity(self) -> None:
        """Verify solver non-convergence produces frozen blocked result identity.

        Uses production finalize_turbulent_solver_failure() which:
          1. Calls compute_turbulent_friction_factor_safe (actual non-convergence)
          2. Builds canonical Task027BlockedResult via build_task027_blocked_result
          3. Computes result_hash via compute_blocked_result_hash
          4. Derives result_id via derive_result_id
        """
        # Step 1: Invoke production finalization with deterministic non-convergence seam
        result = finalize_turbulent_solver_failure(
            profile_id=self._PROFILE,
            request_hash=self._REQUEST_HASH,
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
            raw_request_projection=None,
            raw_upstream_blocked_projection=None,
            warnings=(),
            deferred_capabilities=(),
            provenance=None,
            reynolds=Decimal("4000"),
            relative_roughness=Decimal("0"),
            tolerance=Decimal("1e-12"),
            max_iterations=1,
        )

        # Step 2: Verify production returned a real Task027BlockedResult
        assert isinstance(result, Task027BlockedResult)
        assert result.schema_version == TASK027_BLOCKED_RESULT_SCHEMA_VERSION

        # Step 3: Verify blocker properties
        assert len(result.blockers) == 1
        assert result.blockers[0].code == BlockerCode.BL_T027_TURBULENT_SOLVER_FAILURE

        # Step 4: Verify result_hash is 64-char hex
        assert len(result.result_hash) == 64

        # Step 5: Verify result_id matches derive_result_id(result_hash)
        assert result.result_id == derive_result_id(result.result_hash)

        # Step 6: Independent canonical bytes replay (NOT using production helper)
        blocker = result.blockers[0]
        independent_bytes = self._build_independent_canonical_bytes(
            schema_version=result.schema_version,
            profile_id=result.profile_id,
            request_hash=result.request_hash,
            t025_hash=result.task025_hydraulic_authority_hash,
            t025_result_hash=result.task025_result_hash,
            t026_result_hash=result.task026_result_hash,
            prop_hash=result.property_snapshot_hash,
            raw_req_proj_none=result.raw_request_projection is None,
            raw_upstream_proj_none=result.raw_upstream_blocked_projection is None,
            warnings=result.warnings,
            blocker_code_value=blocker.code.value,
            blocker_field_path=tuple(blocker.field_path),
            blocker_message_key=blocker.message_key,
            blocker_evidence_refs=tuple(blocker.evidence_refs),
            deferred_capabilities=result.deferred_capabilities,
            provenance_none=result.provenance is None,
        )
        assert len(independent_bytes) > 0

        # Verify: single named record with 13 fields (no anonymous suffix)
        import struct as _struct

        ns_len = _struct.unpack(">I", independent_bytes[:4])[0]
        field_count = _struct.unpack(">I", independent_bytes[4 + ns_len : 8 + ns_len])[0]
        assert field_count == 13, f"Expected 13 fields, got {field_count}"

        # Verify: independent hash matches production result_hash
        assert sha256_hex(independent_bytes) == result.result_hash, (
            f"Independent canonical bytes hash {sha256_hex(independent_bytes)} "
            f"!= production result_hash {result.result_hash}"
        )

        # Step 7: Canonical bytes via production framing also match
        canonical_bytes_prod = _frame_blocked_result_semantics(
            schema_version=result.schema_version,
            profile_id=result.profile_id,
            request_hash=result.request_hash,
            task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
            task025_result_hash=result.task025_result_hash,
            task026_result_hash=result.task026_result_hash,
            property_snapshot_hash=result.property_snapshot_hash,
            raw_request_projection=result.raw_request_projection,
            raw_upstream_blocked_projection=result.raw_upstream_blocked_projection,
            warnings=result.warnings,
            blockers=result.blockers,
            deferred_capabilities=result.deferred_capabilities,
            provenance=result.provenance,
        )
        assert canonical_bytes_prod == independent_bytes

        # Step 8: Deterministic replay — second execution produces identical result
        result2 = finalize_turbulent_solver_failure(
            profile_id=self._PROFILE,
            request_hash=self._REQUEST_HASH,
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
            raw_request_projection=None,
            raw_upstream_blocked_projection=None,
            warnings=(),
            deferred_capabilities=(),
            provenance=None,
            reynolds=Decimal("4000"),
            relative_roughness=Decimal("0"),
            tolerance=Decimal("1e-12"),
            max_iterations=1,
        )
        assert result.result_hash == result2.result_hash
        assert result.result_id == result2.result_id
        assert [b.code for b in result.blockers] == [b.code for b in result2.blockers]

        # Step 9: Verify no partial engineering output
        # Task027BlockedResult does not carry darcy_friction_factor or pressure_drop
        # (those fields don't exist on the blocked schema)
        assert not hasattr(result, "darcy_friction_factor")
        assert not hasattr(result, "straight_tube_friction_pressure_drop_pa")

    def test_raw_upstream_projection_none_encoding(self) -> None:
        """Verify raw_upstream_blocked_projection absent uses KIND_NONE encoding."""
        import struct as _struct

        result = finalize_turbulent_solver_failure(
            profile_id=self._PROFILE,
            request_hash=self._REQUEST_HASH,
            task025_hydraulic_authority_hash=self._T025_HASH,
            task025_result_hash=self._T025_HASH,
            task026_result_hash=self._T026_HASH,
            property_snapshot_hash=self._PROP_HASH,
            raw_request_projection=None,
            raw_upstream_blocked_projection=None,
            warnings=(),
            deferred_capabilities=(),
            provenance=None,
            reynolds=Decimal("4000"),
            relative_roughness=Decimal("0"),
            tolerance=Decimal("1e-12"),
            max_iterations=1,
        )
        # Verify raw_upstream_blocked_projection is None
        assert result.raw_upstream_blocked_projection is None

        # Verify canonical bytes use KIND_NONE for field 9
        canonical = _frame_blocked_result_semantics(
            schema_version=result.schema_version,
            profile_id=result.profile_id,
            request_hash=result.request_hash,
            task025_hydraulic_authority_hash=result.task025_hydraulic_authority_hash,
            task025_result_hash=result.task025_result_hash,
            task026_result_hash=result.task026_result_hash,
            property_snapshot_hash=result.property_snapshot_hash,
            raw_request_projection=result.raw_request_projection,
            raw_upstream_blocked_projection=result.raw_upstream_blocked_projection,
            warnings=result.warnings,
            blockers=result.blockers,
            deferred_capabilities=result.deferred_capabilities,
            provenance=result.provenance,
        )
        # Parse to find field 9 kind tag
        ns_len = _struct.unpack(">I", canonical[:4])[0]
        offset = 4 + ns_len + 4  # skip namespace + field_count
        for i in range(13):
            name_len = _struct.unpack(">I", canonical[offset : offset + 4])[0]
            offset += 4 + name_len  # skip name
            # Skip frame_value: kind_len(u32) + kind + payload_len(u64) + payload
            kind_len = _struct.unpack(">I", canonical[offset : offset + 4])[0]
            kind_tag = canonical[offset + 4 : offset + 4 + kind_len]
            offset += 4 + kind_len
            payload_len = _struct.unpack(">Q", canonical[offset : offset + 8])[0]
            offset += 8 + payload_len
            if i == 8:  # field 9 (0-indexed)
                assert kind_tag == b"NONE", f"Field 9 kind={kind_tag}, expected NONE"
                assert payload_len == 0, f"Field 9 payload_len={payload_len}, expected 0"
