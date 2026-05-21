"""Tests for the agent layer."""

from __future__ import annotations

import pytest

from skyshield.agent.agent import AgentResponse, SkyShieldAgent
from skyshield.agent.explain import (
    dv_to_plain_english,
    miss_to_plain_english,
    pc_to_plain_english,
)
from skyshield.agent.tools import TOOL_SCHEMAS, dispatch_tool_call


def test_tool_schemas_well_formed():
    """Every tool schema has name, description, input_schema, and required fields."""
    for tool in TOOL_SCHEMAS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "properties" in tool["input_schema"]


def test_dispatch_unknown_tool():
    result = dispatch_tool_call("does_not_exist", {})
    assert "error" in result


def test_dispatch_compute_pc():
    """Real Pc tool call should return a dict with the expected fields."""
    args = {
        "obj1_position_km": [7000.0, 0.0, 0.0],
        "obj1_velocity_kms": [0.0, 7.5, 0.0],
        "obj2_position_km": [7000.0, 0.0, 0.1],
        "obj2_velocity_kms": [0.0, -7.5, 0.0],
        "obj1_position_sigma_m": 50,
        "obj2_position_sigma_m": 50,
        "hbr_m": 5.0,
    }
    result = dispatch_tool_call("compute_pc", args)
    assert "error" not in result, f"Tool returned error: {result.get('error')}"
    assert "pc" in result
    assert "miss_distance_km" in result
    assert result["miss_distance_km"] == pytest.approx(0.1)
    assert "method" in result


def test_dispatch_avoidance():
    args = {
        "r1_at_tca_km": [7000.0, 0.0, 0.0],
        "r2_at_tca_km": [7000.0, 0.0, 0.1],
        "v1_at_tca_kms": [0.0, 7.5, 0.0],
        "v2_at_tca_kms": [0.0, -7.5, 0.0],
        "burn_time_minutes_before_tca": 30,
        "target_miss_km": 1.0,
        "max_dv_mps": 50,
    }
    result = dispatch_tool_call("find_avoidance_maneuver", args)
    assert "error" not in result
    assert "delta_v_mps" in result
    assert result["delta_v_mps"] <= 50.0 + 1e-6


def test_agent_stub_mode():
    """Without an API key, the agent should run in stub mode without crashing."""
    # Force stub mode by passing empty API key
    agent = SkyShieldAgent(api_key="")
    assert not agent.has_api_access
    response = agent.ask("is my satellite safe?")
    assert isinstance(response, AgentResponse)
    assert response.model == "stub"
    assert "Stub mode" in response.text


def test_pc_to_plain_english():
    assert "Negligible" in pc_to_plain_english(1e-8)
    assert "Very low" in pc_to_plain_english(1e-6)
    assert "Low risk" in pc_to_plain_english(1e-5) or "monitoring" in pc_to_plain_english(1e-5)
    assert "could not" in pc_to_plain_english(None)


def test_miss_to_plain_english():
    assert "m" in miss_to_plain_english(0.005)
    assert "km" in miss_to_plain_english(0.5)
    assert "km" in miss_to_plain_english(50.0)


def test_dv_to_plain_english():
    assert "mm/s" in dv_to_plain_english(0.001)
    assert "m/s" in dv_to_plain_english(5.0)
    assert "large" in dv_to_plain_english(40.0).lower() or "burn" in dv_to_plain_english(40.0).lower()
