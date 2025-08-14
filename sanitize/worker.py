import logging
from banal import ensure_list
from ftmstore import get_dataset
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task, get_rabbitmq_channel, queue_task

log = logging.getLogger(__name__)

OP_SANITIZE = "sanitize"   # must match your pipeline stage name

class SanitizerWorker(Worker):
    """Subscribe to the 'sanitize' queue and process continuation tasks."""

    def _sanitize(self, ftmstore_dataset, task: Task):
        """Do your work here. Return a list of entity_ids to continue the pipeline."""
        log.debug(f"Sanitize task: {task}")
        entity_ids = set(task.payload.get("entity_ids", []))

        # Example: iterate the entities referenced by previous stage
        # If you want to stream all partials, drop the filter
        for entity in ftmstore_dataset.partials(entity_id=entity_ids or None):
            log.debug("Sanitize: %r", entity)
            # TODO: your sanitize logic
            # - read entity / fragments
            # - modify if needed
            # - write via ftmstore_dataset.bulk().put(...)
            pass

        return list(entity_ids)

    def dispatch_task(self, task: Task) -> Task:
        log.info(
            "Task [collection:%s]: op:%s task_id:%s priority:%s (started)",
            task.collection_id, task.operation, task.task_id, task.priority
        )

        # Open the right ftmstore dataset for this stage
        name = task.context.get("ftmstore", task.collection_id)
        ftmstore_dataset = get_dataset(name, task.operation)

        if task.operation == OP_SANITIZE:
            entity_ids = self._sanitize(ftmstore_dataset, task)
            self._dispatch_pipeline(task, {"entity_ids": entity_ids})

        log.info(
            "Task [collection:%s]: op:%s task_id:%s priority:%s (done)",
            task.collection_id, task.operation, task.task_id, task.priority
        )
        return task

    def _dispatch_pipeline(self, task: Task, payload: dict):
        """Forward to the next stage in the pipeline, exactly like ingest-file."""
        log.debug(f"Dispatching pipeline for task: {task.task_id} with payload: {payload}")
        pipeline = ensure_list(task.context.get("pipeline"))
        if not pipeline:
            return
        next_stage = pipeline.pop(0)
        context = dict(task.context)
        context["pipeline"] = pipeline

        queue_task(
            get_rabbitmq_channel(),
            get_redis(),
            task.collection_id,
            next_stage,
            task.job_id,
            context,
            **payload,
        )

def get_worker(num_threads=None):
    # Let’s mirror ingest-file’s QoS style if you want throttle later
    prefetch = {OP_SANITIZE: 1}
    log.info(f"Worker active, stages: {[OP_SANITIZE]}")
    return SanitizerWorker(
        queues=[OP_SANITIZE],
        conn=get_redis(),
        version="4.1.3",
        num_threads=num_threads,
        prefetch_count_mapping=prefetch,
    )
