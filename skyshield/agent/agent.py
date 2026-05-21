"""SkyShield agent — the tool-using Claude loop.

Single-turn or multi-turn agent that:
  1. Receives a user question
  2. Decides which tool(s) to call (Claude function-calling)
  3. Executes tools via dispatch_tool_call()
  4. Feeds results back to Claude
  5. Returns a plain-English answer

Requires `ANTHROPIC_API_KEY` environment variable. If not set, the agent
falls back to a stub that echoes the question and tool-call plan so the
UI can still demo without the API.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skyshield.agent.tools import TOOL_SCHEMAS, dispatch_tool_call

# Lazy-load the system prompt
_SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"


def _load_system_prompt() -> str:
    if _SYSTEM_PROMPT_PATH.exists():
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return "You are SkyShield, an AI assistant for satellite safety."


@dataclass
class ToolEvent:
    """A single tool-call event in the agent's execution trace."""
    name: str
    input: dict[str, Any]
    output: dict[str, Any]
    elapsed_ms: float = 0.0


@dataclass
class AgentResponse:
    """Final agent output."""
    text: str
    tool_events: list[ToolEvent] = field(default_factory=list)
    n_iterations: int = 0
    model: str = "claude-sonnet-4-6"


class SkyShieldAgent:
    """Agent loop wrapping Anthropic Claude with our verified physics tools."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_iterations: int = 8,
        on_tool_event: Callable[[ToolEvent], None] | None = None,
    ):
        """Create an agent.

        Parameters
        ----------
        api_key : str | None
            Anthropic API key. If None, reads ANTHROPIC_API_KEY env var.
            If still missing, the agent runs in stub mode.
        model : str
            Claude model name.
        max_iterations : int
            Safety cap on the agent's tool-call loop.
        on_tool_event : callable
            Called for each tool event (for live UI streaming via WebSocket).
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.max_iterations = max_iterations
        self.on_tool_event = on_tool_event
        self.system_prompt = _load_system_prompt()
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                # anthropic SDK not installed — agent will run in stub mode
                self._client = None

    @property
    def has_api_access(self) -> bool:
        return self._client is not None

    def ask(self, user_message: str) -> AgentResponse:
        """Run the agent on a single user question.

        Returns AgentResponse with final text + execution trace.
        """
        if not self.has_api_access:
            return self._stub_ask(user_message)

        from time import perf_counter

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message}
        ]
        tool_events: list[ToolEvent] = []

        for iteration in range(self.max_iterations):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )

            # Did Claude request a tool call?
            tool_use_blocks = [
                b for b in response.content if getattr(b, "type", None) == "tool_use"
            ]
            if not tool_use_blocks:
                # Final answer
                text_parts = [
                    b.text for b in response.content if getattr(b, "type", None) == "text"
                ]
                text = "\n".join(text_parts)
                return AgentResponse(
                    text=text,
                    tool_events=tool_events,
                    n_iterations=iteration + 1,
                    model=self.model,
                )

            # Execute each tool call
            messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                t0 = perf_counter()
                result = dispatch_tool_call(block.name, dict(block.input))
                elapsed_ms = (perf_counter() - t0) * 1000.0
                event = ToolEvent(
                    name=block.name,
                    input=dict(block.input),
                    output=result,
                    elapsed_ms=elapsed_ms,
                )
                tool_events.append(event)
                if self.on_tool_event:
                    self.on_tool_event(event)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
            messages.append({"role": "user", "content": tool_results})

        # Hit max iterations without a final answer
        return AgentResponse(
            text=(
                "I hit my tool-call limit while answering. "
                "Try asking a more specific question."
            ),
            tool_events=tool_events,
            n_iterations=self.max_iterations,
            model=self.model,
        )

    def _stub_ask(self, user_message: str) -> AgentResponse:
        """Stub responder for when no API key is available.

        Demos the UI flow without making real API calls. Always returns the
        same shape of response so the WebSocket UI can be tested.
        """
        return AgentResponse(
            text=(
                "[Stub mode — no ANTHROPIC_API_KEY set]\n\n"
                f"You asked: '{user_message}'\n\n"
                "In production, I'd plan tool calls (likely propagate + screen + Pc + maneuver),"
                " run them, and reply in plain English. "
                "Set ANTHROPIC_API_KEY in .env to enable the agent."
            ),
            tool_events=[],
            n_iterations=0,
            model="stub",
        )
