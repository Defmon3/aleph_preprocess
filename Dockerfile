# ---- builder ----
FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev libpq-dev \
    libxml2-dev libxslt1-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# copy lock + manifest first for better caching
COPY pyproject.toml uv.lock ./
# ensure we don't carry any host .venv into the image
RUN rm -rf .venv
COPY . .

# system install (no venv): installs to /usr/local prefix
# per uv docs: set UV_PROJECT_ENVIRONMENT to the Python prefix (Debian images -> /usr/local)
RUN uv sync --frozen --no-dev

# ---- final ----
FROM python:3.12-slim-bookworm AS final
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 libicu72 libxml2 libxslt1.1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# bring site-packages + console scripts installed system-wide by the builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/sanitize /usr/local/bin/sanitize

ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app
CMD ["sanitize","worker"]
