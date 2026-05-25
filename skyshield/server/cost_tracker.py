"""Hard USD spending cap for the SkyShield agent.

Tracks cumulative Anthropic token usage to disk and refuses requests once
estimated cumulative spend hits HARD_CAP_USD. Sonnet 4.6 pricing is
hardcoded — update INPUT_USD_PER_MTOK / OUTPUT_USD_PER_MTOK if pricing
changes.

This is a best-effort in-container fail-safe. The container's /tmp survives
within a single App Runner instance but not across restarts, so for true
hard guarantees ALSO set a spending limit on the Anthropic API key in the
Anthropic console.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

# Anthropic public pricing as of 2026-05 (USD per million tokens).
INPUT_USD_PER_MTOK = 3.0
OUTPUT_USD_PER_MTOK = 15.0

# Hard cap. Once cumulative recorded spend reaches this, all further
# agent calls are rejected with SpendCapExceeded.
HARD_CAP_USD = 20.0

# Persistent state path. /tmp is writable on App Runner.
STATE_PATH = Path("/tmp/skyshield_spend.json")

_lock = threading.Lock()


class SpendCapExceeded(Exception):
    """Raised when cumulative recorded spend hits HARD_CAP_USD."""


def _load() -> dict[str, float]:
    if not STATE_PATH.exists():
        return {"input_tokens": 0, "output_tokens": 0, "usd_spent": 0.0}
    try:
        data = json.loads(STATE_PATH.read_text())
        # Defensive defaults for partial files
        return {
            "input_tokens": int(data.get("input_tokens", 0)),
            "output_tokens": int(data.get("output_tokens", 0)),
            "usd_spent": float(data.get("usd_spent", 0.0)),
        }
    except Exception:
        return {"input_tokens": 0, "output_tokens": 0, "usd_spent": 0.0}


def _save(state: dict[str, float]) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state))
    except Exception:
        # If /tmp isn't writable, the cap silently degrades — the Anthropic
        # console-side spend limit is the real safety net.
        pass


def check_cap() -> None:
    """Raise SpendCapExceeded if we are already at or past HARD_CAP_USD."""
    with _lock:
        state = _load()
        if state["usd_spent"] >= HARD_CAP_USD:
            raise SpendCapExceeded(
                f"SkyShield demo spending cap of ${HARD_CAP_USD:.2f} reached. "
                f"Cumulative spend: ${state['usd_spent']:.4f}. "
                "Try again later or reach out to the maintainer."
            )


def record_usage(input_tokens: int, output_tokens: int) -> dict[str, float]:
    """Add this call's token usage to the running total. Returns new state."""
    cost = (
        input_tokens * INPUT_USD_PER_MTOK / 1_000_000
        + output_tokens * OUTPUT_USD_PER_MTOK / 1_000_000
    )
    with _lock:
        state = _load()
        state["input_tokens"] += int(input_tokens)
        state["output_tokens"] += int(output_tokens)
        state["usd_spent"] = round(state["usd_spent"] + cost, 6)
        _save(state)
        return state


def current_spend() -> dict[str, float]:
    """Return current cumulative spend (read-only)."""
    with _lock:
        state = _load()
        state["cap_usd"] = HARD_CAP_USD
        state["remaining_usd"] = max(0.0, HARD_CAP_USD - state["usd_spent"])
        return state
