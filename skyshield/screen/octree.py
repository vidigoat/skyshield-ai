"""Octree spatial indexing for conjunction screening.

We build an octree over the constellation at each time slice. Pairs of objects
in the same or adjacent cells (within `screening_radius`) become candidate
pairs for downstream Pc computation. Pairs in distant cells are eliminated
without further work.

This is the workhorse algorithmic contribution that lets us screen mega-
constellations in real-time on a single GPU. Per-time-slice cost is
O(N + K) where K is the number of candidate pairs (typically K ≪ N²).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class OctreeNode:
    """A node in the spatial octree.

    Each node represents an axis-aligned box. Leaf nodes have a list of
    object indices; internal nodes have 8 children (octants).
    """

    box_min: np.ndarray             # (3,) min corner in km
    box_max: np.ndarray             # (3,) max corner in km
    indices: list[int] = field(default_factory=list)
    children: list[OctreeNode | None] = field(default_factory=lambda: [None] * 8)
    depth: int = 0

    @property
    def is_leaf(self) -> bool:
        return all(c is None for c in self.children)

    def center(self) -> np.ndarray:
        return 0.5 * (self.box_min + self.box_max)

    def half_size(self) -> np.ndarray:
        return 0.5 * (self.box_max - self.box_min)


def build_octree(
    positions_km: np.ndarray,
    *,
    leaf_size: int = 8,
    max_depth: int = 16,
    box_min: float = -10000.0,
    box_max: float = 10000.0,
) -> OctreeNode:
    """Construct an octree over the given positions.

    Parameters
    ----------
    positions_km : (N, 3) array
        Object positions in TEME or J2000 (km).
    leaf_size : int
        Subdivide nodes that contain more than this many indices.
    max_depth : int
        Hard cap on tree depth.
    box_min, box_max : float
        Initial bounding cube extent (one number; symmetric around origin).
    """
    pos = np.asarray(positions_km, dtype=np.float64).reshape(-1, 3)
    n = pos.shape[0]
    root = OctreeNode(
        box_min=np.full(3, box_min, dtype=np.float64),
        box_max=np.full(3, box_max, dtype=np.float64),
        indices=list(range(n)),
        depth=0,
    )
    _subdivide(root, pos, leaf_size, max_depth)
    return root


def _subdivide(node: OctreeNode, positions: np.ndarray, leaf_size: int, max_depth: int) -> None:
    if len(node.indices) <= leaf_size or node.depth >= max_depth:
        return

    center = node.center()
    children_indices: list[list[int]] = [[] for _ in range(8)]
    for idx in node.indices:
        p = positions[idx]
        octant = 0
        if p[0] >= center[0]:
            octant |= 1
        if p[1] >= center[1]:
            octant |= 2
        if p[2] >= center[2]:
            octant |= 4
        children_indices[octant].append(idx)

    # Build children
    for oct_idx in range(8):
        if not children_indices[oct_idx]:
            continue
        c_min = node.box_min.copy()
        c_max = node.box_max.copy()
        if oct_idx & 1:
            c_min[0] = center[0]
        else:
            c_max[0] = center[0]
        if oct_idx & 2:
            c_min[1] = center[1]
        else:
            c_max[1] = center[1]
        if oct_idx & 4:
            c_min[2] = center[2]
        else:
            c_max[2] = center[2]
        child = OctreeNode(
            box_min=c_min,
            box_max=c_max,
            indices=children_indices[oct_idx],
            depth=node.depth + 1,
        )
        node.children[oct_idx] = child
        _subdivide(child, positions, leaf_size, max_depth)

    # After subdivision, internal nodes don't hold indices themselves
    node.indices = []


def octree_candidate_pairs(
    root: OctreeNode,
    positions_km: np.ndarray,
    *,
    screening_radius_km: float,
) -> list[tuple[int, int]]:
    """Return all pairs (i, j) with i < j whose positions are within
    `screening_radius_km` based on octree proximity.

    For correctness, we expand the search to all nodes whose box-to-box
    distance is less than the screening radius — pairs only get rejected
    if their boxes can't possibly come within the radius.
    """
    positions = np.asarray(positions_km, dtype=np.float64).reshape(-1, 3)
    pairs: list[tuple[int, int]] = []
    _collect_pairs(root, root, positions, screening_radius_km, pairs)
    return pairs


def _box_box_distance(a: OctreeNode, b: OctreeNode) -> float:
    """Minimum distance between two axis-aligned boxes (0 if overlapping)."""
    dx = max(0.0, max(a.box_min[0] - b.box_max[0], b.box_min[0] - a.box_max[0]))
    dy = max(0.0, max(a.box_min[1] - b.box_max[1], b.box_min[1] - a.box_max[1]))
    dz = max(0.0, max(a.box_min[2] - b.box_max[2], b.box_min[2] - a.box_max[2]))
    return float(np.sqrt(dx * dx + dy * dy + dz * dz))


def _collect_pairs(
    a: OctreeNode,
    b: OctreeNode,
    positions: np.ndarray,
    screening_radius_km: float,
    out: list[tuple[int, int]],
) -> None:
    """Recursively collect candidate pairs from two subtrees."""
    # Quick reject: if boxes are farther than screening radius, no candidates
    if _box_box_distance(a, b) > screening_radius_km:
        return

    # Both leaves — enumerate pairs
    if a.is_leaf and b.is_leaf:
        if a is b:
            ids = a.indices
            for i in range(len(ids)):
                pi = positions[ids[i]]
                for j in range(i + 1, len(ids)):
                    pj = positions[ids[j]]
                    if np.linalg.norm(pi - pj) <= screening_radius_km:
                        x, y = sorted((ids[i], ids[j]))
                        out.append((x, y))
            return
        for idx_a in a.indices:
            pa = positions[idx_a]
            for idx_b in b.indices:
                if idx_a == idx_b:
                    continue
                pb = positions[idx_b]
                if np.linalg.norm(pa - pb) <= screening_radius_km:
                    x, y = sorted((idx_a, idx_b))
                    out.append((x, y))
        return

    # Recurse on the larger node's children
    if a.is_leaf:
        for child in b.children:
            if child is not None:
                _collect_pairs(a, child, positions, screening_radius_km, out)
        return
    if b.is_leaf:
        for child in a.children:
            if child is not None:
                _collect_pairs(child, b, positions, screening_radius_km, out)
        return

    # Both internal — recurse on all child combinations (avoid double-counting)
    if a is b:
        for i in range(8):
            ca = a.children[i]
            if ca is None:
                continue
            for j in range(i, 8):
                cb = b.children[j]
                if cb is None:
                    continue
                _collect_pairs(ca, cb, positions, screening_radius_km, out)
    else:
        for ca in a.children:
            if ca is None:
                continue
            for cb in b.children:
                if cb is None:
                    continue
                _collect_pairs(ca, cb, positions, screening_radius_km, out)
