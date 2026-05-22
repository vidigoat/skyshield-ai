/**
 * Top header — black-and-white minimal.
 */
export default function Header() {
  return (
    <header className="border-b border-neutral-200 px-4 sm:px-8 py-3 flex items-center justify-between bg-white">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md border border-neutral-900 flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="12" rx="9" ry="3.5" />
            <ellipse cx="12" cy="12" rx="3.5" ry="9" />
            <circle cx="20" cy="6" r="1.2" fill="currentColor" />
          </svg>
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-[15px] font-semibold tracking-tight">SkyShield AI</span>
          <span className="text-[11px] text-neutral-500 mt-0.5">
            Open AI agent for satellite safety
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3 text-[11px] font-mono text-neutral-500">
        <a
          href="https://github.com/vidigoat/skyshield-ai"
          target="_blank"
          rel="noreferrer"
          className="hover:text-neutral-900 transition-colors hidden sm:inline"
        >
          github.com/vidigoat/skyshield-ai ↗
        </a>
        <span className="hidden md:inline border-l border-neutral-200 pl-3">
          100% on TraCSS · 67/67 tests
        </span>
      </div>
    </header>
  );
}
