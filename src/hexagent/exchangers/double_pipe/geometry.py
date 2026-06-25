"""Double-pipe heat-exchanger geometry model and validation.

All internal computations use SI units.  The geometry is immutable and
JSON round-trip capable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DoublePipeGeometry:
    """Fixed-geometry double-pipe heat exchanger.

    Attributes
    ----------
    inner_tube_inner_diameter_m :
        Inner tube inside diameter [m].
    inner_tube_outer_diameter_m :
        Inner tube outside diameter [m].
    outer_pipe_inner_diameter_m :
        Outer pipe inside diameter [m].
    effective_length_m :
        Effective heat-transfer length [m].
    wall_thermal_conductivity_w_m_k :
        Tube wall thermal conductivity [W/(m·K)].
    inner_surface_roughness_m :
        Inner tube surface roughness [m] (default 0).
    annulus_surface_roughness_m :
        Outer pipe surface roughness [m] (default 0).
    inner_fouling_resistance_m2k_w :
        Inner-side fouling resistance [m²·K/W] (default 0).
    outer_fouling_resistance_m2k_w :
        Outer-side fouling resistance [m²·K/W] (default 0).
    """

    inner_tube_inner_diameter_m: float
    inner_tube_outer_diameter_m: float
    outer_pipe_inner_diameter_m: float
    effective_length_m: float
    wall_thermal_conductivity_w_m_k: float
    inner_surface_roughness_m: float = 0.0
    annulus_surface_roughness_m: float = 0.0
    inner_fouling_resistance_m2k_w: float = 0.0
    outer_fouling_resistance_m2k_w: float = 0.0

    def __post_init__(self) -> None:
        """Validate geometric constraints."""
        d_i = self.inner_tube_inner_diameter_m
        d_o = self.inner_tube_outer_diameter_m
        d_outer = self.outer_pipe_inner_diameter_m
        L = self.effective_length_m
        k = self.wall_thermal_conductivity_w_m_k
        r_i = self.inner_surface_roughness_m
        r_o = self.annulus_surface_roughness_m
        rf_i = self.inner_fouling_resistance_m2k_w
        rf_o = self.outer_fouling_resistance_m2k_w

        errors: list[str] = []
        if not math.isfinite(d_i) or d_i <= 0:
            errors.append(f"inner_tube_inner_diameter_m must be > 0, got {d_i}")
        if not math.isfinite(d_o) or d_o <= 0:
            errors.append(f"inner_tube_outer_diameter_m must be > 0, got {d_o}")
        if not math.isfinite(d_outer) or d_outer <= 0:
            errors.append(f"outer_pipe_inner_diameter_m must be > 0, got {d_outer}")
        if not (d_i < d_o):
            errors.append(
                f"inner_tube_inner_diameter ({d_i}) must be < inner_tube_outer_diameter ({d_o})"
            )
        if not (d_o < d_outer):
            errors.append(
                f"inner_tube_outer_diameter ({d_o}) must be < outer_pipe_inner_diameter ({d_outer})"
            )
        if not math.isfinite(L) or L <= 0:
            errors.append(f"effective_length_m must be > 0, got {L}")
        if not math.isfinite(k) or k <= 0:
            errors.append(f"wall_thermal_conductivity_w_m_k must be > 0, got {k}")
        if not math.isfinite(r_i) or r_i < 0:
            errors.append(f"inner_surface_roughness_m must be >= 0, got {r_i}")
        if not math.isfinite(r_o) or r_o < 0:
            errors.append(f"annulus_surface_roughness_m must be >= 0, got {r_o}")
        if not math.isfinite(rf_i) or rf_i < 0:
            errors.append(f"inner_fouling_resistance_m2k_w must be >= 0, got {rf_i}")
        if not math.isfinite(rf_o) or rf_o < 0:
            errors.append(f"outer_fouling_resistance_m2k_w must be >= 0, got {rf_o}")

        if errors:
            raise ValueError("; ".join(errors))

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------

    @property
    def area_inner_m2(self) -> float:
        """Inner surface area of the inner tube [m²]."""
        return math.pi * self.inner_tube_inner_diameter_m * self.effective_length_m

    @property
    def area_outer_m2(self) -> float:
        """Outer surface area of the inner tube [m²]."""
        return math.pi * self.inner_tube_outer_diameter_m * self.effective_length_m

    @property
    def hydraulic_diameter_annulus_m(self) -> float:
        """Hydraulic diameter of the annulus [m].

        ``D_h = D_outer_pipe_ID - D_inner_tube_OD``
        """
        return self.outer_pipe_inner_diameter_m - self.inner_tube_outer_diameter_m

    @property
    def flow_area_annulus_m2(self) -> float:
        """Cross-sectional flow area of the annulus [m²]."""
        r_o = self.inner_tube_outer_diameter_m / 2.0
        r_outer = self.outer_pipe_inner_diameter_m / 2.0
        return math.pi * (r_outer**2 - r_o**2)

    @property
    def flow_area_tube_m2(self) -> float:
        """Cross-sectional flow area of the inner tube [m²]."""
        r_i = self.inner_tube_inner_diameter_m / 2.0
        return math.pi * r_i**2

    @property
    def diameter_ratio(self) -> float:
        """Ratio D_inner_tube_OD / D_outer_pipe_ID."""
        return self.inner_tube_outer_diameter_m / self.outer_pipe_inner_diameter_m

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-compatible)."""
        return {
            "inner_tube_inner_diameter_m": self.inner_tube_inner_diameter_m,
            "inner_tube_outer_diameter_m": self.inner_tube_outer_diameter_m,
            "outer_pipe_inner_diameter_m": self.outer_pipe_inner_diameter_m,
            "effective_length_m": self.effective_length_m,
            "wall_thermal_conductivity_w_m_k": self.wall_thermal_conductivity_w_m_k,
            "inner_surface_roughness_m": self.inner_surface_roughness_m,
            "annulus_surface_roughness_m": self.annulus_surface_roughness_m,
            "inner_fouling_resistance_m2k_w": self.inner_fouling_resistance_m2k_w,
            "outer_fouling_resistance_m2k_w": self.outer_fouling_resistance_m2k_w,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoublePipeGeometry:
        """Deserialize from a plain dict."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
