import { useCallback, useEffect, useRef, useState } from "react";
import Message from "./Message";
import Composer from "./Composer";
import { openAgentWebSocket, postChat } from "../lib/api";
import { type ChatMessage, uid } from "../lib/types";

const INITIAL_MESSAGE: ChatMessage = {
  id: "init",
  role: "agent",
  text: `Ask me anything about satellite safety.

I plan a sequence of physics tool calls, run them through code that is **validated 100% against the US Office of Space Commerce TraCSS verification benchmark**, and give you a plain-English answer with the numbers visible.

Try one of the prompts below.`,
  timestamp: Date.now(),
};

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, thinking]);

  const send = useCallback(
    (text: string) => {
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
      setThinking(true);

      let appended = false;
      let sawToolEvent = false;

      const finishWithError = (msg: string) => {
        if (appended) return;
        appended = true;
        setMessages((m) => [
          ...m,
          {
            id: uid(),
            role: "agent",
            text: msg,
            timestamp: Date.now(),
          },
        ]);
        setStreaming(false);
        setThinking(false);
      };

      // REST fallback — runs the real backend (not a hardcoded demo)
      // when the WebSocket closes before delivering a `final` event.
      const restFallback = async () => {
        if (appended) return;
        try {
          const resp = await postChat(text);
          if (appended) return;
          appended = true;
          // Only append tool events if the WS hadn't already shown them.
          if (!sawToolEvent) {
            for (const ev of resp.tool_events) {
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
            }
          }
          setMessages((m) => [
            ...m,
            {
              id: uid(),
              role: "agent",
              text: resp.text,
              timestamp: Date.now(),
            },
          ]);
        } catch (err) {
          finishWithError(`[error] ${(err as Error).message ?? String(err)}`);
          return;
        }
        setStreaming(false);
        setThinking(false);
      };

      const ws = openAgentWebSocket(
        (ev) => {
          if (ev.type === "tool_event") {
            sawToolEvent = true;
            setThinking(false);
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
            setThinking(true);
          } else if (ev.type === "final") {
            appended = true;
            setThinking(false);
            setMessages((m) => [
              ...m,
              {
                id: uid(),
                role: "agent",
                text: ev.text,
                timestamp: Date.now(),
              },
            ]);
            setStreaming(false);
          } else if (ev.type === "error") {
            finishWithError(`[error] ${ev.error}`);
          }
        },
        () => {
          // WS closed without `final`. Use the REST endpoint (real backend),
          // never a hardcoded demo — demos lie about what the agent did.
          if (!appended) void restFallback();
        },
      );

      if (!ws) {
        void restFallback();
        return;
      }
      ws.onopen = () => ws.send(JSON.stringify({ type: "user_message", message: text }));
    },
    [streaming],
  );

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto chat-scroll">
        <div className="max-w-3xl mx-auto px-4 sm:px-8 py-6">
          {messages.map((m) => (
            <Message key={m.id} msg={m} />
          ))}
          {thinking && (
            <div className="mt-2 mb-4 flex items-center gap-1 text-neutral-500 text-[12px] font-mono">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="ml-2">planning…</span>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-3xl w-full mx-auto">
        <Composer
          value={input}
          onChange={setInput}
          onSubmit={() => send(input)}
          showExamples={messages.length <= 1}
          onExampleClick={(q) => send(q)}
          disabled={streaming}
        />
      </div>
    </div>
  );
}
