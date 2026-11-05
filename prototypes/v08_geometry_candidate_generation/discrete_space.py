"""Load and validate V08-02 authorized geometry discrete space."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from prototypes.v08_geometry_candidate_generation.geometry_source_verification import (
    verify_discrete_space_payload,
)

DEFAULT_V08_DISCRETE_SPACE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs/tasks/evidence/V08-02-general-geometry-discrete-space-r1.json"
)

V08_GEOMETRY_SOURCE_AUTHORITY = "V08-GENERAL-GEOMETRY-DISCRETE-SPACE-R1"


@dataclass(frozen=True)
class TubeBaffleLadderStep:
    tube_length_m: Decimal
    baffle_spacing_m: Decimal
    baffle_count: int

    def pair_key(self) -> tuple[str, str, int]:
        return (
            format_engineering_decimal(self.tube_length_m),
            format_engineering_decimal(self.baffle_spacing_m),
            self.baffle_count,
        )


def format_engineering_decimal(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.000001"))
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass(frozen=True)
class V08DiscreteSpaceAuthority:
    authority_id: str
    authority_version: str
    source_class: str
    approval_status: str
    evidence_refs: tuple[str, ...]
    tube_outer_diameter_m: Decimal
    tube_wall_thickness_m: Decimal
    tube_pitch_m: Decimal
    tube_layout: str
    tube_pass_counts: tuple[int, ...]
    shell_inside_diameters_m: tuple[Decimal, ...]
    tube_baffle_ladder: tuple[TubeBaffleLadderStep, ...]
    baffle_type: str
    baffle_cut: Decimal
    construction_family: str
    content_hash: str

    @property
    def allowed_ladder_keys(self) -> frozenset[tuple[str, str, int]]:
        return frozenset(step.pair_key() for step in self.tube_baffle_ladder)

    @property
    def tube_lengths_m(self) -> tuple[Decimal, ...]:
        seen: list[Decimal] = []
        for step in self.tube_baffle_ladder:
            if step.tube_length_m not in seen:
                seen.append(step.tube_length_m)
        return tuple(seen)

    @property
    def baffle_spacings_m(self) -> tuple[Decimal, ...]:
        seen: list[Decimal] = []
        for step in self.tube_baffle_ladder:
            if step.baffle_spacing_m not in seen:
                seen.append(step.baffle_spacing_m)
        return tuple(seen)


def load_v08_discrete_space(path: Path | None = None) -> V08DiscreteSpaceAuthority:
    resolved = path or DEFAULT_V08_DISCRETE_SPACE_PATH
    if not resolved.is_file():
        raise FileNotFoundError(f"V08 geometry discrete space not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return parse_discrete_space_payload(payload, source_path=str(resolved))


def parse_discrete_space_payload(
    payload: dict[str, Any], *, source_path: str
) -> V08DiscreteSpaceAuthority:
    verify_discrete_space_payload(payload)
    authority_id = str(payload["authority_id"])
    tube = payload["tube_geometry"]
    ladder_raw = payload["tube_baffle_ladder"]
    ladder = tuple(
        TubeBaffleLadderStep(
            tube_length_m=Decimal(str(row["tube_length_m"])),
            baffle_spacing_m=Decimal(str(row["baffle_spacing_m"])),
            baffle_count=int(row["baffle_count"]),
        )
        for row in ladder_raw
    )
    shells = tuple(Decimal(str(value)) for value in payload["shell_inside_diameters_m"])
    content_hash = canonical_sha256(payload)
    return V08DiscreteSpaceAuthority(
        authority_id=authority_id,
        authority_version=str(payload["authority_version"]),
        source_class=str(payload["source_class"]),
        approval_status=str(payload["approval_status"]),
        evidence_refs=tuple(str(item) for item in payload.get("evidence_refs", ())),
        tube_outer_diameter_m=Decimal(str(tube["tube_outer_diameter_m"])),
        tube_wall_thickness_m=Decimal(str(tube["tube_wall_thickness_m"])),
        tube_pitch_m=Decimal(str(tube["tube_pitch_m"])),
        tube_layout=str(tube["tube_layout"]),
        tube_pass_counts=tuple(int(value) for value in tube["tube_pass_counts"]),
        shell_inside_diameters_m=shells,
        tube_baffle_ladder=ladder,
        baffle_type=str(payload["baffle_type"]),
        baffle_cut=Decimal(str(payload["baffle_cut"])),
        construction_family=str(payload["construction_family"]),
        content_hash=content_hash,
    )
