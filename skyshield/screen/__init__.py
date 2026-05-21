"""Spatial screening — multi-stage filter from N² pairs down to candidate pairs.

The novel algorithmic contribution of SkyShield. Three filters compose:
  1. Apogee-perigee: kicks out pairs whose orbits can never come close
  2. Octree spatial: bins by 3D position at coarse time steps
  3. Z-order Morton curve: locality-preserving sort for cache-efficient batching

The SFSH rules module implements the Space Flight Safety Handbook rectangular
screening volumes per TraCSS Table 3.
"""

from skyshield.screen.apogee_perigee import apogee_perigee_filter
from skyshield.screen.octree import OctreeNode, build_octree, octree_candidate_pairs
from skyshield.screen.sfsh_volumes import (
    SFSHVolume,
    classify_orbit_regime,
    sfsh_volume_for_regime,
)
from skyshield.screen.smart_screen import smart_screen
from skyshield.screen.zorder import morton_encode_3d

__all__ = [
    "OctreeNode",
    "SFSHVolume",
    "apogee_perigee_filter",
    "build_octree",
    "classify_orbit_regime",
    "morton_encode_3d",
    "octree_candidate_pairs",
    "sfsh_volume_for_regime",
    "smart_screen",
]
