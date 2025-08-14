# syntax=docker/dockerfile:1.7

# ---- builder ----
FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential python3-dev pkg-config libicu-dev libpq-dev libxml2-dev libxslt1-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./

# export locked deps to requirements.txt, then install deps into *system* Python
RUN --mount=type=cache,target=/root/.cache/uv \
    sh -lc 'uv export --format requirements-txt > requirements.txt && \
            uv pip install --python /usr/local/bin/python -r requirements.txt'

# now add your source and install the project itself (no venv)
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /usr/local/bin/python .   # installs console_script `sanitize`

# ---- final ----
FROM python:3.12-slim-bookworm AS final
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 libicu72 libxml2 libxslt1.1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -d /app -g app app
WORKDIR /app

# bring system site-packages + console scripts
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/sanitize /usr/local/bin/sanitize

ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app
CMD ["sanitize", "worker"]
