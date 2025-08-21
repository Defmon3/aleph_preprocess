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

from sanitize.phone import process_entity_phones

log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3"


class SanitizeWorker(Worker):
    """
    Worker for the ``sanitize`` stage of an Aleph ingestion pipeline.

    Delegates phone number extraction and mention creation to ``sanitize.phone``.
    """


    def _ingest(self, ftmstore_dataset, task: Task):
        log.info("[sanitize._ingest] enter task_id=%s collection_id=%s", task.task_id, task.collection_id)
        log.debug("[sanitize._ingest] ftmstore_dataset=%s", getattr(ftmstore_dataset, "name", str(ftmstore_dataset)))
        entity = model.get_proxy(task.payload)
        log.debug("[sanitize._ingest] proxy schema=%s id=%s", getattr(entity, "schema", None), getattr(entity, "id", None))
        manager = Manager(ftmstore_dataset, task)
        log.debug("[sanitize._ingest] manager created")
        try:
            log.info("[sanitize._ingest] ingest_entity start")
            manager.ingest_entity(entity)
            log.info("[sanitize._ingest] ingest_entity done")
        except Exception as e:
            log.exception("[sanitize._ingest] ingest_entity error: %s", e)
            raise
        finally:
            try:
                manager.close()
                log.debug("[sanitize._ingest] manager closed")
            except Exception as e:
                log.exception("[sanitize._ingest] manager close error: %s", e)
        emitted = list(manager.emitted)
        log.info("[sanitize._ingest] exit emitted_count=%d emitted=%s", len(emitted), emitted)
        return emitted

    def _analyze(self, analyze_db, ingest_db, task: Task):
        log.info("[sanitize._analyze] enter task_id=%s collection_id=%s", task.task_id, task.collection_id)
        log.debug("[sanitize._analyze] analyze_db=%s ingest_db=%s", getattr(analyze_db, "name", str(analyze_db)), getattr(ingest_db, "name", str(ingest_db)))
        analyzer = None
        entity_ids = set()
        total_seen = 0
        try:
            for e in ingest_db.partials():
                total_seen += 1
                log.debug("[sanitize._analyze] seen ingest partial entity_id=%s schema=%s", getattr(e, "id", None), getattr(getattr(e, "schema", None), "name", None))
                if analyzer is None or analyzer.entity.id != e.id:
                    if analyzer is not None:
                        flushed_before = analyzer.flush()
                        entity_ids.update(flushed_before)
                        log.debug("[sanitize._analyze] flushed previous analyzer results_count=%d", len(flushed_before))
                    analyzer = Analyzer(analyze_db, e, task.context or {})
                    log.debug("[sanitize._analyze] new Analyzer created for entity_id=%s", getattr(e, "id", None))
                analyzer.feed(e)
                log.debug("[sanitize._analyze] fed chunk for entity_id=%s", getattr(e, "id", None))
            if analyzer is not None:
                flushed_after = analyzer.flush()
                entity_ids.update(flushed_after)
                log.debug("[sanitize._analyze] final flush results_count=%d", len(flushed_after))
        except Exception as e:
            log.exception("[sanitize._analyze] error: %s", e)
            raise
        log.info("[sanitize._analyze] exit seen=%d updated_entity_ids_count=%d", total_seen, len(entity_ids))
        return list(entity_ids)

    def dispatch_task(self, task: Task) -> Task:
        log.info("[sanitize.dispatch_task] enter task_id=%s collection_id=%s op=%s priority=%s", task.task_id, task.collection_id, task.operation, task.priority)
        name = task.context.get("ftmstore", task.collection_id)
        log.debug("[sanitize.dispatch_task] resolved_dataset_name=%s", name)
        try:
            analyze_db = get_dataset(name, "analyze")
            log.debug("[sanitize.dispatch_task] opened analyze_db=%s", getattr(analyze_db, "name", str(analyze_db)))
            ingest_db = get_dataset(name, settings.STAGE_INGEST)
            log.debug("[sanitize.dispatch_task] opened ingest_db=%s", getattr(ingest_db, "name", str(ingest_db)))
            dst = get_dataset(name, STAGE_SANITIZE)
            log.debug("[sanitize.dispatch_task] opened dst=%s", getattr(dst, "name", str(dst)))
        except Exception as e:
            log.exception("[sanitize.dispatch_task] dataset open error: %s", e)
            self.dispatch_pipeline(task, payload=task.payload or {})
            log.info("[sanitize.dispatch_task] exit early due to dataset open error")
            return task
        writer = dst.bulk()
        log.debug("[sanitize.dispatch_task] writer created for dst")
        processed = 0
        had_partials = False
        try:
            for entity in analyze_db.partials():
                had_partials = True
                log.debug("[sanitize.dispatch_task] analyze partial entity_id=%s schema=%s", getattr(entity, "id", None), getattr(getattr(entity, "schema", None), "name", None))
                self.sanitize_entity(writer, entity)
                processed += 1
            log.debug("[sanitize.dispatch_task] analyze_partials_done had_partials=%s processed=%d", had_partials, processed)
            if not had_partials:
                log.info("[sanitize.dispatch_task] no analyze partials found, attempting on-the-fly ingest+analyze")
                emitted = self._ingest(ingest_db, task)
                log.debug("[sanitize.dispatch_task] ingest emitted_count=%d", len(emitted))
                if emitted:
                    updated_ids = self._analyze(analyze_db, ingest_db, task)
                    log.debug("[sanitize.dispatch_task] analyze updated_ids_count=%d", len(updated_ids))
                    for entity in analyze_db.partials():
                        log.debug("[sanitize.dispatch_task] post-analyze partial entity_id=%s schema=%s", getattr(entity, "id", None), getattr(getattr(entity, "schema", None), "name", None))
                        self.sanitize_entity(writer, entity)
                        processed += 1
                else:
                    log.warning("[sanitize.dispatch_task] ingest emitted no entities")
            writer.flush()
            log.debug("[sanitize.dispatch_task] writer flushed")
        except Exception as e:
            log.exception("[sanitize.dispatch_task] processing error: %s", e)
            raise
        log.info("[sanitize.dispatch_task] processed_count=%d", processed)
        try:
            self.dispatch_pipeline(task, payload=task.payload or {})
            log.debug("[sanitize.dispatch_task] dispatched pipeline continuation")
        except Exception as e:
            log.exception("[sanitize.dispatch_task] pipeline dispatch error: %s", e)
            raise
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
