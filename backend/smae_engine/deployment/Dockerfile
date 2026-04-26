# ==============================================================================
# Stage 1: builder — install dependencies into an isolated virtual environment
# Build context: backend/ (parent of smae_engine/)
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Copy dependency manifests first to maximise layer-cache hits
COPY pyproject.toml .
COPY uv.lock .

# Install only the smae dependency group into /app/.venv
# --no-dev excludes pytest/dev tools; --no-install-project skips editable install
RUN uv sync --group smae --no-dev --no-install-project

# ==============================================================================
# Stage 2: runtime — lean image with only the venv and application code
# ==============================================================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy entire backend directory so all modules are importable under /app/backend/
COPY . /app/backend/

# Make /app a Python package root so `import smae_engine` resolves correctly
RUN touch /app/__init__.py

# Activate the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Allow absolute imports from /app (e.g., smae_engine.source_code.main)
ENV PYTHONPATH="/app"

EXPOSE 8080

CMD ["python", "-m", "functions_framework", "--target=smae_handler", "--source=/app/backend/smae_engine/source_code/main.py", "--port=8080"]
