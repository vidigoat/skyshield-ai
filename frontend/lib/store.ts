/**
 * Lightweight cross-tab store (no Zustand dep — just a custom EventTarget).
 *
 * Used so that clicking a satellite on the globe (Tab A) auto-fills the
 * chat input on Tab B.
 */

"use client";

type Listener = () => void;

class SkyShieldStore {
  selectedSatId: number | null = null;
  selectedSatName: string | null = null;
  prefillChatQuery: string | null = null;
  activeTab: "globe" | "chat" = "globe";

  private listeners = new Set<Listener>();

  subscribe(l: Listener): () => void {
    this.listeners.add(l);
    return () => {
      this.listeners.delete(l);
    };
  }

  private notify() {
    this.listeners.forEach((l) => l());
  }

  selectSatellite(id: number, name: string) {
    this.selectedSatId = id;
    this.selectedSatName = name;
    this.notify();
  }

  setPrefill(q: string | null) {
    this.prefillChatQuery = q;
    this.notify();
  }

  setActiveTab(t: "globe" | "chat") {
    this.activeTab = t;
    this.notify();
  }
}

export const store = new SkyShieldStore();
