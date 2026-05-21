"""AI agent layer powered by Anthropic Claude.

Anyone with a satellite can ask "is it safe?" in plain English. The agent
plans, calls physics tools, and explains the result.

This is the "AI" in SkyShield AI — uses an existing Claude model via API.
We do not train any model.
"""

from skyshield.agent.agent import (
    AgentResponse,
    SkyShieldAgent,
)
from skyshield.agent.tools import (
    TOOL_SCHEMAS,
    dispatch_tool_call,
)

__all__ = [
    "TOOL_SCHEMAS",
    "AgentResponse",
    "SkyShieldAgent",
    "dispatch_tool_call",
]
