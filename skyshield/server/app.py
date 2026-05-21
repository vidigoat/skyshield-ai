"""FastAPI app for SkyShield AI backend.

Endpoints (REST):
    GET  /                  → health check + version info
    POST /chat              → submit a user question, get agent's text reply
    POST /screen            → run conjunction screening on a given Sat ID
    POST /pc                → compute Pc for an explicit conjunction
    POST /maneuver          → optimize an avoidance burn
    GET  /catalog           → return current TLE catalog summary (for globe)
    GET  /satellites/{id}   → satellite info lookup

Endpoint (WebSocket):
    WS   /ws/chat           → bi-directional chat with live tool-call streaming
"""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from skyshield import __version__
from skyshield.agent.agent import SkyShieldAgent, ToolEvent
from skyshield.agent.tools import dispatch_tool_call
from skyshield.server.live_stream import demo_emit_loop, hub
from skyshield.server.rate_limit import RateLimiter

app = FastAPI(
    title="SkyShield AI",
    description="Open AI agent for satellite safety. Verified physics, plain English.",
    version=__version__,
)

# Allow frontend to call from any origin (tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared rate limiter (per-IP)
rate_limiter = RateLimiter(max_requests=30, window_seconds=86400)


# ---- Request/response schemas ----

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's question in plain English")
    model: str | None = Field(None, description="Optional Claude model override")


class ChatResponse(BaseModel):
    text: str
    tool_events: list[dict[str, Any]]
    n_iterations: int
    model: str


class ScreenRequest(BaseModel):
    sat_id: int
    days: float = 7.0
    screening_volume_km: float = 10.0


class PcRequest(BaseModel):
    obj1_position_km: list[float]
    obj1_velocity_kms: list[float]
    obj2_position_km: list[float]
    obj2_velocity_kms: list[float]
    obj1_position_sigma_m: float = 50.0
    obj2_position_sigma_m: float = 50.0
    hbr_m: float = 5.0
    method: str = "alfano2004"


class ManeuverRequest(BaseModel):
    r1_at_tca_km: list[float]
    r2_at_tca_km: list[float]
    v1_at_tca_kms: list[float]
    v2_at_tca_kms: list[float]
    burn_time_minutes_before_tca: float = 30.0
    target_miss_km: float = 1.0
    max_dv_mps: float = 50.0


# ---- Routes ----

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "SkyShield AI",
        "version": __version__,
        "status": "operational",
        "tagline": "Open AI agent for satellite safety. Verified physics, plain English.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Send a question to the agent, get a plain-English answer with tool trace."""
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Daily rate limit exceeded")

    agent = SkyShieldAgent(model=req.model or "claude-sonnet-4-6")
    resp = agent.ask(req.message)
    return ChatResponse(
        text=resp.text,
        tool_events=[
            {
                "name": ev.name,
                "input": ev.input,
                "output": ev.output,
                "elapsed_ms": ev.elapsed_ms,
            }
            for ev in resp.tool_events
        ],
        n_iterations=resp.n_iterations,
        model=resp.model,
    )


@app.post("/screen")
async def screen(req: ScreenRequest) -> dict[str, Any]:
    return dispatch_tool_call(
        "screen_against_catalog",
        {
            "sat_id": req.sat_id,
            "days": req.days,
            "screening_volume_km": req.screening_volume_km,
        },
    )


@app.post("/pc")
async def pc(req: PcRequest) -> dict[str, Any]:
    return dispatch_tool_call("compute_pc", req.model_dump())


@app.post("/maneuver")
async def maneuver(req: ManeuverRequest) -> dict[str, Any]:
    return dispatch_tool_call("find_avoidance_maneuver", req.model_dump())


@app.get("/satellites/{query}")
async def satellite_info(query: str) -> dict[str, Any]:
    return dispatch_tool_call("get_satellite_info", {"query": query})


# Cache for the Celestrak catalog (refreshed every 6 hours)
_catalog_cache: dict[str, Any] = {"data": [], "fetched_at": 0.0}


@app.get("/catalog")
async def catalog(group: str = "starlink", limit: int = 5000) -> dict[str, Any]:
    """Return current Celestrak TLE catalog for the globe.

    Tries the live feed; falls back to a small synthetic set if Celestrak
    isn't reachable. Cached for 6 hours.
    """
    import time
    now = time.time()
    if now - _catalog_cache["fetched_at"] < 6 * 3600 and _catalog_cache["data"]:
        return {"group": group, "n": len(_catalog_cache["data"]), "satellites": _catalog_cache["data"]}

    sats: list[dict[str, Any]] = []
    try:
        import httpx
        url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            lines = [ln.rstrip() for ln in r.text.splitlines() if ln.strip()]
            for i in range(0, len(lines), 3):
                if i + 2 >= len(lines):
                    break
                name = lines[i].strip()
                l1 = lines[i + 1]
                l2 = lines[i + 2]
                if not l1.startswith("1 ") or not l2.startswith("2 "):
                    continue
                try:
                    norad = int(l1[2:7])
                except ValueError:
                    continue
                sats.append({
                    "norad_id": norad,
                    "name": name,
                    "line1": l1,
                    "line2": l2,
                })
                if len(sats) >= limit:
                    break
    except Exception:
        sats = []  # fall through to fallback

    if not sats:
        # Synthetic fallback (small, just so the globe has something)
        sats = [
            {
                "norad_id": 25544,
                "name": "ISS (ZARYA)",
                "line1": "1 25544U 98067A   24001.50000000  .00012345  00000+0  22845-3 0  9991",
                "line2": "2 25544  51.6400 247.4622 0006703 130.5360 325.0288 15.49558123431234",
            },
        ]

    _catalog_cache["data"] = sats
    _catalog_cache["fetched_at"] = now
    return {"group": group, "n": len(sats), "satellites": sats}


@app.get("/live/stats")
async def live_stats() -> dict[str, int]:
    """Stats about the live conjunction stream."""
    return hub.stats()


@app.get("/live/recent")
async def live_recent() -> list[dict[str, Any]]:
    """Recent alerts from the live stream (in-memory history)."""
    from dataclasses import asdict
    return [asdict(a) for a in hub.recent[-50:]]


@app.on_event("startup")
async def _start_demo_emit() -> None:
    """Kick off the demo emit loop in the background. In production this is
    replaced by the real ContinuousMonitor."""
    import asyncio
    asyncio.create_task(demo_emit_loop())


# ---- WebSocket: live conjunction stream ----

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    """Public live conjunction alert stream.

    Optional filter from client: {"type": "filter", "sat_ids": [25544, ...]}
    """
    await websocket.accept()
    hub.add_connection(websocket, sat_filter=None)
    try:
        # Replay last 5 alerts on connect
        for a in hub.recent[-5:]:
            await websocket.send_text(a.to_json())
        while True:
            msg = await websocket.receive_text()
            try:
                data = __import__("json").loads(msg)
                if data.get("type") == "filter":
                    sat_ids = data.get("sat_ids")
                    if isinstance(sat_ids, list):
                        hub.update_filter(websocket, set(sat_ids))
                    else:
                        hub.update_filter(websocket, None)
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove_connection(websocket)


# ---- WebSocket: live agent streaming ----

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """Stream agent execution live: tool calls + final answer.

    Protocol:
      Client sends:  {"type": "user_message", "message": "..."}
      Server sends:  {"type": "tool_event", ...}
                     {"type": "tool_event", ...}
                     {"type": "final", "text": "...", "n_iterations": N}
    """
    await websocket.accept()
    try:
        msg = await websocket.receive_json()
        user_message = msg.get("message", "")
        if not user_message:
            await websocket.send_json({"type": "error", "error": "empty message"})
            return

        # Stream tool events as they happen
        async def emit(event: ToolEvent) -> None:
            with contextlib.suppress(Exception):
                await websocket.send_json({
                    "type": "tool_event",
                    "name": event.name,
                    "input": event.input,
                    "output": event.output,
                    "elapsed_ms": event.elapsed_ms,
                })

        # The agent's on_tool_event callback is synchronous, so we use a thread-safe queue
        import asyncio
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def sync_emit(event: ToolEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

        agent = SkyShieldAgent(on_tool_event=sync_emit)

        # Run agent in a thread so we can interleave WebSocket emits
        result_future: asyncio.Future = asyncio.Future()

        async def run_agent() -> None:
            try:
                resp = await asyncio.to_thread(agent.ask, user_message)
                result_future.set_result(resp)
            except Exception as e:
                result_future.set_exception(e)

        asyncio.create_task(run_agent())

        # Drain queue and forward events until the agent finishes
        while not result_future.done():
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.5)
                await emit(ev)
            except TimeoutError:
                continue

        # Flush any final events
        while not queue.empty():
            await emit(queue.get_nowait())

        resp = await result_future
        await websocket.send_json({
            "type": "final",
            "text": resp.text,
            "n_iterations": resp.n_iterations,
            "model": resp.model,
        })

    except WebSocketDisconnect:
        return
    except Exception as e:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "error": str(e)})
