"""FastAPI backend for SkyShield AI.

REST + WebSocket endpoints powering the frontend (Tab 1 globe + Tab 2 chat).
WebSocket streams live tool-call events for the chat UI.
"""

from skyshield.server.rate_limit import RateLimiter

__all__ = ["RateLimiter"]
