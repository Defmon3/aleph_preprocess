FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LANG=en_US.UTF-8

RUN apt-get -qq update && apt-get -qq install -y \
    build-essential locales ca-certificates \
    python3-dev python3-icu libpq-dev \
 && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd -g 1000 -r app && useradd -m -u 1000 -s /bin/false -g app app

COPY . /sanitize
WORKDIR /sanitize
RUN pip install --no-cache-dir -U pip setuptools wheel \
 && pip install --no-cache-dir -e .

ENV FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph \
    REDIS_URL=redis://redis:6379/0

USER app
CMD sanitize worker
