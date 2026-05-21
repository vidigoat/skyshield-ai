"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import TabsBar, { type TabId } from "@/components/Tabs";

// Dynamic imports so SSR doesn't try to instantiate Three.js / WebSocket
const GlobeView = dynamic(() => import("@/components/Globe"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-slate-500 font-mono text-sm">
      Loading constellation…
    </div>
  ),
});
const ChatView = dynamic(() => import("@/components/Chat"), {
  ssr: false,
});

export default function Page() {
  const [tab, setTab] = useState<TabId>("globe");

  return (
    <div className="flex flex-col h-screen bg-[#0a0e27]">
      <TabsBar active={tab} onChange={setTab} />

      <div className="flex-1 relative overflow-hidden">
        {/* Keep both mounted so state persists across tab switches. */}
        <div
          className={`absolute inset-0 transition-opacity duration-300 ${
            tab === "globe" ? "opacity-100 z-10" : "opacity-0 pointer-events-none z-0"
          }`}
        >
          <GlobeView />
        </div>
        <div
          className={`absolute inset-0 transition-opacity duration-300 ${
            tab === "chat" ? "opacity-100 z-10" : "opacity-0 pointer-events-none z-0"
          }`}
        >
          <ChatView />
        </div>
      </div>

      <footer className="border-t border-white/5 bg-[#060a1f] px-4 sm:px-6 py-2 flex items-center justify-between text-[10px] font-mono text-slate-500 flex-shrink-0">
        <div>
          v0.1 · 100% on TraCSS · 30K-object real-time globe ·{" "}
          <a
            href="https://github.com/vidigoat/skyshield-ai"
            target="_blank"
            rel="noreferrer"
            className="text-cyan-400 hover:underline"
          >
            open source
          </a>
        </div>
        <div className="hidden md:block">
          Built solo at 14 · response to Elon&apos;s SpaceXAI hiring tweet (May 21, 2026)
        </div>
      </footer>
    </div>
  );
}
