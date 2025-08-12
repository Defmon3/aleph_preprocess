# Stage 1: The "builder" stage
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install `uv`.
COPY --from=ghcr.io/astral-sh/uv:0.4.1 /uv /uvx /bin/

# Install system dependencies.
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential \
    python3-dev \
    pkg-config \
    libicu-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .




# Stage 2: The "final" production stage
FROM python:3.12-slim-bookworm AS final

# Install only the run-time libraries.
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the non-root user.
RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy the installed packages from the builder's system site-packages.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy the executable script from the builder's system bin.
COPY --from=builder /usr/local/bin/sanitize /usr/local/bin/

WORKDIR /app
# Install dependencies and the project into the system Python site-packages.
RUN uv sync
ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

# The executable is on the system PATH.
CMD ["sanitize", "worker"]