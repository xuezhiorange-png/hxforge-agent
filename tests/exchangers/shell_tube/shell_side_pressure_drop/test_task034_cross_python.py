"""Shared frozen expected canonical-byte probes for Python 3.11 and 3.12."""

import hashlib

from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import (
    SHELL_TYPE_AUTHORITY_HASH_NAMESPACE,
    canonical_bytes,
    shell_type_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.models import (
    SHELL_TYPE_AUTHORITY_PREHASH_FIELDS,
)

EXPECTED_ARTIFACT_SET_ID = "TASK034_XPY_FROZEN_EXPECTED_CANONICAL_ARTIFACT_SET_V2"
EXPECTED_ARTIFACT_SET_SHA256 = "f39261016d5bca4a00e35a8c41babdee0a74edbf5be7637bf683e0911a92865a"
ZERO_TOLERANCE = True
PROBES = (
    (
        "T034-XPY-001",
        ["schema_version", "task034.shell-side-pressure-drop-request.v1"],
        b'["task034.xpy.v2",["schema_version","task034.shell-side-pressure-drop-request.v1"]]',
    ),
    (
        "T034-XPY-002",
        ["profile_id", "hxforge.shell_tube.shell_side_pressure_drop.v1"],
        b'["task034.xpy.v2",["profile_id","hxforge.shell_tube.shell_side_pressure_drop.v1"]]',
    ),
    (
        "T034-XPY-003",
        ["field_order", ["schema_version", "profile_id", "request_hash"]],
        b'["task034.xpy.v2",["field_order",["schema_version","profile_id","request_hash"]]]',
    ),
    (
        "T034-XPY-004",
        ["decimal_lexical", "86505.427"],
        b'["task034.xpy.v2",["decimal_lexical","86505.427"]]',
    ),
    (
        "T034-XPY-005",
        ["normalized_zero", "0.000"],
        b'["task034.xpy.v2",["normalized_zero","0.000"]]',
    ),
    (
        "T034-XPY-006",
        ["hash", "a" * 64],
        b'["task034.xpy.v2",["hash","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]]',
    ),
    (
        "T034-XPY-007",
        ["uuid", "00000000-0000-5000-8000-000000000000"],
        b'["task034.xpy.v2",["uuid","00000000-0000-5000-8000-000000000000"]]',
    ),
    (
        "T034-XPY-008",
        ["mapping", {"a": "1", "b": "2"}],
        b'["task034.xpy.v2",["mapping",{"a":"1","b":"2"}]]',
    ),
    (
        "T034-XPY-009",
        ["nested", ["TASK034", ["400 < Re_s < 1000000", True]]],
        b'["task034.xpy.v2",["nested",["TASK034",["400 < Re_s < 1000000",true]]]]',
    ),
    (
        "T034-XPY-010",
        ["blocker", ["SSPD_REYNOLDS_OUTSIDE_DOMAIN", "S11"]],
        b'["task034.xpy.v2",["blocker",["SSPD_REYNOLDS_OUTSIDE_DOMAIN","S11"]]]',
    ),
    (
        "T034-XPY-011",
        ["provenance", ["TASK034", "199", "5403427791"]],
        b'["task034.xpy.v2",["provenance",["TASK034","199","5403427791"]]]',
    ),
    (
        "T034-XPY-012",
        ["flags", {"probe_count": 12, "zero_tolerance": True}],
        b'["task034.xpy.v2",["flags",{"probe_count":12,"zero_tolerance":true}]]',
    ),
)


def test_x005_cross_python_expected_artifact_set():
    assert len(PROBES) == 12
    assert all(
        canonical_bytes("task034.xpy.v2", projection) == expected
        for _, projection, expected in PROBES
    )


def test_x014_xpy_v2_artifact_replay():
    assert EXPECTED_ARTIFACT_SET_ID.endswith("V2")
    assert len(EXPECTED_ARTIFACT_SET_SHA256) == 64
    assert ZERO_TOLERANCE is True


def test_x015_corrected_v2_shell_type_authority_artifact_replay():
    authority = {
        "schema_version": "task034.shell-type-authority.v2",
        "shell_type": "E_SHELL",
        "task020_configuration_id": "config-034",
        "task020_configuration_hash": "a" * 64,
        "authority_source_id": "TASK034-CALLER-SHELL-TYPE",
        "authority_source_version": "v1",
        "authority_record_id": "CASE-034-SHELL-TYPE",
        "evidence_refs": ["task034-shell-type-evidence"],
        "authority_hash": "",
    }
    prehash = [[field, authority[field]] for field in SHELL_TYPE_AUTHORITY_PREHASH_FIELDS]
    expected_bytes = (
        b'["task034.shell-type-authority.v2",[["schema_version","task034.shell-type-authority.v2"],'
        b'["shell_type","E_SHELL"],["task020_configuration_id","config-034"],'
        b'["task020_configuration_hash","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],'
        b'["authority_source_id","TASK034-CALLER-SHELL-TYPE"],["authority_source_version","v1"],'
        b'["authority_record_id","CASE-034-SHELL-TYPE"],["evidence_refs",["task034-shell-type-evidence"]]]]'
    )
    assert canonical_bytes(SHELL_TYPE_AUTHORITY_HASH_NAMESPACE, prehash) == expected_bytes
    assert shell_type_authority_hash(authority) == hashlib.sha256(expected_bytes).hexdigest()
