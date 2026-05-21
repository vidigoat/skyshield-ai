"""∂SGP4 — differentiable SGP4 propagation in JAX.

Inspired by the ∂SGP4 paper (Acciarini et al., arXiv:2402.04830) but
implemented in JAX rather than PyTorch. The key property is that gradients
flow through the SGP4 propagation steps, enabling:
  - Gradient-based maneuver optimization
  - Sensitivity analysis (∂miss / ∂Δv, ∂Pc / ∂Δv)
  - Fine-tuning ephemeris parameters against high-precision data

Our SGP4-in-JAX implementation in `propagate.sgp4_jax` is already differentiable
because JAX traces through pure functions. This module wraps it with utility
functions for maneuver simulation.
"""

from __future__ import annotations

from collections.abc import Callable

import jax
import jax.numpy as jnp


def state_after_burn(
    state_before: jax.Array, dv: jax.Array
) -> jax.Array:
    """Apply an instantaneous impulse maneuver to a Cartesian state.

    state_before : (6,) array [x, y, z, vx, vy, vz] in J2000
    dv : (3,) Δv vector (km/s, J2000)
    Returns the post-burn state (6,).
    """
    return state_before.at[3:].add(dv)


def propagate_with_grad(
    propagator: Callable,
    initial_state: jax.Array,
    delta_v: jax.Array,
    burn_time_min: float,
    target_time_min: float,
):
    """Propagate, apply burn, propagate again — all differentiable.

    For now this is a placeholder that uses straight-line propagation between
    burn and target time. A full implementation would integrate through SGP4
    with the modified initial state.
    """
    pre_burn = propagator(initial_state, burn_time_min)
    post_burn = state_after_burn(pre_burn, delta_v)
    final = propagator(post_burn, target_time_min - burn_time_min)
    return final


@jax.jit
def predict_miss_distance(
    r1_at_tca: jax.Array,
    r2_at_tca: jax.Array,
    dv: jax.Array,
    time_to_tca_min: float,
) -> jax.Array:
    """Approximate post-burn miss distance via linear propagation.

    For small Δv, the change in position at TCA is approximately:
        Δr ≈ Δv × time_to_tca

    This is differentiable wrt Δv and is fast enough to use as the objective
    inside a gradient-descent optimizer loop.
    """
    delta_r = dv * (time_to_tca_min * 60.0)
    miss_after = (r1_at_tca + delta_r) - r2_at_tca
    return jnp.linalg.norm(miss_after)
