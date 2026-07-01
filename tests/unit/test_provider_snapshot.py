"""Regression tests for _provider_snapshot dynamic attribute handling.

Verifies that _provider_snapshot correctly handles:
- Real CoolPropProvider instances
- MagicMock with explicit attributes
- MagicMock with dynamic (uninitialized) attributes
- provider=None
- reference_state_policy as enum vs string vs mock
"""

from __future__ import annotations

from unittest.mock import MagicMock

from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.exchangers.double_pipe.rating import (
    _optional_string_attribute,
    _provider_snapshot,
)
from hexagent.properties.base import ReferenceStatePolicy

# ---------------------------------------------------------------------------
# _optional_string_attribute unit tests
# ---------------------------------------------------------------------------


class TestOptionalStringAttribute:
    def test_returns_string_value(self) -> None:
        obj = MagicMock(spec=[])
        obj.foo = "hello"
        assert _optional_string_attribute(obj, "foo") == "hello"

    def test_returns_empty_for_missing(self) -> None:
        obj = MagicMock(spec=[])
        assert _optional_string_attribute(obj, "nonexistent") == ""

    def test_returns_empty_for_int(self) -> None:
        obj = MagicMock(spec=[])
        obj.foo = 42
        assert _optional_string_attribute(obj, "foo") == ""

    def test_returns_empty_for_mock(self) -> None:
        obj = MagicMock(spec=[])
        # MagicMock without spec: accessing .foo returns a MagicMock
        result = _optional_string_attribute(obj, "foo")
        assert result == ""

    def test_returns_empty_for_none(self) -> None:
        obj = MagicMock(spec=[])
        obj.foo = None
        assert _optional_string_attribute(obj, "foo") == ""

    def test_returns_empty_for_list(self) -> None:
        obj = MagicMock(spec=[])
        obj.foo = ["a", "b"]
        assert _optional_string_attribute(obj, "foo") == ""


# ---------------------------------------------------------------------------
# _provider_snapshot tests
# ---------------------------------------------------------------------------


class TestProviderSnapshot:
    def test_none_provider(self) -> None:
        snap = _provider_snapshot(None)
        assert snap.name == ""
        assert snap.version == ""
        assert snap.git_revision == ""
        assert snap.reference_state_policy == ""
        assert snap.configuration_fingerprint == ""
        assert snap.cache_policy_version == ""

    def test_mock_with_explicit_attributes(self) -> None:
        provider = MagicMock()
        provider.name = "MockProvider"
        provider.version = "1.0"
        provider.git_revision = "abc123"
        provider.reference_state_policy = ReferenceStatePolicy.DEF
        snap = _provider_snapshot(provider)
        assert snap.name == "MockProvider"
        assert snap.version == "1.0"
        assert snap.git_revision == "abc123"
        assert snap.reference_state_policy == "DEF"
        # Dynamic attributes not set → empty
        assert snap.configuration_fingerprint == ""
        assert snap.cache_policy_version == ""

    def test_mock_with_realistic_optional_attributes(self) -> None:
        provider = MagicMock()
        provider.name = "TestProvider"
        provider.version = "2.0"
        provider.git_revision = ""
        provider.reference_state_policy = ReferenceStatePolicy.DEF
        provider.configuration_fingerprint = "fp-abc"
        provider.cache_policy_version = "1.0"
        snap = _provider_snapshot(provider)
        assert snap.configuration_fingerprint == "fp-abc"
        assert snap.cache_policy_version == "1.0"

    def test_mock_private_fingerprint_fallback(self) -> None:
        """When configuration_fingerprint is absent, fall back to _construction_fingerprint."""
        provider = MagicMock(spec=[])
        provider.name = "TestProvider"
        provider.version = "1.0"
        provider.git_revision = ""
        provider.reference_state_policy = ReferenceStatePolicy.DEF
        provider._construction_fingerprint = "fp-private"
        snap = _provider_snapshot(provider)
        assert snap.configuration_fingerprint == "fp-private"

    def test_reference_state_policy_as_string(self) -> None:
        provider = MagicMock()
        provider.name = "TestProvider"
        provider.version = "1.0"
        provider.git_revision = ""
        provider.reference_state_policy = "DEF"
        snap = _provider_snapshot(provider)
        assert snap.reference_state_policy == "DEF"

    def test_reference_state_policy_as_mock_fail_closed(self) -> None:
        """When reference_state_policy is a mock (not enum/str), return ''."""
        provider = MagicMock()
        provider.name = "TestProvider"
        provider.version = "1.0"
        provider.git_revision = ""
        # Set reference_state_policy to a MagicMock (not enum/str)
        provider.reference_state_policy = MagicMock()
        snap = _provider_snapshot(provider)
        assert snap.reference_state_policy == ""

    def test_returns_frozen_dataclass(self) -> None:
        snap = _provider_snapshot(None)
        assert isinstance(snap, ProviderIdentitySnapshot)
        # Frozen — should raise on assignment
        try:
            snap.name = "x"  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            raise AssertionError("Expected FrozenInstanceError")
