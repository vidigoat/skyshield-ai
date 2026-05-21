# Acknowledgments

SkyShield AI stands on top of work by many researchers and organizations.
We credit each here.

## Datasets

- **TraCSS Aerospace IVV verification dataset** (CC0-1.0, Oct 2025)
  Kerstyn Auman, Timothy S. Murphy, Eric George — The Aerospace Corporation.
  Released by the US Office of Space Commerce.
  https://space.commerce.gov/dataset-for-conjunction-assessment-verification/

- **Celestrak satellite catalog** — Dr. T.S. Kelso. https://celestrak.org

- **Space-Track.org** — US Combined Space Operations Center.

## Algorithms & methods

- **Alfano 2004 Pc method** — Salvatore Alfano,
  *Relating Position Uncertainty to Maximum Conjunction Probability* (2004).
  This is the method TraCSS uses for the answer-key `prob` column.

- **Chan 1997** — F. K. Chan, *Collision Probability Analyses for Earth-Orbiting Satellites* (AAS 97-628).

- **Foster 1992** — Joel L. Foster, NASA JSC-25898 technical report (1992).

- **Patera 2001** — R.P. Patera, *General Method for Calculating Satellite Collision Probability* (JGCD).

- **SGP4 / SDP4** — Hoots & Roehrich, STR-3 (1980); Vallado et al., AIAA 2006-6753.

- **∂SGP4 (differentiable propagator)** — Acciarini et al.,
  *Closing the Gap Between SGP4 and High-Precision Propagation via Differentiable Programming*,
  arXiv:2402.04830 (2024).

- **jaxsgp4 (GPU mega-constellation propagation)** —
  *jaxsgp4: GPU-accelerated mega-constellation propagation with batch parallelism*,
  arXiv:2603.27830 (2026). Inspiration for our SGP4-in-JAX functional refactor.

- **COVGEN** — Peterson, Gist, Oltrogge,
  *Covariance Generation for Space Objects Using Public Data* (AAS Space Flight Mechanics Meeting, 2001).

- **TraCSS validation methodology** — Auman et al.,
  *Validation Methodology for TraCSS Conjunction Assessment*,
  AMOS Technical Conference 2025.
  https://amostech.com/TechnicalPapers/2025/ConjunctionRPO/Auman.pdf

- **SFSH screening volumes** — 18th & 19th Space Defense Squadron,
  *Spaceflight Safety Handbook for Satellite Operators* (v1.7, 2023).

## Tools used (open-source software)

- **NASA CARA** SDK — https://github.com/nasa/CARA_Analysis_Tools
- **JAX** — Google
- **NumPy**, **SciPy**, **Polars**, **Pydantic**, **FastAPI**, **uvicorn**
- **Next.js** 16 — Vercel
- **globe.gl**, **three-globe**, **satellite.js** — Vasco Asturiano + contributors
- **Anthropic Python SDK** — Anthropic
- **Modal** for serverless cloud deployment
- **Tailwind CSS v4**, **Geist** fonts — Vercel
- **Click** CLI framework
- **pytest**, **hypothesis**, **ruff**, **mypy**

## Inspiration

- Elon Musk's May 21, 2026 SpaceXAI hiring tweet — the proximate cause of this project.
- George Hotz's iPhone unlock (2007) — proved that solo, public-facing technical work could change a career.
- Andrej Karpathy's nanoGPT — proved that legible from-scratch reimplementations matter as artifacts.
- The Office of Space Commerce TraCSS team — for being uncommonly generous with open data.

## Disclaimer

This project is an **independent open-source effort**. It is not affiliated with, endorsed by, or sponsored by SpaceX, Anthropic, the US Office of Space Commerce, NASA, ESA, or any of the cited researchers. All trademarks belong to their respective owners.

SkyShield AI's outputs are intended for research, education, and self-evaluation. The TraCSS verification dataset itself is explicitly **not** for operational use (per User Guide §2). SkyShield AI inherits the same disclaimer: this is a diagnostic tool, not an operational certification.
