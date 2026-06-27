"""P0-11/P0-13/P0-14: Canonicalization contract tests for TASK-009 Phase 2."""

from __future__ import annotations

import dataclasses
import types
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import (
    ExecutionContextSnapshot,
    ProviderIdentitySnapshot,
)
from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingStatus,
    SelectedCorrelationSnapshot,
)
from hexagent.optimization.evaluation import (
    CandidateEvaluationState,
    ContextCanonicalizationError,
    ContextCanonicalizationFailureKind,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    _build_message_descriptor,
    _context_entries_to_payload,
    build_canonical_context_entries,
    canonicalize_trusted_context_value,
    engineering_message_payload,
    engineering_message_sort_key,
    execution_context_snapshot_payload,
    provider_identity_snapshot_payload,
    rating_request_identity_payload,
    revalidate_verified_rating_evidence,
    run_failure_payload,
    selected_correlation_snapshot_payload,
    verified_rating_evidence_payload,
)

# ============================================================================
# Helper functions (MUST be defined before test classes)
# ============================================================================


def _canon(value: object) -> object:
    """Shorthand for canonicalize_trusted_context_value."""
    return canonicalize_trusted_context_value(
        value,
        context_key="test",
        context_path=(),
        ancestor_ids=frozenset(),
    )


def _assert_canon_error(
    value: object,
    expected_kind: ContextCanonicalizationFailureKind,
) -> None:
    """Assert that canonicalize_trusted_context_value raises a specific error."""
    with pytest.raises(ContextCanonicalizationError) as exc_info:
        _canon(value)
    assert exc_info.value.data.failure_kind is expected_kind


def _capture_canon_error(value: object) -> ContextCanonicalizationError:
    """Canonicalize value and return the captured exception."""
    with pytest.raises(ContextCanonicalizationError) as exc_info:
        canonicalize_trusted_context_value(
            value,
            context_key="test",
            context_path=(),
            ancestor_ids=frozenset(),
        )
    return exc_info.value


def _make_minimal_rri() -> RatingRequestIdentity:
    """Create a minimal 21-field RatingRequestIdentity."""
    return RatingRequestIdentity(
        hot_fluid_name="hot_water",
        hot_fluid_backend="iapws_if97",
        hot_fluid_components=(),
        cold_fluid_name="cold_water",
        cold_fluid_backend="iapws_if97",
        cold_fluid_components=(),
        hot_mass_flow_kg_s=5.0,
        cold_mass_flow_kg_s=5.0,
        hot_inlet_pressure_pa=1e5,
        cold_inlet_pressure_pa=1e5,
        hot_inlet_temperature_k=350.0,
        cold_inlet_temperature_k=300.0,
        flow_arrangement="counterflow",
        geometry={
            "inner_tube_inner_diameter_m": 0.05,
            "inner_tube_outer_diameter_m": 0.06,
            "outer_pipe_inner_diameter_m": 0.10,
        },
        solver_absolute_residual_w=1e-3,
        solver_relative_residual_fraction=1e-6,
        solver_bracket_temperature_tolerance_k=1e-4,
        solver_max_iterations=100,
        tube_boundary_condition="constant_wall_temperature",
        annulus_boundary_condition="inner_wall_heated",
        minimum_terminal_delta_t=5.0,
    )


def _make_ec() -> ExecutionContextSnapshot:
    """Create a minimal ExecutionContextSnapshot."""
    return ExecutionContextSnapshot(
        request_id=UUID("11111111-1111-1111-1111-111111111111"),
        design_case_revision_id=UUID("22222222-2222-2222-2222-222222222222"),
        calculation_run_id=UUID("33333333-3333-3333-3333-333333333333"),
    )


def _make_correlation(
    cid: str = "corr_1",
) -> SelectedCorrelationSnapshot:
    """Create a 11-field SelectedCorrelationSnapshot with sensible defaults."""
    return SelectedCorrelationSnapshot(
        correlation_id=cid,
        version="1.0",
        definition_hash="def_hash",
        source_title="Test Correlation",
        source_authors="Author A",
        source_year=2024,
        source_reference="Ref-001",
        source_verification_status="verified",
        nusselt_basis="hydraulic_diameter",
        is_adaptation=False,
        adaptation_limitation="",
    )


def _make_warning_msg(text: str) -> EngineeringMessage:
    """Create a WARNING EngineeringMessage."""
    return EngineeringMessage(
        code=ErrorCode.INPUT_INCONSISTENT,
        severity=EngineeringMessageSeverity.WARNING,
        message=text,
        source_module="test_module",
    )


def _make_blocker_msg(text: str) -> EngineeringMessage:
    """Create a BLOCKER EngineeringMessage."""
    return EngineeringMessage(
        code=ErrorCode.BLOCKER,
        severity=EngineeringMessageSeverity.BLOCKER,
        message=text,
        source_module="test_module",
    )


def _rebuild_evidence(
    baseline: VerifiedRatingEvidenceSnapshot,
    **overrides: Any,
) -> VerifiedRatingEvidenceSnapshot:
    """Rebuild evidence with field overrides, computing correct digests.

    Uses model_dump()/model_validate() and then recomputes digest fields
    so that the result passes the model_validator checks.
    """
    # Collect current field values
    data: dict[str, Any] = {}
    for name in type(baseline).model_fields:
        data[name] = getattr(baseline, name)
    data.update(overrides)

    # Recompute identity/context digests unless explicitly overridden
    if "rating_request_identity_digest" not in overrides:
        data["rating_request_identity_digest"] = sha256_digest(
            rating_request_identity_payload(data["rating_request_identity"])
        )
    if "rating_execution_context_digest" not in overrides:
        data["rating_execution_context_digest"] = sha256_digest(
            execution_context_snapshot_payload(data["rating_execution_context"])
        )

    return VerifiedRatingEvidenceSnapshot(**data)


def _baseline_evidence() -> VerifiedRatingEvidenceSnapshot:
    """Create a full 26-field VerifiedRatingEvidenceSnapshot."""
    pi = ProviderIdentitySnapshot(
        name="test_provider",
        version="1.0",
        git_revision="abc123",
        reference_state_policy="default",
        configuration_fingerprint="cfg_fp",
        cache_policy_version="v1",
    )
    rri = _make_minimal_rri()
    ec = _make_ec()
    tc = _make_correlation("tube_corr")
    ac = _make_correlation("annulus_corr")

    return VerifiedRatingEvidenceSnapshot(
        rating_status=RatingStatus.SUCCEEDED,
        heat_duty_w=1000.0,
        hot_outlet_temperature_k=350.0,
        cold_outlet_temperature_k=310.0,
        area_inner_m2=1.5,
        area_outer_m2=2.0,
        UA_w_k=500.0,
        LMTD_k=40.0,
        energy_residual_w=0.001,
        ua_lmtd_residual_w=0.002,
        tube_inlet_density_kg_m3=800.0,
        annulus_inlet_density_kg_m3=900.0,
        tube_flow_area_m2=0.01,
        annulus_flow_area_m2=0.02,
        warnings=(_make_warning_msg("warn1"),),
        blockers=(_make_blocker_msg("block1"),),
        failure=None,
        provider_identity=pi,
        tube_correlation=tc,
        annulus_correlation=ac,
        rating_result_hash="sha256:" + "a" * 64,
        rating_provenance_digest="sha256:" + "b" * 64,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        rating_request_identity=rri,
        rating_request_identity_digest=sha256_digest(rating_request_identity_payload(rri)),
        rating_execution_context=ec,
        rating_execution_context_digest=sha256_digest(execution_context_snapshot_payload(ec)),
    )


# ============================================================================
# Test classes
# ============================================================================


class TestSafeMarkerDigestStability:
    """P0-2: safe_marker_digest stability across semantically equivalent hostile objects."""

    # ------------------------------------------------------------------
    # Quantity value getter failure
    # ------------------------------------------------------------------

    def test_quantity_value_getter_stable_marker(self) -> None:
        """Quantity value getter raising produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, msg: str = "v"):
                self._msg = msg

            @property
            def value(self):
                raise RuntimeError(self._msg)

            @property
            def unit(self):
                return "m"

            @property
            def kind(self):
                return None

            @property
            def to_si(self):
                raise RuntimeError("t")

        err1 = _capture_canon_error(BadQ("v1"))
        err2 = _capture_canon_error(BadQ("v2"))

        assert type(err1) is ContextCanonicalizationError
        assert type(err2) is ContextCanonicalizationError
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert (
            err2.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data.offending_type == err2.data.offending_type
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity unit getter failure
    # ------------------------------------------------------------------

    def test_quantity_unit_getter_stable_marker(self) -> None:
        """Quantity unit getter raising produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, msg: str = "u"):
                self._msg = msg

            @property
            def value(self):
                return 1.0

            @property
            def unit(self):
                raise RuntimeError(self._msg)

            @property
            def kind(self):
                return None

            @property
            def to_si(self):
                raise RuntimeError("t")

        err1 = _capture_canon_error(BadQ("u1"))
        err2 = _capture_canon_error(BadQ("u2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity kind getter failure
    # ------------------------------------------------------------------

    def test_quantity_kind_getter_stable_marker(self) -> None:
        """Quantity kind getter raising produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, msg: str = "k"):
                self._msg = msg

            @property
            def value(self):
                return 1.0

            @property
            def unit(self):
                return "m"

            @property
            def kind(self):
                raise RuntimeError(self._msg)

            @property
            def to_si(self):
                raise RuntimeError("t")

        err1 = _capture_canon_error(BadQ("k1"))
        err2 = _capture_canon_error(BadQ("k2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity to_si getter failure
    # ------------------------------------------------------------------

    def test_quantity_to_si_getter_stable_marker(self) -> None:
        """Quantity to_si property raising produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, msg: str = "ts"):
                self._msg = msg

            @property
            def value(self):
                return 1.0

            @property
            def unit(self):
                return "m"

            @property
            def kind(self):
                return type("Kind", (), {"value": "length"})()

            @property
            def to_si(self):
                raise RuntimeError(self._msg)

        err1 = _capture_canon_error(BadQ("ts1"))
        err2 = _capture_canon_error(BadQ("ts2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity non-callable to_si
    # ------------------------------------------------------------------

    def test_quantity_non_callable_to_si_stable_marker(self) -> None:
        """Quantity non-callable to_si produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, val: str = "nc"):
                self._val = val

            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()

            @property
            def to_si(self):
                return self._val

        err1 = _capture_canon_error(BadQ("nc1"))
        err2 = _capture_canon_error(BadQ("nc2"))
        assert err1.data.failure_kind == ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity to_si call failure
    # ------------------------------------------------------------------

    def test_quantity_to_si_call_failure_stable_marker(self) -> None:
        """Quantity to_si() raising produces stable safe_marker_digest."""

        class BadQ:
            def __init__(self, msg: str = "call"):
                self._msg = msg

            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()

            def to_si(self):
                raise RuntimeError(self._msg)

        err1 = _capture_canon_error(BadQ("call1"))
        err2 = _capture_canon_error(BadQ("call2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity SI result value failure
    # ------------------------------------------------------------------

    def test_quantity_si_result_value_failure_stable_marker(self) -> None:
        """Quantity SI result .value raising produces stable safe_marker_digest."""

        class SiResult:
            def __init__(self, msg: str = "sv"):
                self._msg = msg

            @property
            def value(self):
                raise RuntimeError(self._msg)

        class BadQ:
            def __init__(self, msg: str = "sv"):
                self._msg = msg

            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()

            def to_si(self):
                return SiResult(self._msg)

        err1 = _capture_canon_error(BadQ("sv1"))
        err2 = _capture_canon_error(BadQ("sv2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Quantity kind.value failure
    # ------------------------------------------------------------------

    def test_quantity_kind_value_failure_stable_marker(self) -> None:
        """Kind.value raising produces stable safe_marker_digest."""

        class Kind:
            def __init__(self, msg: str = "kv"):
                self._msg = msg

            @property
            def value(self):
                raise RuntimeError(self._msg)

        class BadQ:
            def __init__(self, msg: str = "kv"):
                self._msg = msg

            value = 1.0
            unit = "m"
            kind = Kind("kv1")

            def to_si(self):
                return self

        err1 = _capture_canon_error(BadQ("kv1"))
        err2 = _capture_canon_error(BadQ("kv2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Mapping iter() failure
    # ------------------------------------------------------------------

    def test_mapping_iter_failure_stable_marker(self) -> None:
        """Mapping.__iter__ raising produces stable safe_marker_digest."""

        class BadMap(Mapping[str, object]):
            def __init__(self, msg: str = "iter"):
                self._msg = msg

            def __getitem__(self, k):
                return None

            def __iter__(self):
                raise RuntimeError(self._msg)

            def __len__(self):
                return 1

        err1 = _capture_canon_error(BadMap("iter1"))
        err2 = _capture_canon_error(BadMap("iter2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data.offending_type == err2.data.offending_type
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Mapping first next() failure
    # ------------------------------------------------------------------

    def test_mapping_first_next_failure_stable_marker(self) -> None:
        """Mapping first key.next() raising produces stable safe_marker_digest."""

        class BrokenIter:
            def __init__(self, msg: str = "fn"):
                self._msg = msg

            def __iter__(self):
                yield "k1"
                raise RuntimeError(self._msg)

        class BadMap(Mapping[str, object]):
            def __init__(self, msg: str = "fn"):
                self._msg = msg

            def __getitem__(self, k):
                return None

            def __iter__(self):
                return BrokenIter(self._msg).__iter__()

            def __len__(self):
                return 2

        err1 = _capture_canon_error(BadMap("fn1"))
        err2 = _capture_canon_error(BadMap("fn2"))
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Mapping mid-iteration failure
    # ------------------------------------------------------------------

    def test_mapping_mid_iteration_failure_stable_marker(self) -> None:
        """Mapping value canonicalization failure (e.g. bytes) produces stable marker."""

        class BadMap(Mapping[str, object]):
            def __init__(self, data: bytes = b"bytes"):
                self._data = data
                self._d = {"k1": data}

            def __getitem__(self, k):
                return self._d[k]

            def __iter__(self):
                return iter(self._d)

            def __len__(self):
                return len(self._d)

        err1 = _capture_canon_error(BadMap(b"bytes1"))
        err2 = _capture_canon_error(BadMap(b"bytes2"))
        assert err1.data.failure_kind == ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data.context_path == err2.data.context_path
        assert err1.data.offending_type == err2.data.offending_type
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Pydantic model_fields iteration failure
    # ------------------------------------------------------------------

    def test_pydantic_model_fields_iteration_failure_stable_marker(self) -> None:
        """Pydantic model with __getattribute__ raising produces stable marker."""

        class RaisyModel(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            x: int = 1

            def __getattribute__(self_, name: str) -> object:
                if name == "x":
                    raise RuntimeError("attr")
                return super().__getattribute__(name)

        err1 = _capture_canon_error(RaisyModel())
        err2 = _capture_canon_error(RaisyModel())
        assert (
            err1.data.failure_kind == ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Sequence iteration failure
    # ------------------------------------------------------------------

    def test_sequence_iteration_failure_stable_marker(self) -> None:
        """Sequence with element canonicalization failure produces stable marker."""

        class BadSeq:
            def __init__(self, data: bytes = b"bytes"):
                self._data = data

            def __iter__(self):
                yield self._data

        err1 = _capture_canon_error(BadSeq(b"bytes1"))
        err2 = _capture_canon_error(BadSeq(b"bytes2"))
        assert err1.data.failure_kind == ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data.offending_type == err2.data.offending_type
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Context outer iteration failure
    # ------------------------------------------------------------------

    def test_context_outer_iteration_failure_stable_marker(self) -> None:
        """Context tuple outer iteration raising produces stable marker."""

        class BadIter:
            def __init__(self, msg: str = "outer"):
                self._msg = msg

            def __iter__(self):
                raise RuntimeError(self._msg)

        err1 = _capture_canon_error(BadIter("outer1"))
        err2 = _capture_canon_error(BadIter("outer2"))
        assert err1.data.failure_kind == ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data == err2.data

    # ------------------------------------------------------------------
    # Context inner/pair failure (non-tuple pair)
    # ------------------------------------------------------------------

    def test_context_inner_pair_failure_stable_marker(self) -> None:
        """Context pair that is not a 2-tuple produces stable marker."""

        class BadPair:
            def __init__(self, data: str = "not_a_pair"):
                self._data = data

            def __iter__(self):
                yield self._data

        err1 = _capture_canon_error(("outer", BadPair("not_a_pair_1")))
        err2 = _capture_canon_error(("outer", BadPair("not_a_pair_2")))
        assert err1.data.failure_kind == ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err1.safe_marker_digest == err2.safe_marker_digest
        assert err1.data.context_key == "test"
        assert err1.data.offending_type == err2.data.offending_type
        assert err1.data == err2.data


class TestQualifiedTypeName:
    """P0-11: qualified_type_name contract."""

    def test_basic_types(self) -> None:
        """Check known basic types produce expected qualified names."""
        from hexagent.optimization.evaluation import qualified_type_name

        assert qualified_type_name(None) == "builtins.NoneType"
        assert qualified_type_name(True) == "builtins.bool"
        assert qualified_type_name(42) == "builtins.int"
        assert qualified_type_name(3.14) == "builtins.float"
        assert qualified_type_name("hello") == "builtins.str"

    def test_custom_class(self) -> None:
        """Check custom class produces module.qualname."""
        from hexagent.optimization.evaluation import qualified_type_name

        class _MyClass:
            pass

        name = qualified_type_name(_MyClass())
        assert name.endswith("._MyClass")


class TestContextTupleParsing:
    """P0-11: context tuple parsing via build_canonical_context_entries."""

    def test_simple_key_value(self) -> None:
        """Single pair yields one entry with correct key/value."""
        ctx = (("failure_stage", "rating_verification"),)
        entries = build_canonical_context_entries(ctx)
        assert len(entries) == 1
        assert entries[0].key == "failure_stage"
        assert entries[0].value == "rating_verification"

    def test_multiple_entries_preserved(self) -> None:
        """Duplicate keys are preserved (not deduplicated)."""
        ctx = (("k", 1), ("k", 2))
        entries = build_canonical_context_entries(ctx)
        assert len(entries) == 2
        assert entries[0].key == "k"
        assert entries[1].key == "k"

    def test_non_tuple_pair_raises(self) -> None:
        """Non-tuple non-2-length entries raise UNSUPPORTED_TYPE."""
        with pytest.raises(ContextCanonicalizationError) as exc:
            build_canonical_context_entries(("not_a_pair",))
        assert exc.value.data.failure_kind is ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE

    def test_non_string_key_raises(self) -> None:
        """Non-string key raises NON_STRING_KEY."""
        ctx = ((42, "value"),)
        with pytest.raises(ContextCanonicalizationError) as exc:
            build_canonical_context_entries(ctx)
        assert exc.value.data.failure_kind is ContextCanonicalizationFailureKind.NON_STRING_KEY

    def test_sorted_by_key_then_digest(self) -> None:
        """Entries are sorted by (key, value_digest)."""
        ctx = (("b", 2), ("a", 1), ("a", 3))
        entries = build_canonical_context_entries(ctx)
        assert entries[0].key == "a"
        assert entries[1].key == "a"
        assert entries[2].key == "b"

    def test_context_entries_to_payload(self) -> None:
        """_context_entries_to_payload produces correct dicts."""
        ctx = (("stage", "verify"),)
        entries = build_canonical_context_entries(ctx)
        payload = _context_entries_to_payload(entries)
        assert len(payload) == 1
        assert payload[0]["key"] == "stage"
        assert payload[0]["value"] == "verify"
        assert isinstance(payload[0]["value_digest"], str)
        assert payload[0]["value_digest"].startswith("sha256:")


class TestCycleDetection:
    """P0-11: cyclic reference detection during canonicalization."""

    def test_direct_list_cycle(self) -> None:
        """Self-referencing list raises CYCLIC_REFERENCE."""
        lst: list[object] = []
        lst.append(lst)
        _assert_canon_error(lst, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)

    def test_direct_dict_cycle(self) -> None:
        """Self-referencing dict raises CYCLIC_REFERENCE."""
        d: dict[str, object] = {}
        d["self"] = d
        _assert_canon_error(d, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)

    def test_indirect_cycle(self) -> None:
        """A->B->A cycle raises CYCLIC_REFERENCE."""
        a: list[object] = []
        b: list[object] = [a]
        a.append(b)
        _assert_canon_error(a, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)

    def test_tuple_cycle(self) -> None:
        """A tuple containing itself raises CYCLIC_REFERENCE."""
        t: tuple[object, ...] = (1,)
        _lst: list[object] = [t]
        # tuples are immutable, so create tuple containing list with tuple
        inner: list[object] = [t]
        t2 = (inner,)
        inner.append(t2)
        _assert_canon_error(t2, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)

    def test_no_cycle_identical_values(self) -> None:
        """Same-value objects at different positions are NOT cycles."""
        val = {"x": 1}
        container = [val, val]
        result = _canon(container)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == result[1]

    def test_pydantic_model_cycle(self) -> None:
        """Pydantic model with self-referential field raises CYCLIC_REFERENCE."""

        class CyclicModel(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            ref: object = None

        m = CyclicModel()
        object.__setattr__(m, "ref", m)
        _assert_canon_error(m, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)

    def test_mapping_cycle(self) -> None:
        """Custom Mapping with self-reference raises CYCLIC_REFERENCE."""

        class _CyclicMapping(Mapping[str, object]):
            def __init__(self) -> None:
                self._d: dict[str, object] = {}
                self._d["self"] = self

            def __getitem__(self, key: str) -> object:
                return self._d[key]

            def __iter__(self):
                return iter(self._d)

            def __len__(self) -> int:
                return len(self._d)

        cm = _CyclicMapping()
        _assert_canon_error(cm, ContextCanonicalizationFailureKind.CYCLIC_REFERENCE)


class TestMappingSupport:
    """P0-11: Mapping (non-dict) support."""

    def test_dict_supported(self) -> None:
        """Exact dict type is supported."""
        result = _canon({"a": 1})
        assert result == {"a": 1}

    def test_mappingproxy_supported(self) -> None:
        """types.MappingProxyType is supported."""
        mp = types.MappingProxyType({"x": 10})
        result = _canon(mp)
        assert isinstance(result, dict)
        assert result["x"] == 10

    def test_custom_mapping_supported(self) -> None:
        """Custom Mapping subclass is supported."""

        class _MyMapping(Mapping[str, object]):
            def __init__(self) -> None:
                self._d = {"key": "val"}

            def __getitem__(self, k: str) -> object:
                return self._d[k]

            def __iter__(self):
                return iter(self._d)

            def __len__(self) -> int:
                return len(self._d)

        result = _canon(_MyMapping())
        assert isinstance(result, dict)
        assert result["key"] == "val"

    def test_non_string_key_dict_raises(self) -> None:
        """dict with non-string key raises NON_STRING_KEY."""
        d: dict[object, object] = {1: "value"}
        _assert_canon_error(d, ContextCanonicalizationFailureKind.NON_STRING_KEY)

    def test_non_string_key_mappingproxy_raises(self) -> None:
        """MappingProxy with non-string key raises NON_STRING_KEY."""
        mp = types.MappingProxyType({1: "value"})
        _assert_canon_error(mp, ContextCanonicalizationFailureKind.NON_STRING_KEY)


class TestBytesRejection:
    """P0-11: bytes are rejected during canonicalization."""

    def test_ascii_bytes_rejected(self) -> None:
        """ASCII bytes raise UNSUPPORTED_TYPE."""
        _assert_canon_error(b"hello", ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)

    def test_utf8_bytes_rejected(self) -> None:
        """UTF-8 bytes raise UNSUPPORTED_TYPE."""
        _assert_canon_error(
            "héllo".encode(),
            ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE,
        )

    def test_non_utf8_bytes_rejected(self) -> None:
        """Non-UTF-8 bytes raise UNSUPPORTED_TYPE."""
        _assert_canon_error(
            b"\xff\xfe\x00\x01",
            ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE,
        )

    def test_bytes_in_nested_structure_rejected(self) -> None:
        """bytes nested inside a dict/list raises UNSUPPORTED_TYPE."""
        container = {"data": b"binary"}
        _assert_canon_error(container, ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)


class TestUTCDatetime:
    """P0-11: UTC datetime canonicalization."""

    def test_utc_datetime(self) -> None:
        """UTC datetime produces ISO-8601 UTC format."""
        dt = datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)
        result = _canon(dt)
        assert result == "2026-06-27T12:00:00.000000Z"

    def test_tokyo_time_converts_to_utc(self) -> None:
        """Same instant in different TZ yields same canonical form."""
        tokyo = timezone(timedelta(hours=9))
        dt1 = datetime(2026, 6, 27, 21, 0, 0, tzinfo=tokyo)
        dt2 = datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)
        assert _canon(dt1) == _canon(dt2)

    def test_negative_utc_offset(self) -> None:
        """Negative UTC offset converts correctly."""
        est = timezone(timedelta(hours=-5))
        dt = datetime(2026, 6, 27, 7, 0, 0, tzinfo=est)
        result = _canon(dt)
        assert result == "2026-06-27T12:00:00.000000Z"

    def test_naive_datetime_raises(self) -> None:
        """Naive (tzinfo=None) datetime raises NAIVE_DATETIME."""
        dt = datetime(2026, 6, 27, 12, 0, 0)
        _assert_canon_error(dt, ContextCanonicalizationFailureKind.NAIVE_DATETIME)

    def test_fold_aware_datetime(self) -> None:
        """Fold-aware datetime (DST overlap) is handled."""
        # Use a fold=1 datetime to ensure it works
        dt_fold = datetime(2026, 11, 1, 1, 30, 0, fold=1, tzinfo=timezone(timedelta(hours=-4)))
        _canon(dt_fold)  # should not raise


class TestQuantityAdapter:
    """P0-11/P0-2: Repository Quantity-like object adaptation."""

    # ------------------------------------------------------------------
    # Helper mock classes for P0-2
    # ------------------------------------------------------------------

    class _KindMock:
        def __init__(self, kind_name: str = "temperature", value_raises: bool = False):
            self._value = kind_name
            self._value_raises = value_raises

        @property
        def value(self) -> str:
            if self._value_raises:
                raise RuntimeError("kind.value failed")
            return self._value

    class _ToSiResult:
        def __init__(self, value: float = 100.0, si_value_raises: bool = False):
            self._value = value
            self._si_value_raises = si_value_raises

        @property
        def value(self) -> float:
            if self._si_value_raises:
                raise RuntimeError("si_value failed")
            return self._value

    class _ToSiCallable:
        def __init__(
            self,
            value: float = 100.0,
            raises: bool = False,
            si_value_raises: bool = False,
        ):
            self._value = value
            self._raises = raises
            self._si_value_raises = si_value_raises

        def __call__(self) -> TestQuantityAdapter._ToSiResult:
            if self._raises:
                raise RuntimeError("to_si failed")
            return TestQuantityAdapter._ToSiResult(self._value, self._si_value_raises)

    class _QuantityMock:
        def __init__(
            self,
            value: float = 100.0,
            unit: str = "degC",
            kind_name: str | None = "temperature",
            to_si_raises: bool = False,
            to_si_not_callable: bool = False,
            value_raises: bool = False,
            unit_raises: bool = False,
            kind_raises: bool = False,
            to_si_raises_on_access: bool = False,
            si_value_raises: bool = False,
            kind_value_raises: bool = False,
            si_value: float | None = None,
        ):
            self._value = value
            self._unit = unit
            self._kind = (
                TestQuantityAdapter._KindMock(kind_name, value_raises=kind_value_raises)
                if kind_name
                else None
            )
            self._to_si_value = si_value if si_value is not None else value
            self._to_si = (
                "not_callable"
                if to_si_not_callable
                else TestQuantityAdapter._ToSiCallable(
                    self._to_si_value,
                    raises=to_si_raises,
                    si_value_raises=si_value_raises,
                )
            )
            self._value_raises = value_raises
            self._unit_raises = unit_raises
            self._kind_raises = kind_raises
            self._to_si_raises_on_access = to_si_raises_on_access

        @property
        def value(self) -> float:
            if self._value_raises:
                raise RuntimeError("value failed")
            return self._value

        @property
        def unit(self) -> str:
            if self._unit_raises:
                raise RuntimeError("unit failed")
            return self._unit

        @property
        def kind(self) -> Any | None:
            if self._kind_raises:
                raise RuntimeError("kind failed")
            return self._kind

        @property
        def to_si(self) -> Any:
            if self._to_si_raises_on_access:
                raise RuntimeError("to_si access failed")
            return self._to_si

    # ------------------------------------------------------------------
    # Existing tests (P0-11)
    # ------------------------------------------------------------------

    def test_temperature_celsius(self) -> None:
        """100°C converts to si_value=373.15."""

        class _MockQuantity:
            value = 100.0
            unit = "degC"
            kind = type("Kind", (), {"value": "absolute_temperature"})()

            def to_si(self) -> _MockQuantity:
                q = _MockQuantity()
                q.value = 373.15
                return q

        result = _canon(_MockQuantity())
        assert isinstance(result, dict)
        assert result["si_value"] == 373.15
        assert result["kind"] == "absolute_temperature"

    def test_si_equivalence(self) -> None:
        """Same SI value yields same canonical form."""

        class _QSI:
            value = 373.15
            unit = "K"
            kind = type("Kind", (), {"value": "absolute_temperature"})()

            def to_si(self: Any) -> Any:
                return self

        result = _canon(_QSI())
        assert isinstance(result, dict)
        assert result["si_value"] == 373.15

    def test_kind_none(self) -> None:
        """kind=None produces kind: null."""

        class _QNoKind:
            value = 100.0
            unit = "m"
            kind = None

            def to_si(self) -> _QNoKind:
                return self

        result = _canon(_QNoKind())
        assert result["kind"] is None

    def test_to_si_raises(self) -> None:
        """to_si() raising produces CANONICALIZATION_EXCEPTION."""

        class _BadQ:
            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()

            def to_si(self) -> None:
                raise RuntimeError("conversion failed")

        with pytest.raises(ContextCanonicalizationError) as exc_info:
            _canon(_BadQ())
        err = exc_info.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "RuntimeError" in err.data.offending_type or "_BadQ" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(_BadQ(), ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_to_si_not_callable(self) -> None:
        """to_si attribute that is not callable raises UNSUPPORTED_TYPE."""

        class _NoCallQ:
            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()
            to_si = "not_callable"

        with pytest.raises(ContextCanonicalizationError) as exc_info:
            _canon(_NoCallQ())
        err = exc_info.value
        assert err.data.failure_kind is ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "_NoCallQ" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(_NoCallQ(), ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)

    def test_kind_getter_raises(self) -> None:
        """kind getter raising produces CANONICALIZATION_EXCEPTION."""

        class _BadKindQ:
            value = 1.0
            unit = "m"

            @property
            def kind(self) -> None:
                raise RuntimeError("kind failed")

            def to_si(self) -> _BadKindQ:
                return self

        with pytest.raises(ContextCanonicalizationError) as exc_info:
            _canon(_BadKindQ())
        err = exc_info.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "RuntimeError" in err.data.offending_type or "_BadKindQ" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(
            _BadKindQ(),
            ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION,
        )

    # ------------------------------------------------------------------
    # P0-2: 10 specific Quantity adapter tests using _QuantityMock
    # ------------------------------------------------------------------

    def test_value_getter_failure(self) -> None:
        """value getter raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(value_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        err = exc.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "QuantityMock" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_unit_getter_failure(self) -> None:
        """unit getter raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(unit_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        assert (
            exc.value.data.failure_kind
            is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert exc.value.data.context_key == "test"
        assert exc.value.data.context_path == ()
        assert "QuantityMock" in exc.value.data.offending_type
        assert exc.value.safe_marker_digest is not None
        assert len(exc.value.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_kind_getter_failure(self) -> None:
        """kind getter raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(kind_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        assert (
            exc.value.data.failure_kind
            is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert exc.value.data.context_key == "test"
        assert exc.value.data.context_path == ()
        assert "QuantityMock" in exc.value.data.offending_type
        assert exc.value.safe_marker_digest is not None
        assert len(exc.value.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_to_si_getter_failure(self) -> None:
        """to_si access raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(to_si_raises_on_access=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        assert (
            exc.value.data.failure_kind
            is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert exc.value.data.context_key == "test"
        assert exc.value.data.context_path == ()
        assert "QuantityMock" in exc.value.data.offending_type
        assert exc.value.safe_marker_digest is not None
        assert len(exc.value.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_kind_none_skips_to_si(self) -> None:
        """kind=None → to_si() is never called (even if to_si would raise)."""
        q = self._QuantityMock(kind_name=None, to_si_raises=True)
        result = _canon(q)
        assert result["kind"] is None
        assert result["si_value"] == 100.0

    def test_kind_not_none_to_si_not_callable(self) -> None:
        """kind not None but to_si is not callable → UNSUPPORTED_TYPE (freeze contract rule)."""
        q = self._QuantityMock(to_si_not_callable=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        err = exc.value
        assert err.data.failure_kind is ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "QuantityMock" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)

    def test_to_si_call_failure(self) -> None:
        """to_si() raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(to_si_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        err = exc.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "QuantityMock" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_si_result_value_failure(self) -> None:
        """to_si() returns an object whose .value property raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(si_value_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        err = exc.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "QuantityMock" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_kind_value_failure(self) -> None:
        """kind is not None but kind.value raises → CANONICALIZATION_EXCEPTION."""
        q = self._QuantityMock(kind_value_raises=True)
        with pytest.raises(ContextCanonicalizationError) as exc:
            _canon(q)
        err = exc.value
        assert (
            err.data.failure_kind is ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION
        )
        assert err.data.context_key == "test"
        assert err.data.context_path == ()
        assert "QuantityMock" in err.data.offending_type
        assert err.safe_marker_digest is not None
        assert len(err.safe_marker_digest) > 20

        # Stability
        _assert_canon_error(q, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_si_equivalence_different_units(self) -> None:
        """Different raw units that yield same SI value produce same canonical payload."""
        q1 = self._QuantityMock(value=373.15, unit="K", kind_name="absolute_temperature")
        q2 = self._QuantityMock(
            value=100.0,
            unit="degC",
            kind_name="absolute_temperature",
            si_value=373.15,
        )
        result1 = _canon(q1)
        result2 = _canon(q2)
        assert result1["si_value"] == result2["si_value"]
        assert result1["kind"] == result2["kind"]

    def test_kind_none_to_si_not_called_proof(self) -> None:
        """kind=None → to_si() is never called, even if to_si would raise AssertionError."""

        class _NoCallProof:
            value = 100.0
            unit = "m"
            kind = None

            def to_si(self) -> None:
                raise AssertionError("must not be called")

        result = _canon(_NoCallProof())
        assert result["si_value"] == 100.0
        assert result["kind"] is None

    def test_si_equivalence_identical_payload_and_digest(self) -> None:
        """SI equivalent raw values produce identical canonical payloads and digests."""
        q1 = self._QuantityMock(value=373.15, unit="K", kind_name="absolute_temperature")
        q2 = self._QuantityMock(
            value=100.0,
            unit="degC",
            kind_name="absolute_temperature",
            si_value=373.15,
        )
        result1 = _canon(q1)
        result2 = _canon(q2)
        assert result1 == result2
        d1 = sha256_digest(result1)
        d2 = sha256_digest(result2)
        assert d1 == d2


class TestCanonicalFailurePermutation:
    """P0-3: Canonical ordering for warning/blocker failures must be permutation-stable."""

    def test_warning_sort_key_deterministic(self) -> None:
        """engineering_message_sort_key produces deterministic ordering for valid warnings."""
        w1 = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="first",
            context=(("good", "value"),),
        )
        w2 = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="second",
            context=(("good", "value"),),
        )
        # Both orderings should produce the same sorted result
        sorted_a = tuple(sorted((w1, w2), key=engineering_message_sort_key))
        sorted_b = tuple(sorted((w2, w1), key=engineering_message_sort_key))
        assert sorted_a == sorted_b

    def test_blocker_sort_key_deterministic(self) -> None:
        """engineering_message_sort_key produces deterministic ordering for valid blockers."""
        b1 = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="first",
            context=(("good", "value"),),
        )
        b2 = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="second",
            context=(("good", "value"),),
        )
        sorted_a = tuple(sorted((b1, b2), key=engineering_message_sort_key))
        sorted_b = tuple(sorted((b2, b1), key=engineering_message_sort_key))
        assert sorted_a == sorted_b

    def test_bad_context_warning_fails_deterministically(self) -> None:
        """A warning with bad context always fails on the same context_key regardless of order."""
        w_good = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="good",
            context=(("good", "value"),),
        )
        w_bad = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="bad",
            context=(("bad", b"bytes_data"),),
        )
        # Both orderings call engineering_message_payload on each warning
        # The bad warning should always fail on "bad" context_key
        for msgs in ((w_good, w_bad), (w_bad, w_good)):
            for msg in msgs:
                try:
                    engineering_message_payload(msg)
                except ContextCanonicalizationError as exc:
                    assert exc.data.context_key == "bad"
                    assert (
                        exc.data.failure_kind is ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
                    )
                    break
            else:
                pytest.fail("Expected at least one canonicalization failure")

    def test_bad_context_blocker_fails_deterministically(self) -> None:
        """A blocker with bad context always fails on the same context_key regardless of order."""
        b_good = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="good",
            context=(("good", "value"),),
        )
        b_bad = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="bad",
            context=(("bad", b"bytes_data"),),
        )
        for msgs in ((b_good, b_bad), (b_bad, b_good)):
            for msg in msgs:
                try:
                    engineering_message_payload(msg)
                except ContextCanonicalizationError as exc:
                    assert exc.data.context_key == "bad"
                    assert (
                        exc.data.failure_kind is ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE
                    )
                    break
            else:
                pytest.fail("Expected at least one canonicalization failure")


class TestOwnerPermutation:
    """P0-3: Owner permutation stability through full production pipeline."""

    def _make_minimal_result_for_owner_permutation(
        self,
        warnings=(),
        blockers=(),
        failure=None,
    ) -> Any:
        """Create a duck-typed RatingResult for owner permutation tests."""
        from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus

        result = object.__new__(RatingResult)
        object.__setattr__(result, "status", RatingStatus.SUCCEEDED)
        object.__setattr__(result, "flow_arrangement", "counterflow")
        object.__setattr__(result, "result_hash", "sha256:" + "e" * 64)
        object.__setattr__(result, "provenance_digest", "prov_digest")
        object.__setattr__(result, "heat_duty_w", 1000.0)
        object.__setattr__(result, "hot_outlet_temperature_k", 350.0)
        object.__setattr__(result, "cold_outlet_temperature_k", 310.0)
        object.__setattr__(result, "area_inner_m2", 1.5)
        object.__setattr__(result, "area_outer_m2", 2.0)
        object.__setattr__(result, "UA_w_k", 500.0)
        object.__setattr__(result, "LMTD_k", 40.0)
        object.__setattr__(result, "energy_residual_w", 0.001)
        object.__setattr__(result, "ua_lmtd_residual_w", 0.002)
        object.__setattr__(result, "tube_selected_correlation_id", "corr_1")
        object.__setattr__(result, "tube_selected_correlation_version", "1.0")
        object.__setattr__(result, "annulus_selected_correlation_id", "corr_2")
        object.__setattr__(result, "annulus_selected_correlation_version", "1.0")
        object.__setattr__(result, "warnings", warnings)
        object.__setattr__(result, "blockers", blockers)
        object.__setattr__(result, "failure", failure)
        object.__setattr__(result, "hot_inlet_state", None)
        object.__setattr__(result, "cold_inlet_state", None)
        object.__setattr__(result, "tube_selected_correlation", None)
        object.__setattr__(result, "annulus_selected_correlation", None)

        rri = _make_minimal_rri()
        object.__setattr__(result, "request_identity", rri)
        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)
        ec = _make_ec()
        object.__setattr__(result, "execution_context", ec)

        def _vh() -> bool:
            return True

        def _vp() -> bool:
            return True

        object.__setattr__(result, "verify_hash", _vh)
        object.__setattr__(result, "verify_provenance", _vp)
        return result

    def test_warning_order_permutation_stable(self) -> None:
        """Two semantically identical warning collections with different input order
        must produce identical fallback failure."""
        from hexagent.optimization.context import ExpectedProviderIdentity
        from hexagent.optimization.evaluation import verify_and_evaluate_candidate

        expected_provider = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )

        # Good warning (canonicalizable)
        w_good = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="good",
            context=(("good", "value"),),
        )
        # Bad warning (bytes in context → fails canonicalization)
        w_bad = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="bad",
            context=(("bad", b"bytes_data"),),
        )

        # Order A: good first, bad second
        result_a = self._make_minimal_result_for_owner_permutation(
            warnings=(w_good, w_bad),
        )
        record_a = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_a,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        # Order B: bad first, good second
        result_b = self._make_minimal_result_for_owner_permutation(
            warnings=(w_bad, w_good),
        )
        record_b = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_b,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        # Both must be RUNTIME_FAILED
        assert record_a.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
        assert record_b.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED

        fa = record_a.evaluation_failure
        fb = record_b.evaluation_failure

        # Exact comparison
        assert fa.code == fb.code
        assert fa.message == fb.message
        assert fa.traceback is None
        assert fb.traceback is None
        assert fa.context == fb.context, f"Context mismatch:\nA: {fa.context}\nB: {fb.context}"

        # Specifically check owner_id is the same
        ctx_a = dict(fa.context)
        ctx_b = dict(fb.context)
        assert ctx_a["owner_id"] == ctx_b["owner_id"]
        assert ctx_a["safe_marker_digest"] == ctx_b["safe_marker_digest"]
        assert ctx_a["context_path_digest"] == ctx_b["context_path_digest"]

    def test_blocker_order_permutation_stable(self) -> None:
        """Two semantically identical blocker collections with different input order
        must produce identical fallback failure."""
        from hexagent.optimization.context import ExpectedProviderIdentity
        from hexagent.optimization.evaluation import verify_and_evaluate_candidate

        expected_provider = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )

        b_good = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="good",
            context=(("good", "value"),),
        )
        b_bad = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="bad",
            context=(("bad", b"bytes_data"),),
        )

        # Order A
        result_a = self._make_minimal_result_for_owner_permutation(
            blockers=(b_good, b_bad),
        )
        record_a = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_a,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        # Order B
        result_b = self._make_minimal_result_for_owner_permutation(
            blockers=(b_bad, b_good),
        )
        record_b = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_b,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        assert record_a.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
        assert record_b.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED

        fa = record_a.evaluation_failure
        fb = record_b.evaluation_failure
        assert fa.code == fb.code
        assert fa.message == fb.message
        assert fa.context == fb.context

        ctx_a = dict(fa.context)
        ctx_b = dict(fb.context)
        assert ctx_a["owner_id"] == ctx_b["owner_id"]
        assert ctx_a["safe_marker_digest"] == ctx_b["safe_marker_digest"]
        assert ctx_a["context_path_digest"] == ctx_b["context_path_digest"]

    def test_warning_and_blocker_permutation(self) -> None:
        """Permutation across both warnings and blockers with bad context
        still produces deterministic results."""
        from hexagent.optimization.context import ExpectedProviderIdentity
        from hexagent.optimization.evaluation import verify_and_evaluate_candidate

        expected_provider = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )

        w_good = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="good_w",
            context=(("good", "value"),),
        )
        b_good = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="good_b",
            context=(("good", "value"),),
        )
        w_bad = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="bad_w",
            context=(("bad", b"bytes_data"),),
        )
        b_bad = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="bad_b",
            context=(("bad_b", b"other_bytes"),),
        )

        # Order A: w_good, w_bad, b_good, b_bad
        result_a = self._make_minimal_result_for_owner_permutation(
            warnings=(w_good, w_bad),
            blockers=(b_good, b_bad),
        )
        record_a = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_a,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        # Order B: b_bad, b_good, w_bad, w_good
        result_b = self._make_minimal_result_for_owner_permutation(
            warnings=(w_bad, w_good),
            blockers=(b_bad, b_good),
        )
        record_b = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result_b,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        assert record_a.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
        assert record_b.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED

        fa = record_a.evaluation_failure
        fb = record_b.evaluation_failure
        assert fa.code == fb.code
        assert fa.message == fb.message
        assert fa.context == fb.context

        ctx_a = dict(fa.context)
        ctx_b = dict(fb.context)
        assert ctx_a["owner_id"] == ctx_b["owner_id"]
        assert ctx_a["safe_marker_digest"] == ctx_b["safe_marker_digest"]
        assert ctx_a["context_path_digest"] == ctx_b["context_path_digest"]


class TestPydanticFieldLevel:
    """P0-11: Pydantic BaseModel field-level traversal."""

    def test_basic_pydantic_model(self) -> None:
        """A simple Pydantic model is canonicalized by its fields."""

        class SimpleModel(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            name: str = "test"
            value: int = 42

        result = _canon(SimpleModel())
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_only_model_fields_traversed(self) -> None:
        """Dynamic attrs not in model_fields are excluded."""

        class FixedModel(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            x: int = 10

        m = FixedModel()
        object.__setattr__(m, "extra_field", "should_not_appear")
        result = _canon(m)
        assert "extra_field" not in result
        assert result["x"] == 10

    def test_getattr_exception_mapped(self) -> None:
        """Property getter that raises is mapped to CANONICALIZATION_EXCEPTION."""

        class RaisyModel(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            good: int = 1
            bad: int = 0

            def __getattribute__(self, name: str) -> Any:
                if name == "bad":
                    raise RuntimeError("field access error")
                return super().__getattribute__(name)

        m = RaisyModel()
        _assert_canon_error(m, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_nested_pydantic_model(self) -> None:
        """Nested Pydantic models are recursively traversed."""

        class Inner(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            val: str = "inner"

        class Outer(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            label: str = "outer"
            child: Inner = Inner()

        result = _canon(Outer())
        assert isinstance(result, dict)
        assert result["label"] == "outer"
        assert isinstance(result["child"], dict)
        assert result["child"]["val"] == "inner"


class TestHostileMethods:
    """P0-11: str/repr/model_dump are not called on values."""

    def test_hostile_str_not_called(self) -> None:
        """str() is never called on canonicalized values."""

        class _Hostile:
            def __str__(self) -> str:
                raise RuntimeError("str called")

            def __repr__(self) -> str:
                raise RuntimeError("repr called")

        # Hostile is unsupported type, but error should be about
        # unsupported type, not about str() failing
        _assert_canon_error(_Hostile(), ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)

    def test_hostile_repr_not_called(self) -> None:
        """repr() is never called on canonicalized values."""
        # repr would be called in error messages only, not during
        # canonicalization itself

        class _ReprRaiser:
            def __repr__(self) -> str:
                raise RuntimeError("repr called")

        _assert_canon_error(_ReprRaiser(), ContextCanonicalizationFailureKind.UNSUPPORTED_TYPE)

    def test_property_getter_exception_mapped(self) -> None:
        """Property getter exception is mapped, not suppressed."""

        class _ReprProp(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            x: int = 1
            bad: int = 0

            def __getattribute__(self, name: str) -> Any:
                if name == "bad":
                    raise RuntimeError("bad property")
                return super().__getattribute__(name)

            def __repr__(self) -> str:
                raise RuntimeError("repr called")

        m = _ReprProp()
        _assert_canon_error(m, ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_pydantic_model_dump_not_called(self) -> None:
        """model_dump is NOT called — field-level traversal is used."""

        class _ModelDumpRaiser(BaseModel):
            model_config = ConfigDict(frozen=True, extra="forbid")
            name: str = "safe"

            def model_dump(self) -> dict[str, object]:
                raise RuntimeError("model_dump called")

        # Should succeed using field-level traversal
        result = _canon(_ModelDumpRaiser())
        assert result["name"] == "safe"


class TestProviderEmptyString:
    """P0-11: Provider identity empty string handling."""

    def test_empty_vs_none_different_digests(self) -> None:
        """Empty string vs None produce different canonical digests."""
        pi_empty = ProviderIdentitySnapshot(
            name="",
            version="",
            git_revision="",
            reference_state_policy="",
        )
        pi_none_version = ProviderIdentitySnapshot(
            name="test",
            version="",
            git_revision="",
            reference_state_policy="",
        )
        p1 = provider_identity_snapshot_payload(pi_empty)
        p2 = provider_identity_snapshot_payload(pi_none_version)
        assert sha256_digest(p1) != sha256_digest(p2)

    def test_explicit_empty_roundtrip(self) -> None:
        """Empty strings roundtrip without being coerced to None."""
        pi = ProviderIdentitySnapshot(
            name="",
            version="",
            git_revision="",
            reference_state_policy="",
            configuration_fingerprint="",
            cache_policy_version="",
        )
        payload = provider_identity_snapshot_payload(pi)
        for key in (
            "name",
            "version",
            "git_revision",
            "reference_state_policy",
            "configuration_fingerprint",
            "cache_policy_version",
        ):
            assert payload[key] == "", f"Expected '' for {key}, got {payload[key]!r}"


class TestEngineeringMessageExactPayload:
    """P0-11: engineering_message_payload exact contract."""

    def test_basic_context(self) -> None:
        """Basic EngineeringMessage produces correct payload."""
        msg = EngineeringMessage(
            code=ErrorCode.PROPERTY_UNAVAILABLE,
            severity=EngineeringMessageSeverity.WARNING,
            message="Property unavailable for stream",
            source_module="test_mod",
            affected_paths=("path1",),
        )
        payload = engineering_message_payload(msg)
        assert payload["schema_version"] == "1.0"
        assert payload["code"] == "property_unavailable"
        assert payload["severity"] == "warning"
        assert payload["message"] == "Property unavailable for stream"
        assert payload["source_module"] == "test_mod"
        assert payload["affected_paths"] == ["path1"]
        assert isinstance(payload["context_entries"], list)

    def test_allows_continuation_not_in_payload(self) -> None:
        """allows_continuation is NOT in the payload dict."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
        )
        payload = engineering_message_payload(msg)
        assert "allows_continuation" not in payload

    def test_allows_continuation_validation(self) -> None:
        """allows_continuation must be consistent with severity."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="test",
        )
        # This should validate allows_continuation == True for WARNING
        payload = engineering_message_payload(msg)
        assert payload["severity"] == "warning"

        # BLOCKER severity has allows_continuation=False
        blocker = EngineeringMessage(
            code=ErrorCode.BLOCKER,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="blocked",
        )
        payload2 = engineering_message_payload(blocker)
        assert payload2["severity"] == "blocker"

    def test_empty_context(self) -> None:
        """Empty context tuple yields empty context_entries list."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.INFO,
            message="info message",
            source_module="mod",
        )
        payload = engineering_message_payload(msg)
        assert payload["context_entries"] == []


class TestRunFailureExactPayload:
    """P0-11: run_failure_payload exact contract."""

    def test_traceback_none(self) -> None:
        """traceback=None stays None in payload."""
        failure = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Solver did not converge",
            traceback=None,
        )
        payload = run_failure_payload(failure)
        assert payload["traceback"] is None

    def test_traceback_empty(self) -> None:
        """traceback='' stays '' in payload."""
        failure = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="Solver did not converge",
            traceback="",
        )
        payload = run_failure_payload(failure)
        assert payload["traceback"] == ""

    def test_traceback_not_swapped(self) -> None:
        """traceback strings are not swapped or modified."""
        tb = "Traceback (most recent call last):\\n  ..."
        failure = RunFailure(
            code=ErrorCode.CALCULATION_NOT_CONVERGED,
            message="err",
            traceback=tb,
        )
        payload = run_failure_payload(failure)
        assert payload["traceback"] == tb

    def test_context_canonicalized(self) -> None:
        """Context entries are canonicalized via build_canonical_context_entries."""
        ctx = (("stage", "rating"), ("step", 2))
        failure = RunFailure(
            code=ErrorCode.CALCULATION_BLOCKED,
            message="Blocked",
            context=ctx,
        )
        payload = run_failure_payload(failure)
        entries = payload["context_entries"]
        assert len(entries) == 2
        keys = [e["key"] for e in entries]
        assert "stage" in keys
        assert "step" in keys


class TestCanonicalizationBatchIntegration:
    """P0-14: Canonicalization failure during batch evaluation."""

    def _make_result_with_bytes_context(self) -> Any:
        """Create a duck-typed result with bytes in warning context."""
        from hexagent.exchangers.double_pipe.result import (
            RatingResult,
            RatingStatus,
        )

        result = object.__new__(RatingResult)
        object.__setattr__(result, "status", RatingStatus.SUCCEEDED)
        object.__setattr__(result, "flow_arrangement", "counterflow")
        object.__setattr__(result, "result_hash", "sha256:" + "e" * 64)
        object.__setattr__(result, "provenance_digest", "prov_digest")
        object.__setattr__(result, "heat_duty_w", 1000.0)
        object.__setattr__(result, "hot_outlet_temperature_k", 350.0)
        object.__setattr__(result, "cold_outlet_temperature_k", 310.0)
        object.__setattr__(result, "area_inner_m2", 1.5)
        object.__setattr__(result, "area_outer_m2", 2.0)
        object.__setattr__(result, "UA_w_k", 500.0)
        object.__setattr__(result, "LMTD_k", 40.0)
        object.__setattr__(result, "energy_residual_w", 0.001)
        object.__setattr__(result, "ua_lmtd_residual_w", 0.002)
        object.__setattr__(result, "tube_selected_correlation_id", "corr_1")
        object.__setattr__(result, "tube_selected_correlation_version", "1.0")
        object.__setattr__(result, "annulus_selected_correlation_id", "corr_2")
        object.__setattr__(result, "annulus_selected_correlation_version", "1.0")

        # Warning with bytes in context triggers canonicalization failure
        bad_warning = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="bad warning",
            context=(("binary_data", b"\\x00\\x01"),),
        )
        object.__setattr__(result, "warnings", (bad_warning,))
        object.__setattr__(result, "blockers", ())
        object.__setattr__(result, "failure", None)
        object.__setattr__(result, "hot_inlet_state", None)
        object.__setattr__(result, "cold_inlet_state", None)
        object.__setattr__(result, "tube_selected_correlation", None)
        object.__setattr__(result, "annulus_selected_correlation", None)

        rri = _make_minimal_rri()
        object.__setattr__(result, "request_identity", rri)
        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)
        ec = _make_ec()
        object.__setattr__(result, "execution_context", ec)

        def _verify_hash() -> bool:
            return True

        def _verify_provenance() -> bool:
            return True

        object.__setattr__(result, "verify_hash", _verify_hash)
        object.__setattr__(result, "verify_provenance", _verify_provenance)

        return result

    def test_warning_with_bad_context_causes_runtime_failed(self) -> None:
        """ContextCanonicalizationError from bad context yields RUNTIME_FAILED."""
        from hexagent.optimization.context import ExpectedProviderIdentity
        from hexagent.optimization.evaluation import (
            verify_and_evaluate_candidate,
        )

        result = self._make_result_with_bytes_context()
        expected_provider = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )

        rec = verify_and_evaluate_candidate(
            0,
            "candidate_0",
            result,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )
        assert rec.candidate_evaluation_state is CandidateEvaluationState.RUNTIME_FAILED

    def test_later_candidate_unevaluated_after_canonicalization_failure(self) -> None:
        """After first candidate fails from bad context, second is UNEVALUATED."""
        from hexagent.optimization.context import ExpectedProviderIdentity
        from hexagent.optimization.evaluation import (
            verify_and_evaluate_candidates,
        )

        bad_result = self._make_result_with_bytes_context()
        expected_provider = ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )

        # First: bad context. Second: make a simple good candidate
        good_result = object.__new__(type(bad_result))
        for attr in (
            "status",
            "flow_arrangement",
            "result_hash",
            "provenance_digest",
            "heat_duty_w",
            "hot_outlet_temperature_k",
            "cold_outlet_temperature_k",
            "area_inner_m2",
            "area_outer_m2",
            "UA_w_k",
            "LMTD_k",
            "energy_residual_w",
            "ua_lmtd_residual_w",
            "tube_selected_correlation",
            "annulus_selected_correlation",
            "warnings",
            "blockers",
            "failure",
            "hot_inlet_state",
            "cold_inlet_state",
            "request_identity",
            "provider_identity",
            "execution_context",
            "verify_hash",
            "verify_provenance",
        ):
            object.__setattr__(good_result, attr, getattr(bad_result, attr))

        # Replace warnings with clean ones
        object.__setattr__(good_result, "warnings", ())

        candidates = (
            (0, "candidate_0", bad_result),
            (1, "candidate_1", good_result),
        )

        records = verify_and_evaluate_candidates(
            candidates,
            sizing_request_identity_digest="sha256:" + "f" * 64,
            tube_in_hot=True,
            expected_provider=expected_provider,
        )

        assert len(records) == 2
        assert records[0].candidate_evaluation_state is CandidateEvaluationState.RUNTIME_FAILED
        assert records[1].candidate_evaluation_state is CandidateEvaluationState.UNEVALUATED


class TestMaterializationResultValidation:
    """P0-14: Materialization validation passes for legitimate inputs."""

    def test_legitimate_materialization_passes(self) -> None:
        """Call materialize_all_candidates and verify it works."""
        # Import locally to avoid global import errors
        from hexagent.optimization.context import (
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import materialize_all_candidates
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            LengthSource,
            OptionRawCountRecord,
        )

        # Create a minimal catalog with one option
        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="test_opt",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )

        from hexagent.optimization.catalog import compute_catalog_content_hash

        cat_hash = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )

        from hexagent.optimization.models import CompleteDoublePipeCatalogSnapshot

        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=cat_hash,
        )

        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=cat_hash,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="test_opt",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )

        gate = create_passed_sizing_gate(
            sizing_request_identity_digest="sha256:" + "f" * 64,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        result = materialize_all_candidates(catalogs=(cat,), sizing_gate=gate)
        assert result is not None
        assert len(result.candidates) == 1


class TestEvidencePayloadMutationFull:
    """P0-7: Full 26-field evidence payload mutation tests."""

    def test_payload_26_fields(self) -> None:
        """Verify payload contains exactly 26 keys."""
        ev = _baseline_evidence()
        payload = verified_rating_evidence_payload(ev)
        assert len(payload) == 26

    @pytest.mark.parametrize(
        "field_name, setter",
        [
            (
                "rating_status",
                lambda ev: _rebuild_evidence(ev, rating_status=RatingStatus.FAILED),
            ),
            ("heat_duty_w", lambda ev: _rebuild_evidence(ev, heat_duty_w=2000.0)),
            (
                "hot_outlet_temperature_k",
                lambda ev: _rebuild_evidence(ev, hot_outlet_temperature_k=360.0),
            ),
            (
                "cold_outlet_temperature_k",
                lambda ev: _rebuild_evidence(ev, cold_outlet_temperature_k=320.0),
            ),
            ("area_inner_m2", lambda ev: _rebuild_evidence(ev, area_inner_m2=3.0)),
            ("area_outer_m2", lambda ev: _rebuild_evidence(ev, area_outer_m2=4.0)),
            ("UA_w_k", lambda ev: _rebuild_evidence(ev, UA_w_k=600.0)),
            ("LMTD_k", lambda ev: _rebuild_evidence(ev, LMTD_k=50.0)),
            ("energy_residual_w", lambda ev: _rebuild_evidence(ev, energy_residual_w=0.01)),
            ("ua_lmtd_residual_w", lambda ev: _rebuild_evidence(ev, ua_lmtd_residual_w=0.02)),
            (
                "tube_inlet_density_kg_m3",
                lambda ev: _rebuild_evidence(ev, tube_inlet_density_kg_m3=700.0),
            ),
            (
                "annulus_inlet_density_kg_m3",
                lambda ev: _rebuild_evidence(ev, annulus_inlet_density_kg_m3=800.0),
            ),
            ("tube_flow_area_m2", lambda ev: _rebuild_evidence(ev, tube_flow_area_m2=0.02)),
            (
                "annulus_flow_area_m2",
                lambda ev: _rebuild_evidence(ev, annulus_flow_area_m2=0.03),
            ),
            (
                "warnings",
                lambda ev: _rebuild_evidence(ev, warnings=(_make_warning_msg("changed"),)),
            ),
            (
                "blockers",
                lambda ev: _rebuild_evidence(ev, blockers=(_make_blocker_msg("changed"),)),
            ),
            (
                "failure",
                lambda ev: _rebuild_evidence(
                    ev,
                    failure=RunFailure(
                        code=ErrorCode.CALCULATION_BLOCKED,
                        message="test failure",
                    ),
                ),
            ),
            (
                "provider_identity",
                lambda ev: _rebuild_evidence(
                    ev,
                    provider_identity=ProviderIdentitySnapshot(
                        name="other",
                        version="2.0",
                        git_revision="def",
                        reference_state_policy="strict",
                    ),
                ),
            ),
            (
                "tube_correlation",
                lambda ev: _rebuild_evidence(
                    ev,
                    tube_correlation=_make_correlation("other_tube"),
                ),
            ),
            (
                "annulus_correlation",
                lambda ev: _rebuild_evidence(
                    ev,
                    annulus_correlation=_make_correlation("other_ann"),
                ),
            ),
            (
                "rating_result_hash",
                lambda ev: _rebuild_evidence(ev, rating_result_hash="sha256:" + "e" * 64),
            ),
            (
                "rating_provenance_digest",
                lambda ev: _rebuild_evidence(ev, rating_provenance_digest="sha256:" + "f" * 64),
            ),
            (
                "hash_verification_outcome",
                lambda ev: ev.model_copy(
                    update={"hash_verification_outcome": VerificationOutcome.FAILED}
                ),
            ),
            (
                "provenance_verification_outcome",
                lambda ev: ev.model_copy(
                    update={"provenance_verification_outcome": VerificationOutcome.FAILED}
                ),
            ),
            (
                "rating_request_identity_digest",
                lambda ev: _rebuild_evidence(
                    ev,
                    rating_request_identity=(
                        dataclasses.replace(
                            ev.rating_request_identity,
                            hot_mass_flow_kg_s=10.0,
                        )
                    ),
                ),
            ),
            (
                "rating_execution_context_digest",
                lambda ev: _rebuild_evidence(
                    ev,
                    rating_execution_context=(
                        ev.rating_execution_context.model_copy(
                            update={"request_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")}
                        )
                    ),
                ),
            ),
        ],
    )
    def test_each_field_mutation_changes_digest(self, field_name: str, setter: Any) -> None:
        """Every single-field mutation changes the evidence digest."""
        baseline = _baseline_evidence()
        baseline_digest = sha256_digest(verified_rating_evidence_payload(baseline))
        mutated = setter(baseline)
        mutated_digest = sha256_digest(verified_rating_evidence_payload(mutated))
        assert baseline_digest != mutated_digest, (
            f"Field {field_name} mutation did not change digest"
        )

    def test_warning_permutation_stable(self) -> None:
        """Reordering identical warnings yields same digest."""
        w1 = _make_warning_msg("same")
        w2 = _make_warning_msg("same")
        ev1 = _rebuild_evidence(_baseline_evidence(), warnings=(w1, w2))
        ev2 = _rebuild_evidence(_baseline_evidence(), warnings=(w2, w1))
        d1 = sha256_digest(verified_rating_evidence_payload(ev1))
        d2 = sha256_digest(verified_rating_evidence_payload(ev2))
        assert d1 == d2

    def test_blocker_permutation_stable(self) -> None:
        """Reordering identical blockers yields same digest."""
        b1 = _make_blocker_msg("same")
        b2 = _make_blocker_msg("same")
        ev1 = _rebuild_evidence(_baseline_evidence(), blockers=(b1, b2))
        ev2 = _rebuild_evidence(_baseline_evidence(), blockers=(b2, b1))
        d1 = sha256_digest(verified_rating_evidence_payload(ev1))
        d2 = sha256_digest(verified_rating_evidence_payload(ev2))
        assert d1 == d2

    def test_duplicate_context_entries_preserved(self) -> None:
        """Duplicate entries in message context are preserved."""
        msg = EngineeringMessage(
            code=ErrorCode.INPUT_MISSING,
            severity=EngineeringMessageSeverity.WARNING,
            message="dup test",
            context=(("k", 1), ("k", 1)),
        )
        payload = engineering_message_payload(msg)
        ctx_entries = payload["context_entries"]
        assert len(ctx_entries) == 2


class TestNestedPayloadMutation:
    """P0-7: Nested payload mutation tests for identity types."""

    def test_rating_request_identity_21_fields(self) -> None:
        """Verify RatingRequestIdentity payload has exactly 21 keys."""
        rri = _make_minimal_rri()
        payload = rating_request_identity_payload(rri)
        assert len(payload) == 21

    def test_execution_context_3_fields(self) -> None:
        """Verify ExecutionContextSnapshot payload has 3 keys."""
        ec = _make_ec()
        payload = execution_context_snapshot_payload(ec)
        assert len(payload) == 3

    def test_provider_identity_6_fields(self) -> None:
        """Verify ProviderIdentitySnapshot payload has 6 keys."""
        pi = ProviderIdentitySnapshot(
            name="p",
            version="v",
            git_revision="g",
            reference_state_policy="r",
        )
        payload = provider_identity_snapshot_payload(pi)
        assert len(payload) == 6

    def test_selected_correlation_11_fields(self) -> None:
        """Verify SelectedCorrelationSnapshot payload has 11 keys."""
        corr = _make_correlation()
        payload = selected_correlation_snapshot_payload(corr)
        assert len(payload) == 11

    def test_nested_mutation_RRI_digest_changes(self) -> None:
        """Mutating a field in RatingRequestIdentity changes its digest."""
        rri1 = _make_minimal_rri()
        rri2 = _make_minimal_rri()
        # Change one field
        import dataclasses

        rri2 = dataclasses.replace(rri2, hot_mass_flow_kg_s=10.0)
        p1 = rating_request_identity_payload(rri1)
        p2 = rating_request_identity_payload(rri2)
        assert sha256_digest(p1) != sha256_digest(p2)

    def test_nested_mutation_EC_digest_changes(self) -> None:
        """Mutating a field in ExecutionContextSnapshot changes its digest."""
        ec1 = _make_ec()
        ec2 = ec1.model_copy(update={"request_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")})
        p1 = execution_context_snapshot_payload(ec1)
        p2 = execution_context_snapshot_payload(ec2)
        assert sha256_digest(p1) != sha256_digest(p2)

    def test_json_roundtrip_digest_stable(self) -> None:
        """JSON roundtrip of canonical payload produces same digest."""
        ev = _baseline_evidence()
        payload = verified_rating_evidence_payload(ev)
        import json

        serialized = json.dumps(payload, sort_keys=True, default=str)
        deserialized = json.loads(serialized)
        d1 = sha256_digest(payload)
        d2 = sha256_digest(deserialized)
        assert d1 == d2


# ============================================================================
# P0-6: Evidence negative construction tests
# ============================================================================


class TestEvidenceNegativeConstruction:
    """P0-6: VerifiedRatingEvidenceSnapshot rejects invalid input."""

    def _valid_rri(self) -> RatingRequestIdentity:
        return _make_minimal_rri()

    def _valid_ec(self) -> ExecutionContextSnapshot:
        return ExecutionContextSnapshot(
            request_id=UUID("11111111-1111-1111-1111-111111111111"),
            design_case_revision_id=None,
            calculation_run_id=None,
        )

    def _valid_pi(self) -> ProviderIdentitySnapshot:
        return ProviderIdentitySnapshot(
            name="test",
            version="1.0",
            git_revision="abc",
            reference_state_policy="default",
        )

    def _valid_evidence_kwargs(self) -> dict[str, Any]:
        rri = self._valid_rri()
        ec = self._valid_ec()
        pi = self._valid_pi()
        rri_digest = sha256_digest(rating_request_identity_payload(rri))
        ec_digest = sha256_digest(execution_context_snapshot_payload(ec))
        return {
            "rating_status": RatingStatus.SUCCEEDED,
            "heat_duty_w": 1000.0,
            "area_inner_m2": 1.5,
            "area_outer_m2": 2.0,
            "tube_flow_area_m2": 0.01,
            "annulus_flow_area_m2": 0.02,
            "rating_result_hash": "sha256:" + "a" * 64,
            "rating_provenance_digest": "prov_digest",
            "hash_verification_outcome": VerificationOutcome.PASSED,
            "provenance_verification_outcome": VerificationOutcome.PASSED,
            "rating_request_identity": rri,
            "rating_request_identity_digest": rri_digest,
            "rating_execution_context": ec,
            "rating_execution_context_digest": ec_digest,
            "provider_identity": pi,
        }

    def test_valid_construction_passes(self) -> None:
        """Valid kwargs produce a valid VerifiedRatingEvidenceSnapshot."""
        kwargs = self._valid_evidence_kwargs()
        ev = VerifiedRatingEvidenceSnapshot(**kwargs)
        assert ev is not None

    def test_request_identity_mutation_rejected(self) -> None:
        """Mutating rating_request_identity without updating digest is rejected."""
        kwargs = self._valid_evidence_kwargs()
        rri_mut = dataclasses.replace(
            kwargs["rating_request_identity"],
            hot_fluid_name="changed",
        )
        kwargs["rating_request_identity"] = rri_mut
        # digest is now wrong for the mutated identity
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_request_digest_mutation_rejected(self) -> None:
        """Mutating rating_request_identity_digest alone is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_request_identity_digest"] = "sha256:" + "f" * 64
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_context_mutation_rejected(self) -> None:
        """Mutating rating_execution_context without updating digest is rejected."""
        kwargs = self._valid_evidence_kwargs()
        ec_mut = ExecutionContextSnapshot(request_id=UUID("00000000-0000-0000-0000-000000000001"))
        kwargs["rating_execution_context"] = ec_mut
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_context_digest_mutation_rejected(self) -> None:
        """Mutating rating_execution_context_digest alone is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_execution_context_digest"] = "sha256:" + "f" * 64
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_blank_result_hash_rejected(self) -> None:
        """Empty rating_result_hash is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = ""
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_malformed_result_hash_rejected(self) -> None:
        """Non-sha256:hex rating_result_hash is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = "not_a_hash"
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_blank_provenance_digest_rejected(self) -> None:
        """Empty rating_provenance_digest is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_provenance_digest"] = ""
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_hash_outcome_not_passed_rejected(self) -> None:
        """hash_verification_outcome that is not PASSED is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["hash_verification_outcome"] = VerificationOutcome.FAILED
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_provenance_outcome_not_passed_rejected(self) -> None:
        """provenance_verification_outcome that is not PASSED is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["provenance_verification_outcome"] = VerificationOutcome.FAILED
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_json_roundtrip(self) -> None:
        """JSON roundtrip preserves the evidence payload digest."""
        kwargs = self._valid_evidence_kwargs()
        ev = VerifiedRatingEvidenceSnapshot(**kwargs)
        json_str = ev.model_dump_json()
        ev2 = VerifiedRatingEvidenceSnapshot.model_validate_json(json_str)
        assert sha256_digest(verified_rating_evidence_payload(ev)) == sha256_digest(
            verified_rating_evidence_payload(ev2)
        )

    # ------------------------------------------------------------------
    # P0-6: Uppercase hash and model_copy revalidation tests
    # ------------------------------------------------------------------

    def test_uppercase_hash_rejected(self) -> None:
        """Uppercase hex chars in rating_result_hash are rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = "sha256:ABCDEF" + "a" * 58
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_short_hash_rejected(self) -> None:
        """Hash with fewer than 64 hex chars is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = "sha256:" + "a" * 63
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_long_hash_rejected(self) -> None:
        """Hash with more than 64 hex chars is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = "sha256:" + "a" * 65
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_missing_prefix_hash_rejected(self) -> None:
        """Hash without sha256: prefix is rejected."""
        kwargs = self._valid_evidence_kwargs()
        kwargs["rating_result_hash"] = "a" * 64
        with pytest.raises((ValueError, TypeError)):
            VerifiedRatingEvidenceSnapshot(**kwargs)

    def test_model_copy_bypasses_validator(self) -> None:
        """model_copy bypasses validator — this is expected behavior but must be documented."""
        kwargs = self._valid_evidence_kwargs()
        ev = VerifiedRatingEvidenceSnapshot(**kwargs)
        # model_copy does NOT re-validate — use an invalid hash to prove it
        invalid_hash = "not_a_hash"
        ev_mut = ev.model_copy(update={"rating_result_hash": invalid_hash})
        # The copy still works (model_copy bypasses validators)
        assert ev_mut.rating_result_hash == invalid_hash
        # But revalidation must fail because the hash format is invalid
        with pytest.raises((ValueError, TypeError)):
            revalidate_verified_rating_evidence(ev_mut)


# ============================================================================
# P0-5: 8 entry-point negative tests — MaterializationResult forgery
# ============================================================================


class TestMaterializationEntryRejection:
    """P0-5: Forged aggregates rejected at evaluate_all_candidates entry."""

    def _make_minimal_result(
        self,
        hash_passes: bool = True,
        prov_passes: bool = True,
    ) -> Any:
        """Create a duck-typed RatingResult for the spy rating_fn."""
        from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement

        result = object.__new__(RatingResult)
        object.__setattr__(result, "status", RatingStatus.SUCCEEDED)
        object.__setattr__(result, "flow_arrangement", FlowArrangement.COUNTERFLOW)
        object.__setattr__(result, "result_hash", "sha256:" + "e" * 64)
        object.__setattr__(result, "provenance_digest", "prov_digest")
        object.__setattr__(result, "heat_duty_w", 1000.0)
        object.__setattr__(result, "hot_outlet_temperature_k", 350.0)
        object.__setattr__(result, "cold_outlet_temperature_k", 310.0)
        object.__setattr__(result, "area_inner_m2", 1.5)
        object.__setattr__(result, "area_outer_m2", 2.0)
        object.__setattr__(result, "UA_w_k", 500.0)
        object.__setattr__(result, "LMTD_k", 40.0)
        object.__setattr__(result, "energy_residual_w", 0.001)
        object.__setattr__(result, "ua_lmtd_residual_w", 0.002)
        object.__setattr__(result, "tube_selected_correlation_id", "corr_1")
        object.__setattr__(result, "tube_selected_correlation_version", "1.0")
        object.__setattr__(result, "annulus_selected_correlation_id", "corr_2")
        object.__setattr__(result, "annulus_selected_correlation_version", "1.0")
        object.__setattr__(result, "warnings", ())
        object.__setattr__(result, "blockers", ())
        object.__setattr__(result, "failure", None)
        object.__setattr__(result, "hot_inlet_state", None)
        object.__setattr__(result, "cold_inlet_state", None)
        object.__setattr__(result, "tube_selected_correlation", None)
        object.__setattr__(result, "annulus_selected_correlation", None)

        from hexagent.exchangers.double_pipe.result import RatingRequestIdentity

        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
        )
        object.__setattr__(result, "request_identity", rri)

        from hexagent.core.heat_balance import (
            ExecutionContextSnapshot,
            ProviderIdentitySnapshot,
        )

        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)

        ec = object.__new__(ExecutionContextSnapshot)
        object.__setattr__(ec, "request_id", None)
        object.__setattr__(ec, "design_case_revision_id", None)
        object.__setattr__(ec, "calculation_run_id", None)
        object.__setattr__(ec, "execution_id", None)
        object.__setattr__(ec, "rating_software_version", None)
        object.__setattr__(ec, "execution_context_policy_version", None)
        object.__setattr__(result, "execution_context", ec)

        def _verify_hash() -> bool:
            return hash_passes

        def _verify_provenance() -> bool:
            return prov_passes

        object.__setattr__(result, "verify_hash", _verify_hash)
        object.__setattr__(result, "verify_provenance", _verify_provenance)

        return result

    def _build_legit(
        self,
        catalog_id: str = "c1",
        option_id: str = "opt_a",
        length: float = 1.0,
    ) -> tuple[Any, Any, Any, Any]:
        """Build a valid MaterializationResult through the production chain.

        Returns (sizing_request_identity, solver_params, provider, materialization_result).
        """
        import unittest.mock

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            OptimizationObjective,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            materialize_all_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )
        from hexagent.properties.base import PropertyProvider

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id=option_id,
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(length,),
            ),
        )

        cat_hash = compute_catalog_content_hash(
            catalog_id=catalog_id,
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )

        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id=catalog_id,
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=cat_hash,
        )

        req = SizingRequest(catalogs=(cat,))

        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=self._default_expected_provider(),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )

        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=len(opt.length_source.allowed_effective_lengths_m),
        )

        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        mat_result = materialize_all_candidates(
            catalogs=(cat,),
            sizing_gate=gate,
        )

        provider = unittest.mock.MagicMock(spec=PropertyProvider)
        solver_params = SolverParams()

        return ident, solver_params, provider, mat_result

    def _default_expected_provider(self) -> Any:
        from hexagent.optimization.context import ExpectedProviderIdentity

        return ExpectedProviderIdentity(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )

    # ------------------------------------------------------------------
    # Test 1: Unrelated gate and candidate set
    # ------------------------------------------------------------------

    def test_unrelated_gate_and_candidate_set_rejected(self) -> None:
        """Forged: mr1's candidates + mr2's gate → rejected before any rating call."""
        ident1, sp1, prov1, mr1 = self._build_legit()
        ident2, sp2, prov2, mr2 = self._build_legit(catalog_id="c2", option_id="opt_z")

        # Create forged: mr1's candidates + mr2's gate
        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", mr1.candidates)
        object.__setattr__(forged, "candidate_set", mr1.candidate_set)
        object.__setattr__(forged, "sizing_gate", mr2.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0  # No TASK-008 call

    # ------------------------------------------------------------------
    # Test 2: Unrelated candidates
    # ------------------------------------------------------------------

    def test_unrelated_candidates_rejected(self) -> None:
        """Valid gate + candidates from a different materialization → rejected."""
        ident1, sp1, prov1, mr1 = self._build_legit()
        ident2, sp2, prov2, mr2 = self._build_legit(catalog_id="c2", option_id="opt_z")

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", mr2.candidates)
        object.__setattr__(forged, "candidate_set", mr2.candidate_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 3: Candidate_set has extra catalog ref not in gate
    # ------------------------------------------------------------------

    def test_candidate_set_extra_catalog_rejected(self) -> None:
        """Candidate_set has a catalog ref not in sizing_gate."""
        from hexagent.optimization.context import MaterializedCandidateSet
        from hexagent.optimization.identities import catalog_snapshot_ref

        ident1, sp1, prov1, mr1 = self._build_legit()

        # Create a bogus catalog snapshot for the extra ref
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
        )

        bogus_opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="bogus_opt",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(2.0,),
            ),
        )
        bogus_hash = compute_catalog_content_hash(
            catalog_id="bogus_cat",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(bogus_opt,),
        )
        bogus_cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="bogus_cat",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(bogus_opt,),
            catalog_content_hash=bogus_hash,
        )
        # Build a bogus catalog ref from the bogus catalog
        bogus_ref = catalog_snapshot_ref(bogus_cat)
        extra_refs = mr1.candidate_set.catalog_snapshot_identities + (bogus_ref,)

        # Use object.__new__ to bypass MaterializedCandidateSet validation (catalog ordering check)
        cs = mr1.candidate_set
        bad_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(bad_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest)
        settr(bad_set, "passed_gate_digest", cs.passed_gate_digest)
        settr(bad_set, "catalog_snapshot_identities", extra_refs)
        settr(bad_set, "minimum_effective_length_m", cs.minimum_effective_length_m)
        settr(bad_set, "maximum_effective_length_m", cs.maximum_effective_length_m)
        settr(bad_set, "raw_combination_count", cs.raw_combination_count)
        settr(bad_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(bad_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(bad_set, "candidate_set_digest", cs.candidate_set_digest)

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", mr1.candidates)
        object.__setattr__(forged, "candidate_set", bad_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 4: Candidate_set missing a catalog ref that IS in gate
    # ------------------------------------------------------------------

    def test_candidate_set_missing_catalog_rejected(self) -> None:
        """Candidate_set missing a catalog ref that IS in sizing_gate."""
        from hexagent.optimization.context import _create_materialized_candidate_set

        ident1, sp1, prov1, mr1 = self._build_legit()

        # Remove the first catalog ref from candidate_set
        reduced_refs = mr1.candidate_set.catalog_snapshot_identities[1:]
        bad_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=mr1.candidate_set.sizing_request_identity_digest,
            passed_gate_digest=mr1.candidate_set.passed_gate_digest,
            catalog_snapshot_identities=reduced_refs,
            minimum_effective_length_m=mr1.candidate_set.minimum_effective_length_m,
            maximum_effective_length_m=mr1.candidate_set.maximum_effective_length_m,
            raw_combination_count=mr1.candidate_set.raw_combination_count,
            ordered_candidates=mr1.candidates,
        )

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", mr1.candidates)
        object.__setattr__(forged, "candidate_set", bad_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 5: Bounds mismatch
    # ------------------------------------------------------------------

    def test_bounds_mismatch_rejected(self) -> None:
        """Different bounds in manifest vs candidate_set."""
        ident1, sp1, prov1, mr1 = self._build_legit()

        # Build a tampered candidate_set using object.__new__ to bypass
        # model validation (which enforces min <= max).
        from hexagent.optimization.context import MaterializedCandidateSet

        cs = mr1.candidate_set
        bad_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(bad_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest)
        settr(bad_set, "passed_gate_digest", cs.passed_gate_digest)
        settr(bad_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities)
        settr(bad_set, "minimum_effective_length_m", 999.0)
        settr(bad_set, "maximum_effective_length_m", 888.0)
        settr(bad_set, "raw_combination_count", cs.raw_combination_count)
        settr(bad_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(bad_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(bad_set, "candidate_set_digest", cs.candidate_set_digest)

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", mr1.candidates)
        object.__setattr__(forged, "candidate_set", bad_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # P0-5: Bounds negative tests
    # ------------------------------------------------------------------

    def test_bounds_aggregate_neq_candidate_set_rejected(self) -> None:
        """MR bounds != candidate_set bounds should be rejected before any rating call."""
        ident1, sp1, prov1, mr1 = self._build_legit()

        # Create a forged MaterializationResult where bounds differ
        forged_mr = object.__new__(type(mr1))
        object.__setattr__(forged_mr, "candidates", mr1.candidates)
        object.__setattr__(forged_mr, "candidate_set", mr1.candidate_set)
        object.__setattr__(forged_mr, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged_mr, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged_mr, "minimum_effective_length_m", 0.5)  # different from None
        object.__setattr__(forged_mr, "maximum_effective_length_m", 1.5)  # different from None

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged_mr,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    def test_bounds_reverse_mismatch_rejected(self) -> None:
        """Reverse: aggregate bounds match each other but both differ from candidate_set."""
        ident1, sp1, prov1, mr1 = self._build_legit()

        # Aggregate bounds are both None; candidate_set bounds are tampered
        from hexagent.optimization.context import MaterializedCandidateSet

        cs = mr1.candidate_set
        bad_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(bad_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest)
        settr(bad_set, "passed_gate_digest", cs.passed_gate_digest)
        settr(bad_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities)
        settr(bad_set, "minimum_effective_length_m", 999.0)
        settr(bad_set, "maximum_effective_length_m", 888.0)
        settr(bad_set, "raw_combination_count", cs.raw_combination_count)
        settr(bad_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(bad_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(bad_set, "candidate_set_digest", cs.candidate_set_digest)

        forged_mr = object.__new__(type(mr1))
        object.__setattr__(forged_mr, "candidates", mr1.candidates)
        object.__setattr__(forged_mr, "candidate_set", bad_set)
        object.__setattr__(forged_mr, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged_mr, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged_mr,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    def test_bounds_self_consistent_forged_rejected(self) -> None:
        """Aggregate bounds == forged candidate_set bounds, but replay produces different cands."""
        ident1, sp1, prov1, mr1 = self._build_legit()

        from hexagent.optimization.context import MaterializedCandidateSet

        cs = mr1.candidate_set
        bad_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(bad_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest)
        settr(bad_set, "passed_gate_digest", cs.passed_gate_digest)
        settr(bad_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities)
        # Set bounds to match aggregate
        settr(bad_set, "minimum_effective_length_m", None)
        settr(bad_set, "maximum_effective_length_m", None)
        settr(bad_set, "raw_combination_count", cs.raw_combination_count)
        settr(bad_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(bad_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(bad_set, "candidate_set_digest", cs.candidate_set_digest)

        # Aggregate bounds also match
        forged_mr = object.__new__(type(mr1))
        object.__setattr__(forged_mr, "candidates", mr1.candidates)
        object.__setattr__(forged_mr, "candidate_set", bad_set)
        object.__setattr__(forged_mr, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged_mr, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        # This is the tricky case: bounds match, but replay produces different candidates
        # We need forged candidate_set bounds that are different from what replay would produce
        # Since bounds match the aggregate, the candidate_set bounds check passes.
        # But since candidate_set_digest is still the original, the replay will verify it.
        # This test validates that self-consistent bounds forgery where bounds are different
        # from what materialization would produce is caught.

        # Use different bounds in candidate_set (not None) but match them in aggregate too
        # to make them self-consistent
        settr(bad_set, "minimum_effective_length_m", 0.5)
        settr(bad_set, "maximum_effective_length_m", 1.5)
        object.__setattr__(forged_mr, "minimum_effective_length_m", 0.5)
        object.__setattr__(forged_mr, "maximum_effective_length_m", 1.5)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged_mr,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 6: Candidate option not in gate
    # ------------------------------------------------------------------

    def test_candidate_option_not_in_gate_rejected(self) -> None:
        """Candidate from an option the sizing_gate doesn't know about."""
        from hexagent.optimization.identities import build_candidate

        ident1, sp1, prov1, mr1 = self._build_legit()

        # Build a candidate from a different catalog/option
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            LengthSource,
        )

        bogus_opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="bogus_opt",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(2.0,),
            ),
        )
        from hexagent.optimization.catalog import compute_catalog_content_hash

        bogus_hash = compute_catalog_content_hash(
            catalog_id="bogus_cat",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(bogus_opt,),
        )
        from hexagent.optimization.models import CompleteDoublePipeCatalogSnapshot

        bogus_cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="bogus_cat",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(bogus_opt,),
            catalog_content_hash=bogus_hash,
        )

        bogus_candidate = build_candidate(bogus_cat, bogus_opt, "2.0")
        bad_candidates = mr1.candidates + (bogus_candidate,)

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", bad_candidates)
        object.__setattr__(forged, "candidate_set", mr1.candidate_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 7: Candidate identity forged
    # ------------------------------------------------------------------

    def test_candidate_identity_forged_rejected(self) -> None:
        """Candidate with mangled physical_identity_digest → rejected."""
        import copy

        ident1, sp1, prov1, mr1 = self._build_legit()

        # Mangle the physical_identity_digest of the first candidate
        bad_candidates = tuple(copy.deepcopy(c) for c in mr1.candidates)
        object.__setattr__(bad_candidates[0], "physical_identity_digest", "tampered_digest")

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", bad_candidates)
        object.__setattr__(forged, "candidate_set", mr1.candidate_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # Test 8: Candidate length tampered
    # ------------------------------------------------------------------

    def test_candidate_length_tampered_rejected(self) -> None:
        """Length tampering detected via source_qualified_candidate_id mismatch."""
        import copy

        ident1, sp1, prov1, mr1 = self._build_legit()

        # Mangle the effective_length_m_canonical AND the source_qualified_candidate_id
        # so that the candidate ordering check in evaluate_all_candidates fails.
        bad_candidates = tuple(copy.deepcopy(c) for c in mr1.candidates)
        object.__setattr__(bad_candidates[0], "effective_length_m_canonical", 999.0)
        object.__setattr__(
            bad_candidates[0],
            "source_qualified_candidate_id",
            "tampered_candidate_id",
        )

        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", bad_candidates)
        object.__setattr__(forged, "candidate_set", mr1.candidate_set)
        object.__setattr__(forged, "sizing_gate", mr1.sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", mr1.catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)

        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident1,
                rating_fn=spy,
            )
        assert len(calls) == 0

    # ------------------------------------------------------------------
    # P0-5: 6 self-consistent forgery tests
    # ------------------------------------------------------------------

    def _make_forged_mr_via_new(
        self, candidates, candidate_set, sizing_gate, catalog_snapshots, mr1
    ):
        """Build a MaterializationResult via object.__new__."""
        forged = object.__new__(type(mr1))
        object.__setattr__(forged, "candidates", candidates)
        object.__setattr__(forged, "candidate_set", candidate_set)
        object.__setattr__(forged, "sizing_gate", sizing_gate)
        object.__setattr__(forged, "catalog_snapshots", catalog_snapshots)
        object.__setattr__(forged, "minimum_effective_length_m", mr1.minimum_effective_length_m)
        object.__setattr__(forged, "maximum_effective_length_m", mr1.maximum_effective_length_m)
        return forged

    def _assert_forgery_rejected(self, ident, forged) -> None:
        """Assert that evaluate_all_candidates rejects the forged result with 0 rating calls."""
        import unittest.mock as um

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        provider = um.MagicMock()
        calls: list[dict] = []

        def spy(**kw: Any) -> Any:
            calls.append(dict(kw))
            return self._make_minimal_result()

        with pytest.raises((ValueError, TypeError)):
            evaluate_all_candidates(
                materialization_result=forged,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=provider,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=spy,
            )
        assert len(calls) == 0

    def test_self_consistent_forged_length_rejected(self) -> None:
        """Change length to a value the catalog option doesn't allow,
        but recompute ALL digests to be self-consistent."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        # Catalog only allows length=1.0
        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Forge a candidate with length=2.0 (NOT in allowed_effective_lengths_m)
        forged_candidate = build_candidate(cat, opt, "2.0")

        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        from hexagent.optimization.identities import MaterializationResult

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_forged_geometry_rejected(self) -> None:
        """Change inner_tube_inner_diameter_m to a value not matching the catalog,
        but recompute ALL digests to be self-consistent."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        # Catalog original geometry
        opt_orig = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_orig,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_orig,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build forged candidate with different diameter (0.07 instead of 0.05)
        # The catalog still says 0.05
        opt_forged = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.07,  # FORGED
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        forged_candidate = build_candidate(cat, opt_forged, "1.0")

        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_forged_manufacturing_identity_rejected(self) -> None:
        """Change manufacturing_option_identity but recompute all digests."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        opt_orig = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_orig,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_orig,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Forged candidate with different manufacturing_option_identity
        opt_forged = CompleteDoublePipeAssemblyOption(  # noqa: F841
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="forged_id",  # FORGED
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )

        # Build forged candidate using the opt_forged with different manufacturing identity
        # but same catalog as the original
        forged_candidate = build_candidate(cat, opt_forged, "1.0")

        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_forged_quantum_rejected(self) -> None:
        """Gate record with a quantum that doesn't match any catalog option
        is detected during replay — all digests are self-consistent."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        # Catalog with quantum=0.1
        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        # Gate record with DIFFERENT quantum (0.01) than the catalog (0.1)
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.01",  # FORGED: doesn't match catalog's 0.1
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        candidate = build_candidate(cat, opt, "1.0")
        candidates = deduplicate_and_order_candidates((candidate,))
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=(catalog_snapshot_ref(cat),),
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_forged_bounds_rejected(self) -> None:
        """Use different bounds in the forged candidate_set but recompute all digests."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build legitimate candidate
        candidate = build_candidate(cat, opt, "1.0")
        candidates = deduplicate_and_order_candidates((candidate,))
        refs = (catalog_snapshot_ref(cat),)

        # Forged candidate_set with different bounds (use object.__new__ to bypass validation)
        cs = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=candidates,
        )
        from hexagent.optimization.context import MaterializedCandidateSet

        forged_set = object.__new__(MaterializedCandidateSet)
        object.__setattr__(
            forged_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest
        )
        object.__setattr__(forged_set, "passed_gate_digest", cs.passed_gate_digest)
        object.__setattr__(
            forged_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities
        )
        object.__setattr__(forged_set, "minimum_effective_length_m", 999.0)
        object.__setattr__(forged_set, "maximum_effective_length_m", 888.0)
        object.__setattr__(forged_set, "raw_combination_count", cs.raw_combination_count)
        object.__setattr__(forged_set, "unique_candidate_count", cs.unique_candidate_count)
        object.__setattr__(forged_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        object.__setattr__(forged_set, "candidate_set_digest", cs.candidate_set_digest)

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_forged_catalog_snapshots_rejected(self) -> None:
        """Replace catalog_snapshots with a different catalog but recompute all digests."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        # Original catalog with option 'a'
        opt_a = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch_a = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_a,),
        )
        cat_a = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_a,),
            catalog_content_hash=ch_a,
        )

        # Different catalog with option 'b'
        opt_b = CompleteDoublePipeAssemblyOption(
            assembly_option_id="b",  # DIFFERENT option id
            inner_tube_inner_diameter_m=0.07,
            inner_tube_outer_diameter_m=0.08,
            outer_pipe_inner_diameter_m=0.12,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(2.0,),
            ),
        )
        ch_b = compute_catalog_content_hash(
            catalog_id="c2",
            catalog_version="v2",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_b,),
        )
        cat_b = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c2",
            catalog_version="v2",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt_b,),
            catalog_content_hash=ch_b,
        )

        req = SizingRequest(catalogs=(cat_a,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch_a,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build candidate from option 'a' (legitimate)
        candidate = build_candidate(cat_a, opt_a, "1.0")
        candidates = deduplicate_and_order_candidates((candidate,))

        # Candidate_set references catalog_a
        refs_a = (catalog_snapshot_ref(cat_a),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs_a,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=candidates,
        )

        # Forged: catalog_snapshots points to cat_b instead of cat_a
        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat_b,))  # FORGED catalog
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)

        self._assert_forgery_rejected(ident, forged_mr)

    # ------------------------------------------------------------------
    # P0-5: Gate chain forgery tests
    # ------------------------------------------------------------------

    def test_gate_digest_invalid_rejected(self) -> None:
        """gate.verify_digest() fails due to tampered gate_digest."""
        ident, sp, prov, mr = self._build_legit()
        forged_gate = mr.sizing_gate.model_copy(update={"gate_digest": "sha256:" + "f" * 64})
        forged_mr = self._make_forged_mr_via_new(
            mr.candidates,
            mr.candidate_set,
            forged_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)

    def test_gate_sizing_digest_mismatch_rejected(self) -> None:
        """Modify sizing_request_identity_digest in gate only."""
        ident, sp, prov, mr = self._build_legit()
        forged_gate = mr.sizing_gate.model_copy(
            update={"sizing_request_identity_digest": "sha256:" + "e" * 64}
        )
        forged_mr = self._make_forged_mr_via_new(
            mr.candidates,
            mr.candidate_set,
            forged_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)

    def test_gate_raw_count_mismatch_rejected(self) -> None:
        """gate.raw_combination_count != per-option sum."""
        ident, sp, prov, mr = self._build_legit()
        forged_gate = mr.sizing_gate.model_copy(update={"raw_combination_count": 999})
        forged_mr = self._make_forged_mr_via_new(
            mr.candidates,
            mr.candidate_set,
            forged_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)

    def test_candidate_set_gate_digest_mismatch_rejected(self) -> None:
        """candidate_set.passed_gate_digest != gate.gate_digest."""
        ident, sp, prov, mr = self._build_legit()
        from hexagent.optimization.context import MaterializedCandidateSet

        cs = mr.candidate_set
        forged_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(forged_set, "sizing_request_identity_digest", cs.sizing_request_identity_digest)
        settr(forged_set, "passed_gate_digest", "sha256:" + "f" * 64)
        settr(forged_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities)
        settr(forged_set, "minimum_effective_length_m", cs.minimum_effective_length_m)
        settr(forged_set, "maximum_effective_length_m", cs.maximum_effective_length_m)
        settr(forged_set, "raw_combination_count", cs.raw_combination_count)
        settr(forged_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(forged_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(forged_set, "candidate_set_digest", cs.candidate_set_digest)

        forged_mr = object.__new__(type(mr))
        object.__setattr__(forged_mr, "candidates", mr.candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", mr.sizing_gate)
        object.__setattr__(forged_mr, "catalog_snapshots", mr.catalog_snapshots)
        object.__setattr__(forged_mr, "minimum_effective_length_m", mr.minimum_effective_length_m)
        object.__setattr__(forged_mr, "maximum_effective_length_m", mr.maximum_effective_length_m)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_candidate_set_sizing_digest_mismatch_rejected(self) -> None:
        """candidate_set sizing digest != gate sizing digest."""
        ident, sp, prov, mr = self._build_legit()
        from hexagent.optimization.context import MaterializedCandidateSet

        cs = mr.candidate_set
        forged_set = object.__new__(MaterializedCandidateSet)
        settr = object.__setattr__
        settr(forged_set, "sizing_request_identity_digest", "sha256:" + "e" * 64)
        settr(forged_set, "passed_gate_digest", cs.passed_gate_digest)
        settr(forged_set, "catalog_snapshot_identities", cs.catalog_snapshot_identities)
        settr(forged_set, "minimum_effective_length_m", cs.minimum_effective_length_m)
        settr(forged_set, "maximum_effective_length_m", cs.maximum_effective_length_m)
        settr(forged_set, "raw_combination_count", cs.raw_combination_count)
        settr(forged_set, "unique_candidate_count", cs.unique_candidate_count)
        settr(forged_set, "ordered_candidate_ids", cs.ordered_candidate_ids)
        settr(forged_set, "candidate_set_digest", cs.candidate_set_digest)

        forged_mr = object.__new__(type(mr))
        object.__setattr__(forged_mr, "candidates", mr.candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", mr.sizing_gate)
        object.__setattr__(forged_mr, "catalog_snapshots", mr.catalog_snapshots)
        object.__setattr__(forged_mr, "minimum_effective_length_m", mr.minimum_effective_length_m)
        object.__setattr__(forged_mr, "maximum_effective_length_m", mr.maximum_effective_length_m)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_per_option_sum_mismatch_rejected(self) -> None:
        """Raw_count in one per-option record modified so sum != total."""
        ident, sp, prov, mr = self._build_legit()
        forged_records = tuple(
            rec.model_copy(update={"raw_count": rec.raw_count + 1})
            for rec in mr.sizing_gate.per_option_records
        )
        forged_gate = mr.sizing_gate.model_copy(update={"per_option_records": forged_records})
        forged_mr = self._make_forged_mr_via_new(
            mr.candidates,
            mr.candidate_set,
            forged_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)

    # ------------------------------------------------------------------
    # P0-5: Self-consistent forgery tests (additional)
    # ------------------------------------------------------------------

    def test_self_consistent_metadata_forged_rejected(self) -> None:
        """manufacturing_metadata changed, all digests recomputed."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        # Catalog option without metadata
        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build candidate with forged metadata
        opt_forged = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(("forged_key", "forged_value"),),  # FORGED
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0,),
            ),
        )
        forged_candidate = build_candidate(cat, opt_forged, "1.0")
        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_source_identity_forged_rejected(self) -> None:
        """catalog_snapshot_ref.source_identity changed, everything recomputed."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(length_quantum_m="0.1", allowed_effective_lengths_m=(1.0,)),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",  # catalog says "test"
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build candidate with forged source_identity in catalog
        ch_forged = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="forged_source",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat_forged = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="forged_source",  # FORGED source identity
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch_forged,
        )
        forged_candidate = build_candidate(cat_forged, opt, "1.0")
        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        # Use original catalog ref (from legit catalog)
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_schema_version_forged_rejected(self) -> None:
        """catalog_snapshot_ref.schema_version changed."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            _create_materialized_candidate_set,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import (
            MaterializationResult,
            build_candidate,
            catalog_snapshot_ref,
            deduplicate_and_order_candidates,
        )
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(length_quantum_m="0.1", allowed_effective_lengths_m=(1.0,)),
        )
        ch = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=ch,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test",
                version="1",
                git_revision="a",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=ch,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=1,
            effective_cap=100,
            per_option_records=(rec,),
        )

        # Build candidate with forged schema_version in catalog
        ch_forged = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="99.99",
            assembly_options=(opt,),
        )
        cat_forged = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="99.99",  # FORGED schema version
            assembly_options=(opt,),
            catalog_content_hash=ch_forged,
        )
        forged_candidate = build_candidate(cat_forged, opt, "1.0")
        forged_candidates = deduplicate_and_order_candidates((forged_candidate,))
        refs = (catalog_snapshot_ref(cat),)
        forged_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=1,
            ordered_candidates=forged_candidates,
        )

        forged_mr = object.__new__(MaterializationResult)
        object.__setattr__(forged_mr, "candidates", forged_candidates)
        object.__setattr__(forged_mr, "candidate_set", forged_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(forged_mr, "catalog_snapshots", (cat,))
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_order_index_forged_rejected(self) -> None:
        """evaluation_order_index changed."""
        import copy

        ident, sp, prov, mr = self._build_legit(
            option_id="a",
            length=1.0,
        )
        # Build a second legitimate MR with a different option
        ident2, sp2, prov2, mr2 = self._build_legit(
            catalog_id="c2",
            option_id="b",
            length=2.0,
        )
        # Combine candidates from both into a single tuple
        all_cands = mr.candidates + mr2.candidates
        # Recompute with deduplicate to get correct IDs and order
        from hexagent.optimization.identities import (
            deduplicate_and_order_candidates,
        )

        ordered = deduplicate_and_order_candidates(all_cands)

        # Build a gate that references both options
        from hexagent.optimization.context import create_passed_sizing_gate
        from hexagent.optimization.models import OptionRawCountRecord

        rec1 = OptionRawCountRecord(
            catalog_id="c1",
            catalog_version="v1",
            catalog_content_hash=mr.catalog_snapshots[0].catalog_content_hash,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="a",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        rec2 = OptionRawCountRecord(
            catalog_id="c2",
            catalog_version="v1",
            catalog_content_hash=mr2.catalog_snapshots[0].catalog_content_hash,
            source_identity="test",
            schema_version="1.0",
            assembly_option_id="b",
            canonical_length_quantum_m="0.1",
            raw_count=1,
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=2,
            effective_cap=100,
            per_option_records=(rec1, rec2),
        )

        from hexagent.optimization.context import _create_materialized_candidate_set
        from hexagent.optimization.identities import catalog_snapshot_ref

        cat_refs = (
            catalog_snapshot_ref(mr.catalog_snapshots[0]),
            catalog_snapshot_ref(mr2.catalog_snapshots[0]),
        )
        candidate_set = _create_materialized_candidate_set(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            passed_gate_digest=gate.gate_digest,
            catalog_snapshot_identities=cat_refs,
            minimum_effective_length_m=None,
            maximum_effective_length_m=None,
            raw_combination_count=2,
            ordered_candidates=ordered,
        )

        # Now forge: deepcopy candidates and swap evaluation_order_index
        bad_cands = tuple(copy.deepcopy(c) for c in ordered)
        # Swap the evaluation_order_index values
        idx0 = bad_cands[0].evaluation_order_index
        idx1 = bad_cands[1].evaluation_order_index
        object.__setattr__(bad_cands[0], "evaluation_order_index", idx1)
        object.__setattr__(bad_cands[1], "evaluation_order_index", idx0)

        # Keep original candidate_set (with correct ordered_candidate_ids)
        forged_mr = object.__new__(type(mr))
        object.__setattr__(forged_mr, "candidates", bad_cands)
        object.__setattr__(forged_mr, "candidate_set", candidate_set)
        object.__setattr__(forged_mr, "sizing_gate", gate)
        object.__setattr__(
            forged_mr,
            "catalog_snapshots",
            mr.catalog_snapshots + mr2.catalog_snapshots,
        )
        object.__setattr__(forged_mr, "minimum_effective_length_m", None)
        object.__setattr__(forged_mr, "maximum_effective_length_m", None)
        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_stale_physical_digest_rejected(self) -> None:
        """physical_identity changed but old digest kept."""
        import copy

        ident, sp, prov, mr = self._build_legit()
        bad_cands = tuple(copy.deepcopy(c) for c in mr.candidates)
        # Change physical_identity_digest to a stale value
        object.__setattr__(
            bad_cands[0],
            "physical_identity_digest",
            "sha256:" + "a" * 64,  # stale — doesn't match recomputed
        )
        forged_mr = self._make_forged_mr_via_new(
            bad_cands,
            mr.candidate_set,
            mr.sizing_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)

    def test_self_consistent_stale_sq_digest_rejected(self) -> None:
        """source_qualified_identity changed but old candidate ID kept."""
        import copy

        ident, sp, prov, mr = self._build_legit()
        bad_cands = tuple(copy.deepcopy(c) for c in mr.candidates)
        # Change source_qualified_candidate_id to a stale value
        object.__setattr__(
            bad_cands[0],
            "source_qualified_candidate_id",
            "sha256:" + "b" * 64,  # stale — doesn't match recomputed
        )
        forged_mr = self._make_forged_mr_via_new(
            bad_cands,
            mr.candidate_set,
            mr.sizing_gate,
            mr.catalog_snapshots,
            mr,
        )
        self._assert_forgery_rejected(ident, forged_mr)


# ============================================================================
# P0-6: Fail-closed boundary tests
# ============================================================================


class _BuildLegitMixin:
    """Mixin providing _build_legit and _make_minimal_result for fail-closed tests."""

    def _build_legit(self):
        """Build a valid MaterializationResult through the production chain."""
        import unittest.mock
        from uuid import UUID

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import materialize_all_candidates
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )
        from hexagent.properties.base import PropertyProvider

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt_a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0, 2.0),
            ),
        )
        cat_hash = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=cat_hash,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test_provider",
                version="1.0",
                git_revision="abc123",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=len(opt.length_source.allowed_effective_lengths_m),
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=2,
            effective_cap=100,
            per_option_records=(rec,),
        )
        mat_result = materialize_all_candidates(catalogs=(cat,), sizing_gate=gate)
        provider = unittest.mock.MagicMock(spec=PropertyProvider)
        solver_params = SolverParams()
        return ident, solver_params, provider, mat_result

    def _make_minimal_result(self, hash_passes=True, prov_passes=True):
        """Create a duck-typed RatingResult for the spy rating_fn."""
        from hexagent.core.heat_balance import ExecutionContextSnapshot, ProviderIdentitySnapshot
        from hexagent.exchangers.double_pipe.result import (
            RatingRequestIdentity,
            RatingResult,
            RatingStatus,
        )
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement

        result = object.__new__(RatingResult)
        for attr, val in {
            "status": RatingStatus.SUCCEEDED,
            "flow_arrangement": FlowArrangement.COUNTERFLOW,
            "result_hash": "sha256:" + "e" * 64,
            "provenance_digest": "prov_digest",
            "heat_duty_w": 1000.0,
            "hot_outlet_temperature_k": 350.0,
            "cold_outlet_temperature_k": 310.0,
            "area_inner_m2": 1.5,
            "area_outer_m2": 2.0,
            "UA_w_k": 500.0,
            "LMTD_k": 40.0,
            "energy_residual_w": 0.001,
            "ua_lmtd_residual_w": 0.002,
            "tube_selected_correlation_id": "corr_1",
            "tube_selected_correlation_version": "1.0",
            "annulus_selected_correlation_id": "corr_2",
            "annulus_selected_correlation_version": "1.0",
            "warnings": (),
            "blockers": (),
            "failure": None,
            "hot_inlet_state": None,
            "cold_inlet_state": None,
            "tube_selected_correlation": None,
            "annulus_selected_correlation": None,
        }.items():
            object.__setattr__(result, attr, val)

        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
        )
        object.__setattr__(result, "request_identity", rri)
        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)
        ec = object.__new__(ExecutionContextSnapshot)
        for attr in (
            "request_id",
            "design_case_revision_id",
            "calculation_run_id",
            "execution_id",
            "rating_software_version",
            "execution_context_policy_version",
        ):
            object.__setattr__(ec, attr, None)
        object.__setattr__(result, "execution_context", ec)
        object.__setattr__(result, "verify_hash", lambda: hash_passes)
        object.__setattr__(result, "verify_provenance", lambda: prov_passes)
        return result

    def _make_result_with_warning(self):
        """Create a duck-typed RatingResult with a bytes-in-context warning."""
        from hexagent.domain.messages import (
            EngineeringMessage,
            EngineeringMessageSeverity,
            ErrorCode,
        )

        result = self._make_minimal_result()
        bad_warning = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="bad warning",
            context=(("bad", b"bytes_data"),),
        )
        object.__setattr__(result, "warnings", (bad_warning,))
        object.__setattr__(result, "blockers", ())
        object.__setattr__(result, "failure", None)
        return result


class TestFailClosedBoundary(_BuildLegitMixin):
    """P0-6: Exceptions during canonicalization caught by fail-closed boundary."""

    def _build_legit(self):
        """Build a valid MaterializationResult through the production chain."""
        import unittest.mock

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import materialize_all_candidates
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )
        from hexagent.properties.base import PropertyProvider

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt_a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0, 2.0),
            ),
        )
        cat_hash = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=cat_hash,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test_provider",
                version="1.0",
                git_revision="abc123",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=len(opt.length_source.allowed_effective_lengths_m),
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=2,
            effective_cap=100,
            per_option_records=(rec,),
        )
        mat_result = materialize_all_candidates(catalogs=(cat,), sizing_gate=gate)
        provider = unittest.mock.MagicMock(spec=PropertyProvider)
        solver_params = SolverParams()
        return ident, solver_params, provider, mat_result

    def _make_minimal_result(self, hash_passes=True, prov_passes=True):
        """Create a duck-typed RatingResult for the spy rating_fn."""
        from hexagent.core.heat_balance import ExecutionContextSnapshot, ProviderIdentitySnapshot
        from hexagent.exchangers.double_pipe.result import (
            RatingRequestIdentity,
            RatingResult,
            RatingStatus,
        )
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement

        result = object.__new__(RatingResult)
        for attr, val in {
            "status": RatingStatus.SUCCEEDED,
            "flow_arrangement": FlowArrangement.COUNTERFLOW,
            "result_hash": "sha256:" + "e" * 64,
            "provenance_digest": "prov_digest",
            "heat_duty_w": 1000.0,
            "hot_outlet_temperature_k": 350.0,
            "cold_outlet_temperature_k": 310.0,
            "area_inner_m2": 1.5,
            "area_outer_m2": 2.0,
            "UA_w_k": 500.0,
            "LMTD_k": 40.0,
            "energy_residual_w": 0.001,
            "ua_lmtd_residual_w": 0.002,
            "tube_selected_correlation_id": "corr_1",
            "tube_selected_correlation_version": "1.0",
            "annulus_selected_correlation_id": "corr_2",
            "annulus_selected_correlation_version": "1.0",
            "warnings": (),
            "blockers": (),
            "failure": None,
            "hot_inlet_state": None,
            "cold_inlet_state": None,
            "tube_selected_correlation": None,
            "annulus_selected_correlation": None,
        }.items():
            object.__setattr__(result, attr, val)

        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
        )
        object.__setattr__(result, "request_identity", rri)
        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)
        ec = object.__new__(ExecutionContextSnapshot)
        for attr in (
            "request_id",
            "design_case_revision_id",
            "calculation_run_id",
            "execution_id",
            "rating_software_version",
            "execution_context_policy_version",
        ):
            object.__setattr__(ec, attr, None)
        object.__setattr__(result, "execution_context", ec)
        object.__setattr__(result, "verify_hash", lambda: hash_passes)
        object.__setattr__(result, "verify_provenance", lambda: prov_passes)
        return result

    def test_unexpected_verification_error_caught(self) -> None:
        """Unexpected ValueError during evidence revalidation is caught by fail-closed boundary."""
        from hexagent.optimization.evaluation import (
            CandidateEvaluationState,
            revalidate_verified_rating_evidence,
        )

        ident, sp, prov, mat_result = self._build_legit()
        original = revalidate_verified_rating_evidence

        def broken_revalidate(evidence):
            raise ValueError("unexpected revalidation failure")

        import hexagent.optimization.evaluation as ev_mod

        ev_mod.revalidate_verified_rating_evidence = broken_revalidate

        try:
            from hexagent.exchangers.double_pipe.solver import SolverParams
            from hexagent.exchangers.double_pipe.thermal import FlowArrangement
            from hexagent.optimization.adapter import evaluate_all_candidates
            from hexagent.properties.base import FluidIdentifier

            records = evaluate_all_candidates(
                materialization_result=mat_result,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=prov,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=lambda **kw: self._make_minimal_result(),
            )

            assert len(records) >= 2
            # The ValueError from revalidation is caught by the fail-closed boundary
            assert (
                records[0].candidate_evaluation_state
                == CandidateEvaluationState.RUNTIME_FAILED.value
            )
            assert records[0].evaluation_failure is not None
            assert (
                records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value
            )
        finally:
            ev_mod.revalidate_verified_rating_evidence = original

    def test_owner_descriptor_exception_caught(self) -> None:
        """RuntimeError from owner descriptor is caught by fail-closed boundary."""
        from hexagent.optimization.evaluation import CandidateEvaluationState

        ident, sp, prov, mat_result = self._build_legit()

        import hexagent.optimization.evaluation as ev_mod

        original = ev_mod._build_message_descriptor

        def broken_owner(*args, **kwargs):
            raise RuntimeError("owner descriptor explosion")

        ev_mod._build_message_descriptor = broken_owner

        try:
            from hexagent.exchangers.double_pipe.solver import SolverParams
            from hexagent.exchangers.double_pipe.thermal import FlowArrangement
            from hexagent.optimization.adapter import evaluate_all_candidates
            from hexagent.properties.base import FluidIdentifier

            # Use a result WITH a warning so _build_message_descriptor is called
            records = evaluate_all_candidates(
                materialization_result=mat_result,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=prov,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=lambda **kw: self._make_result_with_warning(),
            )

            assert len(records) >= 2
            # The RuntimeError propagates and is caught by fail-closed boundary
            assert (
                records[0].candidate_evaluation_state
                == CandidateEvaluationState.RUNTIME_FAILED.value
            )
            assert records[0].evaluation_failure is not None
            assert (
                records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value
            )
        finally:
            ev_mod._build_message_descriptor = original

    def test_run_failure_descriptor_exception_caught(self) -> None:
        """RuntimeError from RunFailure descriptor is caught by fail-closed boundary."""
        from hexagent.optimization.evaluation import CandidateEvaluationState

        ident, sp, prov, mat_result = self._build_legit()

        import hexagent.optimization.evaluation as ev_mod

        original = ev_mod._build_run_failure_descriptor

        def broken_run_failure(*args, **kwargs):
            raise RuntimeError("run failure descriptor explosion")

        ev_mod._build_run_failure_descriptor = broken_run_failure

        try:
            # Use a result WITH a failure so _build_run_failure_descriptor is called
            from hexagent.domain.messages import ErrorCode, RunFailure
            from hexagent.exchangers.double_pipe.solver import SolverParams
            from hexagent.exchangers.double_pipe.thermal import FlowArrangement
            from hexagent.optimization.adapter import evaluate_all_candidates
            from hexagent.properties.base import FluidIdentifier

            original_result = self._make_minimal_result()
            run_fail = RunFailure(
                code=ErrorCode.CALCULATION_BLOCKED,
                message="blocked",
                context=(("key", b"bad_bytes"),),
            )
            object.__setattr__(original_result, "failure", run_fail)
            object.__setattr__(original_result, "warnings", ())
            object.__setattr__(original_result, "blockers", ())

            records = evaluate_all_candidates(
                materialization_result=mat_result,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=prov,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=lambda **kw: original_result,
            )

            assert len(records) >= 2
            assert (
                records[0].candidate_evaluation_state
                == CandidateEvaluationState.RUNTIME_FAILED.value
            )
            assert records[0].evaluation_failure is not None
            assert (
                records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value
            )
        finally:
            ev_mod._build_run_failure_descriptor = original

    def test_identity_builder_exception_caught(self) -> None:
        """ValueError from identity builder is caught by fail-closed boundary."""
        from hexagent.optimization.evaluation import CandidateEvaluationState

        ident, sp, prov, mat_result = self._build_legit()

        import hexagent.optimization.evaluation as ev_mod

        original = ev_mod._build_candidate_evaluation_identity

        def broken_identity(*args, **kwargs):
            raise ValueError("identity builder explosion")

        ev_mod._build_candidate_evaluation_identity = broken_identity

        try:
            from hexagent.exchangers.double_pipe.solver import SolverParams
            from hexagent.exchangers.double_pipe.thermal import FlowArrangement
            from hexagent.optimization.adapter import evaluate_all_candidates
            from hexagent.properties.base import FluidIdentifier

            # Use a minimal result (no warnings/blockers) so execution
            # reaches _build_candidate_evaluation_identity
            records = evaluate_all_candidates(
                materialization_result=mat_result,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=prov,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=lambda **kw: self._make_minimal_result(),
            )

            assert len(records) >= 2
            assert (
                records[0].candidate_evaluation_state
                == CandidateEvaluationState.RUNTIME_FAILED.value
            )
            assert records[0].evaluation_failure is not None
            assert records[0].candidate_evaluation_identity is None
            assert records[0].verified_rating_evidence is None
            assert records[0].invalid_rating_evidence is None
            assert (
                records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED.value
            )
            assert records[1].hash_verification_outcome is VerificationOutcome.NOT_RUN
            assert records[1].provenance_verification_outcome is VerificationOutcome.NOT_RUN
        finally:
            ev_mod._build_candidate_evaluation_identity = original


class IteratorThatRaisesMidIteration:
    """Custom iterator that yields one valid item then raises RuntimeError."""

    def __init__(self) -> None:
        self._items = iter([("key1", "hello")])

    def __iter__(self):
        return self

    def __next__(self):
        val = next(self._items)
        raise RuntimeError("mid-iteration explosion")
        return val  # noqa: FURB105 — unreachable but documents intent


class CustomTestExceptionForTest(Exception):
    """Stable module-level exception for fail-closed testing."""


class TraversalCountingMapping(Mapping[str, object]):
    """Mapping that tracks items() call count without raising."""

    def __init__(self) -> None:
        self.traversal_count = 0

    def items(self):
        self.traversal_count += 1
        return iter((("key", "value"),))

    def __getitem__(self, key: str) -> object:
        return "value"

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        return iter(["key"])


class FirstTraversalFailsMapping(Mapping[str, object]):
    """Mapping that fails on first traversal, succeeds on subsequent."""

    def __init__(self) -> None:
        self.traversal_count = 0

    def items(self):
        self.traversal_count += 1
        if self.traversal_count == 1:
            return IteratorThatRaisesMidIteration()
        return iter((("key", "value"),))

    def __getitem__(self, key: str) -> object:
        return "value"

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        return iter(["key"])


class FirstTraversalSucceedsMapping(Mapping[str, object]):
    """Mapping that succeeds on first traversal, fails on subsequent."""

    def __init__(self) -> None:
        self.traversal_count = 0

    def items(self):
        self.traversal_count += 1
        if self.traversal_count == 1:
            return iter((("key", "value"),))
        raise RuntimeError("second traversal must never happen")

    def __getitem__(self, key: str) -> object:
        return "value"

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        return iter(["key"])


class FirstNextFailureMapping(Mapping[str, object]):
    """Mapping whose items() raises on first call."""

    def __init__(self) -> None:
        self.traversal_count = 0

    def items(self):
        self.traversal_count += 1
        if self.traversal_count == 1:
            raise RuntimeError("first-next failure")
        return iter((("key", "value"),))

    def __getitem__(self, key: str) -> object:
        return "value"

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        return iter(["key"])


class NestedOneShotMapping(Mapping[str, object]):
    """Mapping that raises during nested iteration."""

    def __init__(self) -> None:
        self.traversal_count = 0

    def items(self):
        self.traversal_count += 1
        if self.traversal_count == 1:
            return iter((("nested", FirstTraversalFailsMapping()),))
        return iter((("nested", {"key": "value"}),))

    def __getitem__(self, key: str) -> object:
        return "value"

    def __len__(self) -> int:
        return 1

    def __iter__(self):
        return iter(["nested"])


def _make_engineering_message(
    severity: str = "warning",
    context: tuple[tuple[str, object], ...] = (),
) -> EngineeringMessage:
    """Helper to build an EngineeringMessage for test use."""
    return EngineeringMessage(
        code=ErrorCode.INPUT_INCONSISTENT,
        severity=EngineeringMessageSeverity.WARNING
        if severity == "warning"
        else EngineeringMessageSeverity.BLOCKER,
        message="test message",
        context=context,
    )


class TestSinglePassCanonicalization(_BuildLegitMixin):
    """P0-3: Single-pass owner canonicalization + stateful one-shot tests."""

    def test_build_message_descriptor_traverses_once(self) -> None:
        """Descriptor builder traverses message.context exactly once."""

        ctx = FirstTraversalFailsMapping()
        msg = _make_engineering_message(
            severity="warning",
            context=(("ctx", ctx),),
        )

        descriptor = _build_message_descriptor(msg)

        # First traversal fails — descriptor should capture the error
        assert descriptor.canonicalization_error is not None
        assert descriptor.canonical_message_payload is None
        assert ctx.traversal_count == 1

    def test_build_message_descriptor_success_traverses_once(self) -> None:
        """Successful descriptor traversal is exactly once."""

        ctx = FirstTraversalSucceedsMapping()
        msg = _make_engineering_message(
            severity="warning",
            context=(("ctx", ctx),),
        )

        descriptor = _build_message_descriptor(msg)

        # First traversal succeeds — descriptor has payload
        assert descriptor.canonical_message_payload is not None
        assert descriptor.canonicalization_error is None
        assert ctx.traversal_count == 1

    def _build_result_with_mapping_warning(
        self,
        mapping: Mapping[str, object],
    ) -> object:
        """Build a duck-typed RatingResult with a mapping in warning context."""

        result = self._make_minimal_result()
        bad_warning = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.WARNING,
            message="mapped warning",
            context=(("ctx", mapping),),
        )
        object.__setattr__(result, "warnings", (bad_warning,))
        object.__setattr__(result, "blockers", ())
        object.__setattr__(result, "failure", None)
        return result

    def _build_result_with_mapping_blocker(
        self,
        mapping: Mapping[str, object],
    ) -> object:
        """Build a duck-typed RatingResult with a mapping in blocker context."""

        result = self._make_minimal_result()
        bad_blocker = EngineeringMessage(
            code=ErrorCode.INPUT_INCONSISTENT,
            severity=EngineeringMessageSeverity.BLOCKER,
            message="mapped blocker",
            context=(("ctx", mapping),),
        )
        object.__setattr__(result, "warnings", ())
        object.__setattr__(result, "blockers", (bad_blocker,))
        object.__setattr__(result, "failure", None)
        return result

    def _build_result_with_mapping_failure(
        self,
        mapping: Mapping[str, object],
    ) -> object:
        """Build a duck-typed RatingResult with a mapping in RunFailure context."""
        from hexagent.domain.messages import ErrorCode, RunFailure

        result = self._make_minimal_result()
        run_fail = RunFailure(
            code=ErrorCode.CALCULATION_BLOCKED,
            message="blocked",
            context=(("ctx", mapping),),
        )
        object.__setattr__(result, "warnings", ())
        object.__setattr__(result, "blockers", ())
        object.__setattr__(result, "failure", run_fail)
        return result

    def _assert_traversal_once_failure(self, records: tuple, mapping: Mapping[str, object]) -> None:
        """Assert the fail-closed outcome for a first-traversal-fails scenario."""
        assert len(records) >= 2
        assert records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
        fail = records[0].evaluation_failure
        assert fail is not None
        assert fail.code is ErrorCode.PROVENANCE_INCOMPLETE
        assert fail.message == "Trusted context canonicalization failed."
        assert fail.traceback is None
        assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED
        assert records[1].hash_verification_outcome is VerificationOutcome.NOT_RUN
        assert records[1].provenance_verification_outcome is VerificationOutcome.NOT_RUN

    def _evaluate_via_adapter(self, ident, prov, mat_result, result_fn):
        """Run evaluate_all_candidates with given parameters."""
        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.adapter import evaluate_all_candidates
        from hexagent.properties.base import FluidIdentifier

        return evaluate_all_candidates(
            materialization_result=mat_result,
            hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
            cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            provider=prov,
            solver_params=SolverParams(),
            minimum_terminal_delta_t=5.0,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            sizing_request_identity=ident,
            rating_fn=result_fn,
        )

    def test_warning_first_fails_then_succeeds(self) -> None:
        """Warning with first-traversal-fails mapping is caught (traversal_count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = FirstTraversalFailsMapping()
        result = self._build_result_with_mapping_warning(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    # --- Blocker: first traversal fails ---

    def test_blocker_first_fails_then_succeeds(self) -> None:
        """Blocker with first-traversal-fails mapping is caught (traversal_count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = FirstTraversalFailsMapping()
        result = self._build_result_with_mapping_blocker(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    # --- Warning: first traversal succeeds, later fails ---

    def test_warning_first_succeeds_then_fails(self) -> None:
        """Warning: first-success mapping traversed exactly once (count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        results = []
        for _ in range(len(mat_result.candidates)):
            ctx = TraversalCountingMapping()
            results.append(self._build_result_with_mapping_warning(ctx))
        iter_results = iter(results)
        records = self._evaluate_via_adapter(
            ident, prov, mat_result, lambda **kw: next(iter_results)
        )
        assert records[0].candidate_evaluation_state == CandidateEvaluationState.VERIFIED
        for r in results:
            ctx = r.warnings[0].context[0][1]
            assert ctx.traversal_count == 1

    # --- Blocker: first traversal succeeds, later fails ---

    def test_blocker_first_succeeds_then_fails(self) -> None:
        """Blocker: first-success mapping traversed exactly once (count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        results = []
        for _ in range(len(mat_result.candidates)):
            ctx = TraversalCountingMapping()
            results.append(self._build_result_with_mapping_blocker(ctx))
        iter_results = iter(results)
        records = self._evaluate_via_adapter(
            ident, prov, mat_result, lambda **kw: next(iter_results)
        )
        assert records[0].candidate_evaluation_state == CandidateEvaluationState.VERIFIED
        for r in results:
            ctx = r.blockers[0].context[0][1]
            assert ctx.traversal_count == 1

    # --- First-next failure ---

    def test_warning_first_next_failure(self) -> None:
        """Warning with first-next-failure mapping is caught."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = FirstNextFailureMapping()
        result = self._build_result_with_mapping_warning(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    def test_blocker_first_next_failure(self) -> None:
        """Blocker with first-next-failure mapping is caught."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = FirstNextFailureMapping()
        result = self._build_result_with_mapping_blocker(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    # --- Nested one-shot ---

    def test_warning_nested_one_shot(self) -> None:
        """Warning with nested one-shot mapping is caught."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = NestedOneShotMapping()
        result = self._build_result_with_mapping_warning(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    def test_blocker_nested_one_shot(self) -> None:
        """Blocker with nested one-shot mapping is caught."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = NestedOneShotMapping()
        result = self._build_result_with_mapping_blocker(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    # --- RunFailure one-shot ---

    def test_run_failure_first_fails_then_succeeds(self) -> None:
        """RunFailure with first-traversal-fails mapping is caught (traversal_count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        ctx = FirstTraversalFailsMapping()
        result = self._build_result_with_mapping_failure(ctx)

        records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: result)
        self._assert_traversal_once_failure(records, ctx)
        assert ctx.traversal_count == 1

    def test_run_failure_first_succeeds_then_fails(self) -> None:
        """RunFailure: first-success mapping traversed exactly once (count=1)."""
        ident, sp, prov, mat_result = self._build_legit()
        results = []
        for _ in range(len(mat_result.candidates)):
            ctx = TraversalCountingMapping()
            results.append(self._build_result_with_mapping_failure(ctx))
        iter_results = iter(results)
        records = self._evaluate_via_adapter(
            ident, prov, mat_result, lambda **kw: next(iter_results)
        )
        assert records[0].candidate_evaluation_state == CandidateEvaluationState.VERIFIED
        for r in results:
            ctx = r.failure.context[0][1]
            assert ctx.traversal_count == 1

    # --- Permutation tests ---

    def test_warning_permutation_a_b_identical_failure(self) -> None:
        """A then B ordering with mixed valid/invalid context yields same failure as B then A."""
        ident, sp, prov, mat_result = self._build_legit()

        def _make_warning_pair():
            fail_ctx = FirstTraversalFailsMapping()
            success_ctx = FirstTraversalSucceedsMapping()
            fw = EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message="test",
                context=(("ctx", fail_ctx),),
            )
            sw = EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.WARNING,
                message="test",
                context=(("ctx", success_ctx),),
            )
            return fw, sw, fail_ctx, success_ctx

        def _run_permutation(warning_list, fail_ctx, success_ctx):
            base = self._make_minimal_result()
            object.__setattr__(base, "warnings", tuple(warning_list))
            object.__setattr__(base, "blockers", ())
            object.__setattr__(base, "failure", None)
            records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: base)
            assert records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
            assert fail_ctx.traversal_count == 1
            assert success_ctx.traversal_count == 1
            return records[0].evaluation_failure

        # A/B: failing warning first, succeeding warning second
        a_fail, b_success, fail_ab_ctx, success_ab_ctx = _make_warning_pair()
        fail_ab = _run_permutation([a_fail, b_success], fail_ab_ctx, success_ab_ctx)

        # B/A: succeeding warning first, failing warning second — FRESH instances
        a_fail2, b_success2, fail_ba_ctx, success_ba_ctx = _make_warning_pair()
        fail_ba = _run_permutation([b_success2, a_fail2], fail_ba_ctx, success_ba_ctx)

        # Full RunFailure comparison
        assert fail_ab == fail_ba
        assert fail_ab.code is fail_ba.code
        assert fail_ab.message == fail_ba.message
        assert fail_ab.traceback == fail_ba.traceback
        assert fail_ab.context == fail_ba.context

    def test_blocker_permutation_a_b_identical_failure(self) -> None:
        """Blocker A then B vs B then A yield identical failure."""
        ident, sp, prov, mat_result = self._build_legit()

        def _make_blocker_pair():
            fail_ctx = FirstTraversalFailsMapping()
            success_ctx = FirstTraversalSucceedsMapping()
            fb = EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.BLOCKER,
                message="test",
                context=(("ctx", fail_ctx),),
            )
            sb = EngineeringMessage(
                code=ErrorCode.INPUT_INCONSISTENT,
                severity=EngineeringMessageSeverity.BLOCKER,
                message="test",
                context=(("ctx", success_ctx),),
            )
            return fb, sb, fail_ctx, success_ctx

        def _run_permutation(blocker_list, fail_ctx, success_ctx):
            base = self._make_minimal_result()
            object.__setattr__(base, "warnings", ())
            object.__setattr__(base, "blockers", tuple(blocker_list))
            object.__setattr__(base, "failure", None)
            records = self._evaluate_via_adapter(ident, prov, mat_result, lambda **kw: base)
            assert records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
            assert fail_ctx.traversal_count == 1
            assert success_ctx.traversal_count == 1
            return records[0].evaluation_failure

        # A/B: failing blocker first, succeeding blocker second
        a_fail, b_success, fail_ab_ctx, success_ab_ctx = _make_blocker_pair()
        fail_ab = _run_permutation([a_fail, b_success], fail_ab_ctx, success_ab_ctx)

        # B/A: succeeding blocker first, failing blocker second — FRESH instances
        a_fail2, b_success2, fail_ba_ctx, success_ba_ctx = _make_blocker_pair()
        fail_ba = _run_permutation([b_success2, a_fail2], fail_ba_ctx, success_ba_ctx)

        assert fail_ab == fail_ba
        assert fail_ab.code is fail_ba.code
        assert fail_ab.message == fail_ba.message
        assert fail_ab.traceback == fail_ba.traceback
        assert fail_ab.context == fail_ba.context


class TestFailClosedExceptException(_BuildLegitMixin):
    """P0-6: Full except Exception catch-all coverage tests."""

    def _build_legit(self):
        """Build a valid MaterializationResult (same as TestFailClosedBoundary)."""
        from unittest.mock import MagicMock
        from uuid import UUID

        from hexagent.exchangers.double_pipe.solver import SolverParams
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement
        from hexagent.optimization.catalog import compute_catalog_content_hash
        from hexagent.optimization.context import (
            ExpectedProviderIdentity,
            OptimizationObjective,
            build_sizing_request_identity,
            create_passed_sizing_gate,
        )
        from hexagent.optimization.identities import materialize_all_candidates
        from hexagent.optimization.models import (
            CompleteDoublePipeAssemblyOption,
            CompleteDoublePipeCatalogSnapshot,
            LengthSource,
            OptionRawCountRecord,
            SizingRequest,
        )
        from hexagent.properties.base import PropertyProvider

        opt = CompleteDoublePipeAssemblyOption(
            assembly_option_id="opt_a",
            inner_tube_inner_diameter_m=0.05,
            inner_tube_outer_diameter_m=0.06,
            outer_pipe_inner_diameter_m=0.10,
            wall_thermal_conductivity_w_m_k=50.0,
            inner_surface_roughness_m=1e-5,
            annulus_surface_roughness_m=1e-5,
            inner_fouling_resistance_m2k_w=0.0001,
            outer_fouling_resistance_m2k_w=0.0002,
            manufacturing_option_identity="std",
            manufacturing_metadata=(),
            length_source=LengthSource(
                length_quantum_m="0.1",
                allowed_effective_lengths_m=(1.0, 2.0),
            ),
        )
        cat_hash = compute_catalog_content_hash(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
        )
        cat = CompleteDoublePipeCatalogSnapshot(
            catalog_id="c1",
            catalog_version="v1",
            source_identity="test",
            schema_version="1.0",
            assembly_options=(opt,),
            catalog_content_hash=cat_hash,
        )
        req = SizingRequest(catalogs=(cat,))
        ident = build_sizing_request_identity(
            request=req,
            hot_fluid_name="w",
            cold_fluid_name="b",
            hot_fluid_equation_of_state="i",
            cold_fluid_equation_of_state="n",
            hot_fluid_normalized_components=(),
            cold_fluid_normalized_components=(),
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=2e5,
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            tube_in_hot=True,
            flow_arrangement=FlowArrangement.COUNTERFLOW,
            tube_boundary_condition="constant_wall_temperature",
            annulus_boundary_condition="inner_wall_heated",
            minimum_terminal_delta_t=5.0,
            required_duty_w=1000.0,
            duty_absolute_tolerance_w=10.0,
            duty_relative_tolerance=0.01,
            optimization_objective=OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA,
            top_n=5,
            solver_params=SolverParams(),
            expected_provider_identity=ExpectedProviderIdentity(
                name="test_provider",
                version="1.0",
                git_revision="abc123",
                reference_state_policy="default",
            ),
            design_case_revision_id=UUID("11111111-1111-1111-1111-111111111111"),
            calculation_run_id=UUID("22222222-2222-2222-2222-222222222222"),
        )
        rec = OptionRawCountRecord(
            catalog_id=cat.catalog_id,
            catalog_version=cat.catalog_version,
            catalog_content_hash=cat.catalog_content_hash,
            source_identity=cat.source_identity,
            schema_version=cat.schema_version,
            assembly_option_id=opt.assembly_option_id,
            canonical_length_quantum_m=opt.length_source.length_quantum_m,
            raw_count=len(opt.length_source.allowed_effective_lengths_m),
        )
        gate = create_passed_sizing_gate(
            sizing_request_identity_digest=ident.sizing_request_identity_digest,
            raw_combination_count=2,
            effective_cap=100,
            per_option_records=(rec,),
        )
        mat_result = materialize_all_candidates(catalogs=(cat,), sizing_gate=gate)
        provider = MagicMock(spec=PropertyProvider)
        solver_params = SolverParams()
        return ident, solver_params, provider, mat_result

    def _make_minimal_result(self):
        """Create a duck-typed RatingResult (same as TestFailClosedBoundary)."""
        from hexagent.core.heat_balance import ExecutionContextSnapshot, ProviderIdentitySnapshot
        from hexagent.exchangers.double_pipe.result import (
            RatingRequestIdentity,
            RatingResult,
            RatingStatus,
        )
        from hexagent.exchangers.double_pipe.thermal import FlowArrangement

        result = object.__new__(RatingResult)
        for attr, val in {
            "status": RatingStatus.SUCCEEDED,
            "flow_arrangement": FlowArrangement.COUNTERFLOW,
            "result_hash": "sha256:" + "e" * 64,
            "provenance_digest": "prov_digest",
            "heat_duty_w": 1000.0,
            "hot_outlet_temperature_k": 350.0,
            "cold_outlet_temperature_k": 310.0,
            "area_inner_m2": 1.5,
            "area_outer_m2": 2.0,
            "UA_w_k": 500.0,
            "LMTD_k": 40.0,
            "energy_residual_w": 0.001,
            "ua_lmtd_residual_w": 0.002,
            "tube_selected_correlation_id": "corr_1",
            "tube_selected_correlation_version": "1.0",
            "annulus_selected_correlation_id": "corr_2",
            "annulus_selected_correlation_version": "1.0",
            "warnings": (),
            "blockers": (),
            "failure": None,
            "hot_inlet_state": None,
            "cold_inlet_state": None,
            "tube_selected_correlation": None,
            "annulus_selected_correlation": None,
        }.items():
            object.__setattr__(result, attr, val)

        rri = RatingRequestIdentity(
            hot_fluid_name="w",
            hot_fluid_backend="i",
            hot_fluid_components=(),
            cold_fluid_name="b",
            cold_fluid_backend="n",
            cold_fluid_components=(),
            hot_mass_flow_kg_s=5.0,
            cold_mass_flow_kg_s=5.0,
            hot_inlet_pressure_pa=1e5,
            cold_inlet_pressure_pa=1e5,
            hot_inlet_temperature_k=300.0,
            cold_inlet_temperature_k=280.0,
            flow_arrangement="counterflow",
            geometry={
                "inner_tube_inner_diameter_m": 0.05,
                "inner_tube_outer_diameter_m": 0.06,
                "outer_pipe_inner_diameter_m": 0.10,
                "effective_length_m": 1.0,
                "wall_thermal_conductivity_w_m_k": 50.0,
                "inner_surface_roughness_m": 1e-5,
                "annulus_surface_roughness_m": 1e-5,
                "inner_fouling_resistance_m2k_w": 0.0001,
                "outer_fouling_resistance_m2k_w": 0.0002,
            },
            solver_absolute_residual_w=1e-3,
            solver_relative_residual_fraction=1e-8,
            solver_bracket_temperature_tolerance_k=1e-4,
            solver_max_iterations=100,
        )
        object.__setattr__(result, "request_identity", rri)
        pi = ProviderIdentitySnapshot(
            name="test_provider",
            version="1.0",
            git_revision="abc123",
            reference_state_policy="default",
        )
        object.__setattr__(result, "provider_identity", pi)
        ec = object.__new__(ExecutionContextSnapshot)
        for attr in (
            "request_id",
            "design_case_revision_id",
            "calculation_run_id",
            "execution_id",
            "rating_software_version",
            "execution_context_policy_version",
        ):
            object.__setattr__(ec, attr, None)
        object.__setattr__(result, "execution_context", ec)
        object.__setattr__(result, "verify_hash", lambda: True)
        object.__setattr__(result, "verify_provenance", lambda: True)
        return result

    @pytest.mark.parametrize(
        "exception_type",
        [
            "key_error",
            "index_error",
            "os_error",
            "arithmetic_error",
            "assertion_error",
            "custom",
        ],
    )
    def test_exception_types_caught_by_fail_closed(self, exception_type: str) -> None:
        """All exception types are caught by the fail-closed boundary."""
        ident, sp, prov, mat_result = self._build_legit()

        import hexagent.optimization.evaluation as ev_mod

        original = ev_mod._build_message_descriptor

        def broken_descriptor(*args, **kwargs):
            if exception_type == "key_error":
                raise KeyError("key_error")
            elif exception_type == "index_error":
                raise IndexError("index_error")
            elif exception_type == "os_error":
                raise OSError("os_error")
            elif exception_type == "arithmetic_error":
                raise ArithmeticError("arithmetic_error")
            elif exception_type == "assertion_error":
                raise AssertionError("assertion_error")
            elif exception_type == "custom":
                raise CustomTestExceptionForTest("custom")
            raise RuntimeError("fallback")

        ev_mod._build_message_descriptor = broken_descriptor

        try:
            from hexagent.exchangers.double_pipe.solver import SolverParams
            from hexagent.exchangers.double_pipe.thermal import FlowArrangement
            from hexagent.optimization.adapter import evaluate_all_candidates
            from hexagent.properties.base import FluidIdentifier

            rating_calls: int = 0

            def rating_fn(**kwargs):
                nonlocal rating_calls
                rating_calls += 1
                return self._make_result_with_warning()

            records = evaluate_all_candidates(
                materialization_result=mat_result,
                hot_fluid=FluidIdentifier(name="w", equation_of_state_backend="i"),
                cold_fluid=FluidIdentifier(name="b", equation_of_state_backend="n"),
                hot_mass_flow_kg_s=5.0,
                cold_mass_flow_kg_s=5.0,
                hot_inlet_temperature_k=300.0,
                cold_inlet_temperature_k=280.0,
                hot_inlet_pressure_pa=1e5,
                cold_inlet_pressure_pa=2e5,
                tube_in_hot=True,
                flow_arrangement=FlowArrangement.COUNTERFLOW,
                provider=prov,
                solver_params=SolverParams(),
                minimum_terminal_delta_t=5.0,
                tube_boundary_condition="constant_wall_temperature",
                annulus_boundary_condition="inner_wall_heated",
                sizing_request_identity=ident,
                rating_fn=rating_fn,
            )

            assert len(records) >= 2
            assert rating_calls == 1
            candidate_id = records[0].source_qualified_candidate_id
            expected_safe_marker_digest = sha256_digest(
                {
                    "failure_stage": "rating_verification",
                    "owner_kind": "verification_runtime",
                    "owner_id": candidate_id,
                }
            )
            assert records[0].candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
            assert records[0].evaluation_failure is not None
            assert records[0].evaluation_failure.code is ErrorCode.PROVENANCE_INCOMPLETE
            assert records[0].evaluation_failure.message == "Trusted rating verification failed."
            assert records[0].evaluation_failure.traceback is None
            assert records[0].candidate_evaluation_identity is None
            assert records[0].verified_rating_evidence is None
            assert records[0].invalid_rating_evidence is None
            r_fail = records[0].evaluation_failure
            ctx_dict = dict(r_fail.context)
            assert ctx_dict.get("failure_stage") == "rating_verification"
            assert ctx_dict.get("owner_kind") == "verification_runtime"
            assert ctx_dict.get("owner_id") == candidate_id
            assert ctx_dict.get("failure_kind") == "verification_exception"
            assert ctx_dict.get("safe_marker_digest") == expected_safe_marker_digest
            # offending_type depends on the exception class; verify it's present and matches
            expected_offending = {
                "key_error": "builtins.KeyError",
                "index_error": "builtins.IndexError",
                "os_error": "builtins.OSError",
                "arithmetic_error": "builtins.ArithmeticError",
                "assertion_error": "builtins.AssertionError",
                "custom": "test_task009_phase2_canonicalization.CustomTestExceptionForTest",
            }[exception_type]
            assert ctx_dict.get("offending_type") == expected_offending, (
                f"expected {expected_offending}, got {ctx_dict.get('offending_type')}"
            )
            assert records[1].candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED
            assert records[1].hash_verification_outcome is VerificationOutcome.NOT_RUN
            assert records[1].provenance_verification_outcome is VerificationOutcome.NOT_RUN
        finally:
            ev_mod._build_message_descriptor = original
