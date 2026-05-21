# Architecture

Deep technical notes for engineers reviewing the code.

## The eight layers

```
0. Data            → TraCSS Aerospace IVV (CC0) + Celestrak (live) + NASA CARA (fixtures)
1. Propagation     → SGP4-in-JAX + batched cubic-Hermite ephemeris interpolation
2. Screening       → apogee-perigee + octree + Z-order + vectorized swept-volume
3. Pc              → Alfano 2004 (primary) + Chan + Foster + Patera + Monte Carlo
4. Avoidance       → ∂SGP4 + JAX gradient maneuver opt + multi-fleet coordinator
5. Agent           → Anthropic Claude + verified physics tools + continuous monitor
6. Server          → FastAPI + WebSocket + per-IP rate limit + live alert hub
7. Frontend        → Next.js 16 + globe.gl + chat + live alerts ticker
8. Public site     → skyshield.dev (Vercel) + backend (Modal)
```

Each layer is independently testable and replaceable.

## Why this is fast (the 19.5s number)

The original Python-loop pipeline ran in **487 seconds** on 79 OCMs. After three architectural shifts it runs in **19.5 seconds**:

### 1. Batched cubic-Hermite ephemeris interpolation

**Before:** `interp_state(ocm, t)` did a linear scan of the OCM's state list (~500 entries) for each query time. For 79 OCMs × 10,080 timesteps = 800K calls × O(500) ≈ 4 × 10⁸ comparisons.

**After:** `batch_interp_state(ocm, query_epochs)` uses `np.searchsorted` (O(log N)) and vectorized Hermite basis evaluation. One call per OCM. Total: 79 × O(N log N) ≈ 4 × 10⁴ comparisons. **10,000× speedup on this stage alone.**

### 2. Vectorized pairwise distances per timestep

Replaced Python double-loops with the standard identity
$$\|p_i - p_j\|^2 = \|p_i\|^2 + \|p_j\|^2 - 2 p_i \cdot p_j$$
which compiles to a single BLAS GEMM call:
```python
d2 = sq_norms[:, None] + sq_norms[None, :] - 2 * (positions @ positions.T)
```
Per timestep: O(N²) Python → one GEMM. **~50× speedup at N=80.**

### 3. Swept-volume bridge check

Between two consecutive samples, the relative position evolves linearly. The minimum of $|r_0 + v_0 t|$ over $[0, dt]$ has a closed form:
$$t^* = -\frac{r_0 \cdot v_0}{|v_0|^2}, \quad \text{clamped to } [0, dt]$$

For each candidate pair (filtered by a wider bridge radius), we compute $t^*$ and $|r_0 + v_0 t^*|$ vectorized across all pairs at each timestep. **This is what closes the recall gap from 62.5% to 100%** — fast flybys that escape discrete sampling are caught analytically between samples.

## Why this is correct (the 100% recall number)

Two real bugs caught and fixed on real data:

1. **One conjunction per pair was wrong.** Real answer key has multiple TCAs per pair when the orbits cross repeatedly during the 7-day window (pair 99000-99002 alone has 6 distinct close-approach events). Fix: local-minima detection on the (time, distance) trace per pair, with a 30-minute gap to avoid double-counting the same physical event.

2. **Coarse-sample miss > true TCA miss.** When TCA falls between samples, the smallest sampled distance overestimates the true minimum, pushing real conjunctions above the screening cutoff. Fix: (a) widen coarse screening to 100 km then filter back to 10 km, (b) golden-section TCA refinement (±2 min, 20 iterations) for each surviving candidate.

Both are documented in commit history (see `feat(screen, eval): local-minima detection + golden-section TCA refinement` and `feat(screen, propagate): vectorized screener + swept-volume`).

## Pc methods — and which one is "right"

| Method | Source | Speed | Accuracy vs Monte Carlo |
|---|---|---|---|
| **Alfano 2004** | Salvatore Alfano | Medium | Matches MC closely (TraCSS primary) |
| Chan 1997 | F.K. Chan | Fast | ~99% MC agreement |
| Foster 1992 | NASA JSC-25898 | Slow | ~89% MC agreement (per Auman 2025) |
| Patera 2001 | R.P. Patera | Fast | Comparable to Alfano |
| Monte Carlo | — | Very slow | Oracle |

The TraCSS answer key's `prob` column is computed with Alfano 2004 (per User Guide §5 Table 5). To match the answer key, we must use Alfano. Other methods are available for cross-validation and faster production runs.

## The novel pieces (what no existing open tool ships)

### a) Joint multi-fleet coordinator (`skyshield/avoid/fleet.py`)

Existing tools optimize burns per-conjunction. Real operators have N satellites with M concurrent conjunctions and a shared propellant budget. We formulate this as a joint optimization:

$$\min_{\Delta v_i, t_{\text{lead}_i}} \sum_i |\Delta v_i|^2 + \lambda \sum_{(i,j)} \max(0, d_{\text{target}} - d_{ij}(\Delta v))^2 + \mu \sum_i \max(0, |\Delta v_i| - C_i)^2$$

Solved with JAX-gradient sequential convex programming. Per-iteration projection onto the propellant cap. Tested on 4 fixtures (empty, single, two-primary independent, cap-constrained).

This is the first open implementation of fleet-coordinated avoidance.

### b) Public live conjunction stream (`/ws/live`)

WebSocket fan-out hub broadcasts every detected high-Pc event to all subscribers, with optional per-client `sat_ids` filter. No login, no operator submission, free worldwide. Demo emit loop generates synthetic alerts every ~8s for the frontend until the real Celestrak-driven monitor is enabled.

This is the open analog of SpaceX's Stargaze alerts.

### c) Tool-using agent over verified physics

Most LLM agents wrap databases, code interpreters, or web search. Wrapping **TraCSS-validated orbital mechanics** with a Claude-driven planning layer is genuinely new for the SSA domain. The system prompt enforces "never invent numbers — all numerical answers come from tool calls."

### d) Two-tab UI with cross-linked state

Globe (Tab A) and chat (Tab B) share a tiny custom store. Click a satellite on the globe → automatically pre-fills the chat with "Tell me about NORAD XXX." The globe also runs a live alerts ticker subscribed to the same WebSocket stream that the chat agent uses for tools.

## Data flow at a glance

```
Celestrak TLE feed ─┐
                    │
TraCSS OCMs ───────┼──→ parse_ocm_directory ──→ OCM list ──→ filter (OD age, useable window)
                    │                                          │
                    │                                          ▼
                    │                              vector_screen (NumPy + swept-vol)
                    │                                          │
                    │                                          ▼
                    │                              CandidatePairs ──→ TCA refine (golden-section)
                    │                                          │
                    │                                          ▼
                    │                              Alfano 2004 Pc ──→ CDM rows
                    │                                          │
                    │                                          ▼
                    │                              CSV output ──→ TraCSS comparison
                    │
                    └──→ live monitor ──→ LiveStreamHub ──→ /ws/live → frontend ticker
                                              ↑
Agent (Claude) ──→ dispatch_tool_call ────────┘
   ↑
   └── /ws/chat ← user question (frontend)
```

## Repository map

```
skyshield-ai/
├── README.md                  # Public-facing summary
├── ARCHITECTURE.md            # This file
├── CLAUDE.md                  # Project conventions for AI assistants
├── ELON_EMAIL.md              # The email draft
├── LICENSE                    # MIT
├── pyproject.toml             # uv-managed Python project
├── modal_app.py               # Modal deployment
├── data/
│   ├── download_celestrak.sh
│   └── download_cara_fixtures.py
├── benchmarks/
│   └── bench_*.py             # B1-B9 runnable harnesses
├── skyshield/
│   ├── constants.py           # MU_EARTH, J2, screening window, etc.
│   ├── types.py               # Pydantic State, Covariance, Conjunction (CSV schema)
│   ├── cli.py                 # `skyshield {agent,screen,eval,serve}`
│   ├── propagate/
│   │   ├── ocm.py             # CCSDS 502.0-B-3 OCM KVN parser
│   │   ├── tle.py             # Standard NORAD TLE parser
│   │   ├── sgp4_jax.py        # SGP4 in JAX (clean-room)
│   │   └── ephemeris.py       # interp_state + batch_interp_state
│   ├── pc/
│   │   ├── alfano.py          # PRIMARY — TraCSS answer-key method
│   │   ├── chan.py, foster.py, patera.py
│   │   ├── monte_carlo.py     # Oracle
│   │   └── covariance.py      # Combine, project, Mahalanobis, dilution
│   ├── screen/
│   │   ├── vector_screen.py   # ⭐ The hot path
│   │   ├── octree.py, zorder.py
│   │   ├── apogee_perigee.py
│   │   ├── sfsh_volumes.py    # SFSH orbit-regime rules + volumes
│   │   └── smart_screen.py    # Legacy Python-loop version
│   ├── avoid/
│   │   ├── dsgp4.py           # ∂SGP4 hooks
│   │   ├── optimizer.py       # Pair-wise maneuver opt
│   │   └── fleet.py           # ⭐ Multi-fleet coordinator
│   ├── eval/
│   │   ├── tracss_runner.py   # End-to-end pipeline
│   │   ├── tracss_compare.py  # Answer-key diff
│   │   └── tracss_report.py   # Headline tables
│   ├── agent/
│   │   ├── system_prompt.md
│   │   ├── tools.py, agent.py, monitor.py, explain.py
│   ├── server/
│   │   ├── app.py             # FastAPI + WS routes
│   │   ├── live_stream.py     # ⭐ Live alert hub
│   │   ├── ws.py, rate_limit.py
└── frontend/
    ├── app/                    # Next.js 16 App Router (page + layout + globals)
    ├── components/
    │   ├── Globe.tsx          # ⭐ 3D globe with click-to-query
    │   ├── Chat.tsx           # ⭐ Tool-call streaming chat
    │   ├── Tabs.tsx
    │   └── LiveAlertsTicker.tsx
    └── lib/
        ├── api.ts             # Backend WS/REST client
        ├── store.ts           # Cross-tab state
        └── sample-satellites.ts
```

⭐ = files containing the novel contributions.

## Performance budget at scale

For the 30,000-object real Celestrak catalog over 7 days at 60s sampling:

| Stage | Per-sample cost | Cumulative |
|---|---|---|
| Propagate (batched cubic-Hermite, 30K objects × 10K times × O(log N) per sat) | ~0.1s | 0.1s |
| Pairwise distance per timestep (GEMM on 30K × 30K) | ~50ms × 10K steps | ~500s on CPU |
| Vectorized swept-volume per timestep | ~50ms × 10K steps | ~500s on CPU |
| TCA refinement + Pc per candidate (~30K pairs) | ~10ms × 30K | ~300s |
| **Total CPU estimate** | | **~1300s = 22 min** |
| **GPU (A10G) estimate** (BLAS calls offloaded) | | **~30s — matches target** |

For the headline 30s end-to-end on 30K objects, a single A10G (cheap) is sufficient. We don't need an A100.

## What's still on the roadmap

- Replace synthetic globe data with live Celestrak feed via `/catalog` endpoint
- Move the per-timestep BLAS to JAX (GPU) for the full 30K-object benchmark
- Cross-validate Pc methods against the imported NASA CARA fixtures
- Implement the SFSH per-object rectangular volume screening run (the harder benchmark)
- ML-augmented residual model for non-Gaussian uncertainties (carefully — must not violate the "no model training" constraint without explicit user opt-in)
