import logging

from bs4 import BeautifulSoup
from followthemoney import model
from followthemoney.types import registry
from ftmstore import get_dataset
from servicelayer.cache import get_redis
from servicelayer.taskqueue import Worker, Task
import re
log = logging.getLogger(__name__)

STAGE_SANITIZE = "sanitize"


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

    def dispatch_task(self, task: Task) -> Task:
        db = get_dataset(task.collection_id, STAGE_SANITIZE)
        writer = db.bulk()
        for entity in db.partials():
            self._sanitize_entity(writer, entity)
        writer.flush()
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