# Stage 1: builder with latest uv
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev libpq-dev libxml2-dev libxslt1-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

# Stage 2: runtime
FROM python:3.12-slim-bookworm AS final
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 libicu72 libxml2 libxslt1.1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -d /app -g app app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/sanitize /usr/local/bin/sanitize

USER app
WORKDIR /app

CMD ["sanitize", "worker"]
