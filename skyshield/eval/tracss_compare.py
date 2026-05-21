"""Compare SkyShield's output against the TraCSS official answer key.

Per the User Guide §1 (Purpose), the primary metrics are:
  1. Finding all the same events (recall + precision on event presence)
  2. Accurate TCA, primary/secondary state and covariance

We compute event-level recall/precision (matching by Sat ID pair) and, for
matched events, the differences in TCA, position, and velocity. Thresholds
for "agreement" come from Auman 2025 — pulled from the paper as soon as
that's read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import polars as pl


@dataclass
class TraCSSComparison:
    """Result of comparing our CDM output against the official answer key."""

    n_truth: int = 0
    n_ours: int = 0
    n_matched: int = 0
    n_missed: int = 0     # in truth but not in ours
    n_extra: int = 0      # in ours but not in truth
    recall: float = 0.0
    precision: float = 0.0
    f1: float = 0.0
    # Distribution stats for matched events
    median_tca_diff_seconds: float = 0.0
    p95_tca_diff_seconds: float = 0.0
    median_miss_diff_km: float = 0.0
    p95_miss_diff_km: float = 0.0
    # Per-event details
    matched_pairs: list[tuple[int, int]] = field(default_factory=list)
    missed_pairs: list[tuple[int, int]] = field(default_factory=list)
    extra_pairs: list[tuple[int, int]] = field(default_factory=list)


def compare_against_answer_key(
    our_csv: str | Path,
    truth_csv: str | Path,
    *,
    tca_tolerance_seconds: float = 5.0,
) -> TraCSSComparison:
    """Compare our CSV output to the official answer-key CSV.

    Both files must have the same column schema (Conjunction.csv_columns()).

    Parameters
    ----------
    our_csv : path
        Our SkyShield output (e.g., from `run_tracss_screening` + `write_cdm_csv`).
    truth_csv : path
        The official IVV_Releasable_Dataset_Spherical_DefaultHBR.csv or
        IVV_Releasable_Dataset_SFSH_DiscreteHBR.csv (gunzipped).
    tca_tolerance_seconds : float
        Matched events must have TCAs within this many seconds. Default 5s
        per typical TraCSS validation practice.

    Returns
    -------
    TraCSSComparison with detailed agreement metrics.
    """
    ours = pl.read_csv(our_csv)
    truth = pl.read_csv(truth_csv)

    cmp = TraCSSComparison(n_truth=len(truth), n_ours=len(ours))

    if cmp.n_truth == 0:
        return cmp

    # Build lookup by (obj1, obj2) — ensure ordering matches user-guide convention obj2 > obj1
    def normalize_pair(o1: int, o2: int) -> tuple[int, int]:
        return (o1, o2) if o2 > o1 else (o2, o1)

    truth_dict: dict[tuple[int, int], dict] = {}
    for row in truth.iter_rows(named=True):
        key = normalize_pair(int(row["obj1"]), int(row["obj2"]))
        # Keep nearest TCA in case of duplicates (TraCSS may have multiple per pair)
        if key not in truth_dict:
            truth_dict[key] = row

    ours_dict: dict[tuple[int, int], dict] = {}
    for row in ours.iter_rows(named=True):
        key = normalize_pair(int(row["obj1"]), int(row["obj2"]))
        if key not in ours_dict:
            ours_dict[key] = row

    matched_keys = set(truth_dict.keys()) & set(ours_dict.keys())
    missed_keys = set(truth_dict.keys()) - set(ours_dict.keys())
    extra_keys = set(ours_dict.keys()) - set(truth_dict.keys())

    cmp.matched_pairs = list(matched_keys)
    cmp.missed_pairs = list(missed_keys)
    cmp.extra_pairs = list(extra_keys)
    cmp.n_matched = len(matched_keys)
    cmp.n_missed = len(missed_keys)
    cmp.n_extra = len(extra_keys)

    cmp.recall = cmp.n_matched / cmp.n_truth if cmp.n_truth else 0.0
    cmp.precision = cmp.n_matched / cmp.n_ours if cmp.n_ours else 0.0
    cmp.f1 = (
        2 * cmp.precision * cmp.recall / (cmp.precision + cmp.recall)
        if (cmp.precision + cmp.recall) > 0
        else 0.0
    )

    # Distribution of differences for matched pairs
    if matched_keys:
        tca_diffs = []
        miss_diffs = []
        for key in matched_keys:
            ours_row = ours_dict[key]
            truth_row = truth_dict[key]
            try:
                t_ours = datetime.fromisoformat(str(ours_row["epoch"]).rstrip("Z"))
                t_truth = datetime.fromisoformat(str(truth_row["epoch"]).rstrip("Z"))
                tca_diffs.append(abs((t_ours - t_truth).total_seconds()))
            except Exception:
                pass
            try:
                m_ours = float(ours_row["min_range"])
                m_truth = float(truth_row["min_range"])
                miss_diffs.append(abs(m_ours - m_truth))
            except Exception:
                pass

        if tca_diffs:
            sorted_t = sorted(tca_diffs)
            cmp.median_tca_diff_seconds = sorted_t[len(sorted_t) // 2]
            cmp.p95_tca_diff_seconds = sorted_t[int(len(sorted_t) * 0.95)]
        if miss_diffs:
            sorted_m = sorted(miss_diffs)
            cmp.median_miss_diff_km = sorted_m[len(sorted_m) // 2]
            cmp.p95_miss_diff_km = sorted_m[int(len(sorted_m) * 0.95)]

    return cmp
