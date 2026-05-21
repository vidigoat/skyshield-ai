"""Z-order (Morton) curve for spatial locality preservation.

Used to sort objects by spatial position such that nearby objects in 3D are
also nearby in memory. Combined with the octree, this lets us batch
conjunction-probability evaluations in a cache-friendly way.

We implement the standard "bit-interleaving" Morton encoding for 3D points.
"""

from __future__ import annotations

import numpy as np


def _spread_bits(x: int, n_bits: int = 21) -> int:
    """Spread bits of `x` so they occupy every 3rd bit position.

    Insert two zero bits between every bit of `x`. For 21-bit input, output
    occupies 63 bits — fits in a 64-bit integer.
    """
    x &= (1 << n_bits) - 1
    x = (x | (x << 32)) & 0x1F00000000FFFF
    x = (x | (x << 16)) & 0x1F0000FF0000FF
    x = (x | (x << 8)) & 0x100F00F00F00F00F
    x = (x | (x << 4)) & 0x10C30C30C30C30C3
    x = (x | (x << 2)) & 0x1249249249249249
    return x


def morton_encode_3d(x: int, y: int, z: int, n_bits: int = 21) -> int:
    """Interleave the bits of 3 integers to produce the Morton code."""
    return _spread_bits(x, n_bits) | (_spread_bits(y, n_bits) << 1) | (_spread_bits(z, n_bits) << 2)


def morton_sort_indices(
    positions_km: np.ndarray,
    *,
    box_min_km: float = -10000.0,
    box_max_km: float = 10000.0,
    n_bits: int = 21,
) -> np.ndarray:
    """Return indices that sort positions along the Z-order Morton curve.

    Parameters
    ----------
    positions_km : (N, 3) array
        Cartesian positions in km (typically TEME or J2000).
    box_min_km, box_max_km : float
        Bounding box for the constellation (LEO ~7000 km radius works with default).
    n_bits : int
        Bits per dimension for the Morton code. 21 bits → ~5 m resolution at 10000 km.

    Returns
    -------
    order : (N,) integer array such that positions_km[order] is Z-order-sorted.
    """
    pos = np.asarray(positions_km, dtype=np.float64).reshape(-1, 3)
    box_size = box_max_km - box_min_km
    scale = (1 << n_bits) - 1
    # Normalize to [0, 1] then to integer [0, scale]
    ints = ((pos - box_min_km) / box_size * scale).astype(np.int64)
    ints = np.clip(ints, 0, scale)
    codes = np.array([
        morton_encode_3d(int(ints[i, 0]), int(ints[i, 1]), int(ints[i, 2]), n_bits)
        for i in range(pos.shape[0])
    ], dtype=np.int64)
    return np.argsort(codes)
