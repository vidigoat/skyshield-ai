import { useState, type ReactElement } from "react";
import type { ChatMessage } from "../lib/types";

function fmtValue(v: unknown): string {
  if (v === null || v === undefined) return "null";
  if (typeof v === "string") return v;
  if (typeof v === "number") {
    if (Math.abs(v) > 1e6 || (Math.abs(v) < 1e-3 && v !== 0)) return v.toExponential(3);
    return String(Math.round(v * 1e6) / 1e6);
  }
  if (typeof v === "boolean") return String(v);
  if (Array.isArray(v)) {
    if (v.length === 0) return "[]";
    if (v.every((x) => typeof x === "number")) {
      return `[${v.map((x) => fmtValue(x)).join(", ")}]`;
    }
    return `[${v.map(fmtValue).join(", ")}]`;
  }
  return JSON.stringify(v);
}

function renderKeyValue(obj: Record<string, unknown>, max = 6): ReactElement[] {
  const entries = Object.entries(obj).slice(0, max);
  return entries.map(([k, v]) => (
    <div key={k} className="flex gap-3 text-[12.5px] leading-relaxed">
      <span className="text-neutral-500 shrink-0 min-w-[110px]">{k}</span>
      <span className="text-neutral-900 break-words">{fmtValue(v)}</span>
    </div>
  ));
}

export default function ToolCall({ msg }: { msg: ChatMessage }) {
  const [open, setOpen] = useState(false);
  const inputSummary = msg.toolInput ? renderKeyValue(msg.toolInput, 3) : null;
  const outputKeys = msg.toolOutput ? Object.keys(msg.toolOutput).length : 0;

  return (
    <div className="tool-card my-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full tool-card-header rounded-t-xl px-4 py-2.5 flex items-center justify-between hover:bg-neutral-100/60 transition-colors"
      >
        <div className="flex items-center gap-2 text-[13px]">
          <svg className="w-3.5 h-3.5 text-neutral-500" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 4h8M4 8h8M4 12h5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          <span className="font-mono font-semibold text-neutral-900">{msg.toolName}</span>
          <span className="text-neutral-400 font-mono">
            · {(msg.elapsedMs ?? 0).toFixed(0)} ms
          </span>
          {outputKeys > 0 && (
            <span className="text-neutral-400 font-mono">· {outputKeys} fields</span>
          )}
        </div>
        <svg
          className={`w-3.5 h-3.5 text-neutral-400 transition-transform ${open ? "rotate-90" : ""}`}
          viewBox="0 0 16 16"
          fill="none"
        >
          <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {!open && inputSummary && (
        <div className="px-4 py-2 space-y-0.5 border-t border-neutral-200/60">
          {inputSummary}
        </div>
      )}

      {open && (
        <div className="px-4 py-3 space-y-3 border-t border-neutral-200/60">
          {msg.toolInput && (
            <div>
              <div className="text-[10.5px] uppercase tracking-wider text-neutral-400 mb-1 font-sans">
                Input
              </div>
              <div className="space-y-0.5">{renderKeyValue(msg.toolInput, 20)}</div>
            </div>
          )}
          {msg.toolOutput && (
            <div>
              <div className="text-[10.5px] uppercase tracking-wider text-neutral-400 mb-1 font-sans">
                Output
              </div>
              <div className="space-y-0.5">{renderKeyValue(msg.toolOutput, 20)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
