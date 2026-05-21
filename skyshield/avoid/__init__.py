"""Differentiable collision avoidance maneuver optimization.

Uses gradient-based optimization through ∂SGP4 (the JAX-differentiable
SGP4 propagator) to find the minimum-Δv maneuver that drops Pc below a
configurable safety threshold.
"""

from skyshield.avoid.dsgp4 import propagate_with_grad, state_after_burn
from skyshield.avoid.optimizer import (
    ManeuverPlan,
    optimize_avoidance_maneuver,
)

__all__ = [
    "ManeuverPlan",
    "optimize_avoidance_maneuver",
    "propagate_with_grad",
    "state_after_burn",
]
