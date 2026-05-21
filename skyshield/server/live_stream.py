"""Live conjunction stream — the public open analog of SpaceX Stargaze alerts.

Any client connects via WebSocket and receives EVERY high-Pc close approach
event as it is detected by the continuous monitor. No subscription. No login.
Free for any operator, researcher, or hobbyist worldwide.

This is genuinely novel as a public service:
  - Stargaze: closed, operator-only (you must submit your own ephemerides)
  - LeoLabs, Slingshot, COMSPOC: commercial, paid
  - SkyShield Live: open, public, free, verified physics

Protocol:
    Connect to /ws/live
    Optionally send {"type": "filter", "sat_ids": [25544, 44943, ...]} to
    receive only events involving those satellites.
    Receive a stream of:
      {"type": "alert", "primary": 25544, "secondary": 99999,
       "tca_iso": "2026-05-23T18:42:11Z", "pc": 4.3e-5,
       "min_range_km": 1.2, "vrel_kms": 14.6, "explanation": "..."}

In production this is driven by the ContinuousMonitor scanning Celestrak
every 6 hours and dispatching alerts that crossed the Pc threshold.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LiveAlert:
    """A conjunction alert pushed to live-stream subscribers."""
    primary: int
    secondary: int
    tca_iso: str
    pc: float
    min_range_km: float
    vrel_kms: float
    explanation: str = ""
    detected_at_iso: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_json(self) -> str:
        d = asdict(self)
        d["type"] = "alert"
        return json.dumps(d)


class LiveStreamHub:
    """Fan-out hub: continuous monitor pushes alerts, hub broadcasts to all
    connected WebSockets, optionally filtered per-client.
    """

    def __init__(self) -> None:
        self.connections: dict[Any, set[int] | None] = {}
        self.recent: list[LiveAlert] = []
        self.max_recent = 100

    def add_connection(self, ws: Any, sat_filter: set[int] | None = None) -> None:
        self.connections[ws] = sat_filter

    def remove_connection(self, ws: Any) -> None:
        self.connections.pop(ws, None)

    def update_filter(self, ws: Any, sat_filter: set[int] | None) -> None:
        if ws in self.connections:
            self.connections[ws] = sat_filter

    async def broadcast(self, alert: LiveAlert) -> None:
        # Append to recent history for replay
        self.recent.append(alert)
        if len(self.recent) > self.max_recent:
            self.recent = self.recent[-self.max_recent:]

        payload = alert.to_json()
        dead = []
        for ws, flt in self.connections.items():
            if flt is not None and alert.primary not in flt and alert.secondary not in flt:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_connection(ws)

    def stats(self) -> dict[str, int]:
        return {
            "connected_clients": len(self.connections),
            "recent_alerts": len(self.recent),
        }


# Global singleton (FastAPI app instance)
hub = LiveStreamHub()


async def demo_emit_loop() -> None:
    """Background coroutine that emits synthetic alerts every few seconds.

    In production this is replaced by the real ContinuousMonitor driving the
    hub. The demo loop lets the frontend show a continuously updating stream
    even before the live monitor is wired to Celestrak.
    """
    import random
    counter = 0
    while True:
        await asyncio.sleep(8)
        counter += 1
        alert = LiveAlert(
            primary=random.choice([25544, 44943, 53700, 95222, 99000]),
            secondary=random.choice([46201, 53072, 95343, 99002, 99005]),
            tca_iso=(datetime.utcnow().replace(microsecond=0)).isoformat() + "Z",
            pc=10 ** random.uniform(-7, -3),
            min_range_km=random.uniform(0.5, 9.5),
            vrel_kms=random.uniform(5, 15),
            explanation=(
                "Predicted close approach within 7 days. "
                "Pc above 1e-5 threshold. Operator alert."
            ),
        )
        await hub.broadcast(alert)
