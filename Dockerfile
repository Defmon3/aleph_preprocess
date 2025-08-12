# Stage 1: The "builder" stage
# Use the specific base image recommended by the docs
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- 1. Install `uv` using the official recommended method ---
# Pinning the version for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:latest/uv /uvx /bin/

# Install build-time and run-time system dependencies
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
 && apt-get -qq -y autoremove build-essential python3-dev pkg-config libicu-dev libpq-dev libxml2-dev libxslt1-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the virtual environment using uv
RUN uv venv /opt/venv

# Set the work directory and copy the project files
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .




# Stage 2: The "final" production stage
FROM python:3.12-slim-bookworm AS final

# Install only the required run-time system dependencies
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install `uv` again in the final stage to use `uv run`
COPY --from=ghcr.io/astral-sh/uv:0.4.1 /uv /uvx /bin/

# Create the non-root user
RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy the fully populated virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Change ownership to fix the runtime permission error
RUN chown -R app:app /opt/venv

WORKDIR /app
RUN uv sync --locked
# Set environment variables for the final image
ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

# --- 3. Run the application using the recommended `uv run` ---
# This executes the command within the context of the virtual environment.
CMD ["uv", "run", "--venv", "/opt/venv", "sanitize", "worker"]