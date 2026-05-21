"""Generate the headline benchmark report from TraCSS run + comparison.

Writes to benchmarks/results.md so CI can render it and we can drop the
numbers directly into the Elon email at week 8.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from skyshield.eval.tracss_compare import TraCSSComparison
from skyshield.eval.tracss_runner import TraCSSRunResult


def generate_report(
    spherical_run: TraCSSRunResult,
    spherical_comparison: TraCSSComparison,
    sfsh_run: TraCSSRunResult | None = None,
    sfsh_comparison: TraCSSComparison | None = None,
    output_path: str | Path = "benchmarks/results.md",
) -> str:
    """Generate a markdown report of TraCSS evaluation results."""
    lines: list[str] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines.append("# SkyShield AI — Benchmark Results")
    lines.append("")
    lines.append(f"Auto-generated: {now}")
    lines.append("")
    lines.append("## B4 — TraCSS Spherical Screening Volume (10 km, HBR 0.5 m)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Ephemerides loaded | {spherical_run.n_ephemerides_loaded} |")
    lines.append(f"| After OD-age + useable-window filters | {spherical_run.n_ephemerides_after_filters} |")
    lines.append(f"| Candidate pairs (post-screening) | {spherical_run.n_candidate_pairs} |")
    lines.append(f"| Conjunctions emitted | {spherical_run.n_conjunctions_emitted} |")
    lines.append(f"| Truth conjunctions (answer key) | {spherical_comparison.n_truth} |")
    lines.append(f"| Matched | {spherical_comparison.n_matched} |")
    lines.append(f"| Missed | {spherical_comparison.n_missed} |")
    lines.append(f"| Extra | {spherical_comparison.n_extra} |")
    lines.append(f"| **Recall** | **{spherical_comparison.recall:.4%}** |")
    lines.append(f"| **Precision** | **{spherical_comparison.precision:.4%}** |")
    lines.append(f"| F1 | {spherical_comparison.f1:.4%} |")
    lines.append(f"| Median TCA diff (s) | {spherical_comparison.median_tca_diff_seconds:.3f} |")
    lines.append(f"| p95 TCA diff (s) | {spherical_comparison.p95_tca_diff_seconds:.3f} |")
    lines.append(f"| Median miss diff (km) | {spherical_comparison.median_miss_diff_km:.4f} |")
    lines.append(f"| p95 miss diff (km) | {spherical_comparison.p95_miss_diff_km:.4f} |")
    lines.append(f"| Wall clock (s) | {spherical_run.elapsed_seconds:.1f} |")
    lines.append("")

    if sfsh_run and sfsh_comparison:
        lines.append("## B5 — TraCSS SFSH Screening Volumes (per-object rectangular)")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Candidate pairs | {sfsh_run.n_candidate_pairs} |")
        lines.append(f"| Conjunctions emitted | {sfsh_run.n_conjunctions_emitted} |")
        lines.append(f"| Truth conjunctions | {sfsh_comparison.n_truth} |")
        lines.append(f"| Matched | {sfsh_comparison.n_matched} |")
        lines.append(f"| **Recall** | **{sfsh_comparison.recall:.4%}** |")
        lines.append(f"| **Precision** | **{sfsh_comparison.precision:.4%}** |")
        lines.append(f"| Median TCA diff (s) | {sfsh_comparison.median_tca_diff_seconds:.3f} |")
        lines.append(f"| Wall clock (s) | {sfsh_run.elapsed_seconds:.1f} |")
        lines.append("")

    lines.append("## Targets (from project plan)")
    lines.append("")
    lines.append("- B4 / B5: Near-perfect agreement with answer key (recall ≥ 99%, precision ≥ 99%)")
    lines.append("- B6: End-to-end < 30 sec on a single A100 for 30K-object catalog")
    lines.append("- B7: Maneuver opt 2× lower Δv than greedy heuristic")
    lines.append("")

    text = "\n".join(lines)
    Path(output_path).write_text(text, encoding="utf-8")
    return text
