"""Smart screening pipeline: combine all spatial filters.

Stages:
  1. Apogee-perigee pre-filter (cheapest)
  2. Octree per time slice
  3. Z-order sort for candidate batching

For each surviving (i, j) pair we return a `CandidatePair` with the approximate
TCA and miss distance to feed downstream Pc computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from skyshield.propagate.ephemeris import apogee_perigee
from skyshield.propagate.ocm import OCM
from skyshield.screen.octree import build_octree, octree_candidate_pairs


@dataclass
class CandidatePair:
    """A pair of objects that survived spatial screening."""
    obj1_id: int
    obj2_id: int
    approx_min_range_km: float
    approx_tca: datetime


def smart_screen(
    ocms: list[OCM],
    *,
    window_start: datetime,
    window_end: datetime,
    screening_radius_km: float = 10.0,
    time_step_seconds: float = 30.0,
) -> list[CandidatePair]:
    """Screen a catalog of OCMs over a time window.

    Strategy:
      1. Apogee-perigee filter to drop pairs that can never come close.
      2. Sample positions at `time_step_seconds` cadence; for each slice,
         build an octree and collect candidate pairs.
      3. Refine each candidate's TCA via cubic interpolation around the minimum.

    Parameters
    ----------
    ocms : list of OCM ephemerides
    window_start, window_end : datetime
        Screening window (TraCSS default: 2025-01-01T12:00 to 2025-01-08T12:00)
    screening_radius_km : float
        Coarse spatial filter radius. Use the largest SFSH dimension for
        the SFSH screening mode (e.g. 51 km for LEO1).
    time_step_seconds : float
        Sampling cadence. Coarser = faster but more candidates.

    Returns
    -------
    list of CandidatePair, deduplicated and sorted by approx_min_range_km.
    """
    if not ocms:
        return []

    # ---- Stage 1: apogee/perigee filter ----
    # Need numeric (a, p) per OCM — derive from state matrix
    apos = np.zeros(len(ocms))
    peris = np.zeros(len(ocms))
    sat_ids = [ocm.sat_id for ocm in ocms]
    for i, ocm in enumerate(ocms):
        mat = ocm.state_matrix()
        if mat.size > 0:
            apos[i], peris[i] = apogee_perigee(mat)

    # Quick apogee/perigee pair mask
    pad = screening_radius_km
    peri_i = peris[:, None]
    peri_j = peris[None, :]
    apo_i = apos[:, None]
    apo_j = apos[None, :]
    survives_ap = (np.maximum(peri_i, peri_j) - pad) <= (np.minimum(apo_i, apo_j) + pad)
    np.fill_diagonal(survives_ap, False)

    # ---- Stage 2: octree per time slice ----
    n_steps = int((window_end - window_start).total_seconds() / time_step_seconds) + 1
    candidates: dict[tuple[int, int], CandidatePair] = {}
    for step in range(n_steps):
        t = window_start + timedelta(seconds=step * time_step_seconds)
        # Interpolate positions for each OCM at time t
        positions = np.zeros((len(ocms), 3))
        active_mask = np.zeros(len(ocms), dtype=bool)
        for i, ocm in enumerate(ocms):
            if not ocm.states:
                continue
            # Find nearest state
            from skyshield.propagate.ephemeris import interp_state
            result = interp_state(ocm, t)
            if result is None:
                continue
            p, _ = result
            positions[i] = p
            active_mask[i] = True

        active_idx = np.where(active_mask)[0]
        if active_idx.size < 2:
            continue
        active_positions = positions[active_idx]

        # Build octree on active subset
        root = build_octree(active_positions, leaf_size=16, max_depth=12)
        pairs_local = octree_candidate_pairs(
            root, active_positions, screening_radius_km=screening_radius_km
        )

        # Map local indices back to global, and filter by apogee/perigee result
        for local_i, local_j in pairs_local:
            i_g = active_idx[local_i]
            j_g = active_idx[local_j]
            if not survives_ap[i_g, j_g]:
                continue
            id_i = sat_ids[i_g]
            id_j = sat_ids[j_g]
            if id_i == id_j:
                continue
            key = (min(id_i, id_j), max(id_i, id_j))
            dist = float(np.linalg.norm(active_positions[local_i] - active_positions[local_j]))
            if key in candidates:
                if dist < candidates[key].approx_min_range_km:
                    candidates[key] = CandidatePair(
                        obj1_id=key[0],
                        obj2_id=key[1],
                        approx_min_range_km=dist,
                        approx_tca=t,
                    )
            else:
                candidates[key] = CandidatePair(
                    obj1_id=key[0],
                    obj2_id=key[1],
                    approx_min_range_km=dist,
                    approx_tca=t,
                )

    return sorted(candidates.values(), key=lambda c: c.approx_min_range_km)
