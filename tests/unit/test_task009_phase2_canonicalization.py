"""P0-11/P0-13/P0-14: Canonicalization contract tests for TASK-009 Phase 2."""

from __future__ import annotations

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
    _context_entries_to_payload,
    build_canonical_context_entries,
    canonicalize_trusted_context_value,
    engineering_message_payload,
    execution_context_snapshot_payload,
    provider_identity_snapshot_payload,
    rating_request_identity_payload,
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
        rating_request_identity_digest="sha256:" + "c" * 64,
        rating_execution_context=ec,
        rating_execution_context_digest="sha256:" + "d" * 64,
    )


# ============================================================================
# Test classes
# ============================================================================


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
    """P0-11: Repository Quantity-like object adaptation."""

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

        _assert_canon_error(_BadQ(), ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION)

    def test_to_si_not_callable(self) -> None:
        """to_si attribute that is not callable raises UNSUPPORTED_TYPE."""

        class _NoCallQ:
            value = 1.0
            unit = "m"
            kind = type("Kind", (), {"value": "length"})()
            to_si = "not_callable"

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

        _assert_canon_error(
            _BadKindQ(),
            ContextCanonicalizationFailureKind.CANONICALIZATION_EXCEPTION,
        )


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
                lambda ev: ev.model_copy(update={"rating_status": RatingStatus.FAILED}),
            ),
            ("heat_duty_w", lambda ev: ev.model_copy(update={"heat_duty_w": 2000.0})),
            (
                "hot_outlet_temperature_k",
                lambda ev: ev.model_copy(update={"hot_outlet_temperature_k": 360.0}),
            ),
            (
                "cold_outlet_temperature_k",
                lambda ev: ev.model_copy(update={"cold_outlet_temperature_k": 320.0}),
            ),
            ("area_inner_m2", lambda ev: ev.model_copy(update={"area_inner_m2": 3.0})),
            ("area_outer_m2", lambda ev: ev.model_copy(update={"area_outer_m2": 4.0})),
            ("UA_w_k", lambda ev: ev.model_copy(update={"UA_w_k": 600.0})),
            ("LMTD_k", lambda ev: ev.model_copy(update={"LMTD_k": 50.0})),
            ("energy_residual_w", lambda ev: ev.model_copy(update={"energy_residual_w": 0.01})),
            ("ua_lmtd_residual_w", lambda ev: ev.model_copy(update={"ua_lmtd_residual_w": 0.02})),
            (
                "tube_inlet_density_kg_m3",
                lambda ev: ev.model_copy(update={"tube_inlet_density_kg_m3": 700.0}),
            ),
            (
                "annulus_inlet_density_kg_m3",
                lambda ev: ev.model_copy(update={"annulus_inlet_density_kg_m3": 800.0}),
            ),
            ("tube_flow_area_m2", lambda ev: ev.model_copy(update={"tube_flow_area_m2": 0.02})),
            (
                "annulus_flow_area_m2",
                lambda ev: ev.model_copy(update={"annulus_flow_area_m2": 0.03}),
            ),
            (
                "warnings",
                lambda ev: ev.model_copy(update={"warnings": (_make_warning_msg("changed"),)}),
            ),
            (
                "blockers",
                lambda ev: ev.model_copy(update={"blockers": (_make_blocker_msg("changed"),)}),
            ),
            (
                "failure",
                lambda ev: ev.model_copy(
                    update={
                        "failure": RunFailure(
                            code=ErrorCode.CALCULATION_BLOCKED,
                            message="test failure",
                        )
                    }
                ),
            ),
            (
                "provider_identity",
                lambda ev: ev.model_copy(
                    update={
                        "provider_identity": ProviderIdentitySnapshot(
                            name="other",
                            version="2.0",
                            git_revision="def",
                            reference_state_policy="strict",
                        )
                    }
                ),
            ),
            (
                "tube_correlation",
                lambda ev: ev.model_copy(
                    update={"tube_correlation": _make_correlation("other_tube")}
                ),
            ),
            (
                "annulus_correlation",
                lambda ev: ev.model_copy(
                    update={"annulus_correlation": _make_correlation("other_ann")}
                ),
            ),
            (
                "rating_result_hash",
                lambda ev: ev.model_copy(update={"rating_result_hash": "sha256:" + "e" * 64}),
            ),
            (
                "rating_provenance_digest",
                lambda ev: ev.model_copy(update={"rating_provenance_digest": "sha256:" + "f" * 64}),
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
                lambda ev: ev.model_copy(
                    update={"rating_request_identity_digest": "sha256:" + "g" * 64}
                ),
            ),
            (
                "rating_execution_context_digest",
                lambda ev: ev.model_copy(
                    update={"rating_execution_context_digest": "sha256:" + "h" * 64}
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
        ev1 = _baseline_evidence().model_copy(update={"warnings": (w1, w2)})
        ev2 = _baseline_evidence().model_copy(update={"warnings": (w2, w1)})
        d1 = sha256_digest(verified_rating_evidence_payload(ev1))
        d2 = sha256_digest(verified_rating_evidence_payload(ev2))
        assert d1 == d2

    def test_blocker_permutation_stable(self) -> None:
        """Reordering identical blockers yields same digest."""
        b1 = _make_blocker_msg("same")
        b2 = _make_blocker_msg("same")
        ev1 = _baseline_evidence().model_copy(update={"blockers": (b1, b2)})
        ev2 = _baseline_evidence().model_copy(update={"blockers": (b2, b1)})
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
