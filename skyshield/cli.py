"""Command-line interface for SkyShield AI.

After `uv sync`, run:
    uv run skyshield --help
    uv run skyshield agent "is the ISS at risk this week?"
    uv run skyshield screen --sat-id 25544 --days 7
    uv run skyshield eval tracss --data-dir ./data/tracss
"""

from __future__ import annotations

import json

import click

from skyshield import __version__


@click.group()
@click.version_option(__version__)
def main() -> None:
    """SkyShield AI: open AI agent for satellite safety."""


@main.command()
@click.argument("message", type=str)
@click.option("--model", default=None, help="Override Claude model")
def agent(message: str, model: str | None) -> None:
    """Ask the SkyShield AI agent a question."""
    from skyshield.agent.agent import SkyShieldAgent

    a = SkyShieldAgent(model=model or "claude-sonnet-4-6")
    resp = a.ask(message)
    click.echo(resp.text)
    if resp.tool_events:
        click.echo()
        click.echo(f"[{len(resp.tool_events)} tool call(s)]")
        for ev in resp.tool_events:
            click.echo(f"  - {ev.name} ({ev.elapsed_ms:.0f} ms)")


@main.command()
@click.option("--sat-id", required=True, type=int)
@click.option("--days", default=7.0, type=float)
@click.option("--radius-km", default=10.0, type=float)
def screen(sat_id: int, days: float, radius_km: float) -> None:
    """Screen a single satellite against the catalog for close approaches."""
    from skyshield.agent.tools import dispatch_tool_call

    result = dispatch_tool_call(
        "screen_against_catalog",
        {"sat_id": sat_id, "days": days, "screening_volume_km": radius_km},
    )
    click.echo(json.dumps(result, indent=2))


@main.group()
def eval() -> None:
    """Run evaluations (TraCSS benchmark, etc.)."""


@eval.command("tracss")
@click.option("--data-dir", required=True, type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["spherical", "sfsh"]), default="spherical")
@click.option("--output", default="tracss_output.csv", type=click.Path())
@click.option("--truth", default=None, type=click.Path(exists=True),
              help="Path to the official answer-key CSV (gunzipped)")
def eval_tracss(data_dir: str, mode: str, output: str, truth: str | None) -> None:
    """Run the TraCSS conjunction-screening benchmark."""
    from skyshield.eval.tracss_runner import run_tracss_screening, write_cdm_csv

    click.echo(f"Running TraCSS screening on {data_dir} ({mode} mode)...")
    result = run_tracss_screening(data_dir, mode=mode)  # type: ignore[arg-type]
    click.echo(f"Loaded {result.n_ephemerides_loaded} ephemerides")
    click.echo(f"After filters: {result.n_ephemerides_after_filters}")
    click.echo(f"Candidate pairs: {result.n_candidate_pairs}")
    click.echo(f"Conjunctions emitted: {result.n_conjunctions_emitted}")
    click.echo(f"Elapsed: {result.elapsed_seconds:.1f} s")

    write_cdm_csv(result.conjunctions, output)
    click.echo(f"Wrote {output}")

    if truth:
        from skyshield.eval.tracss_compare import compare_against_answer_key
        cmp = compare_against_answer_key(output, truth)
        click.echo("")
        click.echo("Comparison vs answer key:")
        click.echo(f"  Recall:    {cmp.recall:.2%}")
        click.echo(f"  Precision: {cmp.precision:.2%}")
        click.echo(f"  F1:        {cmp.f1:.2%}")
        click.echo(f"  Median TCA diff: {cmp.median_tca_diff_seconds:.2f} s")


@main.command()
def serve() -> None:
    """Start the FastAPI backend server."""
    import uvicorn

    uvicorn.run("skyshield.server.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
