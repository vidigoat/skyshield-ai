"""Tests for the avoidance maneuver optimizer."""

from __future__ import annotations

import numpy as np
import pytest

from skyshield.avoid.dsgp4 import predict_miss_distance, state_after_burn
from skyshield.avoid.optimizer import optimize_avoidance_maneuver


def test_state_after_burn():
    """An impulsive burn only modifies velocity, not position."""
    import jax.numpy as jnp
    s = jnp.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    dv = jnp.array([0.1, 0.2, 0.3])
    after = state_after_burn(s, dv)
    # Position unchanged
    assert float(after[0]) == 1.0
    assert float(after[1]) == 2.0
    assert float(after[2]) == 3.0
    # Velocity changed
    assert float(after[3]) == pytest.approx(4.1)
    assert float(after[4]) == pytest.approx(5.2)
    assert float(after[5]) == pytest.approx(6.3)


def test_predict_miss_increases_with_dv():
    """Larger Δv away from the conjunction should increase miss distance."""
    import jax.numpy as jnp
    r1 = jnp.array([7000.0, 0.0, 0.0])
    r2 = jnp.array([7000.0, 0.0, 0.05])    # 50 m offset
    dv_small = jnp.array([0.0, 0.0, 1e-5])
    dv_large = jnp.array([0.0, 0.0, 1e-3])
    miss_small = float(predict_miss_distance(r1, r2, dv_small, 30.0))
    miss_large = float(predict_miss_distance(r1, r2, dv_large, 30.0))
    assert miss_large > miss_small


def test_optimizer_reduces_pc_for_close_approach():
    """For a head-on close approach, the optimizer should find a Δv that
    increases miss to at least the target."""
    r1 = np.array([7000.0, 0.0, 0.0])
    r2 = np.array([7000.0, 0.0, 0.1])      # 100 m miss
    v1 = np.array([0.0, 7.5, 0.0])
    v2 = np.array([0.0, -7.5, 0.0])
    plan = optimize_avoidance_maneuver(
        r1_at_tca_km=r1, r2_at_tca_km=r2,
        v1_at_tca_kms=v1, v2_at_tca_kms=v2,
        burn_time_minutes_before_tca=30.0,
        target_miss_km=1.0,
        max_dv_kms=0.05,
        n_iterations=200,
    )
    # Δv should be small (< 50 m/s)
    assert plan.delta_v_mps < 50.0
    # Post-burn miss should be larger than initial
    assert plan.predicted_miss_km_after > 0.1


def test_optimizer_respects_max_dv():
    """Optimizer should never return |Δv| > max_dv."""
    r1 = np.array([7000.0, 0.0, 0.0])
    r2 = np.array([7000.0, 0.0, 0.001])    # 1 m miss
    v1 = np.array([0.0, 7.5, 0.0])
    v2 = np.array([0.0, -7.5, 0.0])
    plan = optimize_avoidance_maneuver(
        r1_at_tca_km=r1, r2_at_tca_km=r2,
        v1_at_tca_kms=v1, v2_at_tca_kms=v2,
        burn_time_minutes_before_tca=10.0,
        target_miss_km=100.0,    # very aggressive — likely needs max Δv
        max_dv_kms=0.05,
        n_iterations=200,
    )
    assert plan.delta_v_mps <= 50.0 + 1e-3   # tiny float-precision slack
