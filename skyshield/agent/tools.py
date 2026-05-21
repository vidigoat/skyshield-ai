"""Tool definitions for the SkyShield agent.

Each tool wraps a physics function from `skyshield/{propagate,screen,pc,avoid}/`
with the Anthropic tool-calling schema and a dispatcher that runs the actual
computation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# Anthropic tool-use schema (JSON Schema)
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "propagate_satellite",
        "description": (
            "Propagate one satellite forward in time using SGP4. "
            "Returns state vectors (position, velocity) at the requested time. "
            "Use this when the user asks 'where will satellite X be at time T?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sat_id": {
                    "type": "integer",
                    "description": "NORAD catalog number of the satellite",
                },
                "hours_forward": {
                    "type": "number",
                    "description": "Hours from now to propagate forward (negative = backward)",
                    "minimum": -168,
                    "maximum": 720,
                },
            },
            "required": ["sat_id", "hours_forward"],
        },
    },
    {
        "name": "screen_against_catalog",
        "description": (
            "Screen a single satellite against the live Celestrak catalog "
            "(~30,000 tracked objects) for close approaches within the next "
            "`days` days. Returns a list of conjunctions sorted by Pc (highest risk first). "
            "Use this when the user asks 'is my satellite safe this week?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sat_id": {
                    "type": "integer",
                    "description": "NORAD catalog number of the target satellite",
                },
                "days": {
                    "type": "number",
                    "description": "Look-ahead window in days (default 7)",
                    "minimum": 0.1,
                    "maximum": 30,
                },
                "screening_volume_km": {
                    "type": "number",
                    "description": "Spherical screening radius in km (default 10 km)",
                    "default": 10,
                },
            },
            "required": ["sat_id"],
        },
    },
    {
        "name": "compute_pc",
        "description": (
            "Compute the probability of collision (Pc) between two objects "
            "at a specific time, given their states and covariances. "
            "Default method is Alfano 2004 — same as TraCSS answer key. "
            "Use when the user asks 'what's my collision probability?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obj1_position_km": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y, z] of object 1 in J2000 frame (km)",
                },
                "obj1_velocity_kms": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[vx, vy, vz] of object 1 (km/s)",
                },
                "obj2_position_km": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "obj2_velocity_kms": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "obj1_position_sigma_m": {
                    "type": "number",
                    "description": "1-sigma position uncertainty for object 1 (meters)",
                    "default": 50,
                },
                "obj2_position_sigma_m": {
                    "type": "number",
                    "default": 50,
                },
                "hbr_m": {
                    "type": "number",
                    "description": "Combined hard-body radius (meters); default 5",
                    "default": 5,
                },
                "method": {
                    "type": "string",
                    "enum": ["alfano2004", "chan", "foster", "patera", "monte_carlo"],
                    "default": "alfano2004",
                },
            },
            "required": ["obj1_position_km", "obj1_velocity_kms",
                         "obj2_position_km", "obj2_velocity_kms"],
        },
    },
    {
        "name": "find_avoidance_maneuver",
        "description": (
            "Given a predicted conjunction, find the minimum-Δv impulsive "
            "maneuver that drops post-burn miss distance to the target. "
            "Returns (Δv vector, burn time before TCA, predicted post-burn miss). "
            "Use when the user asks 'what burn should I plan?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "r1_at_tca_km": {"type": "array", "items": {"type": "number"}},
                "r2_at_tca_km": {"type": "array", "items": {"type": "number"}},
                "v1_at_tca_kms": {"type": "array", "items": {"type": "number"}},
                "v2_at_tca_kms": {"type": "array", "items": {"type": "number"}},
                "burn_time_minutes_before_tca": {
                    "type": "number",
                    "default": 30,
                },
                "target_miss_km": {
                    "type": "number",
                    "description": "Target miss distance after the burn",
                    "default": 1.0,
                },
                "max_dv_mps": {
                    "type": "number",
                    "description": "Maximum Δv magnitude in m/s",
                    "default": 50,
                },
            },
            "required": ["r1_at_tca_km", "r2_at_tca_km", "v1_at_tca_kms", "v2_at_tca_kms"],
        },
    },
    {
        "name": "get_satellite_info",
        "description": (
            "Look up a satellite by NORAD catalog number, name, or international "
            "designator. Returns name, orbit type (LEO/MEO/GEO), perigee/apogee, "
            "inclination, and operator if known."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "NORAD ID (e.g. '25544'), name (e.g. 'ISS'), or designator",
                },
            },
            "required": ["query"],
        },
    },
]


def dispatch_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run the actual physics computation for a given tool call.

    Returns a dict with the result. If anything fails, returns {"error": "..."}.
    """
    try:
        if name == "propagate_satellite":
            return _tool_propagate(**args)
        if name == "screen_against_catalog":
            return _tool_screen(**args)
        if name == "compute_pc":
            return _tool_compute_pc(**args)
        if name == "find_avoidance_maneuver":
            return _tool_avoidance(**args)
        if name == "get_satellite_info":
            return _tool_satellite_info(**args)
        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}


# ---- Tool implementations ----

def _tool_propagate(sat_id: int, hours_forward: float) -> dict[str, Any]:
    """Stub: in a real run we'd look up the TLE from Celestrak.

    For now we return a deterministic mock so the agent loop can be exercised
    end-to-end without network calls.
    """
    return {
        "sat_id": sat_id,
        "epoch_iso": "2026-05-21T00:00:00Z",
        "position_km": [7000.0, 0.0, 0.0],
        "velocity_kms": [0.0, 7.5, 0.0],
        "note": "Mock — requires live TLE pull from Celestrak",
    }


def _tool_screen(sat_id: int, days: float = 7.0, screening_volume_km: float = 10.0) -> dict[str, Any]:
    """Stub for `screen_against_catalog`."""
    return {
        "sat_id": sat_id,
        "window_days": days,
        "screening_volume_km": screening_volume_km,
        "conjunctions": [
            {
                "secondary_norad_id": 99999,
                "tca_iso": "2026-05-23T18:42:11Z",
                "min_range_km": 1.2,
                "pc": 4.3e-5,
                "vrel_kms": 14.6,
            }
        ],
        "note": "Mock — requires live Celestrak TLE pull",
    }


def _tool_compute_pc(
    obj1_position_km: list[float],
    obj1_velocity_kms: list[float],
    obj2_position_km: list[float],
    obj2_velocity_kms: list[float],
    obj1_position_sigma_m: float = 50.0,
    obj2_position_sigma_m: float = 50.0,
    hbr_m: float = 5.0,
    method: str = "alfano2004",
) -> dict[str, Any]:
    """Real Pc computation."""
    from skyshield.pc.alfano import pc_alfano2004
    from skyshield.pc.chan import pc_chan
    from skyshield.pc.foster import pc_foster
    from skyshield.pc.monte_carlo import pc_monte_carlo
    from skyshield.pc.patera import pc_patera

    r1 = np.asarray(obj1_position_km, dtype=np.float64)
    r2 = np.asarray(obj2_position_km, dtype=np.float64)
    v1 = np.asarray(obj1_velocity_kms, dtype=np.float64)
    v2 = np.asarray(obj2_velocity_kms, dtype=np.float64)
    cov1 = np.eye(3) * ((obj1_position_sigma_m / 1000.0) ** 2)
    cov2 = np.eye(3) * ((obj2_position_sigma_m / 1000.0) ** 2)

    pc_fn = {
        "alfano2004": pc_alfano2004,
        "chan": pc_chan,
        "foster": pc_foster,
        "patera": pc_patera,
        "monte_carlo": pc_monte_carlo,
    }.get(method, pc_alfano2004)

    pc = pc_fn(
        r1=r1, r2=r2, v1=v1, v2=v2,
        cov1_pos_j2000=cov1, cov2_pos_j2000=cov2,
        hbr_m=hbr_m,
    )
    miss = float(np.linalg.norm(r2 - r1))
    vrel = float(np.linalg.norm(v2 - v1))
    return {
        "pc": float(pc) if pc is not None and not (isinstance(pc, float) and pc != pc) else None,
        "miss_distance_km": miss,
        "relative_velocity_kms": vrel,
        "method": method,
        "hbr_m": hbr_m,
    }


def _tool_avoidance(
    r1_at_tca_km: list[float],
    r2_at_tca_km: list[float],
    v1_at_tca_kms: list[float],
    v2_at_tca_kms: list[float],
    burn_time_minutes_before_tca: float = 30.0,
    target_miss_km: float = 1.0,
    max_dv_mps: float = 50.0,
) -> dict[str, Any]:
    """Real avoidance optimization."""
    from skyshield.avoid.optimizer import optimize_avoidance_maneuver

    plan = optimize_avoidance_maneuver(
        r1_at_tca_km=np.asarray(r1_at_tca_km),
        r2_at_tca_km=np.asarray(r2_at_tca_km),
        v1_at_tca_kms=np.asarray(v1_at_tca_kms),
        v2_at_tca_kms=np.asarray(v2_at_tca_kms),
        burn_time_minutes_before_tca=burn_time_minutes_before_tca,
        target_miss_km=target_miss_km,
        max_dv_kms=max_dv_mps / 1000.0,
    )
    return {
        "delta_v_kms": list(plan.delta_v_kms),
        "delta_v_mps": plan.delta_v_mps,
        "burn_time_seconds_before_tca": plan.burn_time_seconds_before_tca,
        "predicted_miss_km_after": plan.predicted_miss_km_after,
        "n_iterations": plan.n_iterations,
        "converged": plan.converged,
    }


def _tool_satellite_info(query: str) -> dict[str, Any]:
    """Stub satellite info lookup."""
    # In production this would hit Celestrak's SATCAT API.
    if query == "25544" or query.upper() == "ISS":
        return {
            "norad_id": 25544,
            "name": "ISS (ZARYA)",
            "intl_designator": "98067A",
            "operator": "NASA/Roscosmos partnership",
            "orbit_class": "LEO",
            "perigee_km": 408,
            "apogee_km": 421,
            "inclination_deg": 51.64,
            "period_min": 92.7,
        }
    return {
        "query": query,
        "note": "Catalog lookup not implemented in this build; would query Celestrak SATCAT.",
    }
