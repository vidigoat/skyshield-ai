"""Space Flight Safety Handbook (SFSH) screening volume rules.

Per TraCSS User Guide Table 3 — the orbit-regime-dependent rectangular
screening volumes from the SFSH (18 & 19 SDS Spaceflight Safety Handbook v1.7).

Dimensions are in UVW (Radial / In-track / Cross-track) frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from skyshield.constants import MU_EARTH, R_EARTH


class OrbitRegime(Enum):
    """SFSH orbit regime classifications (per User Guide Table 3)."""

    DEEP_SPACE_TABLE3 = 1     # 1300 min < T < 1800 min, e < 0.25, i < 35°
    LEO4 = 2                  # 1200 km < perigee ≤ 2000 km, e < 0.25
    LEO3 = 3                  # 750 km < perigee ≤ 1200 km, e < 0.25
    LEO2 = 4                  # 500 km < perigee ≤ 750 km, e < 0.25
    LEO1 = 5                  # perigee ≤ 500 km, e < 0.25  (most Starlink lives here)
    DEEP_SPACE_TABLE4 = 6     # period > 225 min
    NEAR_EARTH_TABLE4 = 7     # period < 225 min
    HYPERBOLIC = 8            # e ≥ 1


@dataclass(frozen=True, slots=True)
class SFSHVolume:
    """A rectangular screening volume (half-extents) in UVW frame, km."""

    u_half_km: float          # radial half-extent
    v_half_km: float          # in-track half-extent
    w_half_km: float          # cross-track half-extent
    regime: OrbitRegime


# Per User Guide Table 3
SFSH_VOLUMES: dict[OrbitRegime, SFSHVolume] = {
    OrbitRegime.DEEP_SPACE_TABLE3: SFSHVolume(10.0, 10.0, 10.0, OrbitRegime.DEEP_SPACE_TABLE3),
    OrbitRegime.LEO4: SFSHVolume(0.4, 2.0, 2.0, OrbitRegime.LEO4),
    OrbitRegime.LEO3: SFSHVolume(0.4, 12.0, 12.0, OrbitRegime.LEO3),
    OrbitRegime.LEO2: SFSHVolume(0.4, 25.0, 25.0, OrbitRegime.LEO2),
    OrbitRegime.LEO1: SFSHVolume(0.4, 44.0, 51.0, OrbitRegime.LEO1),
    OrbitRegime.DEEP_SPACE_TABLE4: SFSHVolume(20.0, 20.0, 20.0, OrbitRegime.DEEP_SPACE_TABLE4),
    OrbitRegime.NEAR_EARTH_TABLE4: SFSHVolume(2.0, 25.0, 25.0, OrbitRegime.NEAR_EARTH_TABLE4),
    OrbitRegime.HYPERBOLIC: SFSHVolume(20.0, 50.0, 20.0, OrbitRegime.HYPERBOLIC),
}


def classify_orbit_regime(
    *,
    perigee_km: float,
    apogee_km: float,
    inclination_deg: float | None = None,
    period_min: float | None = None,
    eccentricity: float | None = None,
) -> OrbitRegime:
    """Classify an orbit into one of the SFSH regimes."""
    # Hyperbolic: e ≥ 1
    if eccentricity is not None and eccentricity >= 1.0:
        return OrbitRegime.HYPERBOLIC

    # Eccentricity check for primary SFSH classification
    ecc_ok = eccentricity is None or eccentricity < 0.25

    # Compute period if not given (from apogee + perigee assuming circular avg)
    if period_min is None:
        a = (perigee_km + apogee_km + 2.0 * R_EARTH) / 2.0
        period_sec = 2.0 * np.pi * np.sqrt(a ** 3 / MU_EARTH)
        period_min = period_sec / 60.0

    if not ecc_ok:
        # Falls to Table 4 by period
        return OrbitRegime.NEAR_EARTH_TABLE4 if period_min < 225 else OrbitRegime.DEEP_SPACE_TABLE4

    # SFSH Table 3 — Deep Space
    if 1300 < period_min < 1800:
        if inclination_deg is None or inclination_deg < 35:
            return OrbitRegime.DEEP_SPACE_TABLE3

    # SFSH Table 3 — LEO buckets by perigee
    if perigee_km <= 500:
        return OrbitRegime.LEO1
    if perigee_km <= 750:
        return OrbitRegime.LEO2
    if perigee_km <= 1200:
        return OrbitRegime.LEO3
    if perigee_km <= 2000:
        return OrbitRegime.LEO4

    # Fall-through to Table 4
    return OrbitRegime.NEAR_EARTH_TABLE4 if period_min < 225 else OrbitRegime.DEEP_SPACE_TABLE4


def sfsh_volume_for_regime(regime: OrbitRegime) -> SFSHVolume:
    """Look up the SFSH volume for a given regime."""
    return SFSH_VOLUMES[regime]


def is_within_sfsh_volume(
    relative_uvw_km: np.ndarray, volume: SFSHVolume
) -> bool:
    """Check whether a relative position in primary's UVW frame is inside the volume."""
    r = np.asarray(relative_uvw_km, dtype=np.float64)
    return bool(
        abs(r[0]) <= volume.u_half_km
        and abs(r[1]) <= volume.v_half_km
        and abs(r[2]) <= volume.w_half_km
    )
