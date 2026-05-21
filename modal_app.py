"""Modal deployment for the SkyShield AI backend.

Deploy with:
    uv run modal deploy modal_app.py

This serves the FastAPI app behind a Modal-managed HTTPS endpoint. The
backend uses an A100 GPU for the screening hot path when one is allocated
(falls back to CPU otherwise — the vectorized NumPy path runs on CPU too).

After deployment, set the public URL in the frontend's NEXT_PUBLIC_API_URL.

This file is OPTIONAL — the FastAPI app also runs locally with
    uv run uvicorn skyshield.server.app:app --reload
"""

from __future__ import annotations

import modal

# Define the Modal app
app = modal.App("skyshield-ai")

# Image with our package installed
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "jax>=0.4.30",
        "jaxlib>=0.4.30",
        "numpy>=2.0.0",
        "scipy>=1.14.0",
        "polars>=1.0.0",
        "pydantic>=2.8.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "websockets>=13.0",
        "anthropic>=0.39.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "tqdm>=4.66.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.27.0",
    )
    .add_local_python_source("skyshield")
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic")],  # store ANTHROPIC_API_KEY here
    timeout=300,
    keep_warm=1,  # keep one container warm for low cold-start
)
@modal.asgi_app()
def fastapi_app():
    """Expose the SkyShield FastAPI app behind Modal."""
    from skyshield.server.app import app as fastapi_app
    return fastapi_app


# Optional: GPU-accelerated batch screening function (callable as a webhook)
@app.function(
    image=image,
    gpu="A10G",   # cheap GPU for development; switch to A100 for production
    timeout=900,
    memory=16384,
)
def gpu_screen(data_dir: str, mode: str = "spherical") -> dict:
    """Run the TraCSS screening pipeline on a directory of OCMs."""
    from skyshield.eval.tracss_runner import run_tracss_screening, write_cdm_csv
    result = run_tracss_screening(
        data_dir,
        pattern="*.ocm",
        mode=mode,  # type: ignore[arg-type]
        screening_radius_km=100.0,
        time_step_seconds=60.0,
    )
    return {
        "n_loaded": result.n_ephemerides_loaded,
        "n_after_filters": result.n_ephemerides_after_filters,
        "n_conjunctions": result.n_conjunctions_emitted,
        "elapsed_seconds": result.elapsed_seconds,
    }
