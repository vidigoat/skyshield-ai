"""Tests for spatial screening modules."""

from __future__ import annotations

import numpy as np

from skyshield.screen.apogee_perigee import (
    apogee_perigee_filter,
    apogee_perigee_filter_pairs,
)
from skyshield.screen.octree import build_octree, octree_candidate_pairs
from skyshield.screen.sfsh_volumes import (
    OrbitRegime,
    classify_orbit_regime,
    is_within_sfsh_volume,
    sfsh_volume_for_regime,
)
from skyshield.screen.zorder import morton_encode_3d, morton_sort_indices

# ---- Apogee-perigee tests ----

def test_apogee_perigee_filter_basic():
    """Pairs with disjoint radial ranges should be filtered out."""
    # Object 0: 6800 to 7000 km
    # Object 1: 6900 to 7100 km (overlaps with 0)
    # Object 2: 9000 to 9100 km (no overlap with 0)
    apos = np.array([7000.0, 7100.0, 9100.0])
    peris = np.array([6800.0, 6900.0, 9000.0])
    mask = apogee_perigee_filter(apos, peris, screening_radius_km=10.0)
    assert mask[0, 1]   # overlapping ranges
    assert mask[1, 0]
    assert not mask[0, 2]  # disjoint ranges
    assert not mask[2, 0]
    assert not mask[0, 0]  # self-pair excluded


def test_apogee_perigee_filter_pairs_returns_sorted():
    """Returned pairs should be present (order is implementation-defined)."""
    sat_ids = [42, 17, 99]
    apos = np.array([7000.0, 7100.0, 9100.0])
    peris = np.array([6800.0, 6900.0, 9000.0])
    pairs = apogee_perigee_filter_pairs(sat_ids, apos, peris, screening_radius_km=10.0)
    flat = {tuple(sorted(p)) for p in pairs}
    assert (17, 42) in flat
    # 99 has radial range 9000-9100 — disjoint from 42 and 17 (~6800-7100)
    assert (42, 99) not in flat
    assert (17, 99) not in flat


# ---- SFSH volume tests ----

def test_leo1_classification():
    """ISS-like orbit (~400 km) should be LEO1."""
    regime = classify_orbit_regime(
        perigee_km=400, apogee_km=410, inclination_deg=51.6, eccentricity=0.001
    )
    assert regime == OrbitRegime.LEO1


def test_leo4_classification():
    """Mid-MEO (1500 km perigee) should be LEO4."""
    regime = classify_orbit_regime(
        perigee_km=1500, apogee_km=1600, inclination_deg=53, eccentricity=0.001
    )
    assert regime == OrbitRegime.LEO4


def test_deep_space_classification():
    """Geosynchronous-class (period ~1440 min) should be Deep Space."""
    regime = classify_orbit_regime(
        perigee_km=35780, apogee_km=35800, inclination_deg=0.5, period_min=1436, eccentricity=0.001
    )
    assert regime in (OrbitRegime.DEEP_SPACE_TABLE3, OrbitRegime.DEEP_SPACE_TABLE4)


def test_hyperbolic_classification():
    """Eccentricity ≥ 1 = hyperbolic."""
    regime = classify_orbit_regime(
        perigee_km=200, apogee_km=1e6, eccentricity=1.5
    )
    assert regime == OrbitRegime.HYPERBOLIC


def test_sfsh_leo1_volume_matches_user_guide():
    """LEO1 volume from User Guide Table 3 = (0.4, 44, 51) km."""
    v = sfsh_volume_for_regime(OrbitRegime.LEO1)
    assert v.u_half_km == 0.4
    assert v.v_half_km == 44.0
    assert v.w_half_km == 51.0


def test_within_sfsh_volume():
    v = sfsh_volume_for_regime(OrbitRegime.LEO1)
    # Inside
    assert is_within_sfsh_volume(np.array([0.1, 10.0, 20.0]), v)
    # Outside in u
    assert not is_within_sfsh_volume(np.array([0.5, 10.0, 20.0]), v)
    # Outside in v
    assert not is_within_sfsh_volume(np.array([0.1, 50.0, 20.0]), v)


# ---- Z-order tests ----

def test_morton_encode_zero():
    assert morton_encode_3d(0, 0, 0) == 0


def test_morton_encode_one():
    # (1, 0, 0) = bit 0 of x = bit position 0 of code
    # (0, 1, 0) = bit 0 of y = bit position 1
    # (0, 0, 1) = bit 0 of z = bit position 2
    assert morton_encode_3d(1, 0, 0) == 0b001
    assert morton_encode_3d(0, 1, 0) == 0b010
    assert morton_encode_3d(0, 0, 1) == 0b100
    assert morton_encode_3d(1, 1, 1) == 0b111


def test_morton_sort_groups_nearby():
    """Nearby points in 3D should end up adjacent after Morton sort."""
    # Two clusters of points: near origin and near (5000, 5000, 5000)
    cluster1 = np.array([
        [0.0, 0.0, 0.0],
        [10.0, 10.0, 10.0],
        [20.0, 20.0, 20.0],
    ])
    cluster2 = np.array([
        [5000.0, 5000.0, 5000.0],
        [5010.0, 5010.0, 5010.0],
        [5020.0, 5020.0, 5020.0],
    ])
    pos = np.vstack([cluster1, cluster2[::-1], cluster1[::-1]])  # shuffle
    order = morton_sort_indices(pos)
    sorted_pos = pos[order]
    # After sorting, items from each cluster should be grouped
    # (we don't check exact ordering, just that no cluster point is between two
    # points of the other cluster)
    in_cluster1 = sorted_pos[:, 0] < 1000
    transitions = np.sum(np.diff(in_cluster1.astype(int)) != 0)
    assert transitions <= 1, f"Too many cluster transitions: {transitions}"


# ---- Octree tests ----

def test_octree_returns_close_pairs():
    """Octree should find all close pairs and skip distant ones."""
    positions = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],      # 1 km from origin
        [100.0, 0.0, 0.0],    # 100 km away
        [200.0, 0.0, 0.0],    # close to 100
    ])
    root = build_octree(positions, leaf_size=2)
    pairs = octree_candidate_pairs(root, positions, screening_radius_km=5.0)
    assert (0, 1) in [tuple(sorted(p)) for p in pairs]
    # 100 and 200 are 100 km apart — should NOT pair with screening_radius=5
    assert (2, 3) not in [tuple(sorted(p)) for p in pairs]


def test_octree_self_pair_excluded():
    positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    root = build_octree(positions, leaf_size=2)
    pairs = octree_candidate_pairs(root, positions, screening_radius_km=2.0)
    for i, j in pairs:
        assert i != j


def test_octree_handles_empty():
    positions = np.empty((0, 3))
    root = build_octree(positions, leaf_size=2)
    pairs = octree_candidate_pairs(root, positions, screening_radius_km=10.0)
    assert pairs == []
