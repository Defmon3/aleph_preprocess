import logging
from followthemoney import model
from followthemoney.types import registry
from followthemoney.namespace import Namespace
from ftmstore import get_dataset

log = logging.getLogger(__name__)

def _sanitize_html(text: str) -> str:
    # Keep your real implementation here
    return text.strip()

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
    sanitizer = None
    for entity in db.partials():
        if sanitizer is None or sanitizer.entity.id != entity.id:
            if sanitizer is not None:
                sanitizer.flush()
            sanitizer = Sanitizer(db, entity, {})
        sanitizer.feed(entity)
    if sanitizer is not None:
        sanitizer.flush()
