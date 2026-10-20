"""Production R2A contract constants mirrored from Task173 integrated rating service."""

from __future__ import annotations

from typing import Any, Final

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    CELL_ROOT_SOLVER_AUTHORITY_ID,
    OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    CELL_ROOT_SOLVER_AUTHORITY,
    CELL_ROOT_SOLVER_AUTHORITY_HASH,
    OUTER_BOUNDARY_SOLVER_AUTHORITY,
    OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH,
)

R2A_AUTHORITY_ID: Final = "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A"
R2A_AUTHORITY_HASH: Final = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
R2A_EVENT_SCHEMA: Final = "task173.r2a.transient-provider-enclosure-event.v1"
R2A_CERTIFICATE_SCHEMA: Final = "task173.r2a.production-outer-decision-certificate.v1"
R2A_CONTRACT_SCHEMA: Final = "task173.r2a-authority-contract.v1"

Q_PREDICATE_KEYS: Final = tuple(f"Q{i}" for i in range(1, 16))


def production_r2a_contract_payload() -> dict[str, Any]:
    return {
        "schema_version": R2A_CONTRACT_SCHEMA,
        "r2a_authority_id": R2A_AUTHORITY_ID,
        "r2a_authority_hash": R2A_AUTHORITY_HASH,
        "r2a_event_schema": R2A_EVENT_SCHEMA,
        "r2a_certificate_schema": R2A_CERTIFICATE_SCHEMA,
        "cell_root_solver_authority_id": CELL_ROOT_SOLVER_AUTHORITY_ID,
        "cell_root_solver_authority_hash": CELL_ROOT_SOLVER_AUTHORITY_HASH,
        "outer_boundary_solver_authority_id": OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
        "outer_boundary_solver_authority_hash": OUTER_BOUNDARY_SOLVER_AUTHORITY_HASH,
        "cell_root_solver_authority_projection": CELL_ROOT_SOLVER_AUTHORITY,
        "outer_boundary_solver_authority_projection": OUTER_BOUNDARY_SOLVER_AUTHORITY,
        "q_predicate_keys": list(Q_PREDICATE_KEYS),
        "hash_contracts": {
            "r2a_event": "canonical_sha256(event excluding event_hash)",
            "r2a_certificate": "canonical_sha256(certificate excluding certificate_hash)",
        },
        "trigger_semantics": (
            "Production emits R2A events only when _candidate_provider_enclosure_event "
            "returns non-None after all Q1-Q15 predicates hold; absence of trigger does "
            "not imply invalid mesh acceptance."
        ),
        "contract_canonical_hash": canonical_sha256(
            {
                "schema_version": R2A_CONTRACT_SCHEMA,
                "r2a_authority_id": R2A_AUTHORITY_ID,
                "r2a_authority_hash": R2A_AUTHORITY_HASH,
                "cell_root_solver_authority_id": CELL_ROOT_SOLVER_AUTHORITY_ID,
                "outer_boundary_solver_authority_id": OUTER_BOUNDARY_SOLVER_AUTHORITY_ID,
            }
        ),
    }
