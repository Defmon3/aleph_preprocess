import logging

from bs4 import BeautifulSoup
from followthemoney import model
from followthemoney.namespace import Namespace
from followthemoney.types import registry
from ftmstore import get_dataset
import re
log = logging.getLogger(__name__)


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


class Sanitizer:
    def __init__(self, dataset, entity, context):
        self.dataset = dataset
        self.ns = Namespace(context.get("namespace", dataset.name))
        self.entity = model.make_entity(entity.schema)
        self.entity.id = entity.id

    def feed(self, entity):
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
        partial = self.ns.apply(partial)
        self.dataset.bulk().put(partial)

    def flush(self):
        self.dataset.bulk().flush()


def run_sanitize(dataset_name):
    db = get_dataset(dataset_name, "sanitize")
    if db is None:
        log.error(f"Dataset {dataset_name} not found for sanitization.")
        return
    sanitizer = None
    for entity in db.partials():
        if sanitizer is None or sanitizer.entity.id != entity.id:
            if sanitizer is not None:
                sanitizer.flush()
            log.debug(f"Sanitizing entity: {entity}")
            sanitizer = Sanitizer(db, entity, {})
        else:
            log.debug(f"Could not sanitize : {entity}")
        sanitizer.feed(entity)

    if sanitizer is not None:
        sanitizer.flush()
