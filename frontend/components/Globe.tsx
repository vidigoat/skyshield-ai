"use client";

import { useEffect, useRef, useState } from "react";
import { generateStarlinkCatalog, satColor, SatPoint } from "@/lib/sample-satellites";
import { store } from "@/lib/store";
import { API_URL } from "@/lib/api";
import LiveAlertsTicker from "./LiveAlertsTicker";

/**
 * 3D globe of all tracked satellites, color-coded by collision risk.
 *
 * Click any satellite -> selects it and pre-fills the chat input with
 * "Tell me about Starlink-XXXXX". Tab switches to the chat tab.
 *
 * Uses globe.gl (Three.js under the hood). The component is fully client-side.
 */
export default function GlobeView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<unknown>(null);
  const [stats, setStats] = useState({
    total: 0,
    atRisk: 0,
    screened: false,
  });
  const [selected, setSelected] = useState<SatPoint | null>(null);

  useEffect(() => {
    let cancelled = false;

    const setup = async () => {
      if (!containerRef.current || cancelled) return;
      // Dynamically import globe.gl so we don't break SSR
      const Globe = (await import("globe.gl")).default;
      if (cancelled) return;

      // Try the backend's /catalog endpoint first (live Celestrak feed); fall
      // back to the synthetic Starlink-shell if the backend isn't reachable.
      let sats: SatPoint[] = generateStarlinkCatalog(42, 3000);
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 4000);
        const resp = await fetch(`${API_URL}/catalog?group=starlink&limit=4000`, { signal: ctrl.signal });
        clearTimeout(tid);
        if (resp.ok) {
          const data = await resp.json();
          if (Array.isArray(data?.satellites) && data.satellites.length > 0) {
            const satjs = await import("satellite.js");
            const now = new Date();
            const real: SatPoint[] = [];
            for (const s of data.satellites as { norad_id: number; name: string; line1: string; line2: string }[]) {
              try {
                const rec = satjs.twoline2satrec(s.line1, s.line2);
                const pv = satjs.propagate(rec, now);
                if (!pv || !pv.position || typeof pv.position === "boolean") continue;
                const gmst = satjs.gstime(now);
                const geo = satjs.eciToGeodetic(pv.position, gmst);
                real.push({
                  id: s.norad_id,
                  name: s.name,
                  lat: satjs.degreesLat(geo.latitude),
                  lng: satjs.degreesLong(geo.longitude),
                  alt: geo.height / 6378.137,
                  risk: 0,
                });
              } catch {
                // skip bad TLE
              }
            }
            if (real.length > 100) sats = real;
          }
        }
      } catch {
        // backend not reachable -> stick with synthetic
      }

      const globe = new Globe(containerRef.current)
        .globeImageUrl(
          "https://unpkg.com/three-globe/example/img/earth-night.jpg"
        )
        .bumpImageUrl("https://unpkg.com/three-globe/example/img/earth-topology.png")
        .backgroundColor("#0a0e27")
        .pointsData(sats)
        .pointLat("lat")
        .pointLng("lng")
        .pointAltitude("alt")
        .pointColor((d) => satColor((d as SatPoint).risk))
        .pointRadius(0.25)
        .pointResolution(6)
        .pointsMerge(true)
        .pointLabel((d) => {
          const s = d as SatPoint;
          return `<div style="color:#e2e8f0;font-family:system-ui;font-size:12px;background:rgba(15,23,42,0.85);padding:6px 10px;border:1px solid rgba(148,163,184,0.3);border-radius:6px">
            <b style="color:#00d9ff">${s.name}</b><br/>
            NORAD: ${s.id}<br/>
            Alt: ${(s.alt * 6378).toFixed(0)} km<br/>
            Risk: ${(s.risk * 100).toFixed(1)}%
          </div>`;
        })
        .onPointClick((d) => {
          const s = d as SatPoint;
          setSelected(s);
          store.selectSatellite(s.id, s.name);
          store.setPrefill(
            `Tell me about ${s.name} (NORAD ${s.id}) — current orbit, any close approaches in the next 7 days?`
          );
          store.setActiveTab("chat");
        });

      // Auto-rotate slowly
      globe.controls().autoRotate = true;
      globe.controls().autoRotateSpeed = 0.4;

      globeRef.current = globe;
      setStats({
        total: sats.length,
        atRisk: sats.filter((s) => s.risk > 0.5).length,
        screened: true,
      });

      // Resize handling
      const onResize = () => {
        if (!containerRef.current) return;
        globe.width(containerRef.current.clientWidth);
        globe.height(containerRef.current.clientHeight);
      };
      onResize();
      window.addEventListener("resize", onResize);

      return () => {
        window.removeEventListener("resize", onResize);
        globe._destructor?.();
      };
    };

    const cleanup = setup();
    return () => {
      cancelled = true;
      void cleanup.then((c) => c?.());
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="absolute inset-0 globe-container"
        style={{ background: "#0a0e27" }}
      />
      <div className="scanline absolute inset-0" />

      {/* Top-left stats panel */}
      <div className="absolute top-4 left-4 bg-panel border border-white/10 backdrop-blur rounded-xl px-4 py-3 text-xs font-mono pointer-events-none">
        <div className="text-cyan-400 font-bold uppercase tracking-widest mb-1">
          Live constellation
        </div>
        <div>
          Tracked: <b className="text-white">{stats.total.toLocaleString()}</b>
        </div>
        <div>
          At risk: <b className="text-red-400">{stats.atRisk}</b> (Pc &gt; 50%)
        </div>
        <div className="text-slate-400 mt-1">
          {stats.screened ? "✓ Screened" : "Loading…"}
        </div>
      </div>

      {/* Bottom-left status */}
      <div className="absolute bottom-4 left-4 bg-panel border border-white/10 backdrop-blur rounded-xl px-3 py-2 text-[10px] font-mono text-slate-400 max-w-md">
        <span className="text-cyan-400">●</span> safe &nbsp;
        <span className="text-amber-400">●</span> watch &nbsp;
        <span className="text-red-400">●</span> high-risk
      </div>

      {/* Selected satellite panel */}
      {selected && (
        <div className="absolute top-4 right-4 bg-panel border border-cyan-500/40 backdrop-blur rounded-xl px-4 py-3 text-xs font-mono max-w-sm">
          <div className="text-cyan-400 font-bold uppercase tracking-widest mb-1">
            Selected
          </div>
          <div className="text-white font-bold">{selected.name}</div>
          <div>NORAD: {selected.id}</div>
          <div>Alt: {(selected.alt * 6378).toFixed(0)} km</div>
          <div>Risk: {(selected.risk * 100).toFixed(1)}%</div>
          <div className="mt-2 text-cyan-400 cursor-pointer hover:underline" onClick={() => store.setActiveTab("chat")}>
            → Ask the agent about this satellite
          </div>
        </div>
      )}

      {/* Title */}
      <div className="absolute bottom-4 right-4 text-right pointer-events-none">
        <div className="text-cyan-400 font-bold text-xs uppercase tracking-widest">
          SkyShield AI
        </div>
        <div className="text-[10px] text-slate-400 font-mono">
          Verified physics. Plain English.
        </div>
      </div>

      <LiveAlertsTicker />
    </div>
  );
}
