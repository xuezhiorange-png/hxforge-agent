"""Internal structural geometry results for downstream V08-03 rating."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates.models import CandidateSpec
from hexagent.shell_geometry_catalogs.models import ShellGeometryRecord


@dataclass(frozen=True)
class V08StructuralGeometryBundle:
    """One structurally valid Task168 chain output plus candidate and shell record."""

    candidate: CandidateSpec
    shell_record: ShellGeometryRecord
    bundle: Any
    task168_request_hash_digest: str
