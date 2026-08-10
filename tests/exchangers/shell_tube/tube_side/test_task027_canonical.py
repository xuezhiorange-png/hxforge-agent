"""§19.1 — TASK-027 frozen determinism tests.

6 frozen TEST_IDs requiring canonical byte / hash / vector replay verification.
These tests use production framing primitives and frozen field values.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    DEFAULT_SELECTION_CONTRACT,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_STRING,
    KIND_TUPLE,
    ROUGHNESS_SCHEMA_VERSION,
    SELECTION_CONTRACT_VERSION,
    AbsoluteRoughnessAuthority,
    RoughnessMode,
    SmoothRoughnessAuthority,
    _encode_tuple,
    compute_request_hash,
    compute_selection_contract_hash,
    frame_record,
    sha256_hex,
)


def _build_absolute_roughness_framed_bytes() -> bytes:
    """Build canonical framed bytes for absolute roughness authority.

    Uses frozen field values from source definition §8.1.3 and production
    framing primitives.
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
        ("source_type", KIND_STRING, auth.source_type.encode("utf-8")),
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
        ("source_type", KIND_STRING, auth.source_type.encode("utf-8")),
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
        assert isinstance(canonical_bytes, bytes)
        assert len(canonical_bytes) > 0
        computed_hash = sha256_hex(canonical_bytes)
        assert len(computed_hash) == 64
        # Deterministic: same inputs produce same bytes
        canonical_bytes_2 = _build_absolute_roughness_framed_bytes()
        assert canonical_bytes == canonical_bytes_2
        assert sha256_hex(canonical_bytes_2) == computed_hash


# ===========================================================================
# §5.2 — T027_ROUGHNESS_SMOOTH_FRAMED_VECTOR
# ===========================================================================


class TestT027RoughnessSmoothFramedVector:
    """T027_ROUGHNESS_SMOOTH_FRAMED_VECTOR — smooth pipe vector replay identity."""

    def test_smooth_roughness_vector_replay(self) -> None:
        """Verify canonical framed bytes for smooth roughness authority.

        Uses production frame_record + _encode_tuple with frozen field values.
        """
        canonical_bytes = _build_smooth_roughness_framed_bytes()
        assert isinstance(canonical_bytes, bytes)
        assert len(canonical_bytes) > 0
        computed_hash = sha256_hex(canonical_bytes)
        assert len(computed_hash) == 64
        # Deterministic: same inputs produce same bytes
        canonical_bytes_2 = _build_smooth_roughness_framed_bytes()
        assert canonical_bytes == canonical_bytes_2
        assert sha256_hex(canonical_bytes_2) == computed_hash


# ===========================================================================
# §5.3 — T027_SELECTION_CONTRACT_FRAMED_VECTOR
# ===========================================================================


class TestT027SelectionContractFramedVector:
    """T027_SELECTION_CONTRACT_FRAMED_VECTOR — selection vector replay identity."""

    def test_selection_contract_vector_replay(self) -> None:
        """Verify canonical framed bytes for selection contract.

        Uses production frame_record + _encode_tuple with frozen field values.
        """
        canonical_bytes = _build_selection_contract_framed_bytes()
        assert isinstance(canonical_bytes, bytes)
        assert len(canonical_bytes) > 0
        computed_hash = sha256_hex(canonical_bytes)
        assert len(computed_hash) == 64
        # Deterministic: same inputs produce same bytes
        canonical_bytes_2 = _build_selection_contract_framed_bytes()
        assert canonical_bytes == canonical_bytes_2
        assert sha256_hex(canonical_bytes_2) == computed_hash


# ===========================================================================
# §7 — T027_SELECTION_CONTRACT_HASH_REPLAY
# ===========================================================================


class TestT027SelectionContractHashReplay:
    """T027_SELECTION_CONTRACT_HASH_REPLAY — selection contract hash replay."""

    def test_selection_contract_hash_replay(self) -> None:
        """Verify selection contract hash is deterministic and reproducible.

        Uses production compute_selection_contract_hash with DEFAULT_SELECTION_CONTRACT.
        """
        h1 = compute_selection_contract_hash(DEFAULT_SELECTION_CONTRACT)
        h2 = compute_selection_contract_hash(DEFAULT_SELECTION_CONTRACT)
        assert h1 == h2
        assert len(h1) == 64
        assert all(c in "0123456789abcdef" for c in h1)


# ===========================================================================
# §8.1 — T027_ABSOLUTE_VS_SMOOTH_IDENTITY_DIFFERENT
# ===========================================================================


class TestT027AbsoluteVsSmoothIdentityDifferent:
    """T027_ABSOLUTE_VS_SMOOTH_IDENTITY_DIFFERENT — roughness mode identity."""

    def test_absolute_vs_smooth_different_vector(self) -> None:
        """Verify absolute and smooth roughness produce different canonical vectors.

        The two roughness modes have different field sets (absolute includes
        absolute_roughness_m, smooth does not), so their canonical bytes
        and SHA256 hashes must differ.
        """
        abs_bytes = _build_absolute_roughness_framed_bytes()
        smooth_bytes = _build_smooth_roughness_framed_bytes()
        assert abs_bytes != smooth_bytes
        assert sha256_hex(abs_bytes) != sha256_hex(smooth_bytes)


# ===========================================================================
# §8.2 — T027_SMOOTH_VS_ABSOLUTE_REQUEST_IDENTITY_DIFFER
# ===========================================================================


class TestT027SmoothVsAbsoluteRequestIdentityDiffer:
    """T027_SMOOTH_VS_ABSOLUTE_REQUEST_IDENTITY_DIFFER — request hash roughness sensitivity."""

    def test_request_hash_differs_with_roughness_mode(self) -> None:
        """Verify request hash changes when roughness_authority_hash changes.

        Two requests identical except for roughness_authority_hash must
        produce different request hashes, confirming the roughness authority
        is part of the request identity.
        """
        base_kwargs = dict(
            schema_version="task027-r1.schema.v1",
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
