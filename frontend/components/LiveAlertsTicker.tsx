"use client";

import { useEffect, useState } from "react";
import { WS_URL } from "@/lib/api";

type Alert = {
  type: "alert";
  primary: number;
  secondary: number;
  tca_iso: string;
  pc: number;
  min_range_km: number;
  vrel_kms: number;
  explanation: string;
  detected_at_iso: string;
};

export default function LiveAlertsTicker() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let ws: WebSocket | null = null;
    let mounted = true;

    const connect = () => {
      try {
        ws = new WebSocket(`${WS_URL}/ws/live`);
        ws.onopen = () => mounted && setConnected(true);
        ws.onmessage = (msg) => {
          try {
            const data = JSON.parse(msg.data);
            if (data.type === "alert" && mounted) {
              setAlerts((prev) => [data, ...prev].slice(0, 8));
            }
          } catch {
            /* ignore */
          }
        };
        ws.onclose = () => mounted && setConnected(false);
        ws.onerror = () => mounted && setConnected(false);
      } catch {
        /* ignore */
      }
    };

    connect();

    // Demo fallback: synthesize alerts if backend isn't reachable after 3s
    const fallbackTimer = setTimeout(() => {
      if (alerts.length === 0 && !connected) {
        const demo: Alert[] = [];
        for (let i = 0; i < 5; i++) {
          demo.push({
            type: "alert",
            primary: [25544, 44943, 53700, 95222, 99000][i % 5],
            secondary: [46201, 53072, 95343, 99002, 99005][i % 5],
            tca_iso: new Date(Date.now() + i * 86400e3).toISOString(),
            pc: 10 ** (-3 - Math.random() * 4),
            min_range_km: 0.5 + Math.random() * 9,
            vrel_kms: 5 + Math.random() * 10,
            explanation: "Demo alert (backend not connected yet)",
            detected_at_iso: new Date().toISOString(),
          });
        }
        setAlerts(demo);
      }
    }, 3000);

    return () => {
      mounted = false;
      clearTimeout(fallbackTimer);
      ws?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fmtPc = (pc: number) => {
    if (pc < 1e-6) return "Pc≈0";
    if (pc < 1e-3) return `Pc=${pc.toExponential(1)}`;
    return `Pc=${pc.toFixed(4)}`;
  };

  return (
    <div className="absolute bottom-16 right-4 w-80 max-w-[calc(100vw-2rem)] bg-panel border border-cyan-500/30 backdrop-blur rounded-xl text-xs font-mono pointer-events-auto overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <div className="text-cyan-400 font-bold uppercase tracking-widest">
          Live conjunction stream
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? "bg-emerald-400" : "bg-amber-400 tool-pulse"
            }`}
          />
          <span className="text-[10px] text-slate-400">
            {connected ? "live" : "offline (demo)"}
          </span>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="px-3 py-3 text-slate-500 text-[11px]">
            Waiting for live alerts…
          </div>
        ) : (
          alerts.map((a, i) => (
            <div
              key={`${a.detected_at_iso}-${i}`}
              className="px-3 py-2 border-b border-white/5 hover:bg-cyan-500/5 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-300">
                  <b className="text-cyan-400">{a.primary}</b> ↔{" "}
                  <b className="text-cyan-400">{a.secondary}</b>
                </span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded ${
                    a.pc > 1e-4 ? "bg-red-500/20 text-red-300" : "bg-amber-500/15 text-amber-300"
                  }`}
                >
                  {fmtPc(a.pc)}
                </span>
              </div>
              <div className="text-[10px] text-slate-500 flex items-center justify-between">
                <span>miss {a.min_range_km.toFixed(2)} km</span>
                <span>vrel {a.vrel_kms.toFixed(1)} km/s</span>
              </div>
              <div className="text-[10px] text-slate-600 truncate">
                TCA {new Date(a.tca_iso).toUTCString().slice(5, 22)}
              </div>
            </div>
          ))
        )}
      </div>
      <div className="px-3 py-1.5 text-[10px] text-slate-500 border-t border-white/5">
        Public stream · no login · free · open complement to Stargaze
      </div>
    </div>
  );
}
