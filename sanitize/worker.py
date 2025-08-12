#!/usr/bin/env python3
"""
SPDX-License-Identifier: LicenseRef-NonCommercial-Only
© 2025 github.com/defmon3 — Non-commercial use only. Commercial use requires permission.

Dependencies:
    uv add loguru beautifulsoup4 lxml servicelayer ftmstore followthemoney click
"""

# sanitize/worker.py
from __future__ import annotations

import re
import logging
from bs4 import BeautifulSoup
from followthemoney import model
from followthemoney.types import registry
from ftmstore import Dataset
from servicelayer.worker import Worker
log = logging.getLogger(__name__)
OP_SANITIZE = "sanitize_html"


def _sanitize_html(text: str) -> str:
    """
    Minimal HTML → text suitable for Aleph indexing.

    :param text: Raw HTML
    :return: Collapsed plain text
    """
    soup = BeautifulSoup(text or "", "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    container = soup.body or soup
    raw = container.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", raw).strip()


class ServiceWorker(Worker):
    """
    Long-running stage worker:
    - reads FtM partials from ftmstore
    - sanitizes text fields from HTML
    - writes partials with `translatedText` (to match the example’s pipeline)
    - dispatches to the next stage
    """

    def _dispatch_next(self, task, entity_ids: list[str]) -> None:
        if not entity_ids:
            return
        pipeline = task.context.get("pipeline")
        if not pipeline:
            return
        next_stage = pipeline.pop(0)
        stage = task.job.get_stage(next_stage)
        ctx = task.context
        ctx["pipeline"] = pipeline
        log.info(f"Dispatching {len(entity_ids)} entities → {next_stage}")
        stage.queue({"entity_ids": entity_ids}, ctx)

    def _sanitize_entity(self, writer, entity) -> None:
        if not entity.schema.is_a("Analyzable"):
            return
        texts = entity.get_type_values(registry.text)
        if not texts:
            return
        log.debug(f"Sanitizing {entity}", )
        clean = " ".join(_sanitize_html(t) for t in texts if t)
        if not clean:
            return
        partial = model.make_entity(entity.schema)
        partial.id = entity.id
        # Mirror the example: write to `translatedText` so downstream indexers pick it up
        partial.add("translatedText", clean, quiet=True)
        writer.put(partial)

    def handle(self, task) -> None:
        log.debug(f"Worker handling task: {task}")
        dataset = None
        try:
            name = task.context.get("ftmstore", task.job.dataset.name)
            entity_ids = task.payload.get("entity_ids") or []
            dataset = Dataset(name, OP_SANITIZE)
            writer = dataset.bulk()

            for entity in dataset.partials(entity_id=entity_ids):
                try:
                    # Safely process each entity; if one fails, log it and continue.
                    self._sanitize_entity(writer, entity)
                except Exception:
                    log.exception(f"Failed to sanitize entity: {entity}")

            writer.flush()
            self._dispatch_next(task, entity_ids)
        except Exception:
            log.exception(f"Worker failed to handle task: {task}")
            raise
        finally:
            if dataset is not None:
                dataset.close()