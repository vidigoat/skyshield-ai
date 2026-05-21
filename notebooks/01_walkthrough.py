"""Walkthrough — runnable as a script or convertible to a Jupyter notebook.

`uv run python notebooks/01_walkthrough.py` to execute end-to-end.
`uv run jupyter nbconvert --to notebook --execute notebooks/01_walkthrough.py`
to render as an ipynb.

Demonstrates every layer of SkyShield AI on a small, fast example:
  1. Parse a real OCM ephemeris file
  2. Propagate a satellite forward in time (SGP4-in-JAX)
  3. Build a spatial screener and find candidate pairs
  4. Compute Pc with all 5 methods, side by side
  5. Optimize an avoidance maneuver
  6. Build a multi-fleet plan
  7. (Optional) ask the agent a question (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


def section(title: str) -> None:
    bar = "─" * 60
    print(f"\n{bar}\n  {title}\n{bar}")


# ─────────────────────────────────────────────────────────────────
section("1. Parse a real Aerospace IVV OCM file")
# ─────────────────────────────────────────────────────────────────
from skyshield.propagate.ocm import parse_ocm_file

sample_path = Path(__file__).parent.parent / "data" / "tracss" / "sample_extract" / "AerospaceIVVDataset_20251009" / "CDM" / "95008.ocm"
if sample_path.exists():
    o = parse_ocm_file(sample_path)
    print(f"  Object designator: {o.object_designator}")
    print(f"  Ref frame: {o.ref_frame}, Time system: {o.time_system}")
    print(f"  OD epoch: {o.od_epoch}")
    print(f"  Useable: {o.useable_start} → {o.useable_stop}")
    print(f"  States: {len(o.states)}, Covariances: {len(o.covariances)}")
else:
    print(f"  (sample file not present — re-extract data/tracss/sample_extract/)")

# ─────────────────────────────────────────────────────────────────
section("2. SGP4-in-JAX propagation")
# ─────────────────────────────────────────────────────────────────
from skyshield.propagate.tle import parse_tle_text
from skyshield.propagate.sgp4_jax import elements_from_tle, propagate_one
import jax.numpy as jnp

ISS = """ISS (ZARYA)
1 25544U 98067A   24001.50000000  .00012345  00000+0  22845-3 0  9991
2 25544  51.6400 247.4622 0006703 130.5360 325.0288 15.49558123431234"""

tle = parse_tle_text(ISS)
elt = elements_from_tle(tle)
r0, v0 = propagate_one(elt, jnp.asarray(0.0))
print(f"  ISS at epoch:")
print(f"    r = {tuple(round(float(x), 1) for x in r0)} km")
print(f"    v = {tuple(round(float(x), 3) for x in v0)} km/s")
print(f"    |r| = {float(jnp.linalg.norm(r0)):.1f} km ({float(jnp.linalg.norm(r0)) - 6378:.0f} km alt)")
print(f"    |v| = {float(jnp.linalg.norm(v0)):.3f} km/s")

# ─────────────────────────────────────────────────────────────────
section("3. Pc with all 5 methods on a known conjunction")
# ─────────────────────────────────────────────────────────────────
from skyshield.pc.alfano import pc_alfano2004
from skyshield.pc.chan import pc_chan
from skyshield.pc.foster import pc_foster
from skyshield.pc.patera import pc_patera
from skyshield.pc.monte_carlo import pc_monte_carlo

# 100m miss, isotropic 50m sigma, HBR 5m
fixture = dict(
    r1=np.array([7000.0, 0.0, 0.0]),
    r2=np.array([7000.0, 0.05, 0.1]),
    v1=np.array([0.0, 7.5, 0.0]),
    v2=np.array([0.0, -7.5, 0.0]),
    cov1_pos_j2000=np.eye(3) * (0.05 ** 2),
    cov2_pos_j2000=np.eye(3) * (0.05 ** 2),
    hbr_m=5.0,
)
print(f"  Alfano 2004 (primary, TraCSS):  {pc_alfano2004(**fixture):.3e}")
print(f"  Chan:                           {pc_chan(**fixture):.3e}")
print(f"  Foster:                         {pc_foster(**fixture, n_rings=20, n_angles=36):.3e}")
print(f"  Patera:                         {pc_patera(**fixture):.3e}")
print(f"  Monte Carlo (200k samples):     {pc_monte_carlo(**fixture, n_samples=200_000):.3e}")

# ─────────────────────────────────────────────────────────────────
section("4. Avoidance maneuver — gradient-based")
# ─────────────────────────────────────────────────────────────────
from skyshield.avoid.optimizer import optimize_avoidance_maneuver

plan = optimize_avoidance_maneuver(
    r1_at_tca_km=fixture["r1"],
    r2_at_tca_km=fixture["r2"],
    v1_at_tca_kms=fixture["v1"],
    v2_at_tca_kms=fixture["v2"],
    burn_time_minutes_before_tca=30.0,
    target_miss_km=1.0,
)
print(f"  Δv: {plan.delta_v_mps:.3f} m/s")
print(f"  Burn lead: {plan.burn_time_seconds_before_tca / 60:.0f} min before TCA")
print(f"  Predicted miss after burn: {plan.predicted_miss_km_after:.3f} km")
print(f"  Converged: {plan.converged} after {plan.n_iterations} iterations")

# ─────────────────────────────────────────────────────────────────
section("5. Multi-fleet maneuver plan (novel)")
# ─────────────────────────────────────────────────────────────────
from skyshield.avoid.fleet import FleetConjunction, optimize_fleet_maneuvers

conjs = [
    FleetConjunction(
        primary_id=10,
        secondary_id=20,
        r_primary_at_tca_km=np.array([7000.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7000.0, 0.0, 0.05]),
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=3600.0,
        pc_baseline=1e-3,
    ),
    FleetConjunction(
        primary_id=11,
        secondary_id=21,
        r_primary_at_tca_km=np.array([7100.0, 0.0, 0.0]),
        r_secondary_at_tca_km=np.array([7100.0, 0.0, 0.08]),
        v_primary_at_tca_kms=np.array([0.0, 7.5, 0.0]),
        v_secondary_at_tca_kms=np.array([0.0, -7.5, 0.0]),
        tca_seconds_from_now=7200.0,
        pc_baseline=5e-4,
    ),
]
fleet_plan = optimize_fleet_maneuvers(conjunctions=conjs, target_miss_km=1.0)
print(f"  Primaries: {sorted(fleet_plan.burns.keys())}")
print(f"  Total Δv: {fleet_plan.total_dv_mps:.2f} m/s across the fleet")
for primary_id, dv_mps in fleet_plan.per_primary_dv_mps.items():
    print(f"    Sat {primary_id}: {dv_mps:.2f} m/s")
print(f"  Risk reduction estimate: {fleet_plan.estimated_total_risk_reduction:.4e}")

# ─────────────────────────────────────────────────────────────────
section("6. Agent layer (Anthropic Claude)")
# ─────────────────────────────────────────────────────────────────
from skyshield.agent.agent import SkyShieldAgent

agent = SkyShieldAgent()
if agent.has_api_access:
    resp = agent.ask("What's the typical orbital altitude of the ISS, and what does Pc < 1e-5 mean operationally?")
    print(f"  Model: {resp.model}")
    print(f"  Tool calls: {len(resp.tool_events)}")
    print(f"  Reply (first 400 chars):\n  {resp.text[:400]}…")
else:
    print("  (No ANTHROPIC_API_KEY in env — agent runs in stub mode.)")
    print("  Add to .env and re-run to see the live agent.")

print("\nDone — every layer of SkyShield AI demonstrated in one script.")
