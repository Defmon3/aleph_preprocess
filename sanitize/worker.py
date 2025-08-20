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

from ftmstore import get_dataset
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, queue_task, get_rabbitmq_channel

from sanitize.phone import process_entity_phones

log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3"


class SanitizeWorker(Worker):
    """
    Worker for the ``sanitize`` stage of an Aleph ingestion pipeline.

    Delegates phone number extraction and mention creation to ``sanitize.phone``.
    """

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

    def dispatch_task(self, task: Task) -> Task:
        log.info(
            f"[Sanitize:dispatch_task] Task started "
            f"[collection:{task.collection_id} op:{task.operation} "
            f"task_id:{task.task_id} priority:{task.priority}]"
        )

        try:
            db = get_dataset(task.collection_id, STAGE_SANITIZE)
        except Exception as e:
            log.error(f"Failed to open dataset for collection {task.collection_id}: {e}")
            self.dispatch_pipeline(task, payload=task.payload or {})
            return task
        log.debug(f"Opened sanitize-stage dataset for collection {task.collection_id}")

        writer = db.bulk()
        processed = 0

        for entity in db.partials():
            self.sanitize_entity(writer, entity)
            processed += 1

        writer.flush()
        log.debug(f"Flushed {processed} entities for collection {task.collection_id}")

        self.dispatch_pipeline(task, payload=task.payload or {})
        log.info(f"[Sanitize:dispatch_task] Completed task {task.task_id} with {processed} entities")

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
