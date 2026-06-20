from __future__ import annotations

import math


def counterflow_lmtd(
    hot_in_k: float,
    hot_out_k: float,
    cold_in_k: float,
    cold_out_k: float,
) -> float:
    dt1 = hot_in_k - cold_out_k
    dt2 = hot_out_k - cold_in_k
    if dt1 <= 0.0 or dt2 <= 0.0:
        raise ValueError("Counterflow terminal temperature differences must be positive.")
    if math.isclose(dt1, dt2, rel_tol=1e-12, abs_tol=1e-12):
        return 0.5 * (dt1 + dt2)
    return (dt1 - dt2) / math.log(dt1 / dt2)
