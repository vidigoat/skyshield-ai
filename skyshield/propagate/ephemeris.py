"""Ephemeris utilities: interpolation, frame transforms, useable-window filtering.

For the TraCSS benchmark, OCM ephemerides are sampled at discrete epochs but
TCA (time of closest approach) generally falls between samples. We use cubic
Hermite interpolation (state + derivative) which is exact for two-body motion
in the linear approximation and accurate to within a few meters for typical
LEO sampling rates (60-300 sec).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from skyshield.propagate.ocm import OCM


def interp_state(
    ocm: OCM, query_epoch: datetime
) -> tuple[np.ndarray, np.ndarray] | None:
    """Cubic Hermite interpolation of position/velocity at a given epoch.

    Returns (r, v) in the OCM's reference frame, or None if `query_epoch` falls
    outside the ephemeris's useable window.
    """
    if ocm.useable_start and query_epoch < ocm.useable_start:
        return None
    if ocm.useable_stop and query_epoch > ocm.useable_stop:
        return None
    if not ocm.states:
        return None

    epochs = np.array([s.epoch.timestamp() for s in ocm.states])
    t = query_epoch.timestamp()

    if t < epochs[0] or t > epochs[-1]:
        return None

    # Find bracketing pair
    idx = int(np.searchsorted(epochs, t)) - 1
    idx = max(0, min(idx, len(epochs) - 2))

    t0 = epochs[idx]
    t1 = epochs[idx + 1]
    h = t1 - t0
    if h <= 0:
        return None

    s0 = ocm.states[idx].as_array()
    s1 = ocm.states[idx + 1].as_array()
    p0, v0 = s0[:3], s0[3:]
    p1, v1 = s1[:3], s1[3:]

    # Cubic Hermite basis on normalized parameter u in [0, 1]
    u = (t - t0) / h
    h00 = 2.0 * u**3 - 3.0 * u**2 + 1.0
    h10 = u**3 - 2.0 * u**2 + u
    h01 = -2.0 * u**3 + 3.0 * u**2
    h11 = u**3 - u**2

    # Position interpolation (with velocity tangents scaled by h)
    p = h00 * p0 + h10 * h * v0 + h01 * p1 + h11 * h * v1

    # Velocity is the derivative of the Hermite polynomial wrt time
    h00d = (6.0 * u**2 - 6.0 * u) / h
    h10d = (3.0 * u**2 - 4.0 * u + 1.0)
    h01d = (-6.0 * u**2 + 6.0 * u) / h
    h11d = (3.0 * u**2 - 2.0 * u)
    v = h00d * p0 + h10d * v0 + h01d * p1 + h11d * v1

    return p, v


def filter_by_od_epoch(
    ocms: list[OCM], screening_window_start: datetime, max_age_days: float = 14.0
) -> list[OCM]:
    """Filter OCMs by OD epoch age per TraCSS User Guide §4.4."""
    return [ocm for ocm in ocms if ocm.od_age_days(screening_window_start) < max_age_days]


def filter_by_useable_window(
    ocms: list[OCM], window_start: datetime, window_end: datetime
) -> list[OCM]:
    """Drop OCMs whose useable window is entirely outside the screening window."""
    out = []
    for ocm in ocms:
        us = ocm.useable_start
        ue = ocm.useable_stop
        # Keep if there's any temporal overlap
        if (us is None or us <= window_end) and (ue is None or ue >= window_start):
            out.append(ocm)
    return out


def batch_interp_state(
    ocm,
    query_epochs: list[datetime],
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized cubic-Hermite interpolation at many query epochs.

    Returns (positions, velocities) both shaped (len(query_epochs), 3).
    Cells corresponding to queries outside the OCM's useable window or
    sample range are filled with NaN.

    Internally uses np.searchsorted (O(log N) per query) and vectorized
    Hermite basis evaluation — orders of magnitude faster than calling
    `interp_state` in a Python loop.
    """
    n_q = len(query_epochs)
    out_p = np.full((n_q, 3), np.nan, dtype=np.float64)
    out_v = np.full((n_q, 3), np.nan, dtype=np.float64)

    if not ocm.states:
        return out_p, out_v

    # Build epoch + state arrays once
    epochs_seconds = np.array([s.epoch.timestamp() for s in ocm.states], dtype=np.float64)
    states = np.array([s.as_array() for s in ocm.states], dtype=np.float64)  # (N, 6)
    positions = states[:, :3]
    velocities = states[:, 3:]

    q_t = np.array([t.timestamp() for t in query_epochs], dtype=np.float64)

    # Useable-window mask
    if ocm.useable_start is not None:
        q_t_min = ocm.useable_start.timestamp()
        valid = q_t >= q_t_min
    else:
        valid = np.ones(n_q, dtype=bool)
    if ocm.useable_stop is not None:
        q_t_max = ocm.useable_stop.timestamp()
        valid &= q_t <= q_t_max

    # Sample-range mask
    if epochs_seconds.size > 0:
        valid &= (q_t >= epochs_seconds[0]) & (q_t <= epochs_seconds[-1])

    if not valid.any():
        return out_p, out_v

    # Find bracketing indices via searchsorted
    idx = np.searchsorted(epochs_seconds, q_t, side="right") - 1
    idx = np.clip(idx, 0, epochs_seconds.size - 2)

    t0 = epochs_seconds[idx]
    t1 = epochs_seconds[idx + 1]
    h = t1 - t0
    # Avoid divide-by-zero
    h_safe = np.where(h > 0, h, 1.0)
    u = (q_t - t0) / h_safe

    # Hermite basis functions
    h00 = 2.0 * u**3 - 3.0 * u**2 + 1.0
    h10 = u**3 - 2.0 * u**2 + u
    h01 = -2.0 * u**3 + 3.0 * u**2
    h11 = u**3 - u**2

    p0 = positions[idx]
    p1 = positions[idx + 1]
    v0 = velocities[idx]
    v1 = velocities[idx + 1]
    h_col = h[:, None]
    p = h00[:, None] * p0 + h10[:, None] * h_col * v0 + h01[:, None] * p1 + h11[:, None] * h_col * v1

    # Derivative for velocity
    h00d = (6.0 * u**2 - 6.0 * u) / h_safe
    h10d = 3.0 * u**2 - 4.0 * u + 1.0
    h01d = (-6.0 * u**2 + 6.0 * u) / h_safe
    h11d = 3.0 * u**2 - 2.0 * u
    v = h00d[:, None] * p0 + h10d[:, None] * v0 + h01d[:, None] * p1 + h11d[:, None] * v1

    out_p[valid] = p[valid]
    out_v[valid] = v[valid]
    return out_p, out_v


def apogee_perigee(states: np.ndarray) -> tuple[float, float]:
    """Estimate apogee and perigee from an ephemeris state matrix.

    Parameters
    ----------
    states : ndarray (N, 6)
        [x, y, z, vx, vy, vz] rows.

    Returns
    -------
    (apogee_km, perigee_km) : tuple of floats
        Geocentric distance at apogee and perigee.

    For ephemerides spanning much less than one orbital period, this returns
    (max_r, min_r) over the available samples — useful as a coarse filter for
    apogee-perigee screening even on partial orbits.
    """
    if states.size == 0:
        return 0.0, 0.0
    rs = np.linalg.norm(states[:, :3], axis=1)
    return float(np.max(rs)), float(np.min(rs))
