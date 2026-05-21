"use client";

import { useEffect, useRef, useState } from "react";
import { openAgentWebSocket } from "@/lib/api";
import { store } from "@/lib/store";
import type { ChatMessage } from "@/lib/types";

const EXAMPLE_PROMPTS = [
  "Is the ISS safe this week?",
  "My CubeSat is at 530km altitude, 53° inclination — collision risk for the next 30 days?",
  "Compare two launch dates (Jan 1 vs Jan 8) for a Starlink-shell orbit",
  "Find the minimum-Δv avoidance burn for Starlink-1234",
  "Continuously monitor my fleet of 5 satellites and alert me on Pc > 1e-5",
];

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: "agent",
      text:
        "I'm SkyShield. I can analyze satellite collision risk using physics validated against the US Office of Space Commerce TraCSS benchmark. Try one of the prompts below or ask anything in plain English.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll
  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  // Listen for cross-tab pre-fills from the globe
  useEffect(() => {
    return store.subscribe(() => {
      if (store.prefillChatQuery) {
        setInput(store.prefillChatQuery);
        store.setPrefill(null);
      }
    });
  }, []);

  const send = (text: string) => {
    if (!text.trim() || streaming) return;
    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      text: text.trim(),
      timestamp: Date.now(),
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setStreaming(true);

    let agentText = "";
    const agentMsgId = uid();
    let agentMsgCreated = false;

    const ws = openAgentWebSocket(
      (ev) => {
        if (ev.type === "tool_event") {
          setMessages((m) => [
            ...m,
            {
              id: uid(),
              role: "tool",
              toolName: ev.name,
              toolInput: ev.input,
              toolOutput: ev.output,
              elapsedMs: ev.elapsed_ms,
              timestamp: Date.now(),
            },
          ]);
        } else if (ev.type === "final") {
          agentText = ev.text;
          if (!agentMsgCreated) {
            agentMsgCreated = true;
            setMessages((m) => [
              ...m,
              {
                id: agentMsgId,
                role: "agent",
                text: agentText,
                timestamp: Date.now(),
              },
            ]);
          } else {
            setMessages((m) =>
              m.map((msg) =>
                msg.id === agentMsgId ? { ...msg, text: agentText } : msg
              )
            );
          }
          setStreaming(false);
          ws?.close();
        } else if (ev.type === "error") {
          setMessages((m) => [
            ...m,
            {
              id: uid(),
              role: "agent",
              text: `[error] ${ev.error}`,
              timestamp: Date.now(),
            },
          ]);
          setStreaming(false);
        }
      },
      () => {
        setStreaming(false);
      }
    );

    if (!ws) {
      // Fallback when backend not deployed yet — stub response
      setTimeout(() => {
        setMessages((m) => [
          ...m,
          {
            id: uid(),
            role: "tool",
            toolName: "screen_against_catalog",
            toolInput: { sat_id: 25544, days: 7 },
            toolOutput: { conjunctions: [{ secondary_norad_id: 99999, min_range_km: 1.2, pc: 4.3e-5 }] },
            elapsedMs: 287,
            timestamp: Date.now(),
          },
        ]);
      }, 400);
      setTimeout(() => {
        setMessages((m) => [
          ...m,
          {
            id: uid(),
            role: "agent",
            text:
              "[demo mode — backend not deployed yet]\n\nIn production I would have run propagate → screen → Pc → maneuver via verified physics tools. The answer would be: yes/no/here's-the-Δv with concrete numbers from the TraCSS-validated stack.\n\nDeploy with `uv run uvicorn skyshield.server.app:app` to enable the live agent.",
            timestamp: Date.now(),
          },
        ]);
        setStreaming(false);
      }, 1100);
      return;
    }

    wsRef.current = ws;
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "user_message", message: text }));
    };
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0e27]">
      <div className="border-b border-white/10 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <div className="text-cyan-400 font-bold text-sm uppercase tracking-widest">
            Agent · SkyShield
          </div>
          <div className="text-[10px] text-slate-400 font-mono">
            Claude-backed · verified physics tools · TraCSS-validated
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className={`w-2 h-2 rounded-full ${streaming ? "bg-cyan-400 tool-pulse" : "bg-emerald-400"}`} />
          {streaming ? "Working" : "Ready"}
        </div>
      </div>

      <div
        ref={messagesRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-3"
      >
        {messages.map((m) => (
          <div key={m.id}>
            {m.role === "user" && (
              <div className="msg-user rounded-xl px-4 py-2 max-w-2xl ml-auto text-sm whitespace-pre-wrap">
                {m.text}
              </div>
            )}
            {m.role === "agent" && (
              <div className="msg-agent rounded-xl px-4 py-3 max-w-3xl text-sm whitespace-pre-wrap">
                {m.text}
              </div>
            )}
            {m.role === "tool" && (
              <div className="msg-tool rounded px-3 py-2 max-w-3xl text-xs">
                <div className="text-cyan-400">
                  [tool] <b>{m.toolName}</b>{" "}
                  <span className="text-slate-500">
                    · {(m.elapsedMs ?? 0).toFixed(0)} ms
                  </span>
                </div>
                <div className="text-slate-500 mt-0.5">
                  in: {JSON.stringify(m.toolInput)}
                </div>
                <div className="text-slate-400 mt-0.5">
                  out: {JSON.stringify(m.toolOutput).slice(0, 180)}
                  {JSON.stringify(m.toolOutput).length > 180 && "…"}
                </div>
              </div>
            )}
          </div>
        ))}
        {streaming && messages[messages.length - 1]?.role !== "tool" && (
          <div className="msg-agent rounded-xl px-4 py-3 max-w-md text-sm tool-pulse">
            <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 mr-2" />
            Thinking…
          </div>
        )}
      </div>

      {/* Example prompts (only shown when chat is empty-ish) */}
      {messages.length <= 1 && (
        <div className="border-t border-white/5 px-6 py-3">
          <div className="text-[10px] text-slate-500 uppercase mb-2 font-mono">
            Try one
          </div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => send(p)}
                className="text-xs px-3 py-1.5 rounded-full border border-cyan-500/30 hover:border-cyan-500/60 hover:bg-cyan-500/10 transition-colors text-slate-300"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="border-t border-white/10 px-4 sm:px-6 py-3 flex gap-3 flex-shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
          placeholder="Ask about a satellite, a constellation, an orbit, a maneuver…"
          className="flex-1 bg-slate-900/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/50"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-900 font-bold text-sm transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
}
