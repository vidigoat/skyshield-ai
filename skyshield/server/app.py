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

from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from skyshield import __version__
from skyshield.agent.agent import SkyShieldAgent, ToolEvent
from skyshield.agent.tools import dispatch_tool_call
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
            try:
                await websocket.send_json({
                    "type": "tool_event",
                    "name": event.name,
                    "input": event.input,
                    "output": event.output,
                    "elapsed_ms": event.elapsed_ms,
                })
            except Exception:
                pass

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
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
