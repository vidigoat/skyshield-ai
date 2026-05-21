"use client";

import { useEffect, useState } from "react";
import { store } from "@/lib/store";

const TABS = [
  { id: "globe", label: "Live Globe", glyph: "◉" },
  { id: "chat", label: "AI Agent", glyph: "◎" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function TabsBar({
  active,
  onChange,
}: {
  active: TabId;
  onChange: (t: TabId) => void;
}) {
  const [animActive, setAnimActive] = useState<TabId>(active);

  // Sync from store (e.g. globe click → switch to chat)
  useEffect(() => {
    return store.subscribe(() => {
      if (store.activeTab !== animActive) {
        setAnimActive(store.activeTab as TabId);
        onChange(store.activeTab as TabId);
      }
    });
  }, [animActive, onChange]);

  useEffect(() => setAnimActive(active), [active]);

  return (
    <div className="flex items-center justify-between border-b border-white/10 px-4 sm:px-6 py-3 bg-[#060a1f] flex-shrink-0">
      <div className="flex items-center gap-4">
        <div className="text-lg font-bold text-cyan-400 tracking-tighter">
          SkyShield
          <span className="text-white">.</span>
          <span className="text-amber-400">AI</span>
        </div>
        <div className="hidden sm:block text-[10px] text-slate-500 font-mono">
          Open AI agent for satellite safety
        </div>
      </div>

      <div className="flex items-center gap-1 bg-slate-900/60 border border-white/10 rounded-xl p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => {
              store.setActiveTab(t.id);
              onChange(t.id);
            }}
            className={`px-3 sm:px-4 py-1.5 text-xs sm:text-sm rounded-lg font-medium transition-colors ${
              active === t.id
                ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span className="mr-1.5">{t.glyph}</span>
            {t.label}
          </button>
        ))}
      </div>

      <a
        href="https://github.com/vidigoat/skyshield-ai"
        target="_blank"
        rel="noreferrer"
        className="hidden sm:flex text-xs text-slate-500 hover:text-cyan-400 transition-colors font-mono"
      >
        github ↗
      </a>
    </div>
  );
}

export type { TabId };
