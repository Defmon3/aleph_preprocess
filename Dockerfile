# ---- Stage 1: builder with uv ----
FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# latest uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev \
    libpq-dev libxml2-dev libxslt1-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1) Copy dep files and install deps only (cached unless these change)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# 2) Copy source and install your package into venv
# docker compose build --build-arg CACHE_BUST=$(date +%s) sanitize && docker compose up -d
ARG CACHE_BUST=1
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

# ---- Stage 2: runtime ----
FROM python:3.12-slim-bookworm AS final
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get -qq update && apt-get install -y --no-install-recommends \
    libpq5 libicu72 libxml2 libxslt1.1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

WORKDIR /app

# bring venv and source
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app
CMD ["sanitize", "worker"]
