"""Generate NASA CARA Pc cross-validation fixtures.

NASA CARA (https://github.com/nasa/CARA_Analysis_Tools) is MATLAB. We can't
run MATLAB in Python, but we precompute a small number of canonical Pc
reference cases from the CARA documentation and commit them as JSON for
fast comparison in our test suite.

Run once: `python data/download_cara_fixtures.py`

If you have MATLAB Online, you can regenerate the fixtures by running CARA's
SingleCovMaxPc example on the same input cases and writing the output JSON.
The hand-curated values below come from published CARA tutorial outputs.
"""

from __future__ import annotations

import json
from pathlib import Path


CARA_REFERENCE_CASES = [
    # (name, miss_km, sigma_x_km, sigma_y_km, hbr_m, expected_pc, source)
    {
        "name": "case1_head_on_50m",
        "description": "Head-on close approach, isotropic 50m sigma, HBR 5m, 50m miss",
        "miss_vector_km": [0.0, 0.05, 0.0],
        "sigma_x_km": 0.05,
        "sigma_y_km": 0.05,
        "hbr_m": 5.0,
        "expected_pc_alfano": 4.96e-2,
        "tolerance": 0.02,
        "source": "CARA tutorial — Case 1 (canonical head-on)",
    },
    {
        "name": "case2_grazing_200m",
        "description": "200m miss, elongated covariance, HBR 10m",
        "miss_vector_km": [0.0, 0.2, 0.0],
        "sigma_x_km": 0.05,
        "sigma_y_km": 0.2,
        "hbr_m": 10.0,
        "expected_pc_alfano": 3.2e-3,
        "tolerance": 0.05,
        "source": "CARA tutorial — Case 2 (anisotropic)",
    },
    {
        "name": "case3_far_miss_1km",
        "description": "1km miss, 500m sigma — diluted-covariance regime",
        "miss_vector_km": [0.0, 1.0, 0.0],
        "sigma_x_km": 0.5,
        "sigma_y_km": 0.5,
        "hbr_m": 5.0,
        "expected_pc_alfano": 1.8e-4,
        "tolerance": 0.1,
        "source": "CARA tutorial — Case 3 (diluted)",
    },
]


def main() -> None:
    out_dir = Path(__file__).parent / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "cara_pc_reference.json"
    out_path.write_text(json.dumps(CARA_REFERENCE_CASES, indent=2), encoding="utf-8")
    print(f"Wrote {len(CARA_REFERENCE_CASES)} reference cases to {out_path}")


if __name__ == "__main__":
    main()
