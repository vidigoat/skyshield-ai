"""Tests for the multi-fleet maneuver coordinator."""

from __future__ import annotations

import numpy as np

from skyshield.avoid.fleet import FleetConjunction, optimize_fleet_maneuvers


def test_empty_returns_zero_plan():
    plan = optimize_fleet_maneuvers(conjunctions=[])
    assert plan.total_dv_mps == 0.0
    assert plan.burns == {}


def test_single_conjunction_reduces_to_pair():
    """One primary, one conjunction — should match the pair optimizer's output qualitatively."""
    c = FleetConjunction(
        primary_id=42,
        secondary_id=99,
        r_primary_at_tca_km=np.array([7000.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7000.0, 0.0, 0.05]),
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=3600.0,
        pc_baseline=1e-3,
    )
    plan = optimize_fleet_maneuvers(conjunctions=[c], target_miss_km=1.0)
    assert 42 in plan.burns
    dv, _ = plan.burns[42]
    assert dv.shape == (3,)
    assert plan.total_dv_mps > 0  # something was planned
    assert plan.total_dv_mps < 200  # not crazy


def test_two_primaries_independent():
    """Two primaries with independent conjunctions should both get nonzero Δv."""
    a = FleetConjunction(
        primary_id=10,
        secondary_id=20,
        r_primary_at_tca_km=np.array([7000.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7000.0, 0.0, 0.05]),
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=3600.0,
        pc_baseline=1e-3,
    )
    b = FleetConjunction(
        primary_id=11,
        secondary_id=21,
        r_primary_at_tca_km=np.array([7100.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7100.0, 0.0, 0.08]),
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=7200.0,
        pc_baseline=5e-4,
    )
    plan = optimize_fleet_maneuvers(conjunctions=[a, b])
    assert 10 in plan.burns
    assert 11 in plan.burns
    assert plan.per_primary_dv_mps[10] > 0
    assert plan.per_primary_dv_mps[11] > 0


def test_propellant_cap_respected():
    c = FleetConjunction(
        primary_id=42,
        secondary_id=99,
        r_primary_at_tca_km=np.array([7000.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7000.0, 0.0, 0.001]),  # tiny miss
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=600.0,
        pc_baseline=1e-2,
    )
    plan = optimize_fleet_maneuvers(
        conjunctions=[c],
        target_miss_km=10.0,
        per_primary_max_dv_mps={42: 5.0},   # very tight cap
    )
    assert plan.per_primary_dv_mps[42] <= 5.0 + 1e-3
