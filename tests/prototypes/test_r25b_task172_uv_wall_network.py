"""R25B: physical (u,v) wall mapping and wide-network failure classification."""

from __future__ import annotations

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service


def test_uv_wall_mapping_enforces_ordering() -> None:
    shell_k = 295.0
    tube_k = 310.0
    for u, v in ((0.0, 0.0), (0.25, 0.5), (1.0, 1.0)):
        twi, two = task172_service._wall_temperatures_from_uv(
            u,
            v,
            shell_bulk_k=shell_k,
            tube_bulk_k=tube_k,
        )
        assert shell_k <= two <= twi <= tube_k
    twi, two = task172_service._wall_temperatures_from_uv(
        0.5,
        0.5,
        shell_bulk_k=shell_k,
        tube_bulk_k=tube_k,
    )
    u_back, v_back = task172_service._uv_from_wall_temperatures(
        twi,
        two,
        shell_bulk_k=shell_k,
        tube_bulk_k=tube_k,
    )
    assert u_back == pytest.approx(0.5)
    assert v_back == pytest.approx(0.5)


def test_wall_network_failure_selection_prefers_residual_acceptance() -> None:
    residual = task172_service._RuntimeFailure("BLOCKED_RESIDUAL_ACCEPTANCE", "diag")
    nonconv = task172_service._RuntimeFailure("BLOCKED_NONCONVERGENCE", "wall_network")
    selected = task172_service._select_wall_network_failure((nonconv, residual))
    assert selected.code == "BLOCKED_RESIDUAL_ACCEPTANCE"


def test_wide_profile_is_r25b_uv_network() -> None:
    profile = task172_service._WIDE_DELTA_T_EXPERIMENTAL_NUMERICAL_PROFILE_ID
    assert "R25B" in profile
    assert "UV" in profile
