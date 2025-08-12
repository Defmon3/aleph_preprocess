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

# Copy the dependency definitions
COPY pyproject.toml requirements.lock ./

# This `uv sync` will now install both production AND test dependencies
# because the new `requirements.lock` contains them.
RUN uv sync --no-cache --system-site-packages requirements.lock

# Copy the rest of the application source
COPY . .

# Install the local project itself
RUN uv pip install --no-cache --no-deps .


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

# Copy the virtual environment (which now has all deps)
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