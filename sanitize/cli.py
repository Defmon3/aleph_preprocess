#!/usr/bin/env python3
# /// script
# requires-python = "==3.12.9"
# dependencies = []
# ///

"""
SPDX-License-Identifier: LicenseRef-NonCommercial-Only
© 2025 github.com/defmon3 — Non-commercial use only. Commercial use requires permission.

Format docstrings according to PEP 287
File: cli.py
"""

import logging

import click
from servicelayer.logs import configure_logging

from sanitize.worker import get_worker

log = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """
    Root Click command group for the sanitize worker CLI.

    This initializes logging via ``servicelayer.logs.configure_logging()`` and
    serves as the parent for subcommands related to the sanitize pipeline
    worker.
    """
    configure_logging()


@cli.command()
@click.option(
    "--dataset",
    required=False,
    help="Name of the dataset to target; if omitted, all datasets in the queue are processed.",
)
def worker(dataset: str | None) -> None:
    """
    Start a sanitize-stage worker process.

    :param dataset: Optional dataset name to filter the worker's scope.
    :workflow:
        1. Log the dataset being targeted (if provided).
        2. Construct a ``SanitizeWorker`` via ``get_worker()``.
        3. Run the worker loop until stopped.
    :notes:
        - If ``dataset`` is not provided, the worker processes any sanitize
          tasks in its subscribed queues.
        - Logging output is controlled by the root CLI logging configuration.
    """
    log.debug(f"Starting worker for dataset: {dataset}")
    worker_instance = get_worker()
    worker_instance.run()
    log.debug("Worker has stopped.")


if __name__ == "__main__":
    cli()
