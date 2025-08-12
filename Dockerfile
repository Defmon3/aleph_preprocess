# Stage 1: The "builder" stage
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build tools, run-time libs, and uv
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential \
    python3-dev \
    pkg-config \
    libicu-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libpq5 \
    libicu72 \
    ca-certificates \
 && pip3 install --no-cache-dir uv \
 && apt-get -qq -y autoremove build-essential python3-dev pkg-config libicu-dev libpq-dev libxml2-dev libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the virtual environment using uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the project and lock files first to leverage Docker's cache
COPY pyproject.toml uv.lock ./

# Copy the rest of the application source code
COPY . .

# --- THE CORRECT COMMAND ---
# `uv pip install --locked` automatically detects and uses `uv.lock`.
# This single command installs both the project and its locked dependencies.
RUN uv pip install --no-cache --locked .


# Stage 2: The "final" production stage
FROM python:3.12-slim AS final

# Install only the required run-time system dependencies
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the non-root user
RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Change ownership to fix the runtime permission error
RUN chown -R app:app /opt/venv

WORKDIR /app

# Set environment variables for the final image
ENV PATH="/opt/venv/bin:$PATH" \
    FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

CMD ["sanitize", "worker"]