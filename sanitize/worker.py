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
import re

from bs4 import BeautifulSoup
from followthemoney import model
from followthemoney.types import registry
from ftmstore import get_dataset
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, queue_task, get_rabbitmq_channel

log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3"


def _sanitize_html(text: str) -> str:
    """
    Convert minimal HTML to collapsed plain text for indexing.

    :param text: Raw or partially structured HTML content.
    :returns: Plain text with scripts/styles removed and whitespace collapsed.
    :raises ValueError: If ``text`` is None or empty after stripping.
    :notes: Uses ``lxml`` parser via BeautifulSoup for robust tag handling.
    """
    preview = (text or "")[:50]
    log.debug(f"Sanitizing HTML: {preview}...")
    soup = BeautifulSoup(text or "", "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    container = soup.body or soup
    raw = container.get_text(separator=" ", strip=True)
    result = re.sub(r"\s+", " ", raw).strip()
    if not result:
        raise ValueError("No textual content after sanitization")
    return result


class SanitizeWorker(Worker):
    """
    Worker for the ``sanitize`` stage of an Aleph ingestion pipeline.

    The worker reads partial entities for a collection, extracts text fields
    from analyzable entities, sanitizes minimal HTML into plain text, writes a
    partial update under ``translatedText``, and optionally dispatches the next
    pipeline stage.
    """

    def _sanitize_entity(self, writer, entity) -> None:
        """
        Sanitize all text fields of an entity and write a partial update.

        :param writer: Bulk writer from ``ftmstore`` used to persist partials.
        :param entity: FollowTheMoney entity to be processed.
        :returns: ``None``. Writes a partial entity when sanitized text exists.
        :notes:
            - Only entities whose schema ``is_a("Analyzable")`` are processed.
            - Aggregates all text-type properties, sanitizes, and stores the
              result in ``translatedText``.
        """
        if not entity.schema.is_a("Analyzable"):
            log.debug(f"Skipping non-analyzable entity: {entity}")
            return
        texts = entity.get_type_values(registry.text)
        if not texts:
            log.debug(f"No text fields to sanitize for entity: {entity}")
            return
        log.debug(f"Sanitizing {entity}")
        clean_parts = []
        for t in texts:
            if not t:
                continue
            try:
                clean_parts.append(_sanitize_html(t))
            except ValueError:
                continue
        clean = " ".join(clean_parts).strip()
        if not clean:
            log.debug(f"No valid text found for entity: {entity}")
            return
        partial = model.make_entity(entity.schema)
        partial.id = entity.id
        partial.add("translatedText", clean, quiet=True)
        writer.put(partial)

    def _dispatch_pipeline(self, task: Task, payload: dict | None = None) -> None:
        """
        Forward the task to the next pipeline stage, if configured.

        :param task: The current task containing context and pipeline info.
        :param payload: Optional payload to merge into the queued task kwargs.
        :returns: ``None``. Queues the next stage when available.
        :notes:
            - The next stage is taken from ``task.context['pipeline']``.
            - Preserves remaining pipeline by popping the next stage and
              re-enqueuing with updated context.
        """
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
            next_stage,
            task.job_id,
            context,
            **(payload or {}),
        )

    def dispatch_task(self, task: Task) -> Task:
        """
        Process a sanitize-stage task: read partials, sanitize, write, dispatch.

        :param task: Incoming task with ``collection_id``, ``operation``,
                     ``priority``, and pipeline context.
        :returns: The same ``task`` after processing and optional dispatch.
        :workflow:
            1. Open dataset stage ``sanitize``.
            2. Iterate partial entities and sanitize where applicable.
            3. Flush bulk writer.
            4. Dispatch next stage if present.
        """
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
    """
    Construct and return a configured ``SanitizeWorker``.

    :param num_threads: Optional worker thread count for task consumption.
    :returns: ``SanitizeWorker`` subscribed to the ``sanitize`` queue.
    :notes:
        - ``prefetch_count_mapping`` is set to 1 for deterministic processing.
        - ``version`` is independent of ``__version__`` from the ingestors pkg.
    """
    log.info(f"SanitizeWorker active on stage: {STAGE_SANITIZE}")
    return SanitizeWorker(
        queues=[STAGE_SANITIZE],
        conn=get_redis(),
        version="1.0",
        num_threads=num_threads,
        prefetch_count_mapping={STAGE_SANITIZE: 1},
    )
