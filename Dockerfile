# Stage 1: builder
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.4.1 /uv /uvx /bin/

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev \
    libpq-dev libxml2-dev libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .

# Install into system site-packages in builder
RUN uv sync --frozen


# Stage 2: final
FROM python:3.12-slim-bookworm AS final

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 libicu72 ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy installed packages and entrypoints from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/sanitize /usr/local/bin/sanitize

WORKDIR /app
COPY . .

ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

CMD ["sanitize", "worker"]
