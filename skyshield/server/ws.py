"""Helper utilities for WebSocket connection management.

Kept in a separate module so the main app.py file stays focused on routes.
"""

from __future__ import annotations

from collections import defaultdict


class ConnectionManager:
    """Track active WebSocket connections by client_id.

    Used for broadcasting alerts (from the continuous monitor) to all
    subscribed clients.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list] = defaultdict(list)

    def add(self, client_id: str, websocket) -> None:
        self._connections[client_id].append(websocket)

    def remove(self, client_id: str, websocket) -> None:
        if client_id in self._connections:
            self._connections[client_id].remove(websocket)
            if not self._connections[client_id]:
                del self._connections[client_id]

    async def broadcast(self, client_id: str, message: dict) -> None:
        for ws in list(self._connections.get(client_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.remove(client_id, ws)

    def count(self) -> int:
        return sum(len(v) for v in self._connections.values())
