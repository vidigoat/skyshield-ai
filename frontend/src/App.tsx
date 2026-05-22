import Chat from "./components/Chat";
import Header from "./components/Header";

export default function App() {
  return (
    <div className="flex flex-col h-full bg-white text-neutral-900">
      <Header />
      <Chat />
      <footer className="border-t border-neutral-200 px-4 sm:px-8 py-2 text-[10.5px] text-neutral-400 flex items-center justify-between bg-white">
        <span>
          SkyShield AI v0.1 ·{" "}
          <a
            href="https://github.com/vidigoat/skyshield-ai"
            target="_blank"
            rel="noreferrer"
            className="text-neutral-600 hover:text-neutral-900"
          >
            open source
          </a>{" "}
          · MIT
        </span>
        <span className="hidden sm:inline">
          Built solo in response to Elon&apos;s SpaceXAI hiring tweet (May 21, 2026)
        </span>
      </footer>
    </div>
  );
}
