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

export function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}
