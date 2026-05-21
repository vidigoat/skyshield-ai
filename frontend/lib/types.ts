export type Conjunction = {
  obj1: number;
  obj2: number;
  min_range_km: number;
  pc: number | null;
  tca_iso: string;
  vrel_kms: number;
};

export type SatelliteRender = {
  norad_id: number;
  name: string;
  lat: number;
  lng: number;
  alt: number;
  color: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "agent" | "tool";
  text?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: Record<string, unknown>;
  elapsedMs?: number;
  timestamp: number;
};
