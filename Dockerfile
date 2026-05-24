FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY skyshield/ ./skyshield/

RUN pip install --no-cache-dir -e . && pip cache purge

# data/ copied last so future data-only changes reuse the pip install layer.
COPY data/ ./data/

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn skyshield.server.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
