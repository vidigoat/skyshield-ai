import { useCallback, useEffect, useRef, useState } from "react";
import Message from "./Message";
import Composer from "./Composer";
import { openAgentWebSocket, pickDemoFlow } from "../lib/api";
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

      const ws = openAgentWebSocket(
        (ev) => {
          if (ev.type === "tool_event") {
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
            appended = true;
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
            setThinking(false);
          }
        },
        () => {
          if (!appended) {
            // Connection closed without a `final` — fall to stub
            playDemo(text);
          }
        },
      );

      if (!ws) {
        playDemo(text);
        return;
      }
      ws.onopen = () => ws.send(JSON.stringify({ type: "user_message", message: text }));
    },
    [streaming],
  );

  // Stub-mode playback for when the backend isn't reachable
  const playDemo = (text: string) => {
    const flow = pickDemoFlow(text);
    let delay = 700;
    setThinking(true);
    for (const step of flow.steps) {
      setTimeout(() => {
        setThinking(false);
        setMessages((m) => [
          ...m,
          {
            id: uid(),
            role: "tool",
            toolName: step.name,
            toolInput: step.input,
            toolOutput: step.output,
            elapsedMs: step.elapsed_ms,
            timestamp: Date.now(),
          },
        ]);
        setThinking(true);
      }, delay);
      delay += 900 + Math.random() * 400;
    }
    setTimeout(() => {
      setThinking(false);
      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "agent",
          text: flow.finalText,
          timestamp: Date.now(),
        },
      ]);
      setStreaming(false);
    }, delay + 300);
  };

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
