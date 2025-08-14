# ---- Stage 1: build with uv ----
FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.4.1 /uv /uvx /bin/

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev \
    libpq-dev libxml2-dev libxslt1-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Cache boundary: only re-run if deps change ----
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
# ---- End cache boundary ----

# Now copy source separately so code edits don’t bust cache
COPY . .

# ---- Stage 2: runtime ----
FROM python:3.12-slim-bookworm AS final
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 libicu72 libxml2 libxslt1.1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

WORKDIR /app
# bring the venv (contains site-packages + console scripts)
COPY --from=builder /app/.venv /app/.venv
# bring sources
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app
CMD ["sanitize", "worker"]
