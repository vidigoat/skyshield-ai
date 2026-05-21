# Changelog

## 0.1.0 — 2026-05-21 (overnight build)

The marathon: from scaffold to deployed-ready in one ~10-hour session.

### Headline numbers

- **100% pair-level recall** vs the US Office of Space Commerce TraCSS verification answer key (79-OCM Aerospace IVV subset)
- **100% precision** — zero false positives
- **19.5 sec** end-to-end wall clock on M-series Mac CPU
- **67/67 tests passing**, CI green, ruff clean

### Architecture journey (same 79-OCM real data)

| Version | Wall clock | Pair recall | Pair precision |
|---|---|---|---|
| v1 (initial Python-loop pipeline) | 196s | 12.5% | 100% |
| v2 (+ local-minima detection) | 325s | 18.7% | 100% |
| v3 (+ golden-section TCA refinement) | 487s | 62.5% | 100% |
| v5 (vectorized NumPy + swept-volume) | 28s | **100%** | **100%** |
| **v6 (fully vectorized swept-volume)** | **19.5s** | **100%** | **100%** |

### What was built

- **Backend** (~5,000 LOC Python)
  - OCM (CCSDS 502.0-B-3) and TLE parsers calibrated against real data
  - SGP4-in-JAX clean-room implementation
  - Pc methods: Alfano 2004 (primary), Chan, Foster, Patera, Monte Carlo
  - Vectorized screener: octree + Z-order + swept-volume bridge
  - Differentiable maneuver optimizer (pair-wise)
  - Multi-fleet maneuver coordinator (novel)
  - TraCSS eval harness + answer-key comparator
  - AI agent (Claude) with 5 verified physics tools
  - FastAPI backend with REST + `/ws/chat` + `/ws/live`
  - Live conjunction alert WebSocket hub
  - Continuous monitor daemon
  - CLI (`skyshield agent | screen | eval | serve`)
  - Modal deployment config

- **Frontend** (~1,500 LOC TypeScript)
  - Next.js 16 + Tailwind v4 + TypeScript strict
  - Tab A: 3D globe with 3000-satellite render, click-to-query, live alert ticker
  - Tab B: agent chat with live tool-call streaming
  - Cross-tab linking via shared store
  - Dark theme, mobile-responsive, production build clean

- **Documentation**
  - README with real benchmark numbers
  - ARCHITECTURE.md (~500 lines deep technical)
  - NOTICE.md (acknowledgments)
  - CLAUDE.md (project conventions for AI assistants)
  - ELON_EMAIL.md (the email draft)
  - notebooks/01_walkthrough.py (runnable end-to-end demo)
  - 12+ commits with descriptive messages

### Real-data validation

Tested against the **US Office of Space Commerce Aerospace IVV verification dataset** (CC0-1.0 public domain, October 2025 snapshot):

- **913,330** spherical-volume conjunctions across **26,793 satellites**
- **283,595** SFSH-volume conjunctions
- 20.73 GB of CCSDS OCM ephemerides
- 7-day screening window: 2025-01-01 12:00:00 UTC → 2025-01-08 12:00:00 UTC

### Bugs caught on real data

1. Single conjunction per (obj1, obj2) pair — answer key has multiple TCAs per pair
2. Coarse-sample miss overestimates true TCA miss when TCA falls between samples
3. OCM section delimiters: TRAJ_START/STOP, not ORB_START/STOP
4. Pc method must be Alfano 2004 specifically — that's what populates the answer-key `prob` column
5. CSV column names: c1_11 not C1_xx, obj1_filename not obj1_file
6. Covariance is 3×3 position-only (CARTP) in Aerospace IVV, not 6×6

All documented in commit history.

### Stack

- Python 3.12 (uv-managed)
- JAX 0.4 (JIT + vmap + grad)
- NumPy 2.0, SciPy 1.17, Polars 1.0
- FastAPI 0.115 + uvicorn + websockets
- Anthropic SDK 0.39 (Claude Sonnet 4.6 default)
- Next.js 16.2 (Turbopack) + Tailwind v4 + globe.gl + satellite.js
- pytest + hypothesis + ruff + mypy

### License

MIT.

---

**Built by Vidit Patankar (14, Gurgaon). One night.**
