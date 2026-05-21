"""Apogee-perigee pre-filter — the cheapest stage of conjunction screening.

If object A's perigee distance from Earth's center is greater than object B's
apogee + screening volume, the orbits can never come within the screening
volume — eliminate the pair without any expensive computation.

This filter typically removes 99%+ of the N² candidate pairs in a real
constellation catalog, dramatically speeding up downstream stages.
"""

from __future__ import annotations

import numpy as np


def apogee_perigee_filter(
    apogees_km: np.ndarray,
    perigees_km: np.ndarray,
    *,
    screening_radius_km: float = 10.0,
) -> np.ndarray:
    """Return a boolean (N, N) matrix where True = pair survives the filter.

    Pair (i, j) survives if their radial extents could possibly overlap with
    the screening radius added.

    Parameters
    ----------
    apogees_km : (N,) array of apogee geocentric radii in km
    perigees_km : (N,) array of perigee geocentric radii in km
    screening_radius_km : float
        Add this to each object's apogee (and subtract from perigee) before
        the overlap check. Use the largest SFSH volume dimension for the
        SFSH config (e.g., 51 km for LEO1).

    Returns
    -------
    mask : (N, N) boolean array. mask[i, j] is True if pair (i, j) survives.
    """
    apogees = np.asarray(apogees_km, dtype=np.float64).reshape(-1)
    perigees = np.asarray(perigees_km, dtype=np.float64).reshape(-1)
    n = apogees.size
    if n != perigees.size:
        raise ValueError("apogees and perigees must have the same length")

    # Pad by the screening radius — both objects can be displaced from their
    # mean orbit by uncertainty + screening volume
    pad = screening_radius_km
    # Pair (i, j) survives iff:
    #   max(peri_i, peri_j) - pad <= min(apo_i, apo_j) + pad
    # i.e., the radial ranges overlap once padded.
    peri_i = perigees[:, None]
    peri_j = perigees[None, :]
    apo_i = apogees[:, None]
    apo_j = apogees[None, :]
    max_peri = np.maximum(peri_i, peri_j) - pad
    min_apo = np.minimum(apo_i, apo_j) + pad

    survives = max_peri <= min_apo
    # Exclude self-pairs (diagonal)
    np.fill_diagonal(survives, False)
    return survives


def apogee_perigee_filter_pairs(
    sat_ids: list[int],
    apogees_km: np.ndarray,
    perigees_km: np.ndarray,
    *,
    screening_radius_km: float = 10.0,
) -> list[tuple[int, int]]:
    """Return a list of surviving (i, j) Sat ID pairs with i < j."""
    mask = apogee_perigee_filter(apogees_km, perigees_km, screening_radius_km=screening_radius_km)
    pairs: list[tuple[int, int]] = []
    n = len(sat_ids)
    for i in range(n):
        for j in range(i + 1, n):
            if mask[i, j]:
                pairs.append((sat_ids[i], sat_ids[j]))
    return pairs
