import os
import json
import logging
from collections import deque
from ftmstore import get_dataset # noqa
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, get_rabbitmq_channel, queue_task
from sanitize.phone import process_text_mentions

log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"
__version__ = "4.1.3"

TEXT_KEYS = {"text", "html", "content", "body", "message", "description", "summary", "notes"}
PAYLOAD_SAMPLE_LEN = int(os.environ.get("SANITIZE_PAYLOAD_SAMPLE_LEN", "2000"))
MAX_TEXT_ITEMS = int(os.environ.get("SANITIZE_MAX_TEXT_ITEMS", "64"))
MAX_TEXT_LEN = int(os.environ.get("SANITIZE_MAX_TEXT_LEN", "500000"))

def _safe_sample(value, limit=PAYLOAD_SAMPLE_LEN):
    try:
        if isinstance(value, str):
            return (value[:limit] + ("…" if len(value) > limit else ""))
        return json.dumps(value)[:limit]
    except Exception:
        return "<unserializable>"

def _describe_payload(payload):
    try:
        if isinstance(payload, dict):
            keys = list(payload.keys())
            sample = {k: ("<str:{}>".format(len(payload[k])) if isinstance(payload[k], str) else type(payload[k]).__name__) for k in keys[:12]}
            return {"type": "dict", "keys": keys, "sample": sample}
        if isinstance(payload, list):
            return {"type": "list", "length": len(payload), "head_types": [type(x).__name__ for x in payload[:10]]}
        if isinstance(payload, str):
            return {"type": "str", "length": len(payload), "sample": _safe_sample(payload)}
        return {"type": type(payload).__name__}
    except Exception as e:
        return {"type": "unknown", "error": str(e)}

def _collect_texts(payload, max_items=MAX_TEXT_ITEMS, max_len=MAX_TEXT_LEN):
    texts = []
    reasons = []
    if isinstance(payload, str):
        s = payload.strip()
        if s:
            texts.append(s[:max_len])
        else:
            reasons.append("top_level_str_empty")
        return texts, reasons
    if not isinstance(payload, (dict, list, tuple)):
        reasons.append(f"unsupported_top_level:{type(payload).__name__}")
        return texts, reasons
    q = deque([payload])
    visits = 0
    while q and len(texts) < max_items:
        item = q.popleft()
        visits += 1
        if isinstance(item, dict):
            for k, v in item.items():
                if isinstance(v, str):
                    if k in TEXT_KEYS or len(v) > 20:
                        s = v.strip()
                        if s:
                            texts.append(s[:max_len])
                        else:
                            reasons.append(f"empty_string_key:{k}")
                elif isinstance(v, (dict, list, tuple)):
                    q.append(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                if isinstance(v, str):
                    s = v.strip()
                    if len(s) > 20:
                        texts.append(s[:max_len])
                    else:
                        reasons.append("short_string_skipped")
                elif isinstance(v, (dict, list, tuple)):
                    q.append(v)
    if not texts:
        reasons.append("no_text_found")
    return texts, reasons

class SanitizeWorker(Worker):
    def dispatch_pipeline(self, task: Task, payload: dict | None = None) -> None:
        pipeline = list(task.context.get("pipeline") or [])
        if not pipeline:
            log.info("[sanitize.dispatch_pipeline] no_next_stage")
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
        log.info("[sanitize.dispatch_pipeline] queued=%s remaining=%d", next_stage, len(pipeline))

    def dispatch_task(self, task: Task) -> Task:
        log.info("[sanitize.dispatch_task] enter task_id=%s collection_id=%s op=%s", task.task_id, task.collection_id, task.operation)
        name = task.context.get("ftmstore", task.collection_id)
        log.info("[sanitize.dispatch_task] ftmstore_dataset=%s", name)
        log.info("[sanitize.dispatch_task] context_keys=%s", list(task.context.keys()))

        try:
            dst = get_dataset(name, STAGE_SANITIZE)
            writer = dst.bulk()
            log.info("[sanitize.dispatch_task] dst_open_ok")
        except Exception as e:
            log.exception("[sanitize.dispatch_task] dataset_open_error: %s", e)
            self.dispatch_pipeline(task, payload=task.payload or {})
            log.info("[sanitize.dispatch_task] exit_early")
            return task

        desc = _describe_payload(task.payload)
        log.info("[sanitize.dispatch_task] payload_desc=%s", desc)

        texts, reasons = _collect_texts(task.payload)
        log.info("[sanitize.dispatch_task] text_chunks=%d reasons=%s", len(texts), reasons[:10])

        processed = 0
        for idx, t in enumerate(texts, start=1):
            log.info("[sanitize.dispatch_task] process_chunk idx=%d len=%d", idx, len(t))
            try:
                processed += process_text_mentions(
                    writer,
                    t,
                    link_entity_id=task.payload.get("id") if isinstance(task.payload, dict) else None,
                    link_document_id=task.payload.get("document") if isinstance(task.payload, dict) else None,
                )
            except Exception as e:
                log.exception("[sanitize.dispatch_task] chunk_error idx=%d: %s", idx, e)

        try:
            writer.flush()
            log.info("[sanitize.dispatch_task] writer_flushed")
        except Exception as e:
            log.exception("[sanitize.dispatch_task] writer_flush_error: %s", e)

        log.info("[sanitize.dispatch_task] processed_mentions=%d", processed)
        try:
            self.dispatch_pipeline(task, payload=task.payload or {})
        except Exception as e:
            log.exception("[sanitize.dispatch_task] pipeline_error: %s", e)
        log.info("[sanitize.dispatch_task] exit task_id=%s", task.task_id)
        return task

def get_worker(num_threads=None):
    log.info("SanitizeWorker active on stage: %s", STAGE_SANITIZE)
    return SanitizeWorker(
        queues=[STAGE_SANITIZE],
        conn=get_redis(),
        version=__version__,
        num_threads=num_threads,
        prefetch_count_mapping={STAGE_SANITIZE: 1},
    )
