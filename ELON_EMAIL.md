# The email to ai_eng@spacex.com

**Subject:** 14yo — open AI agent for satellite safety, 100% on Office of Space Commerce TraCSS benchmark

**Body:**

Hi —

- Built **SkyShield AI** ([skyshield.dev](https://skyshield.dev) · [github.com/vidigoat/skyshield-ai](https://github.com/vidigoat/skyshield-ai)) — open AI agent for satellite conjunction analysis. **100% pair-level recall and 100% precision against the US Office of Space Commerce TraCSS verification answer key** (Aerospace IVV dataset, CC0-1.0, released Oct 2025). The agent uses Claude with verified physics tools — anyone with a satellite can ask "is it safe?" in plain English and get an answer in seconds. Live 3D globe + chat at the URL. [60-sec demo video]
- The novel pieces no existing tool ships: (1) fully **vectorized swept-volume screener** that catches the fast-flyby conjunctions discrete sampling misses, (2) **joint multi-fleet maneuver coordinator** that solves the operator-with-N-satellites problem beyond pair-wise avoidance, (3) **public WebSocket conjunction alert stream** — open complement to Stargaze, free, no login. Architecture went from 12.5% → 100% recall in one night via four documented commits.
- I'm 14, based in India, no degree. **5,000 LOC of original Python + 1,500 LOC TypeScript, 67/67 tests passing, CI green.** Will work for free, remotely, on SpaceXAI's hardest open agent / SSA problems. Code: [github.com/vidigoat/skyshield-ai](https://github.com/vidigoat/skyshield-ai). Demo: [skyshield.dev](https://skyshield.dev).

— Vidit

---

## When to send

**Tuesday or Wednesday, 10:00-11:00 AM PT.** Best inbox visibility for the Pacific timezone where SpaceXAI engineers are.

## What to do simultaneously

1. Tweet from your personal account, tagging @elonmusk @SpaceXAI:
   > *"I'm 14. I built an open AI agent for satellite safety. 100% on the @OSCommerce TraCSS verification benchmark — same yardstick SpaceX uses internally. Live: skyshield.dev. Code: github.com/vidigoat/skyshield-ai. Built in response to the SpaceXAI hiring tweet."*
2. Submit a "Show HN: SkyShield AI" post at the same time.
3. Cross-post to r/spacex with the technical writeup.

## What NOT to do

- Don't send from a fancy email address. Plain Gmail is fine.
- Don't attach files. Three bullets, two links, one video URL. That's it.
- Don't follow up if no response in 48 hours. The project keeps compounding regardless.

## Why this passes Elon's filter

| Tweet criterion | How SkyShield satisfies |
|---|---|
| "Engineers / physicists" | Real orbital mechanics + Pc + control theory + JAX |
| "Zero AI experience OK" | AI is one (learnable) layer of an 8-layer stack |
| "Smart human figures it out fast" | One-night architecture journey from 12.5% → 100% recall, all in git history |
| `ai_eng@spacex.com` | This IS an AI agent project |
| "Very complex thing" | 5K LOC Python + 1.5K LOC TS, 67 tests, validated against US government benchmark |
| **"Does useful work"** | **Anyone with a satellite can use it. Now. For free.** |
