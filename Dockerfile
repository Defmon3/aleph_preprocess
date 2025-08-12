# Stage 1: The "builder" stage
# Installs build tools, compiles dependencies, and prepares the application
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=true

# Install build-time and run-time system dependencies
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    build-essential \
    python3-dev \
    pkg-config \
    libicu-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    # We also install run-time libs here for simplicity
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install uv, our fast installer
RUN pip3 install --no-cache-dir uv

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy only the dependency definition file first
COPY pyproject.toml .

# Install Python dependencies into the virtual environment
# This layer is cached as long as pyproject.toml doesn't change
RUN uv pip install --no-cache --system -e .

# Now copy the rest of the application source code
COPY . .


# Stage 2: The "final" production stage
# This stage is slim and only contains what's needed to run the app
FROM python:3.12-slim AS final

# Install only the required run-time system dependencies
RUN apt-get -qq update && apt-get -qq install -y --no-install-recommends \
    libpq5 \
    libicu72 \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
COPY --chown=app:app --from=builder /app /app

WORKDIR /app

# Set environment variables for the final image
ENV PATH="/opt/venv/bin:$PATH" \
    FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app

CMD ["sanitize", "worker"]