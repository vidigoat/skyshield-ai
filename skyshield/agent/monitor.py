"""Continuous monitoring daemon.

Background loop that periodically re-screens a subscribed satellite (or list of
satellites) against the current catalog and emits alerts when Pc crosses a
threshold. This is the open analog of SpaceX's Stargaze service.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from skyshield.agent.tools import dispatch_tool_call


@dataclass
class Alert:
    """A conjunction alert above the threshold."""
    primary_sat_id: int
    secondary_sat_id: int
    tca: datetime
    min_range_km: float
    pc: float | None
    triggered_at: datetime = field(default_factory=datetime.utcnow)


class ContinuousMonitor:
    """Background monitor for a list of subscribed satellites."""

    def __init__(
        self,
        subscribed_sat_ids: list[int],
        *,
        check_interval_seconds: float = 6 * 3600,    # every 6 hours
        pc_threshold: float = 1e-5,
        on_alert: Callable[[Alert], None] | None = None,
    ):
        self.subscribed_sat_ids = list(subscribed_sat_ids)
        self.check_interval_seconds = check_interval_seconds
        self.pc_threshold = pc_threshold
        self.on_alert = on_alert
        self._running = False

    async def run_forever(self) -> None:
        """Main monitor loop. Runs until stop() is called."""
        self._running = True
        while self._running:
            try:
                await self._check_once()
            except Exception as e:
                # Log but don't crash the monitor
                print(f"[monitor] check failed: {e}")
            await asyncio.sleep(self.check_interval_seconds)

    def stop(self) -> None:
        self._running = False

    async def _check_once(self) -> None:
        for sat_id in self.subscribed_sat_ids:
            result = dispatch_tool_call(
                "screen_against_catalog",
                {"sat_id": sat_id, "days": 7, "screening_volume_km": 10.0},
            )
            for conj in result.get("conjunctions", []):
                pc = conj.get("pc")
                if pc is None:
                    continue
                if pc >= self.pc_threshold:
                    try:
                        tca = datetime.fromisoformat(conj["tca_iso"].rstrip("Z"))
                    except Exception:
                        tca = datetime.utcnow()
                    alert = Alert(
                        primary_sat_id=sat_id,
                        secondary_sat_id=conj.get("secondary_norad_id", 0),
                        tca=tca,
                        min_range_km=float(conj.get("min_range_km", 0.0)),
                        pc=pc,
                    )
                    if self.on_alert:
                        self.on_alert(alert)
