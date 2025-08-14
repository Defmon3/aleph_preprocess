#!/usr/bin/env python3
# /// script
# requires-python = "==3.12.9"
# dependencies = []
# ///

"""
SPDX-License-Identifier: LicenseRef-NonCommercial-Only
© 2025 github.com/defmon3 — Non-commercial use only. Commercial use requires permission.
Format docstrings according to PEP 287
File: worker.py

"""

import logging

from bs4 import BeautifulSoup
from followthemoney import model
from followthemoney.types import registry
from ftmstore import get_dataset
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, queue_task, get_rabbitmq_channel

import re
log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3" # Version of ingestors package

def _sanitize_html(text: str) -> str:
    """
    Minimal HTML → text suitable for Aleph indexing.

    :param text: Raw HTML
    :return: Collapsed plain text
    """
    log.debug(f"Sanitizing HTML: {text[:50]}...")  # Log first 100 chars for brevity
    soup = BeautifulSoup(text or "", "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    container = soup.body or soup
    raw = container.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", raw).strip()


class SanitizeWorker(Worker):
    def _sanitize_entity(self, writer, entity) -> None:
        if not entity.schema.is_a("Analyzable"):
            log.debug(f"Skipping non-analyzable entity: {entity}")
            return
        texts = entity.get_type_values(registry.text)
        if not texts:
            log.debug(f"No text fields to sanitize for entity: {entity}")
            return
        log.debug(f"Sanitizing {entity}")
        clean = " ".join(_sanitize_html(t) for t in texts if t)
        if not clean:
            log.debug(f"No valid text found for entity: {entity}")
            return
        partial = model.make_entity(entity.schema)
        partial.id = entity.id
        partial.add("translatedText", clean, quiet=True)
        writer.put(partial)

    def _dispatch_pipeline(self, task: Task, payload: dict | None = None) -> None:
        """Forward to next stage in the pipeline if any."""
        pipeline = list(task.context.get("pipeline") or [])
        if not pipeline:
            log.debug(f"No pipeline stages left for task: {task.task_id}")
            return
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
        log.info(
            f"Task [collection:{task.collection_id}]: "
            f"op:{task.operation} task_id:{task.task_id} priority:{task.priority} (started)"
        )

        db = get_dataset(task.collection_id, STAGE_SANITIZE)
        writer = db.bulk()
        for entity in db.partials():
            self._sanitize_entity(writer, entity)
        writer.flush()
        self._dispatch_pipeline(task, payload={})

        return task


def get_worker(num_threads=None):
    log.info(f"SanitizeWorker active on stage: {STAGE_SANITIZE}")
    return SanitizeWorker(
        queues=[STAGE_SANITIZE],
        conn=get_redis(),
        version="1.0",
        num_threads=num_threads,
        prefetch_count_mapping={STAGE_SANITIZE: 1},
    )