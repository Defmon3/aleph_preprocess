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

from sanitize.worker import  get_worker

log = logging.getLogger(__name__)


@click.group()
def cli():
    configure_logging()


@cli.command()
@click.option("--dataset", required=False, help="Name of the dataset")
def worker(dataset):
    log.debug(f"Starting worker for dataset: {dataset}")
    worker = get_worker()
    worker.run()
    log.debug("Worker has stopped.")

if __name__ == "__main__":
    cli()
