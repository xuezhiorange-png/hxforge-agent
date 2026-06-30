"""TASK-010 Phase 2 — Sizing application service.

Orchestrates: SizingApiRequest → validation → projection → result.
Does NOT call DoublePipeService.size() or any assumed-U path.
Does NOT implement the full optimization loop — that's deferred.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from hexagent.api.models import (
    ResolvedProviderAuthority,
    SizingApiRequest,
)
from hexagent.api.projection import project_sizing_api_request
from hexagent.api.registry import CatalogRegistry, ProviderRegistry
from hexagent.domain.models import DesignCase
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.optimization.context import SizingRequestIdentity
from hexagent.optimization.models import (
    CompleteDoublePipeCatalogSnapshot,
    SizingRequest,
)


class SizingServiceResult(BaseModel, frozen=True):
    """Immutable result from the sizing service.

    Carries all Phase 1 projection artifacts plus the resolved provider
    and catalog authorities.  Downstream code (repository, envelope,
    report) must use these artifacts rather than re-projecting.

    Uses Pydantic BaseModel (frozen) so FastAPI can serialize it as a
    response model.
    """

    design_case: DesignCase
    sizing_request: SizingRequest
    sizing_request_identity: SizingRequestIdentity
    effective_solver_params: SolverParams
    resolved_provider: ResolvedProviderAuthority
    resolved_catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]
    canonical_request_snapshot: dict[str, Any]
    request_digest: str


class SizingService:
    """Application service for sizing requests.

    Responsibilities:
    1. Accept validated SizingApiRequest
    2. Resolve provider and catalog authorities via registries
    3. Project to domain models via Phase 1 projection
    4. Return structured result with all artifacts

    Does NOT:
    - Call DoublePipeService.size()
    - Implement optimization loop
    - Manage repository state
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        catalog_registry: CatalogRegistry,
    ) -> None:
        self._provider_registry = provider_registry
        self._catalog_registry = catalog_registry

    def process(self, request: SizingApiRequest) -> SizingServiceResult:
        """Process a sizing request through Phase 1 projection.

        Raises:
            ValueError: on provider mismatch, catalog mismatch,
                duplicate refs, same-identity-different-hash.
        """
        projected = project_sizing_api_request(
            request,
            self._provider_registry,
            self._catalog_registry,
        )
        return SizingServiceResult(
            design_case=projected.design_case,
            sizing_request=projected.sizing_request,
            sizing_request_identity=projected.sizing_request_identity,
            effective_solver_params=projected.effective_solver_params,
            resolved_provider=projected.resolved_provider,
            resolved_catalogs=projected.resolved_catalogs,
            canonical_request_snapshot=projected.canonical_request_snapshot,
            request_digest=projected.request_digest,
        )
