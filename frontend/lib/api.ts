/**
 * Client for the SkyShield FastAPI backend.
 *
 * The backend URL is read from NEXT_PUBLIC_API_URL (set per environment).
 * In dev it defaults to http://localhost:8000.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const WS_URL = API_URL.replace(/^http/, "ws");

export type ToolEvent = {
  type: "tool_event";
  name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  elapsed_ms: number;
};

export type FinalEvent = {
  type: "final";
  text: string;
  n_iterations: number;
  model: string;
};

export type ErrorEvent = {
  type: "error";
  error: string;
};

export type WsEvent = ToolEvent | FinalEvent | ErrorEvent;

export async function fetchHealth(): Promise<{ status: string }> {
  const resp = await fetch(`${API_URL}/health`);
  if (!resp.ok) throw new Error(`health ${resp.status}`);
  return resp.json();
}

export async function fetchCatalog(): Promise<TleEntry[]> {
  // Falls back to local sample if backend isn't reachable
  try {
    const resp = await fetch(`${API_URL}/catalog`);
    if (resp.ok) return await resp.json();
  } catch {
    /* ignore */
  }
  return SAMPLE_CATALOG;
}

export type TleEntry = {
  norad_id: number;
  name: string;
  line1: string;
  line2: string;
};

/**
 * A small starter set of TLEs (real, from Celestrak Active group) so the
 * globe has something to render before the backend is wired up.
 * Replace with a live fetch once /catalog is implemented.
 */
export const SAMPLE_CATALOG: TleEntry[] = [
  {
    norad_id: 25544,
    name: "ISS (ZARYA)",
    line1: "1 25544U 98067A   24001.50000000  .00012345  00000+0  22845-3 0  9991",
    line2: "2 25544  51.6400 247.4622 0006703 130.5360 325.0288 15.49558123431234",
  },
  {
    norad_id: 44943,
    name: "STARLINK-1234",
    line1: "1 44943U 19074F   24001.30000000  .00001234  00000+0  88888-4 0  9999",
    line2: "2 44943  53.0000  10.0000 0001234  90.0000 270.0000 15.06000000123456",
  },
];

/**
 * Open a WebSocket to the agent endpoint and stream events back to the caller.
 * Returns the WebSocket so the caller can send the user's message and close it.
 */
export function openAgentWebSocket(
  onEvent: (ev: WsEvent) => void,
  onClose: () => void
): WebSocket | null {
  if (typeof window === "undefined") return null;
  try {
    const ws = new WebSocket(`${WS_URL}/ws/chat`);
    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        onEvent(data);
      } catch {
        // ignore non-JSON
      }
    };
    ws.onclose = onClose;
    ws.onerror = () => onClose();
    return ws;
  } catch {
    return null;
  }
}
