import math

from prototypes.v08_thermal_rating.cell0_bracketed_root_ulp import (
    bracket_endpoints_adjacent,
    localize_sign_bracket_near_root,
    shrink_sign_bracket_float64,
)


def test_bracket_adjacent_detect() -> None:
    lo = 1.0
    hi = math.nextafter(lo, math.inf)
    assert bracket_endpoints_adjacent(lo, hi)
    assert not bracket_endpoints_adjacent(lo, math.nextafter(hi, math.inf))


def test_shrink_preserves_sign_change() -> None:
    def f(x: float) -> float:
        return x - 1.25

    lo, hi = 1.0, 2.0
    out = shrink_sign_bracket_float64(f, lo, hi, max_evaluations=96)
    assert out["final_lo"] < out["final_hi"]
    assert out["f_lo"] * out["f_hi"] < 0
    assert out["representables_between_final"] != ">=2000000"


def test_localize_near_root() -> None:
    def f(x: float) -> float:
        return x - 1.0

    br = localize_sign_bracket_near_root(f, 1.0, lo_limit=0.5, hi_limit=1.5)
    assert br is not None
    a, b = br
    assert f(a) * f(b) < 0
