import type { ChatMessage } from "../lib/types";
import ToolCall from "./ToolCall";

/**
 * Minimal markdown-ish renderer:
 *  - **bold**
 *  - bullet lines starting with "- "
 *  - inline `code`
 *  - markdown tables (| ... |)
 *  - blank lines separate paragraphs
 *
 * We keep this tiny — no markdown lib needed for the agent's controlled output.
 */
function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // First pass: split by `code` to handle inline code separately
  const codeSplit = text.split(/(`[^`]+`)/);
  let key = 0;
  for (const piece of codeSplit) {
    if (piece.startsWith("`") && piece.endsWith("`")) {
      parts.push(
        <code
          key={`c${key++}`}
          className="px-1.5 py-0.5 rounded bg-neutral-100 border border-neutral-200 text-[12px] font-mono"
        >
          {piece.slice(1, -1)}
        </code>,
      );
      continue;
    }
    // Then split by **bold**
    const boldSplit = piece.split(/(\*\*[^*]+\*\*)/);
    for (const sub of boldSplit) {
      if (sub.startsWith("**") && sub.endsWith("**")) {
        parts.push(<b key={`b${key++}`}>{sub.slice(2, -2)}</b>);
      } else if (sub) {
        parts.push(<span key={`s${key++}`}>{sub}</span>);
      }
    }
  }
  return parts;
}

function MarkdownTable({ rows }: { rows: string[] }) {
  // rows is a contiguous block of |…| lines.
  const cells = rows.map((r) =>
    r
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => c.trim()),
  );
  const header = cells[0];
  // Skip the alignment row (---|---) by checking for dashes
  const dataStart = cells[1] && cells[1].every((c) => /^-+$/.test(c.replace(/:/g, ""))) ? 2 : 1;
  const data = cells.slice(dataStart);
  return (
    <table className="my-3 w-full text-[13px] border-collapse">
      <thead>
        <tr>
          {header.map((h, i) => (
            <th
              key={i}
              className="text-left font-semibold text-neutral-900 border-b border-neutral-300 px-2 py-1.5"
            >
              {renderInline(h)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, ri) => (
          <tr key={ri} className="border-b border-neutral-200 last:border-0">
            {row.map((cell, ci) => (
              <td key={ci} className="px-2 py-1.5 align-top text-neutral-800">
                {renderInline(cell)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderText(text: string) {
  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let buffer: string[] = [];
  let bulletBuffer: string[] = [];
  let tableBuffer: string[] = [];
  let blockIdx = 0;

  const flushParagraph = () => {
    if (buffer.length === 0) return;
    blocks.push(
      <p key={`p${blockIdx++}`} className="my-1.5">
        {renderInline(buffer.join(" "))}
      </p>,
    );
    buffer = [];
  };

  const flushBullets = () => {
    if (bulletBuffer.length === 0) return;
    blocks.push(
      <ul key={`u${blockIdx++}`} className="list-disc list-outside ml-5 my-2 space-y-0.5">
        {bulletBuffer.map((b, i) => (
          <li key={i} className="leading-relaxed">
            {renderInline(b)}
          </li>
        ))}
      </ul>,
    );
    bulletBuffer = [];
  };

  const flushTable = () => {
    if (tableBuffer.length === 0) return;
    blocks.push(<MarkdownTable key={`t${blockIdx++}`} rows={tableBuffer} />);
    tableBuffer = [];
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("|") && line.endsWith("|")) {
      flushParagraph();
      flushBullets();
      tableBuffer.push(line);
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      flushParagraph();
      flushTable();
      bulletBuffer.push(line.slice(2));
    } else if (line === "") {
      flushParagraph();
      flushBullets();
      flushTable();
    } else {
      flushBullets();
      flushTable();
      buffer.push(line);
    }
  }
  flushParagraph();
  flushBullets();
  flushTable();
  return blocks;
}

export default function Message({ msg }: { msg: ChatMessage }) {
  if (msg.role === "tool") return <ToolCall msg={msg} />;

  if (msg.role === "user") {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%] bg-neutral-100 border border-neutral-200 px-4 py-2.5 rounded-2xl rounded-tr-md text-[14.5px] leading-relaxed">
          {msg.text}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4">
      <div className="text-[10.5px] uppercase tracking-wider text-neutral-400 mb-1 font-mono">
        SkyShield
      </div>
      <div className="text-[14.5px] leading-relaxed text-neutral-900">
        {msg.text ? renderText(msg.text) : null}
      </div>
    </div>
  );
}
