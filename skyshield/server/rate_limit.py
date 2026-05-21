"""Per-IP rate limiting for the public demo.

Simple in-memory sliding window. For production at scale we'd back this with
Redis, but for the launch demo running on a single Modal instance, in-memory
is sufficient and avoids an extra dependency.
"""

from __future__ import annotations

from collections import defaultdict
from time import time


class RateLimiter:
    """Sliding-window rate limiter, in-memory.

    Tracks requests per IP and rejects when an IP exceeds `max_requests` in
    the trailing `window_seconds` seconds.
    """

    def __init__(self, *, max_requests: int = 30, window_seconds: float = 86400):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, ip: str) -> bool:
        """Return True if this IP may make another request right now."""
        now = time()
        cutoff = now - self.window_seconds
        hits = self._hits[ip]
        # Drop expired entries
        while hits and hits[0] < cutoff:
            hits.pop(0)
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True

    def remaining(self, ip: str) -> int:
        """Return the number of requests remaining in the current window."""
        now = time()
        cutoff = now - self.window_seconds
        hits = [t for t in self._hits[ip] if t >= cutoff]
        return max(0, self.max_requests - len(hits))

    def reset(self, ip: str | None = None) -> None:
        """Clear rate-limit state. If ip is None, clear all IPs."""
        if ip is None:
            self._hits.clear()
        else:
            self._hits.pop(ip, None)
