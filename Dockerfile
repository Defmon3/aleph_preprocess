FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    locales libxml2 libxslt1.1 \
 && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8 \
    PYTHONIOENCODING=UTF-8

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN pip install -q uv && uv sync --frozen --no-dev
COPY . .
RUN chown -R app:app /app
USER app

ENV REDIS_URL=redis://redis:6379/0 \
    STAGE_NAME=sanitize_html

CMD ["sanitize","worker"]