# CLAUDE.md — SkyShield AI project conventions

Instructions for Claude Code (and other AI assistants) working in this repo.
Read this before making changes.

---

## Project identity

**SkyShield AI** — open AI agent for satellite conjunction analysis. Verified
physics, plain English. Built solo by Vidit Patankar (14, Gurgaon) in 8 weeks,
in response to Elon Musk's 2026-05-21 SpaceXAI hiring tweet.

The headline goal: **near-perfect agreement with the US Office of Space
Commerce TraCSS verification answer key**, scaled to mega-constellations,
with an open AI agent layer that translates physics into plain English.

---

## Hard rules (do not break)

### 1. Multiple commits, never one mega-commit

**Always split logically related work into separate commits.** One commit per
logical concern: one module, one bug fix, one feature, one refactor. Even a
"big sweep" gets split — the audience reading this repo (engineers at
SpaceXAI) will look at the commit history.

When implementing a new module / phase:
- One commit per module (e.g. `feat(pc): ...`, `feat(screen): ...`)
- Tests go *with* the module they test, not in a separate commit
- Lint fixes get a follow-up `chore(lint): ...` if needed, not folded into the feature commit
- Refactors are their own commits

Use **Conventional Commits** prefixes: `feat(scope)`, `fix(scope)`,
`chore(scope)`, `refactor(scope)`, `test(scope)`, `docs(scope)`.

If you find yourself about to do one giant `git commit -m "everything"`,
**stop** and split the changes by `git add -p` or per-file `git add`.

### 2. No model training, ever

This project never trains any ML model. The "AI" is the Anthropic Claude API
calls in `skyshield/agent/`. We use existing models. We don't train, fine-tune,
or distill. If a feature seems to require training, find another way.

### 3. Physics must be verifiable

Every numerical answer in the agent's output must come from a tool call to
real physics code in `skyshield/{propagate,screen,pc,avoid}/`. Never let the
agent invent a number from its own reasoning. The system prompt enforces this
on the LLM side; the tool dispatcher enforces it on the code side.

### 4. Match TraCSS exactly

When parsing OCM, computing Pc, or writing CDM CSV output, follow the
**Conjunction_Screening_Testset_Users_Guide.pdf** (Aerospace IVV) literally:

- CDM CSV column order: see `Conjunction.csv_columns()` in `skyshield/types.py`
- Pc method for the `prob` column: **Alfano 2004** (not Chan, not Foster)
- Screening window: 2025-01-01T12:00:00Z to 2025-01-08T12:00:00Z
- OD epoch filter: <14 days from window start
- SFSH screening volumes: see `skyshield/screen/sfsh_volumes.py` (User Guide Table 3)

If you change any of these, update the test fixtures and the User Guide
citations in docstrings.

---

## Soft conventions

### Stack

- **Python 3.12** (managed by uv)
- **JAX** for all numerical hot paths (functional, JIT-able, vmappable)
- **Polars** for CSV I/O (faster than pandas at TraCSS scale)
- **FastAPI + uvicorn** for the backend
- **Anthropic SDK** for the agent
- **Pydantic v2** for shared types
- **pytest + hypothesis** for testing

### Code style

- `ruff` for linting (`uv run ruff check skyshield benchmarks`)
- `mypy` for type checking (non-strict; missing imports ignored)
- 4-space indent; line length 100
- Module docstrings explain *why* the module exists, not what it contains
- Function docstrings on public API; not required on private (`_foo`) helpers
- Type hints on all public function signatures (use `from __future__ import annotations`)

### Testing

- Each module has a `tests/test_<module>.py` sibling
- 80%+ unit-test coverage as a goal (not enforced)
- Use Hypothesis for property tests of pure-math functions (Pc methods,
  spatial indexing) when the property is well-defined
- Integration tests live under `tests/integration/`
- Run before commit: `uv run pytest skyshield -q`

### Performance

- Hot path = `propagate/sgp4_jax.py`, `screen/`, `pc/`. Keep these JAX-pure.
- Cold path = `agent/`, `server/`, `eval/`. Plain Python is fine.
- Benchmark targets are documented in `benchmarks/results.md`.

---

## Workflow

### Adding a feature

1. Update the relevant module(s) under `skyshield/`
2. Add tests under `skyshield/<module>/tests/`
3. Run `uv run pytest skyshield -q` — all tests must pass before commit
4. Run `uv run ruff check skyshield benchmarks` — fix or `--fix`
5. Commit with a `feat(<scope>): ...` message
6. Push

### Fixing a bug

1. Write a failing test that reproduces the bug
2. Fix the code
3. Verify the test now passes
4. Commit as `fix(<scope>): description (closes #N)` if there's an issue

### Refactoring

1. Refactor with tests green throughout
2. Commit as `refactor(<scope>): description`
3. Performance-sensitive refactors: include before/after benchmark numbers in the commit body

---

## Things to avoid

- One giant commit per work session (see Hard Rule #1)
- Inventing numbers in the agent's output (Hard Rule #3)
- Adding training-flavored ML (Hard Rule #2)
- Diverging from the TraCSS CSV schema (Hard Rule #4)
- Skipping tests because "it's small"
- Using `print()` for logging — use `rich.print` or `logging` instead
- Adding pandas (we use polars)
- Hardcoding API keys, file paths, or credentials

---

## Useful commands

```bash
# Run all tests
uv run pytest skyshield -q

# Lint + autofix
uv run ruff check --fix skyshield benchmarks

# Run a benchmark smoke
uv run python -m benchmarks.bench_propagate --smoke

# Start the backend server
uv run uvicorn skyshield.server.app:app --reload

# Talk to the agent (needs ANTHROPIC_API_KEY)
uv run skyshield agent "is the ISS at risk this week?"

# Run the full TraCSS benchmark (needs the 20.73 GB dataset)
uv run skyshield eval tracss --data-dir ./data/tracss --truth data/tracss/answer_key.csv
```

---

## References on disk

- `README.md` — public-facing project description
- `benchmarks/results.md` — current numbers (auto-generated)
- `skyshield/agent/system_prompt.md` — agent persona + must-not rules

## External references

- TraCSS dataset: https://space.commerce.gov/dataset-for-conjunction-assessment-verification/
- Auman 2025 validation methodology: https://amostech.com/TechnicalPapers/2025/ConjunctionRPO/Auman.pdf
- jaxsgp4: https://arxiv.org/abs/2603.27830
- ∂SGP4: https://arxiv.org/abs/2402.04830
- NASA CARA: https://github.com/nasa/CARA_Analysis_Tools
