# Stage 1: The "builder" stage
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install `uv` using the official recommended method.
COPY --from=ghcr.io/astral-sh/uv:0.4.1 /uv /uvx /bin/

# Install system dependencies needed for building Python packages.
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

# Create the virtual environment.
RUN uv venv /opt/venv

WORKDIR /app

# Copy only the files needed for dependency installation first.
COPY pyproject.toml uv.lock ./

# --- STEP 1: Sync dependencies from the lock file ---
# This follows the pattern you provided.
RUN /opt/venv/bin/uv sync --no-cache --locked

# Copy the rest of the application source code.
COPY . .

# --- STEP 2: Install the local project itself ---
# --no-deps is crucial because `sync` already installed everything.
RUN /opt/venv/bin/uv pip install --no-cache --no-deps .


# Stage 2: The "final" production stage
FROM python:3.12-slim-bookworm AS final

# Install only the run-time libraries our application needs.
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the non-root user.
RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy the entire, self-contained virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Give our non-root user ownership of the application.
RUN chown -R app:app /opt/venv

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

CMD ["sanitize", "worker"]