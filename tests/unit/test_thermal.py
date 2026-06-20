import math

import pytest

from hexagent.correlations.thermal import counterflow_lmtd


def test_counterflow_lmtd() -> None:
    result = counterflow_lmtd(373.15, 333.15, 293.15, 313.15)
    expected = (60.0 - 40.0) / math.log(60.0 / 40.0)
    assert result == pytest.approx(expected)


def test_equal_terminal_differences() -> None:
    assert counterflow_lmtd(350.0, 330.0, 280.0, 300.0) == pytest.approx(50.0)


def test_temperature_cross_rejected() -> None:
    with pytest.raises(ValueError):
        counterflow_lmtd(330.0, 310.0, 300.0, 335.0)
