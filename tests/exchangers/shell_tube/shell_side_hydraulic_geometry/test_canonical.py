# ruff: noqa: E501
from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.canonical import sha256_hex
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
    authority_canonical_projection,
    recompute_engineering_authority_hash,
)


def test_engineering_authority_hash_is_design_pinned_literal() -> None:
    assert (
        ENGINEERING_AUTHORITY_HASH
        == "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989"
    )


def test_engineering_authority_id_is_derived_from_hash() -> None:
    assert ENGINEERING_AUTHORITY_ID == (
        "urn:hxforge:task031:engineering-authority:v1:" + ENGINEERING_AUTHORITY_HASH
    )


def test_authority_canonical_projection_is_stable() -> None:
    first = authority_canonical_projection()
    second = authority_canonical_projection()
    assert first == second
    assert sha256_hex(first) == sha256_hex(second)


def test_recompute_engineering_authority_hash_is_stable() -> None:
    first = recompute_engineering_authority_hash()
    second = recompute_engineering_authority_hash()
    assert first == second
