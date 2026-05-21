"""Natural-language explainer for conjunction-analysis output.

Converts Pc, Δv, and miss-distance numbers into plain English. Used by the
agent's final-answer step when no LLM is available (stub mode) or to provide
deterministic explanations that supplement Claude's free-form output.
"""

from __future__ import annotations


def pc_to_plain_english(pc: float | None) -> str:
    """Translate a Pc value into a plain-English risk statement."""
    if pc is None:
        return "Probability could not be computed (covariance was singular or NaN)."
    if pc <= 0:
        return "Essentially zero collision probability."
    if pc < 1e-7:
        return f"Negligible risk (Pc = {pc:.2e}, roughly 1-in-{int(1/pc):,})."
    if pc < 1e-5:
        return f"Very low risk (Pc = {pc:.2e}, roughly 1-in-{int(1/pc):,})."
    if pc < 1e-4:
        return (
            f"Low risk but worth monitoring (Pc = {pc:.2e}, roughly 1-in-{int(1/pc):,})."
        )
    if pc < 1e-3:
        return (
            f"Elevated risk — operators typically alert at this level "
            f"(Pc = {pc:.2e}, roughly 1-in-{int(1/pc):,})."
        )
    if pc < 1e-2:
        return (
            f"High risk — most operators would consider an avoidance maneuver "
            f"(Pc = {pc:.2e}, roughly 1-in-{int(1/pc):,})."
        )
    return f"Very high risk — collision plausible if uncertainties are correct (Pc = {pc:.2e})."


def miss_to_plain_english(miss_km: float) -> str:
    """Describe a miss distance in human-scale terms."""
    if miss_km < 0.01:
        return f"Miss distance is {miss_km * 1000:.1f} m — closer than a soccer field."
    if miss_km < 1.0:
        return f"Miss distance is {miss_km:.3f} km ({miss_km * 1000:.0f} m)."
    if miss_km < 10:
        return f"Miss distance is {miss_km:.1f} km — within the typical screening volume."
    return f"Miss distance is {miss_km:.0f} km."


def dv_to_plain_english(dv_mps: float) -> str:
    """Describe a Δv magnitude in operator-friendly terms."""
    if dv_mps < 0.01:
        return f"Negligible Δv ({dv_mps * 1000:.2f} mm/s)."
    if dv_mps < 1.0:
        return f"Δv of {dv_mps:.3f} m/s — typical small station-keeping burn."
    if dv_mps < 10:
        return f"Δv of {dv_mps:.1f} m/s — moderate avoidance burn."
    if dv_mps < 50:
        return f"Δv of {dv_mps:.0f} m/s — large avoidance burn, plan propellant accordingly."
    return f"Δv of {dv_mps:.0f} m/s — very large burn, near the safe-maneuver limit."
