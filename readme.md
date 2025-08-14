# Aleph Sanitize Worker

This repository contains the **Sanitize Worker** service for [Aleph](https://github.com/alephdata/aleph). It runs as an additional stage in the Aleph ingestion pipeline to clean or preprocess entity data before the analysis stage.

## How It Works

When `ALEPH_INGEST_PIPELINE=sanitize:analyze` is set in `aleph.env`:

1. Aleph sends ingestion jobs to the `sanitize` queue in RabbitMQ.
2. The Sanitize Worker consumes jobs from this queue.
3. Each entity is processed by your sanitization logic.
4. The processed entity is sent to the next stage (`analyze`).

## Deployment

### Docker Compose

Add this to your Aleph `docker-compose.yml`:

```yaml
services:
  sanitize:
    build: https://github.com/Defmon3/aleph_preprocess.git
    image: aleph-sanitize:latest
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
      - rabbitmq
    env_file:
      - aleph.env
    environment:
      - FTM_STORE_URI=postgresql://aleph:aleph@postgres/aleph
      - REDIS_URL=redis://redis:6379/0
```

In `aleph.env`:

```env
ALEPH_INGEST_PIPELINE=sanitize:analyze
```

## Minimal CLI

```python
import click
from servicelayer.logs import configure_logging
from sanitize.worker import get_worker

@click.group()
def cli():
    configure_logging()

@cli.command()
@click.option("--dataset", required=False)
def worker(dataset):
    get_worker().run()

if __name__ == "__main__":
    cli()
```

## Minimal Worker

```python
from servicelayer.taskqueue import Worker, Task
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, queue_task, get_rabbitmq_channel

STAGE_SANITIZE = "sanitize"

class SanitizeWorker(Worker):
    def _dispatch_pipeline(self, task: Task, payload: dict | None = None) -> None:
        pipeline = list(task.context.get("pipeline") or [])
        next_stage = pipeline.pop(0)
        context = dict(task.context, pipeline=pipeline)

        queue_task(
            get_rabbitmq_channel(),
            get_redis(),
            task.collection_id,
            next_stage,          # e.g. "analyze"
            task.job_id,
            context,
            **(payload or {}),
        )
    def dispatch_task(self, task: Task) -> Task:
        return task

def get_worker():
    return SanitizeWorker(queues=[STAGE_SANITIZE], conn=get_redis(), version="1.0")
```

## Requirements

* Aleph core services running (Postgres, Redis, RabbitMQ)
* Docker & Docker Compose
* Configured `aleph.env`
