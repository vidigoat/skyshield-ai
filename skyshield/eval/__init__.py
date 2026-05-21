"""TraCSS evaluation harness.

The pipeline that takes the official Aerospace IVV ephemeris dataset, runs
SkyShield's screening + Pc pipeline, produces CDM-format CSV output, and
compares against the official answer keys (spherical + SFSH).
"""

from skyshield.eval.tracss_compare import (
    TraCSSComparison,
    compare_against_answer_key,
)
from skyshield.eval.tracss_runner import (
    TraCSSRunResult,
    run_tracss_screening,
)

__all__ = [
    "TraCSSComparison",
    "TraCSSRunResult",
    "compare_against_answer_key",
    "run_tracss_screening",
]
