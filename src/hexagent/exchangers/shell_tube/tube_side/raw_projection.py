"""TASK-025 raw projection.

§7 — Raw projection closure.
§7.1 — Exact atom dispatch.
§7.3 — Exact built-in envelope containers.
§7.4 — Known-object projector table.
§7.5 — Unknown-object safety.
"""




from __future__ import annotations

import enum as _enum
from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ConstructionFamily,
    Orientation,
)
from hexagent.exchangers.shell_tube.tube_layout.models import (
    ApprovedTubeGeometrySnapshot,
    TubeLayout,
    TubePosition,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    FrozenJsonArray,
    FrozenJsonObject,
    PIWrapper,
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
    ReferencePlaneToken,
)

# §7.2 — RECOGNIZED_ENUM_CLASSES (7 concrete enum classes).
RECOGNIZED_ENUM_CLASSES: Final[tuple[type, ...]] = (
    FlowPathMode := __import__(
        "hexagent.exchangers.shell_tube.tube_side.owned_enums",
        fromlist=["FlowPathMode"],
    ).FlowPathMode,
    HydraulicAuthorityMode,
    ReferencePlaneToken,
    BlockerCode := __import__(
        "hexagent.exchangers.shell_tube.tube_side.blocker_registry",
        fromlist=["BlockerCode"],
    ).BlockerCode,
    AuthorityMode,
    ConstructionFamily,
    Orientation,
)


# §7.4.1 — ShellAndTubeConfiguration ordered projection.
_SHELL_TUBE_CONFIGURATION_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "configuration_id",
    "configuration_hash",
    "authority_mode",
    "construction_family",
    "orientation",
    "shell_pass_count",
    "tube_pass_count",
)


# §7.4.2 — TubeLayout ordered projection.
_TUBE_LAYOUT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "layout_id",
    "layout_hash",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "construction_family",
    "equipment_orientation",
    "shell_pass_count",
    "tube_pass_count",
    "tube_hole_count",
    "physical_tube_count",
    "positions",
    "tube_geometry",
)


# §10.1 — Universal labeled-record framing node namespaces for known objects.
_NS_SHELL_TUBE_CONFIGURATION: Final[bytes] = b"hexagent.shell-tube.configuration.v1"
_NS_TUBE_LAYOUT: Final[bytes] = b"hexagent.tube-layout.layout.v1"
_NS_INTERNAL_FLOW_LENGTH: Final[bytes] = b"task025.internal-flow-length-authority.v1"
_NS_HEAT_TRANSFER_LENGTH: Final[bytes] = b"task025.heat-transfer-length-authority.v1"
_NS_HYDRAULIC_PARTICIPATION: Final[bytes] = b"task025.hydraulic-participation-authority.v1"
_NS_REFERENCE_PLANE_PAIR: Final[bytes] = b"task025.reference-plane-pair.v1"


# -----------------------------------------------------------------------
# §7.1 — Atom projectors.
# -----------------------------------------------------------------------


def _project_atom_none(value: None) -> bytes:
    return b""


def _project_atom_bool(value: bool) -> bytes:
    return b""


def _project_atom_int(value: int) -> bytes:
    return str(value).encode("ascii")


def _project_atom_str(value: str) -> bytes:
    return value.encode("utf-8")


def _project_atom_bytes(value: bytes) -> bytes:
    return value


def _project_atom_decimal(value: Decimal) -> bytes:
    return str(value).encode("ascii")


def _project_atom_enum(value: _enum.Enum) -> bytes:
    return value.name.encode("ascii") if hasattr(value, "name") else str(value).encode("ascii")


def _project_pi_wrapper(value: PIWrapper) -> bytes:
    return value.canonical_utf8_bytes


# §7.1 — project_raw_value dispatch.
def project_raw_value(value: Any) -> bytes:
    """§7.1 — Apply the ordered exact atom + container dispatch.

    Returned bytes are the canonical projection bytes.  No recursion
    uses user methods, descriptors, MRO, slots, or arbitrary metadata.
    """
    if value is None:
        return _project_atom_none(value)
    if isinstance(value, bool):
        return _project_atom_bool(value)
    if isinstance(value, int):
        return _project_atom_int(value)
    if isinstance(value, str):
        # §7.1 step 4 — surrogate rejection.
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("project_raw_value: surrogate-containing string rejected")
        return _project_atom_str(value)
    if isinstance(value, bytes):
        return _project_atom_bytes(value)
    if isinstance(value, Decimal):
        return _project_atom_decimal(value)
    if isinstance(value, PIWrapper):
        return _project_pi_wrapper(value)
    # §7.2 — concrete enum dispatch.
    for enum_cls in RECOGNIZED_ENUM_CLASSES:
        if type(value) is enum_cls:
            return _project_atom_enum(value)  # type: ignore[arg-type]
    # §7.4 — exact-type known-object projector table.
    if type(value) is __import__(
        "hexagent.exchangers.shell_tube.models", fromlist=["ShellAndTubeConfiguration"]
    ).ShellAndTubeConfiguration:
        return _project_shell_tube_configuration(value)
    if type(value) is TubeLayout:
        return _project_tube_layout(value)
    from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
        HeatTransferLengthAuthority,
        InternalFlowLengthAuthority,
    )
    if type(value) is InternalFlowLengthAuthority:
        return _project_internal_flow_length_authority(value)
    if type(value) is HeatTransferLengthAuthority:
        return _project_heat_transfer_length_authority(value)
    from hexagent.exchangers.shell_tube.tube_side.hydraulic_participation_authority import (
        Task025HydraulicParticipationAuthority,
    )
    if type(value) is Task025HydraulicParticipationAuthority:
        return _project_hydraulic_participation_authority(value)
    if type(value) is ReferencePlanePair:
        return _project_reference_plane_pair(value)
    if isinstance(value, FrozenJsonArray):
        return _project_frozen_json_array(value)
    if isinstance(value, FrozenJsonObject):
        return _project_frozen_json_object(value)
    # §7.3 — built-in envelope containers.
    if type(value) is dict:
        return _project_dict(value)
    if type(value) is tuple:
        return _project_tuple(value)
    if type(value) is frozenset:
        return _project_frozenset(value)
    # §7.1 — otherwise fail-closed.
    raise ValueError(
        f"project_raw_value: unsupported type {type(value).__name__!r}"
    )


# §7.3 — Container projection.


_DEPTH_LIMIT: Final[int] = 64


def _project_dict(value: dict[str, Any]) -> bytes:
    # §7.3 — exact str keys, sorted by canonical UTF-8 bytes.
    if any(not isinstance(k, str) for k in value):
        raise ValueError("project_raw_dict: dict keys must be exact str")
    sorted_keys = sorted(value.keys())
    out = b""
    for key in sorted_keys:
        v_bytes = project_raw_value(value[key])
        out += _u32_be(len(key.encode("utf-8"))) + key.encode("utf-8") + _u64_be(len(v_bytes)) + v_bytes
    return out


def _project_tuple(value: tuple[Any, ...]) -> bytes:
    out = _u32_be(len(value))
    for item in value:
        item_bytes = project_raw_value(item)
        out += _u32_be(len(item_bytes)) + item_bytes
    return out


def _project_frozenset(value: frozenset[Any]) -> bytes:
    projected_items = [project_raw_value(item) for item in value]
    if len(set(projected_items)) != len(projected_items):
        raise ValueError("project_raw_value: frozenset projected duplicates")
    sorted_items = sorted(projected_items)
    out = _u32_be(len(sorted_items))
    for item in sorted_items:
        out += _u32_be(len(item)) + item
    return out


# §7.4 — Known-object projectors.


def _project_shell_tube_configuration(value: Any) -> bytes:
    fields = []
    for field_name in _SHELL_TUBE_CONFIGURATION_FIELDS:
        field_value = getattr(value, field_name)
        # enum fields projected as enum.
        if field_name == "authority_mode":
            enum_value: Any = field_value
            enum_bytes = _project_atom_enum(enum_value)
            fields.append((field_name, b"ENUM", enum_bytes))
        elif field_name == "construction_family" or field_name == "orientation":
            enum_bytes = _project_atom_enum(field_value)
            fields.append((field_name, b"ENUM", enum_bytes))
        else:
            # Validate atomic types: str / int.
            if not isinstance(field_value, (str, int)):
                raise ValueError(
                    f"project_raw: ShellAndTubeConfiguration.{field_name} "
                    f"must be str or int; got {type(field_value).__name__}"
                )
            if isinstance(field_value, str):
                fields.append((field_name, b"STRING", field_value.encode("utf-8")))
            else:
                fields.append((field_name, b"INT", str(field_value).encode("ascii")))
    # §7.4.1 — CANONICAL_SERIALIZATION uses labeled record framing.
    return _canonicalize_kv_to_record(_NS_SHELL_TUBE_CONFIGURATION, tuple(fields))


def _project_tube_layout(value: TubeLayout) -> bytes:
    fields = []
    for field_name in _TUBE_LAYOUT_FIELDS:
        if field_name == "construction_family" or field_name == "equipment_orientation":
            enum_bytes = _project_atom_enum(getattr(value, field_name))
            fields.append((field_name, b"ENUM", enum_bytes))
        elif field_name == "positions":
            # tuple of position_id strings in upstream order.
            position_ids = tuple(p.position_id for p in value.positions)
            position_bytes = _project_tuple(position_ids)
            fields.append((field_name, b"TUPLE", position_bytes))
        elif field_name == "tube_geometry":
            geom: ApprovedTubeGeometrySnapshot = value.tube_geometry
            # §7.4.2 — exact three geometry identity fields only.
            sub = (
                (b"STRING", geom.geometry_id.encode("utf-8")),
                (b"STRING", geom.record_hash.encode("utf-8")),
                (b"STRING", geom.snapshot_hash.encode("utf-8")),
            )
            inner = _u32_be(len(sub))
            for kind_tag, payload in sub:
                inner += _u32_be(len(kind_tag)) + kind_tag + _u64_be(len(payload)) + payload
            fields.append((field_name, b"RECORD", inner))
        elif field_name in (
            "schema_version",
            "layout_id",
            "layout_hash",
            "request_hash",
            "task020_configuration_id",
            "task020_configuration_hash",
        ):
            v = getattr(value, field_name)
            fields.append((field_name, b"STRING", v.encode("utf-8")))
        else:
            # int fields: shell_pass_count, tube_pass_count, tube_hole_count, physical_tube_count.
            v = getattr(value, field_name)
            fields.append((field_name, b"INT", str(v).encode("ascii")))
    return _canonicalize_kv_to_record(_NS_TUBE_LAYOUT, tuple(fields))


def _project_internal_flow_length_authority(value: Any) -> bytes:
    fields = (
        ("length_id", b"STRING", value.length_id.encode("utf-8")),
        ("length_m", b"DECIMAL", str(value.length_m).encode("ascii")),
        ("start_plane", b"RECORD", _project_reference_plane_pair(value.start_plane)),
        ("end_plane", b"RECORD", _project_reference_plane_pair(value.end_plane)),
        ("authority_mode", b"ENUM", _project_atom_enum(value.authority_mode)),
    )
    return _canonicalize_kv_to_record(_NS_INTERNAL_FLOW_LENGTH, fields)


def _project_heat_transfer_length_authority(value: Any) -> bytes:
    fields = (
        ("length_id", b"STRING", value.length_id.encode("utf-8")),
        ("length_m", b"DECIMAL", str(value.length_m).encode("ascii")),
        ("start_plane", b"RECORD", _project_reference_plane_pair(value.start_plane)),
        ("end_plane", b"RECORD", _project_reference_plane_pair(value.end_plane)),
        ("authority_mode", b"ENUM", _project_atom_enum(value.authority_mode)),
    )
    return _canonicalize_kv_to_record(_NS_HEAT_TRANSFER_LENGTH, fields)


def _project_hydraulic_participation_authority(value: Any) -> bytes:
    all_ids = value.all_layout_position_ids
    active_ids = value.active_position_ids
    inactive_ids = value.inactive_position_ids
    evidence = value.evidence_refs
    fields = (
        ("all_layout_position_ids", b"TUPLE", _project_tuple(all_ids)),
        ("active_position_ids", b"TUPLE", _project_tuple(active_ids)),
        ("inactive_position_ids", b"TUPLE", _project_tuple(inactive_ids)),
        ("authority_mode", b"ENUM", _project_atom_enum(value.authority_mode)),
        ("evidence_refs", b"TUPLE", _project_tuple(evidence)),
    )
    return _canonicalize_kv_to_record(_NS_HYDRAULIC_PARTICIPATION, fields)


def _project_reference_plane_pair(value: ReferencePlanePair) -> bytes:
    fields = (
        ("start", b"ENUM", _project_atom_enum(value.start)),
        ("end", b"ENUM", _project_atom_enum(value.end)),
    )
    return _canonicalize_kv_to_record(_NS_REFERENCE_PLANE_PAIR, fields)


def _project_frozen_json_array(value: FrozenJsonArray) -> bytes:
    out = _u32_be(len(value))
    for item in value:
        item_bytes = project_raw_value(item)
        out += _u32_be(len(item_bytes)) + item_bytes
    return out


def _project_frozen_json_object(value: FrozenJsonObject) -> bytes:
    sorted_keys = sorted(value.keys())
    out = _u32_be(len(sorted_keys))
    for key in sorted_keys:
        v_bytes = project_raw_value(value[key])
        out += _u32_be(len(key.encode("utf-8"))) + key.encode("utf-8") + _u64_be(len(v_bytes)) + v_bytes
    return out


# -----------------------------------------------------------------------
# Internal canonical serialization helpers.
# -----------------------------------------------------------------------


def _u32_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError("u32_be out of range")
    return n.to_bytes(4, "big", signed=False)


def _u64_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("u64_be out of range")
    return n.to_bytes(8, "big", signed=False)


def _canonicalize_kv_to_record(
    namespace: bytes, fields: tuple[tuple[str, bytes, bytes], ...]
) -> bytes:
    """Wrap a list of ``(name, kind_tag, payload)`` triples into the §10.1 frame.

    Frame is ``(node_namespace_len: u32, namespace, field_count: u32, fields...)``.
    Each field is ``(name_len: u32, name_utf8, payload_len: u64, payload_bytes)``.
    """
    out = _u32_be(len(namespace)) + namespace + _u32_be(len(fields))
    for name, kind_tag, payload in fields:
        out += _u32_be(len(name)) + name.encode("utf-8")
        out += _u32_be(len(kind_tag)) + kind_tag
        out += _u64_be(len(payload)) + payload
    return out


# -----------------------------------------------------------------------
# §4.2 / §A07 — project_raw_dict (top-level dict).
# -----------------------------------------------------------------------


def project_raw_dict(value: dict[str, Any]) -> bytes:
    """§4.2 / §7.3 — Top-level dict projection."""
    if type(value) is not dict:
        raise ValueError("project_raw_dict: top-level must be exact dict")
    return _project_dict(value)


# -----------------------------------------------------------------------
# §6.1 — FrozenRawProjection hash computation.
# -----------------------------------------------------------------------


def raw_projection_hex(framed_bytes: bytes) -> str:
    """Return the lowercase-hex SHA-256 of the framed bytes."""
    return sha256_hex_from_framed_bytes(framed_bytes)


# -----------------------------------------------------------------------
# §7.5 — Unknown-object safety: kill-swtich helpers for the scheduler.
# -----------------------------------------------------------------------


def unsafe_object_signal(value: Any) -> bool:
    """Return ``True`` if ``value`` is in a class that triggers unknown-object safety."""
    if value is None or isinstance(value, (bool, int, str, bytes, Decimal)):
        return False
    if isinstance(value, PIWrapper):
        return False
    if isinstance(value, _enum.Enum):
        return False
    if isinstance(value, FrozenJsonArray):
        return False
    if isinstance(value, FrozenJsonObject):
        return False
    if type(value) in RECOGNIZED_ENUM_CLASSES:
        return False
    # Known typed objects — accept.
    from hexagent.exchangers.shell_tube.models import ShellAndTubeConfiguration
    from hexagent.exchangers.shell_tube.tube_side.hydraulic_participation_authority import (
        Task025HydraulicParticipationAuthority,
    )
    from hexagent.exchangers.shell_tube.tube_side.length_authorities import (
        HeatTransferLengthAuthority,
        InternalFlowLengthAuthority,
    )

    if type(value) in (
        ShellAndTubeConfiguration,
        TubeLayout,
        TubePosition,
        InternalFlowLengthAuthority,
        HeatTransferLengthAuthority,
        Task025HydraulicParticipationAuthority,
        ReferencePlanePair,
    ):
        return False
    return not (type(value) is tuple or type(value) is dict or type(value) is frozenset)


__all__ = [
    "RECOGNIZED_ENUM_CLASSES",
    "project_raw_value",
    "project_raw_dict",
    "raw_projection_hex",
    "unsafe_object_signal",
]

# ruff: noqa: E501
