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

from followthemoney import model
from ftmstore import get_dataset, get_dataset
from ingestors import __version__, settings
from ingestors.analysis import Analyzer
from ingestors.manager import Manager
from servicelayer.cache import get_redis
from servicelayer.taskqueue import (
    Worker,
    Task,
    get_rabbitmq_channel,
    queue_task,
)

from sanitize.phone import process_entity_phones, process_text_mentions

log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3"


class SanitizeWorker(Worker):
    """
    Worker for the ``sanitize`` stage of an Aleph ingestion pipeline.

    Delegates phone number extraction and mention creation to ``sanitize.phone``.
    """



    def dispatch_task(self, task: Task) -> Task:
        log.info("[sanitize.dispatch_task] enter task_id=%s collection_id=%s", task.task_id, task.collection_id)
        name = task.context.get("ftmstore", task.collection_id)
        log.debug("[sanitize.dispatch_task] dataset=%s", name)
        try:
            dst = get_dataset(name, STAGE_SANITIZE)
            writer = dst.bulk()
        except Exception as e:
            log.exception("[sanitize.dispatch_task] dataset_open_error: %s", e)
            self.dispatch_pipeline(task, payload=task.payload or {})
            log.info("[sanitize.dispatch_task] exit_early")
            return task

        processed = 0
        payload = task.payload

        try:
            texts = []
            if isinstance(payload, str):
                texts = [payload]
            elif isinstance(payload, dict):
                if isinstance(payload.get("text"), str):
                    texts.append(payload["text"])
                if isinstance(payload.get("html"), str):
                    texts.append(payload["html"])
                if isinstance(payload.get("content"), str):
                    texts.append(payload["content"])
                if isinstance(payload.get("body"), str):
                    texts.append(payload["body"])
                if isinstance(payload.get("texts"), list):
                    texts.extend([t for t in payload["texts"] if isinstance(t, str)])
            else:
                log.warning("[sanitize.dispatch_task] unsupported_payload_type=%s", type(payload).__name__)

            log.info("[sanitize.dispatch_task] text_chunks=%d", len(texts))

            link_entity_id = payload.get("id") if isinstance(payload, dict) else None
            link_document_id = payload.get("document") if isinstance(payload, dict) else None

            for idx, t in enumerate(texts, start=1):
                log.debug("[sanitize.dispatch_task] processing_chunk=%d len=%d", idx, len(t))
                processed += process_text_mentions(writer, t, link_entity_id=link_entity_id, link_document_id=link_document_id)

            writer.flush()
            log.debug("[sanitize.dispatch_task] writer_flushed")
        except Exception as e:
            log.exception("[sanitize.dispatch_task] processing_error: %s", e)

        log.info("[sanitize.dispatch_task] processed_mentions=%d", processed)

        try:
            self.dispatch_pipeline(task, payload=task.payload or {})
        except Exception as e:
            log.exception("[sanitize.dispatch_task] pipeline_error: %s", e)

        log.info("[sanitize.dispatch_task] exit task_id=%s", task.task_id)
        return task


    def sanitize_entity(self, writer, entity) -> None:
        process_entity_phones(writer, entity)

    def dispatch_pipeline(self, task: Task, payload: dict | None = None) -> None:
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

def get_worker(num_threads=None):
    log.info(f"SanitizeWorker active on stage: {STAGE_SANITIZE}")
    return SanitizeWorker(
        queues=[STAGE_SANITIZE],
        conn=get_redis(),
        version="1.0",
        num_threads=num_threads,
        prefetch_count_mapping={STAGE_SANITIZE: 1},
    )
